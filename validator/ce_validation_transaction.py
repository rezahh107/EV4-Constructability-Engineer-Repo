from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .engine import validate_document
from .intermediate_carriers import (
    canonical_sha256,
    evaluate_ce_intermediate_validation,
)
from .project_gate_export import (
    CE_REPOSITORY,
    PIPELINE_ID,
    validate_producer_gate_export,
)
from .project_gate_synthetic import derive_stage_bundle_synthetic
from . import project_gate_exporter_orchestration as orchestration_module
from .project_gate_exporter_build import (
    _build_stage_bundle,
    _handoff_diagnostics,
    _stage_manifest,
)
from .project_gate_exporter_core import (
    BUILDER_PACKAGE_SCHEMA_ID,
    HANDOFF_TARGET,
    PRODUCER_EXPORT_SCHEMA_ID,
    ExportDiagnostic,
    ExporterError,
    GitProvenance,
    _json_hash,
    _reject_non_json_constant,
    validate_builder_package,
    validate_identity_preservation,
    validate_payload_and_ce_semantics,
    verify_source_intake_binding,
)
from .project_gate_exporter_validation import (
    _export_identity_hash,
    validate_stage_bundle_schema,
    verify_export_identity,
)

INTERMEDIATE_INPUTS_FILENAME = "ce-intermediate-export-inputs.json"
INTERMEDIATE_INPUTS_SCHEMA_ID = "ev4-ce-intermediate-export-inputs@1.0.0"


@dataclass(frozen=True)
class JsonSnapshot:
    path: Path
    value: dict[str, Any]
    raw_bytes: bytes
    read_error_code: str
    changed_error_code: str
    label: str


def _duplicate_keys_forbidden(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON object key is forbidden: {key}")
        value[key] = item
    return value


def capture_json_snapshot(
    path: Path,
    *,
    label: str,
    read_error_code: str,
    changed_error_code: str,
) -> JsonSnapshot:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ExporterError(
            ExportDiagnostic(
                read_error_code,
                "source_binding",
                f"Failed to read {label}: {exc}",
                str(path),
                "repository_owner",
            )
        ) from exc
    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_non_json_constant,
            object_pairs_hook=_duplicate_keys_forbidden,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INPUT_INVALID_JSON",
                "input_snapshot_parse",
                f"Invalid {label}: {exc}",
                str(path),
            )
        ) from exc
    if not isinstance(value, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INPUT_INVALID_JSON",
                "input_snapshot_parse",
                f"Expected JSON object in {path}",
                str(path),
            )
        )
    return JsonSnapshot(
        path=path,
        value=value,
        raw_bytes=raw,
        read_error_code=read_error_code,
        changed_error_code=changed_error_code,
        label=label,
    )


def assert_snapshot_unchanged(snapshot: JsonSnapshot) -> None:
    try:
        observed = snapshot.path.read_bytes()
    except OSError as exc:
        raise ExporterError(
            ExportDiagnostic(
                snapshot.read_error_code,
                "source_binding",
                f"Failed to re-read {snapshot.label}: {exc}",
                str(snapshot.path),
                "repository_owner",
            )
        ) from exc
    if observed != snapshot.raw_bytes:
        raise ExporterError(
            ExportDiagnostic(
                snapshot.changed_error_code,
                "source_binding",
                f"{snapshot.label} changed after its exact bytes were captured.",
                str(snapshot.path),
                "repository_owner",
            )
        )


def _owned_output(path: Path) -> bool:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_non_json_constant,
            object_pairs_hook=_duplicate_keys_forbidden,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False
    if not isinstance(value, dict):
        return False
    producer = value.get("producer") if isinstance(value.get("producer"), dict) else {}
    acquisition = (
        value.get("acquisition_mode")
        if isinstance(value.get("acquisition_mode"), dict)
        else {}
    )
    return (
        value.get("schema_version") == PRODUCER_EXPORT_SCHEMA_ID
        and value.get("pipeline_id") == PIPELINE_ID
        and producer.get("stage") == "ce"
        and producer.get("repository") == CE_REPOSITORY
        and acquisition.get("mode") == "producer_emitted_gate_artifact"
        and acquisition.get("silent_fallback_allowed") is False
    )


def safe_output_path(
    repo_root: Path,
    output_path: Path,
    overwrite: bool,
    *,
    protected_inputs: Iterable[Path] = (),
) -> Path:
    try:
        root = repo_root.resolve(strict=True)
        candidate = output_path if output_path.is_absolute() else root / output_path
        if candidate.is_symlink():
            raise ExporterError(
                ExportDiagnostic(
                    "CE_EXPORT_OUTPUT_SYMLINK_FORBIDDEN",
                    "output_safety",
                    "Refusing to write through a symbolic link.",
                    str(candidate),
                    "repository_owner",
                )
            )
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ExporterError(
                ExportDiagnostic(
                    "CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY",
                    "output_safety",
                    "Output path must remain inside the CE repository.",
                    str(output_path),
                    "repository_owner",
                )
            ) from exc
        if resolved == root or resolved.is_dir():
            raise ExporterError(
                ExportDiagnostic(
                    "CE_EXPORT_OUTPUT_IS_DIRECTORY",
                    "output_safety",
                    "Output path cannot be the repository root or a directory.",
                    str(resolved),
                    "repository_owner",
                )
            )
        for protected in protected_inputs:
            if resolved == protected.resolve(strict=False):
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_OUTPUT_ALIASES_INPUT",
                        "output_safety",
                        "Output path must not alias any transaction input.",
                        str(resolved),
                        "repository_owner",
                    )
                )
        if resolved.exists():
            if not overwrite:
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_OUTPUT_EXISTS",
                        "output_safety",
                        "Output already exists; use --overwrite for an explicit replacement.",
                        str(resolved),
                        "repository_owner",
                    )
                )
            if not _owned_output(resolved):
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_OUTPUT_NOT_OWNED",
                        "output_safety",
                        "Refusing to overwrite an existing target not owned by the CE exporter.",
                        str(resolved),
                        "repository_owner",
                    )
                )
        return resolved
    except ExporterError:
        raise
    except (OSError, RuntimeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_OUTPUT_PATH_INSPECTION_FAILED",
                "output_safety",
                f"Failed to inspect the output path safely: {exc}",
                str(output_path),
                "repository_owner",
            )
        ) from exc


def _synchronize_intake_stage_status(
    stage_manifest: list[dict[str, Any]],
    intake_report: dict[str, Any],
    intake: dict[str, Any],
) -> None:
    first = stage_manifest[0]
    if intake_report.get("status") == "valid":
        first["status"] = "complete"
        first["blockers"] = []
        first["unknowns"] = []
        return
    first["status"] = "insufficient_evidence"
    first["blockers"] = [{"code": "CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE"}]
    unknowns = intake.get("missing_evidence") or intake.get("unresolved_evidence") or []
    first["unknowns"] = list(unknowns) if isinstance(unknowns, list) else []


def _intermediate_inputs_path(source_intake_path: Path) -> Path:
    return source_intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)


def _validate_intermediate_inputs(
    value: dict[str, Any],
    *,
    expected_run_id: str,
    path: Path,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    schema_path = repo_root / "schemas/ce_intermediate_export_inputs.v1.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_INPUTS_SCHEMA_UNAVAILABLE",
                "intermediate_validation",
                f"Independent intermediate-input Schema is unavailable: {exc}",
                str(schema_path),
                "repository_owner",
            )
        ) from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: [str(part) for part in item.path],
    )
    if errors:
        error = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.path
        )
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_INPUTS_SCHEMA_INVALID",
                "intermediate_validation",
                error.message,
                location,
            )
        )
    if value.get("run_id") != expected_run_id:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_INPUTS_RUN_ID_MISMATCH",
                "intermediate_validation",
                "Intermediate input artifact run_id differs from the final Payload.",
                "$.run_id",
            )
        )
    review = value.get("constructability_review")
    strategy = value.get("implementation_strategy_map")
    package = value.get("builder_executable_package")
    if not isinstance(review, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_REVIEW_MISSING",
                "intermediate_validation",
                "Independent constructability_review is required.",
                "$.constructability_review",
            )
        )
    if strategy is not None and not isinstance(strategy, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_STRATEGY_INVALID",
                "intermediate_validation",
                "implementation_strategy_map must be an object or null.",
                "$.implementation_strategy_map",
            )
        )
    if package is not None and not isinstance(package, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_BUILDER_PACKAGE_INVALID",
                "intermediate_validation",
                "builder_executable_package must be an object or null.",
                "$.builder_executable_package",
            )
        )
    return review, strategy, package


def _status_surfaces(carrier: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    blockers: list[dict[str, str]] = []
    unknowns: list[dict[str, str]] = []
    for item in carrier.get("diagnostics") or []:
        if not isinstance(item, dict):
            continue
        row = {"code": str(item.get("code") or "CE_INTERMEDIATE_UNKNOWN")}
        severity = item.get("severity_or_status")
        if severity in {"blocked", "invalid"}:
            blockers.append(row)
        elif severity == "insufficient_evidence":
            unknowns.append(row)
    return blockers, unknowns


def _synchronize_intermediate_stage_status(
    stage_manifest: list[dict[str, Any]],
    transaction: dict[str, Any],
    run_id: str,
) -> None:
    carriers = transaction.get("carriers") if isinstance(transaction.get("carriers"), dict) else {}
    stage_map = {
        "identity_lock_validation": "architecture_identity_preservation_result",
        "node_action_interrogation": "ce_review_units_and_interrogation_results",
        "hidden_dependency_classification": "dependency_classification",
        "constructability_review": "dependency_classification",
        "implementation_strategy_determination": "implementation_strategy_coverage_result",
        "builder_package_gate": "implementation_strategy_coverage_result",
    }
    for stage in stage_manifest:
        if not isinstance(stage, dict):
            continue
        carrier_kind = stage_map.get(str(stage.get("stage_id")))
        carrier = carriers.get(carrier_kind) if carrier_kind else None
        if not isinstance(carrier, dict):
            continue
        status = str(carrier.get("status") or "invalid")
        if stage.get("stage_id") == "builder_package_gate":
            status = "complete" if transaction.get("builder_ready") is True else status
        stage["status"] = status
        stage["output"] = {
            "present": True,
            "artifact_ref": f"ce-intermediate-transaction:{run_id}#{carrier_kind}",
            "artifact_hash": {
                "algorithm": "sha256",
                "value": canonical_sha256(carrier),
                "scope": "canonical_json",
            },
        }
        blockers, unknowns = _status_surfaces(carrier)
        stage["blockers"] = blockers
        stage["unknowns"] = unknowns


def _transaction_authorization_diagnostics(
    repo_root: Path,
    export: dict[str, Any],
) -> list[ExportDiagnostic]:
    diagnostics: list[ExportDiagnostic] = []
    handoff = export.get("handoff") if isinstance(export.get("handoff"), dict) else {}
    bundle = export.get("final_stage_bundle") if isinstance(export.get("final_stage_bundle"), dict) else {}
    declared_synthetic = bundle.get("synthetic")
    derived_synthetic = derive_stage_bundle_synthetic(bundle)
    if not isinstance(declared_synthetic, bool) or declared_synthetic != derived_synthetic:
        diagnostics.append(
            ExportDiagnostic(
                "CE_TRX_SYNTHETIC_STATE_MISMATCH",
                "handoff_recomputation",
                "Declared synthetic state does not match validator-derived carried evidence.",
                "$.final_stage_bundle.synthetic",
            )
        )
    if handoff.get("allowed") is not True:
        return diagnostics

    payload_wrapper = bundle.get("payload") if isinstance(bundle.get("payload"), dict) else {}
    payload = payload_wrapper.get("data") if isinstance(payload_wrapper.get("data"), dict) else {}
    review = payload.get("constructability_review") if isinstance(payload.get("constructability_review"), dict) else {}
    package = payload.get("builder_executable_package") if isinstance(payload.get("builder_executable_package"), dict) else None
    if payload.get("payload_status") != "complete":
        diagnostics.append(ExportDiagnostic("CE_TRX_PAYLOAD_STATUS_NOT_COMPLETE", "handoff_recomputation", "Builder handoff requires payload_status=complete.", "$.final_stage_bundle.payload.data.payload_status"))
    if payload.get("unresolved_evidence"):
        diagnostics.append(ExportDiagnostic("CE_TRX_UNRESOLVED_EVIDENCE", "handoff_recomputation", "Builder handoff cannot coexist with unresolved CE evidence.", "$.final_stage_bundle.payload.data.unresolved_evidence"))
    if review.get("constructability_status") not in {"executable_ready", "executable_with_logged_assumption"}:
        diagnostics.append(ExportDiagnostic("CE_TRX_CONSTRUCTABILITY_NOT_EXECUTABLE", "handoff_recomputation", "Builder handoff requires an executable constructability result.", "$.final_stage_bundle.payload.data.constructability_review.constructability_status"))
    if payload.get("builder_package_emitted") is not True or package is None:
        diagnostics.append(ExportDiagnostic("CE_TRX_BUILDER_PACKAGE_NOT_EMITTED", "handoff_recomputation", "Builder handoff requires an emitted Builder Executable Package.", "$.final_stage_bundle.payload.data.builder_package_emitted"))
    elif (
        package.get("schema") != BUILDER_PACKAGE_SCHEMA_ID
        or package.get("builder_package_status") != "executable_ready"
        or package.get("builder_decisions_required") != 0
        or package.get("blocking_dependencies") != []
    ):
        diagnostics.append(ExportDiagnostic("CE_TRX_BUILDER_PACKAGE_NOT_ELIGIBLE", "handoff_recomputation", "Builder package status, decisions, blockers, or schema are not eligible.", "$.final_stage_bundle.payload.data.builder_executable_package"))
    if derived_synthetic:
        diagnostics.append(ExportDiagnostic("CE_TRX_SYNTHETIC_EVIDENCE_BLOCKED", "handoff_recomputation", "Validator-derived synthetic evidence cannot authorize Builder handoff.", "$.final_stage_bundle.synthetic"))
    stages = export.get("stage_manifest") if isinstance(export.get("stage_manifest"), list) else []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            diagnostics.append(ExportDiagnostic("CE_TRX_MANDATORY_STAGE_INVALID", "handoff_recomputation", "Every transaction stage must be a structured record.", f"$.stage_manifest[{index}]"))
            continue
        if stage.get("mandatory") is True and stage.get("status") != "complete":
            diagnostics.append(ExportDiagnostic("CE_TRX_MANDATORY_STAGE_INCOMPLETE", "handoff_recomputation", "All mandatory CE transaction stages must be complete before handoff.", f"$.stage_manifest[{index}].status"))
    if handoff.get("failure_reasons") or handoff.get("blocking_diagnostics") or handoff.get("unresolved_evidence"):
        diagnostics.append(ExportDiagnostic("CE_TRX_ALLOWED_HANDOFF_HAS_FAILURE_SURFACES", "handoff_recomputation", "Allowed handoff cannot contain failure, blocking, or unresolved surfaces.", "$.handoff"))
    semantic = validate_document(payload, repo_root=repo_root, mode="full") if payload else {"passed": False}
    if not semantic.get("passed"):
        diagnostics.append(ExportDiagnostic("CE_TRX_CE_SEMANTIC_VALIDATION_FAILED", "handoff_recomputation", "Official CE semantic validation does not authorize this handoff.", "$.final_stage_bundle.payload.data"))
    return diagnostics


def validate_transaction_artifact(
    repo_root: Path,
    export: dict[str, Any],
) -> list[ExportDiagnostic]:
    return _transaction_authorization_diagnostics(repo_root, export)


def secure_build_export(
    *,
    repo_root: Path,
    payload_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_path: Path,
    provenance: GitProvenance,
) -> tuple[dict[str, Any], dict[str, Any], tuple[ExportDiagnostic, ...]]:
    intermediate_path = _intermediate_inputs_path(source_intake_path)
    if output_path.resolve(strict=False) == intermediate_path.resolve(strict=False):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_OUTPUT_ALIASES_INPUT",
                "output_safety",
                "Output path must not alias the intermediate input artifact.",
                str(output_path),
                "repository_owner",
            )
        )

    payload_snapshot = capture_json_snapshot(payload_path, label="CE Stage Payload", read_error_code="CE_EXPORT_PAYLOAD_READ_FAILED", changed_error_code="CE_EXPORT_PAYLOAD_CHANGED_DURING_EXPORT")
    intake_snapshot = capture_json_snapshot(source_intake_path, label="source Architect intake", read_error_code="CE_EXPORT_SOURCE_INTAKE_READ_FAILED", changed_error_code="CE_EXPORT_SOURCE_INTAKE_CHANGED_DURING_EXPORT")
    bundle_snapshot = capture_json_snapshot(source_bundle_path, label="source Architect bundle", read_error_code="CE_EXPORT_SOURCE_BUNDLE_READ_FAILED", changed_error_code="CE_EXPORT_SOURCE_BUNDLE_CHANGED_DURING_EXPORT")
    intermediate_snapshot = capture_json_snapshot(intermediate_path, label="independent CE intermediate inputs", read_error_code="CE_EXPORT_INTERMEDIATE_INPUTS_READ_FAILED", changed_error_code="CE_EXPORT_INTERMEDIATE_INPUTS_CHANGED_DURING_EXPORT")

    payload = payload_snapshot.value
    intake = intake_snapshot.value
    source_bundle = bundle_snapshot.value
    run_id = str((payload.get("payload_identity") or {}).get("run_id") or "")
    review, strategy, raw_package = _validate_intermediate_inputs(
        intermediate_snapshot.value,
        expected_run_id=run_id,
        path=intermediate_path,
        repo_root=repo_root,
    )

    with orchestration_module._private_validation_snapshots(
        intake_snapshot.raw_bytes,
        bundle_snapshot.raw_bytes,
    ) as (validator_intake_path, validator_bundle_path):
        intake_report = orchestration_module.run_official_intake_validation(
            repo_root,
            validator_intake_path,
            validator_bundle_path,
        )

    source_hash = verify_source_intake_binding(
        payload,
        intake,
        source_intake_path,
        intake_snapshot.raw_bytes,
    )

    intermediate_result = evaluate_ce_intermediate_validation(
        run_id=run_id,
        intake=intake,
        source_bundle=(
            source_bundle
            if isinstance(source_bundle.get("source_bundle"), dict)
            else {"source_bundle": source_bundle}
        ),
        constructability_review=review,
        implementation_strategy_map=strategy,
        builder_executable_package=raw_package,
        final_payload=payload,
        repo_root=repo_root,
    )
    if intermediate_result.get("fidelity_passed") is not True:
        first = next(
            (
                item
                for item in intermediate_result.get("diagnostics") or []
                if isinstance(item, dict)
            ),
            {},
        )
        raise ExporterError(
            ExportDiagnostic(
                str(first.get("code") or "CE_EXPORT_INTERMEDIATE_VALIDATION_FAILED"),
                "intermediate_validation",
                str(first.get("message") or "Authoritative CE intermediate validation failed."),
                str(first.get("path_or_source_ref") or "$"),
            )
        )

    validate_payload_and_ce_semantics(repo_root, payload)
    validate_identity_preservation(payload, intake)
    builder_package_hash = validate_builder_package(payload)
    handoff_diagnostics = _handoff_diagnostics(payload, intake, source_bundle, provenance)
    if not intermediate_result.get("builder_ready") and not handoff_diagnostics:
        handoff_diagnostics.append(
            ExportDiagnostic(
                "CE_EXPORT_INTERMEDIATE_BUILDER_NOT_READY",
                "intermediate_validation",
                "Intermediate validation did not establish Builder readiness.",
                "$.builder_ready",
            )
        )
    handoff_allowed = not handoff_diagnostics
    insufficiency_codes = {
        "CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE",
        "CE_EXPORT_PAYLOAD_INSUFFICIENT_EVIDENCE",
        "CE_EXPORT_UNRESOLVED_EVIDENCE",
    }
    handoff_status = (
        "successful"
        if handoff_allowed
        else "insufficient_evidence"
        if any(item.code in insufficiency_codes for item in handoff_diagnostics)
        else "blocked"
    )
    bundle, bundle_hash = _build_stage_bundle(
        payload,
        intake,
        source_bundle,
        provenance,
        payload_path,
        source_intake_path,
        repo_root,
    )
    validate_stage_bundle_schema(repo_root, bundle)
    manifest = _stage_manifest(
        payload,
        source_intake_path,
        source_hash,
        output_path,
        repo_root,
    )
    _synchronize_intake_stage_status(manifest, intake_report, intake)
    _synchronize_intermediate_stage_status(manifest, intermediate_result, run_id)

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
        "run_id": run_id,
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
    transaction_diagnostics = validate_transaction_artifact(repo_root, export)
    if transaction_diagnostics:
        raise ExporterError(transaction_diagnostics[0])
    if not verify_export_identity(export):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_IDENTITY_SELF_CHECK_FAILED",
                "hash_self_verification",
                "Export identity hash self-check failed.",
            )
        )
    for snapshot in (
        payload_snapshot,
        intake_snapshot,
        bundle_snapshot,
        intermediate_snapshot,
    ):
        assert_snapshot_unchanged(snapshot)

    summary = {
        "export_id": export["export_id"],
        "source_intake_hash": source_hash["value"],
        "source_intake_hash_scope": source_hash["scope"],
        "source_bundle_hash": _json_hash(source_bundle),
        "ce_payload_hash": _json_hash(payload),
        "payload_snapshot_sha256": hashlib.sha256(payload_snapshot.raw_bytes).hexdigest(),
        "source_intake_snapshot_sha256": hashlib.sha256(intake_snapshot.raw_bytes).hexdigest(),
        "source_bundle_snapshot_sha256": hashlib.sha256(bundle_snapshot.raw_bytes).hexdigest(),
        "intermediate_inputs_snapshot_sha256": hashlib.sha256(intermediate_snapshot.raw_bytes).hexdigest(),
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
        "intermediate_transaction_status": intermediate_result["transaction_status"],
        "intermediate_fidelity_passed": intermediate_result["fidelity_passed"],
        "intermediate_builder_ready": intermediate_result["builder_ready"],
        "artifact_integrity_status": "valid",
        "semantic_validation_status": "valid",
        "authorization_valid": handoff_allowed,
    }
    return export, summary, tuple(handoff_diagnostics)
