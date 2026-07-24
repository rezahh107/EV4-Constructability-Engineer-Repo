from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .artifact_parse_formats import (
    ArtifactAdapterError,
    _css_records,
    _find_json_subject,
    _html_records,
    _load_json_bytes,
    _subject_selector_matches,
    _svg_records,
)

def _require_match(observed: Any, expected: Any, field: str) -> None:
    if expected in (None, "", [], {}):
        raise ArtifactAdapterError(f"Claim semantics omit required field: {field}")
    if isinstance(expected, Mapping) and isinstance(observed, Mapping):
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ArtifactAdapterError(f"Parser-derived {field} disagrees with required semantics")
        return
    if observed != expected:
        raise ArtifactAdapterError(f"Parser-derived {field} disagrees with required semantics")


def _derive_from_json(
    claim_id: str, document: Mapping[str, Any], subject_ref: str
) -> dict[str, Any]:
    subject = _find_json_subject(document, subject_ref)
    if subject is None:
        raise ArtifactAdapterError("Bound subject is absent from the original JSON source")
    if claim_id == "geometry":
        layout = subject.get("layout") if isinstance(subject.get("layout"), Mapping) else {}
        model = layout.get("model") or subject.get("layout_model") or subject.get("display")
        anchors = layout.get("anchors") or subject.get("anchors") or {"subject_ref": subject_ref}
        if not isinstance(model, str) or not model or not isinstance(anchors, Mapping):
            raise ArtifactAdapterError("Original JSON source does not establish geometry")
        return {
            "anchor_model": dict(anchors),
            "coordinate_or_layout_model": model,
            "derivation_method": "ce-original-json-geometry-parser@1.0.0",
        }
    if claim_id == "overlay_strategy":
        overlay = subject.get("overlay") if isinstance(subject.get("overlay"), Mapping) else subject
        containment = overlay.get("containment_model") or overlay.get("container")
        positioning = overlay.get("positioning_model") or overlay.get("position")
        stacking = overlay.get("stacking_model") or overlay.get("z_index")
        if not all(value not in (None, "") for value in (containment, positioning, stacking)):
            raise ArtifactAdapterError("Original JSON source does not establish overlay semantics")
        return {
            "containment_model": str(containment),
            "positioning_model": str(positioning),
            "stacking_model": str(stacking),
            "derivation_method": "ce-original-json-overlay-parser@1.0.0",
        }
    if claim_id == "ui_control_path":
        control_path = subject.get("control_path") or subject.get("ui_control_path")
        if not isinstance(control_path, str) or not control_path:
            raise ArtifactAdapterError("UI-control path is absent from the original JSON source")
        return {
            "control_path": control_path,
            "control_path_segments": [part for part in control_path.split("/") if part],
        }
    if claim_id == "asset_source":
        asset_id = subject.get("asset_id") or subject.get("src")
        suitability = subject.get("subject_suitability")
        status = subject.get("suitability_status")
        if not isinstance(asset_id, str) or not asset_id:
            raise ArtifactAdapterError("Asset identity is absent from the original JSON source")
        if (
            status not in {"suitable", "approved"}
            or not isinstance(suitability, str)
            or not suitability
        ):
            raise ArtifactAdapterError("Asset exists but suitability is not derivable")
        return {
            "asset_id": asset_id,
            "intended_subject_ref": subject_ref,
            "suitability_status": status,
            "subject_suitability": suitability,
        }
    raise ArtifactAdapterError(f"No original JSON parser exists for {claim_id}")


def _derive_from_markup(
    claim_id: str, records: list[dict[str, Any]], subject_ref: str
) -> dict[str, Any]:
    subject = next((item for item in records if item.get("id") == subject_ref), None)
    if subject is None:
        raise ArtifactAdapterError("Bound subject is absent from the original markup source")
    attrs = subject.get("attrs") or {}
    style = subject.get("style") or {}
    if claim_id == "geometry":
        model = (
            attrs.get("data-layout-model")
            or style.get("display")
            or attrs.get("display")
        )
        if not isinstance(model, str) or not model:
            raise ArtifactAdapterError("Original markup source does not establish geometry")
        return {
            "anchor_model": {
                "subject_ref": subject_ref,
                "parent_ref": subject.get("parent_id"),
            },
            "coordinate_or_layout_model": model,
            "derivation_method": "ce-original-markup-geometry-parser@1.0.0",
        }
    if claim_id == "overlay_strategy":
        position = style.get("position") or attrs.get("data-positioning-model")
        z_index = style.get("z-index") or attrs.get("data-stacking-model")
        parent = subject.get("parent_id")
        if not position or z_index is None or not parent:
            raise ArtifactAdapterError(
                "Original markup source does not establish overlay semantics"
            )
        return {
            "containment_model": f"parent:{parent}",
            "positioning_model": str(position),
            "stacking_model": f"z-index:{z_index}",
            "derivation_method": "ce-original-markup-overlay-parser@1.0.0",
        }
    if claim_id == "ui_control_path":
        control_path = attrs.get("data-control-path") or attrs.get("name")
        if not isinstance(control_path, str) or not control_path:
            raise ArtifactAdapterError(
                "UI-control path is absent from the original markup source"
            )
        return {
            "control_path": control_path,
            "control_path_segments": [part for part in control_path.split("/") if part],
        }
    if claim_id == "asset_source":
        src = attrs.get("src") or attrs.get("href")
        suitability = attrs.get("data-subject-suitability")
        if not isinstance(src, str) or not src:
            raise ArtifactAdapterError("Asset identity is absent from the original markup source")
        if not isinstance(suitability, str) or not suitability:
            raise ArtifactAdapterError("Asset exists but suitability is not derivable")
        return {
            "asset_id": src,
            "intended_subject_ref": subject_ref,
            "suitability_status": "suitable",
            "subject_suitability": suitability,
        }
    raise ArtifactAdapterError(f"No original markup parser exists for {claim_id}")


def _derive_from_css(
    claim_id: str, records: list[dict[str, Any]], subject_ref: str
) -> dict[str, Any]:
    subject = next(
        (item for item in records if _subject_selector_matches(item["selector"], subject_ref)),
        None,
    )
    if subject is None:
        raise ArtifactAdapterError("Bound subject selector is absent from the original CSS source")
    style = subject["style"]
    if claim_id == "geometry":
        model = style.get("display") or style.get("position")
        if not model:
            raise ArtifactAdapterError("Original CSS source does not establish geometry")
        return {
            "anchor_model": {"selector": subject["selector"]},
            "coordinate_or_layout_model": model,
            "derivation_method": "ce-original-css-geometry-parser@1.0.0",
        }
    if claim_id == "overlay_strategy":
        position = style.get("position")
        z_index = style.get("z-index")
        if not position or z_index is None:
            raise ArtifactAdapterError("Original CSS source does not establish overlay semantics")
        return {
            "containment_model": f"selector:{subject['selector']}",
            "positioning_model": position,
            "stacking_model": f"z-index:{z_index}",
            "derivation_method": "ce-original-css-overlay-parser@1.0.0",
        }
    if claim_id == "asset_source":
        image = style.get("background-image")
        suitability = style.get("--ev4-subject-suitability")
        if not image:
            raise ArtifactAdapterError("Asset identity is absent from the original CSS source")
        if not suitability:
            raise ArtifactAdapterError("Asset exists but suitability is not derivable")
        return {
            "asset_id": image,
            "intended_subject_ref": subject_ref,
            "suitability_status": "suitable",
            "subject_suitability": suitability,
        }
    raise ArtifactAdapterError(f"No original CSS parser exists for {claim_id}")


def _compare(claim_id: str, facts: Mapping[str, Any], semantics: Mapping[str, Any]) -> None:
    if claim_id == "geometry":
        _require_match(
            facts.get("anchor_model"), semantics.get("anchor_model"), "anchor_model"
        )
        _require_match(
            facts.get("coordinate_or_layout_model"),
            semantics.get("coordinate_or_layout_model"),
            "coordinate_or_layout_model",
        )
        if (
            not isinstance(semantics.get("derivation_method"), str)
            or not semantics.get("derivation_method")
        ):
            raise ArtifactAdapterError("Claim semantics omit required field: derivation_method")
    elif claim_id == "overlay_strategy":
        for key in ("containment_model", "positioning_model", "stacking_model"):
            _require_match(facts.get(key), semantics.get(key), key)
        if (
            not isinstance(semantics.get("derivation_method"), str)
            or not semantics.get("derivation_method")
        ):
            raise ArtifactAdapterError("Claim semantics omit required field: derivation_method")
    elif claim_id == "ui_control_path":
        _require_match(
            facts.get("control_path"), semantics.get("control_path"), "control_path"
        )
    elif claim_id == "asset_source":
        _require_match(
            facts.get("subject_suitability"),
            semantics.get("subject_suitability"),
            "subject_suitability",
        )


def _regenerate(
    path: Path, claim_id: str, subject_ref: str
) -> tuple[dict[str, Any], str, bytes]:
    raw = path.read_bytes()
    suffix = path.suffix.casefold()
    if suffix == ".json":
        facts = _derive_from_json(claim_id, _load_json_bytes(raw), subject_ref)
        parser_id = f"ce-original-json-{claim_id}-parser@1.0.0"
    elif suffix in {".html", ".htm"}:
        facts = _derive_from_markup(claim_id, _html_records(raw), subject_ref)
        parser_id = f"ce-original-html-{claim_id}-parser@1.0.0"
    elif suffix == ".css":
        facts = _derive_from_css(claim_id, _css_records(raw), subject_ref)
        parser_id = f"ce-original-css-{claim_id}-parser@1.0.0"
    elif suffix == ".svg":
        facts = _derive_from_markup(claim_id, _svg_records(raw), subject_ref)
        parser_id = f"ce-original-svg-{claim_id}-parser@1.0.0"
    else:
        raise ArtifactAdapterError(
            f"Unsupported original-source format: {suffix or '<none>'}"
        )
    return facts, parser_id, raw


