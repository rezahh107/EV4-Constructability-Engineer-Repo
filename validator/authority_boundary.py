from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .project_gate_exporter_core import ExportDiagnostic, ExporterError, _json_hash
from .project_gate_exporter_validation import _export_identity_hash
from .verified_project_gate_exporter import secure_build_export

_INSTALLED = False
_ORIGINAL_LEGACY_BUILD: Callable[..., Any] | None = None
_ORIGINAL_VERIFY_REPO_ARTIFACT: Callable[..., Any] | None = None


def _reject_legacy_orchestration_build(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    raise ExporterError(
        ExportDiagnostic(
            "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN",
            "legacy_preview_boundary",
            "Raw CE Stage Payload mappings and paths cannot enter the official export transaction.",
            "$.payload_path",
        )
    )


def _legacy_preview_build(*args: Any, **kwargs: Any) -> Any:
    if _ORIGINAL_LEGACY_BUILD is None:
        raise RuntimeError("Legacy preview boundary was not initialized")
    export, summary, diagnostics = _ORIGINAL_LEGACY_BUILD(*args, **kwargs)
    boundary = ExportDiagnostic(
        "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN",
        "legacy_preview_boundary",
        "Legacy CE Stage Payload was validated as a DECLARATION preview only; it cannot authorize Builder handoff.",
        "$.final_stage_bundle.payload.data",
    )
    carried = list(diagnostics)
    carried.append(boundary)
    export["handoff"] = {
        "target": "builder",
        "status": "blocked",
        "allowed": False,
        "failure_reasons": [item.as_dict() for item in carried],
        "blocking_diagnostics": [item.as_dict() for item in carried],
        "unresolved_evidence": list(
            export.get("final_stage_bundle", {})
            .get("payload", {})
            .get("data", {})
            .get("unresolved_evidence", [])
        ),
    }
    identity_hash = _export_identity_hash(export)
    export["export_id"] = f"ce-project-gate-export-{identity_hash}"
    export["stage_manifest"][-1]["output"]["artifact_hash"]["value"] = identity_hash
    summary = {
        **summary,
        "export_identity_hash": identity_hash,
        "export_hash": _json_hash(export),
        "authorization_valid": False,
        "assurance_kind": "DECLARATION",
        "verification_status": "MANUAL_UNVERIFIED",
        "official_builder_authorization": False,
    }
    return export, summary, tuple(carried)


def _validate_verified_successor_semantics(
    document: dict[str, Any],
    *,
    repo_root: Path | None = None,
    mode: str = "full",
) -> dict[str, Any]:
    """Adapt the historical validator result shape to the successor authority validator."""
    del mode
    from .verified_project_gate_exporter import validate_verified_payload_authority

    root = (repo_root or Path.cwd()).resolve()
    diagnostics = validate_verified_payload_authority(root, document)
    violations = [
        {
            "rule_id": item.code,
            "status": "blocked",
            "message": item.message,
            "location": item.path,
        }
        for item in diagnostics
    ]
    return {
        "passed": not diagnostics,
        "mode": "full",
        "schema_errors": [],
        "violations": violations,
        "successor_schema_id": document.get("schema_id"),
        "semantic_authority": "claim_policy_resolution",
    }


def _verify_repo_artifact_fail_closed(*args: Any, **kwargs: Any) -> Any:
    if _ORIGINAL_VERIFY_REPO_ARTIFACT is None:
        raise RuntimeError("Verified artifact adapter boundary was not initialized")
    from .verified_constructability import EvidenceVerificationError

    try:
        return _ORIGINAL_VERIFY_REPO_ARTIFACT(*args, **kwargs)
    except OSError as exc:
        source_ref = kwargs.get("source_ref", "unknown")
        raise EvidenceVerificationError(
            f"Verified artifact source is unavailable: {source_ref}"
        ) from exc


def install_authority_boundary() -> None:
    """Replace former raw-payload authority entrypoints with verified or preview-only paths."""
    global _INSTALLED, _ORIGINAL_LEGACY_BUILD, _ORIGINAL_VERIFY_REPO_ARTIFACT
    if _INSTALLED:
        return

    from . import ce_validation_transaction as transaction
    from . import project_gate_exporter as exporter
    from . import project_gate_exporter_orchestration as legacy_orchestration
    from . import verified_constructability
    from . import verified_project_gate_exporter as verified_exporter
    from .claim_policy_registry import mutable_claim_policies

    _ORIGINAL_LEGACY_BUILD = exporter.build_export
    _ORIGINAL_VERIFY_REPO_ARTIFACT = verified_constructability.verify_repo_artifact
    canonical_policies = mutable_claim_policies()
    verified_constructability.CLAIM_POLICIES = canonical_policies
    verified_exporter.CLAIM_POLICIES = canonical_policies
    transaction.secure_build_export = secure_build_export  # type: ignore[assignment]
    exporter.build_export = _legacy_preview_build  # type: ignore[assignment]
    legacy_orchestration.build_export = _reject_legacy_orchestration_build  # type: ignore[assignment]
    verified_constructability.verify_repo_artifact = _verify_repo_artifact_fail_closed  # type: ignore[assignment]
    verified_exporter.validate_document = _validate_verified_successor_semantics  # type: ignore[assignment]
    verified_exporter.VERIFIED_EXPORTER_ID = "ev4-producer-gate-export-validator"
    verified_exporter.VERIFIED_EXPORTER_VERSION = "1.0.0"
    _INSTALLED = True


def legacy_payload_authorization_is_closed() -> bool:
    from . import ce_validation_transaction as transaction
    from . import project_gate_exporter as exporter
    from . import project_gate_exporter_orchestration as legacy_orchestration
    from . import verified_constructability
    from . import verified_project_gate_exporter as verified_exporter
    from .claim_policy_registry import mutable_claim_policies

    return (
        transaction.secure_build_export is secure_build_export
        and exporter.build_export is _legacy_preview_build
        and legacy_orchestration.build_export is _reject_legacy_orchestration_build
        and verified_constructability.verify_repo_artifact is _verify_repo_artifact_fail_closed
        and verified_exporter.validate_document is _validate_verified_successor_semantics
        and verified_exporter.VERIFIED_EXPORTER_ID == "ev4-producer-gate-export-validator"
        and verified_exporter.VERIFIED_EXPORTER_VERSION == "1.0.0"
        and verified_constructability.CLAIM_POLICIES == mutable_claim_policies()
        and verified_exporter.CLAIM_POLICIES == mutable_claim_policies()
    )


def reject_raw_payload_path(path: Path) -> None:
    raise ExporterError(
        ExportDiagnostic(
            "CE_EXPORT_VERIFIED_PAYLOAD_CAPABILITY_REQUIRED",
            "verified_payload_boundary",
            f"Raw Payload path is non-authoritative: {path}",
            "$.verified_payload",
        )
    )
