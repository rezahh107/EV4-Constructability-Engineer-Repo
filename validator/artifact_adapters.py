from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ArtifactAdapterError(ValueError):
    """Raised when a candidate artifact cannot be parsed by a supported adapter."""


@dataclass(frozen=True)
class ArtifactBinding:
    claim_id: str
    subject_ref: str
    selected_candidate_id: str
    source_bundle_id: str
    intake_digest: str


_SCHEMA_BY_CLAIM = {
    "geometry": "ev4-ce-geometry-extract@1.0.0",
    "overlay_strategy": "ev4-ce-overlay-extract@1.0.0",
    "ui_control_path": "ev4-ce-ui-control-extract@1.0.0",
    "asset_source": "ev4-ce-asset-extract@1.0.0",
}
_ALLOWED_ROLES_BY_CLAIM = {
    "geometry": {"geometry_extract", "layout_extract", "architect_geometry_extract"},
    "overlay_strategy": {"overlay_extract", "stacking_extract"},
    "ui_control_path": {"ui_control_extract"},
    "asset_source": {"asset_inventory_extract", "asset_suitability_extract"},
}



def _load_structured(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactAdapterError(
            "Unsupported artifact format; a repository-defined JSON extract is required"
        ) from exc
    if not isinstance(value, dict):
        raise ArtifactAdapterError("Artifact extract must be a JSON object")
    return value, raw


def _validate_binding(document: Mapping[str, Any], binding: ArtifactBinding) -> None:
    observed = document.get("binding")
    if not isinstance(observed, Mapping):
        raise ArtifactAdapterError("Artifact extract has no canonical binding record")
    expected = {
        "claim_id": binding.claim_id,
        "subject_ref": binding.subject_ref,
        "selected_candidate_id": binding.selected_candidate_id,
        "source_bundle_id": binding.source_bundle_id,
        "intake_digest": binding.intake_digest,
    }
    if any(observed.get(key) != value for key, value in expected.items()):
        raise ArtifactAdapterError(
            "Artifact extract is bound to another claim, node, candidate, intake, or source bundle"
        )


def _facts(document: Mapping[str, Any]) -> dict[str, Any]:
    facts = document.get("facts")
    if not isinstance(facts, Mapping):
        raise ArtifactAdapterError("Artifact extract has no structured facts")
    return dict(facts)


def _require_equal(
    facts: Mapping[str, Any],
    semantics: Mapping[str, Any],
    fields: tuple[str, ...],
) -> None:
    missing = [field for field in fields if field not in facts]
    if missing:
        raise ArtifactAdapterError(
            "Artifact extract omits required derived facts: " + ", ".join(missing)
        )
    mismatched = [field for field in fields if facts.get(field) != semantics.get(field)]
    if mismatched:
        raise ArtifactAdapterError(
            "Derived artifact facts do not match required claim semantics: "
            + ", ".join(mismatched)
        )


def _geometry(document: Mapping[str, Any], semantics: Mapping[str, Any]) -> dict[str, Any]:
    facts = _facts(document)
    _require_equal(
        facts,
        semantics,
        ("anchor_model", "coordinate_or_layout_model", "derivation_method"),
    )
    anchors = facts.get("anchor_model")
    if not isinstance(anchors, Mapping) or not anchors:
        raise ArtifactAdapterError("Geometry extract contains no structured anchors")
    return facts


def _overlay(document: Mapping[str, Any], semantics: Mapping[str, Any]) -> dict[str, Any]:
    facts = _facts(document)
    _require_equal(
        facts,
        semantics,
        (
            "containment_model",
            "positioning_model",
            "stacking_model",
            "derivation_method",
        ),
    )
    if not all(isinstance(facts.get(key), str) and facts.get(key) for key in (
        "containment_model",
        "positioning_model",
        "stacking_model",
    )):
        raise ArtifactAdapterError("Overlay extract is structurally incomplete")
    return facts


def _ui_control(document: Mapping[str, Any], semantics: Mapping[str, Any]) -> dict[str, Any]:
    facts = _facts(document)
    _require_equal(facts, semantics, ("control_path",))
    path_segments = facts.get("control_path_segments")
    if not isinstance(path_segments, list) or not path_segments:
        raise ArtifactAdapterError("UI-control extract has no parsed control-path segments")
    return facts


def _asset(document: Mapping[str, Any], semantics: Mapping[str, Any]) -> dict[str, Any]:
    facts = _facts(document)
    if facts.get("intended_subject_ref") != document.get("binding", {}).get("subject_ref"):
        raise ArtifactAdapterError("Asset extract is not suitable for the bound subject")
    if facts.get("suitability_status") not in {"suitable", "approved"}:
        raise ArtifactAdapterError("Asset suitability was not derived by the source adapter")
    suitability = facts.get("subject_suitability")
    if not isinstance(suitability, str) or not suitability:
        raise ArtifactAdapterError("Asset extract has no derived suitability rationale")
    expected = semantics.get("subject_suitability")
    if isinstance(expected, str) and expected and expected != suitability:
        raise ArtifactAdapterError(
            "Derived asset suitability does not match the required claim semantics"
        )
    asset_id = facts.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id:
        raise ArtifactAdapterError("Asset extract has no asset identity")
    return facts


_ADAPTERS = {
    "geometry": _geometry,
    "overlay_strategy": _overlay,
    "ui_control_path": _ui_control,
    "asset_source": _asset,
}


def evaluate_artifact_source(
    *,
    claim_id: str,
    path: Path,
    semantics: Mapping[str, Any],
    binding: ArtifactBinding,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_schema = _SCHEMA_BY_CLAIM.get(claim_id)
    adapter = _ADAPTERS.get(claim_id)
    if expected_schema is None or adapter is None:
        raise ArtifactAdapterError(f"No repository artifact adapter exists for {claim_id}")
    document, raw = _load_structured(path)
    if document.get("schema_id") != expected_schema:
        raise ArtifactAdapterError(
            f"Unsupported artifact Schema for {claim_id}: {document.get('schema_id')!r}"
        )
    source_role = document.get("source_role")
    if source_role not in _ALLOWED_ROLES_BY_CLAIM[claim_id]:
        raise ArtifactAdapterError(
            f"Unsupported artifact source role for {claim_id}: {source_role!r}"
        )
    _validate_binding(document, binding)
    facts = adapter(document, semantics)
    source_metadata = {
        "adapter_id": f"ce-{claim_id}-artifact-adapter@1.0.0",
        "schema_id": expected_schema,
        "source_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "source_role": str(source_role),
    }
    return facts, source_metadata


__all__ = [
    "ArtifactAdapterError",
    "ArtifactBinding",
    "evaluate_artifact_source",
]
