from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from .project_gate_export import PIPELINE_ID, validate_producer_gate_export
from .project_gate_exporter_core import (
    HANDOFF_TARGET,
    PRODUCER_EXPORT_SCHEMA_ID,
    ExportDiagnostic,
    ExporterError,
    GitProvenance,
    _json_hash,
    _load_object,
    run_official_intake_validation,
    validate_builder_package,
    validate_identity_preservation,
    validate_payload_and_ce_semantics,
    verify_source_intake_binding,
)
from .project_gate_exporter_build import (
    _build_stage_bundle,
    _handoff_diagnostics,
    _stage_manifest,
)
from .project_gate_exporter_validation import (
    _export_identity_hash,
    validate_stage_bundle_schema,
    verify_export_identity,
)


def _safe_output_path(repo_root: Path, output_path: Path, overwrite: bool) -> Path:
    root = repo_root.resolve()
    resolved = output_path if output_path.is_absolute() else root / output_path
    resolved = resolved.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ExporterError(ExportDiagnostic("CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY", "output_safety", "Output path must remain inside the CE repository.", str(output_path), "repository_owner")) from exc
    if resolved.exists() and resolved.is_symlink():
        raise ExporterError(ExportDiagnostic("CE_EXPORT_OUTPUT_SYMLINK_FORBIDDEN", "output_safety", "Refusing to write through a symbolic link.", str(resolved), "repository_owner"))
    if resolved.exists() and not overwrite:
        raise ExporterError(ExportDiagnostic("CE_EXPORT_OUTPUT_EXISTS", "output_safety", "Output already exists; use --overwrite for an explicit replacement.", str(resolved), "repository_owner"))
    return resolved


def _atomic_write(path: Path, data: bytes) -> None:
    temp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            temp_name = None
        finally:
            if temp_name is not None and os.path.exists(temp_name):
                os.unlink(temp_name)
    except OSError as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_WRITE_FAILED",
                "atomic_write",
                f"Failed to write output file atomically: {exc}",
                str(path),
                "repository_owner",
            )
        ) from exc


def build_export(
    *,
    repo_root: Path,
    payload_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_path: Path,
    provenance: GitProvenance,
) -> tuple[dict[str, Any], dict[str, Any], tuple[ExportDiagnostic, ...]]:
    payload = _load_object(payload_path, "ce_payload_parse")
    intake = _load_object(source_intake_path, "source_intake_parse")
    source_bundle = _load_object(source_bundle_path, "source_bundle_parse")
    intake_report = run_official_intake_validation(repo_root, source_intake_path, source_bundle_path)
    source_hash = verify_source_intake_binding(payload, intake, source_intake_path)
    validate_payload_and_ce_semantics(repo_root, payload)
    validate_identity_preservation(payload, intake)
    builder_package_hash = validate_builder_package(payload)
    handoff_diagnostics = _handoff_diagnostics(payload, intake, source_bundle, provenance)
    handoff_allowed = not handoff_diagnostics
    insufficiency_codes = {
        "CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE",
        "CE_EXPORT_PAYLOAD_INSUFFICIENT_EVIDENCE",
        "CE_EXPORT_UNRESOLVED_EVIDENCE",
    }
    handoff_status = "successful" if handoff_allowed else (
        "insufficient_evidence" if any(item.code in insufficiency_codes for item in handoff_diagnostics) else "blocked"
    )
    bundle, bundle_hash = _build_stage_bundle(payload, intake, source_bundle, provenance, payload_path, source_intake_path, repo_root)
    validate_stage_bundle_schema(repo_root, bundle)
    manifest = _stage_manifest(payload, source_intake_path, source_hash, output_path, repo_root)
    export: dict[str, Any] = {
        "schema_version": PRODUCER_EXPORT_SCHEMA_ID,
        "export_id": "",
        "producer": {
            "stage": "ce",
            "repository": provenance.repository,
            "ref": provenance.ref,
            "commit_sha": provenance.commit_sha,
        },
        "pipeline_id": PIPELINE_ID,
        "run_id": payload["payload_identity"]["run_id"],
        "stage_manifest": manifest,
        "final_stage_bundle": bundle,
        "handoff": {
            "target": HANDOFF_TARGET,
            "status": handoff_status,
            "allowed": handoff_allowed,
            "failure_reasons": [item.as_dict() for item in handoff_diagnostics],
            "blocking_diagnostics": [item.as_dict() for item in handoff_diagnostics],
            "unresolved_evidence": list(payload.get("unresolved_evidence") or []),
        },
        "validation": {
            "schema_valid": True,
            "semantic_valid": True,
            "validator_id": "ev4-producer-gate-export-validator",
            "validator_version": "1.0.0",
            "diagnostics": [],
        },
        "acquisition_mode": {
            "mode": "producer_emitted_gate_artifact",
            "silent_fallback_allowed": False,
        },
    }
    identity_hash = _export_identity_hash(export)
    export["export_id"] = f"ce-project-gate-export-{identity_hash}"
    export["stage_manifest"][-1]["output"]["artifact_hash"]["value"] = identity_hash
    diagnostics = validate_producer_gate_export(repo_root, export)
    if diagnostics:
        first = diagnostics[0]
        raise ExporterError(ExportDiagnostic(first.code, "producer_export_validation", first.message, first.path))
    if not verify_export_identity(export):
        raise ExporterError(ExportDiagnostic("CE_EXPORT_IDENTITY_SELF_CHECK_FAILED", "hash_self_verification", "Export identity hash self-check failed."))
    summary = {
        "export_id": export["export_id"],
        "source_intake_hash": source_hash["value"],
        "source_intake_hash_scope": source_hash["scope"],
        "source_bundle_hash": _json_hash(source_bundle),
        "ce_payload_hash": _json_hash(payload),
        "builder_executable_package_hash": builder_package_hash,
        "bundle_hash": bundle_hash,
        "export_identity_hash": identity_hash,
        "export_hash": _json_hash(export),
        "producer_commit": provenance.commit_sha,
        "producer_ref": provenance.ref,
        "repository_dirty": provenance.dirty,
        "dirty_paths": list(provenance.dirty_paths),
        "handoff_target": HANDOFF_TARGET,
        "intake_validation_status": intake_report["status"],
    }
    return export, summary, tuple(handoff_diagnostics)
