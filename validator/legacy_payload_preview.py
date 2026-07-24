from __future__ import annotations

from typing import Any, Iterable

from .project_gate_exporter_core import ExportDiagnostic, _json_hash
from .project_gate_exporter_validation import _export_identity_hash

LEGACY_DIAGNOSTIC_CODE = "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN"


def apply_legacy_preview_boundary(
    export: dict[str, Any],
    summary: dict[str, Any],
    diagnostics: Iterable[ExportDiagnostic],
) -> tuple[dict[str, Any], dict[str, Any], tuple[ExportDiagnostic, ...]]:
    """Convert a validated historical raw Payload export into a diagnostic-only preview."""
    boundary = ExportDiagnostic(
        LEGACY_DIAGNOSTIC_CODE,
        "legacy_preview_boundary",
        "Legacy ev4-ce-stage-payload@1.0.0 is preview-only and cannot authorize Builder handoff.",
        "$.final_stage_bundle.payload.data",
    )
    carried = tuple([*diagnostics, boundary])
    unresolved = (
        export.get("final_stage_bundle", {})
        .get("payload", {})
        .get("data", {})
        .get("unresolved_evidence", [])
    )
    export["handoff"] = {
        "target": "builder",
        "status": "blocked",
        "allowed": False,
        "failure_reasons": [item.as_dict() for item in carried],
        "blocking_diagnostics": [item.as_dict() for item in carried],
        "unresolved_evidence": list(unresolved) if isinstance(unresolved, list) else [],
    }
    identity_hash = _export_identity_hash(export)
    export["export_id"] = f"ce-project-gate-export-{identity_hash}"
    stage_manifest = export.get("stage_manifest")
    if isinstance(stage_manifest, list) and stage_manifest:
        output = stage_manifest[-1].get("output") if isinstance(stage_manifest[-1], dict) else None
        artifact_hash = output.get("artifact_hash") if isinstance(output, dict) else None
        if isinstance(artifact_hash, dict):
            artifact_hash["value"] = identity_hash
    return (
        export,
        {
            **summary,
            "export_identity_hash": identity_hash,
            "export_hash": _json_hash(export),
            "authorization_valid": False,
            "assurance_kind": "DECLARATION",
            "verification_status": "MANUAL_UNVERIFIED",
            "official_builder_authorization": False,
        },
        carried,
    )
