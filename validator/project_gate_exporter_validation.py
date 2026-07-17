from __future__ import annotations

from pathlib import Path
from typing import Any

from . import project_gate_exporter_build as build
from .project_gate_exporter_core import ExportDiagnostic, ExporterError


def validate_stage_bundle_lock(repo_root: Path) -> None:
    """Run the pinned lock check with stable fail-closed diagnostics."""
    try:
        build.validate_stage_bundle_lock(repo_root)
    except ExporterError:
        raise
    except FileNotFoundError as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_STAGE_BUNDLE_LOCK_MISSING",
                "stage_bundle_contract_lock",
                f"Required Project Gate contract file is missing: {exc.filename}",
                str(exc.filename or repo_root),
                "repository_owner",
            )
        ) from exc
    except (OSError, TypeError, ValueError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_STAGE_BUNDLE_LOCK_INVALID",
                "stage_bundle_contract_lock",
                f"Failed to load the Stage Bundle contract or lock: {exc}",
                str(repo_root / "contracts/project-gate/stage-bundle.v1.lock.json"),
                "repository_owner",
            )
        ) from exc


def validate_stage_bundle_schema(repo_root: Path, bundle: dict[str, Any]) -> None:
    """Validate the common Stage Bundle without leaking file/parser exceptions."""
    try:
        build.validate_stage_bundle_schema(repo_root, bundle)
    except ExporterError:
        raise
    except FileNotFoundError as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_STAGE_BUNDLE_SCHEMA_MISSING",
                "stage_bundle_validation",
                f"Required Stage Bundle schema is missing: {exc.filename}",
                str(exc.filename or repo_root),
                "repository_owner",
            )
        ) from exc
    except (OSError, TypeError, ValueError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_STAGE_BUNDLE_SCHEMA_UNREADABLE",
                "stage_bundle_validation",
                f"Failed to load or validate the pinned Stage Bundle schema: {exc}",
                str(repo_root / "contracts/project-gate/stage-bundle.v1.schema.json"),
                "repository_owner",
            )
        ) from exc


def _export_identity_hash(export: dict[str, Any]) -> str:
    """Compute export identity only after validating the required manifest shape."""
    manifest = export.get("stage_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_MANIFEST_SHAPE_INVALID",
                "hash_self_verification",
                "stage_manifest must be a non-empty array.",
                "$.stage_manifest",
            )
        )
    last_stage = manifest[-1]
    if not isinstance(last_stage, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_MANIFEST_SHAPE_INVALID",
                "hash_self_verification",
                "The final stage manifest entry must be an object.",
                "$.stage_manifest[-1]",
            )
        )
    output = last_stage.get("output")
    artifact_hash = output.get("artifact_hash") if isinstance(output, dict) else None
    if not isinstance(artifact_hash, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_MANIFEST_SHAPE_INVALID",
                "hash_self_verification",
                "The final stage output must contain artifact_hash.",
                "$.stage_manifest[-1].output.artifact_hash",
            )
        )
    return build._export_identity_hash(export)


def verify_export_identity(export: dict[str, Any]) -> bool:
    """Return False for malformed or tampered untrusted exports; never raise."""
    try:
        manifest = export.get("stage_manifest")
        if not isinstance(manifest, list) or not manifest:
            return False
        last_stage = manifest[-1]
        if not isinstance(last_stage, dict):
            return False
        output = last_stage.get("output")
        if not isinstance(output, dict):
            return False
        artifact_hash = output.get("artifact_hash")
        if not isinstance(artifact_hash, dict):
            return False
        identity_hash = _export_identity_hash(export)
        return (
            export.get("export_id") == f"ce-project-gate-export-{identity_hash}"
            and artifact_hash.get("value") == identity_hash
        )
    except (ExporterError, KeyError, IndexError, TypeError, ValueError):
        return False
