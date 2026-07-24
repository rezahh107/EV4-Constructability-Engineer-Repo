from __future__ import annotations

import copy
from typing import Any

from .intermediate_carriers_common import *  # noqa: F403

def derive_review_units_and_interrogation_results(
    *,
    run_id: str,
    intake: dict[str, Any],
    constructability_review: dict[str, Any],
) -> dict[str, Any]:
    kind = "ce_review_units_and_interrogation_results"
    diagnostics: list[CarrierDiagnostic] = []
    required_nodes = _strings(item.get("source_node_id") for item in _intake_nodes(intake))
    raw_units = [item for item in _as_list(constructability_review.get("reviewed_nodes")) if isinstance(item, dict)]
    normalized_units: list[dict[str, Any]] = []
    unit_ids: list[str] = []
    source_refs: list[str] = []

    for index, item in enumerate(raw_units):
        unit_id = _review_unit_id(item)
        source_ref = _review_source_ref(item)
        if not unit_id:
            diagnostics.append(_diag("CE_REVIEW_UNIT_ID_MISSING", kind, "invalid", "Every review unit requires review_unit_id or node_id.", f"$.constructability_review.reviewed_nodes[{index}]"))
            continue
        if not source_ref:
            diagnostics.append(_diag("CE_REVIEW_UNIT_SOURCE_REF_MISSING", kind, "blocked", "Every review unit requires an Architect node reference.", f"$.constructability_review.reviewed_nodes[{index}]", related_ids=[unit_id]))
            continue
        unit_ids.append(unit_id)
        source_refs.append(source_ref)
        interrogation = item.get("interrogation_result")
        if not isinstance(interrogation, dict):
            diagnostics.append(_diag("CE_REVIEW_UNIT_INTERROGATION_MISSING", kind, "blocked", "Every review unit requires a structured interrogation_result.", f"$.constructability_review.reviewed_nodes[{index}].interrogation_result", related_ids=[unit_id]))
            interrogation = {}
        missing_fields = sorted(REQUIRED_INTERROGATION_FIELDS - set(interrogation))
        if missing_fields:
            diagnostics.append(_diag("CE_REVIEW_UNIT_INTERROGATION_FIELD_MISSING", kind, "invalid", "Interrogation result is missing fields required by the current review schema.", f"$.constructability_review.reviewed_nodes[{index}].interrogation_result", related_ids=[unit_id, *missing_fields]))
        if (interrogation.get("requires_class_change") is True or interrogation.get("requires_structure_change") is True) and "architect_decomposition_permission" not in interrogation:
            diagnostics.append(_diag("CE_REVIEW_UNIT_ARCHITECT_PERMISSION_FIELD_MISSING", kind, "invalid", "Class or structure change requires architect_decomposition_permission.", f"$.constructability_review.reviewed_nodes[{index}].interrogation_result", related_ids=[unit_id]))
        normalized = copy.deepcopy(item)
        normalized["review_unit_id"] = unit_id
        normalized["architect_node_ref"] = source_ref
        normalized["architect_evidence_refs"] = _strings(item.get("architect_evidence_refs") or [])
        normalized_units.append(normalized)

    duplicate_unit_ids = sorted({value for value in unit_ids if unit_ids.count(value) > 1})
    duplicate_source_refs = sorted({value for value in source_refs if source_refs.count(value) > 1})
    missing_source_nodes = sorted(set(required_nodes) - set(source_refs))
    orphan_review_units = sorted(set(source_refs) - set(required_nodes))
    if duplicate_unit_ids:
        diagnostics.append(_diag("CE_REVIEW_UNIT_DUPLICATE_ID", kind, "invalid", "Review-unit IDs must be unique.", "$.constructability_review.reviewed_nodes", related_ids=duplicate_unit_ids))
    if duplicate_source_refs:
        diagnostics.append(_diag("CE_REVIEW_UNIT_DUPLICATE_SOURCE_MAPPING", kind, "blocked", "Multiple review units map to one Architect node without an allowing rule.", "$.constructability_review.reviewed_nodes", related_ids=duplicate_source_refs))
    if missing_source_nodes:
        diagnostics.append(_diag("CE_REVIEW_UNIT_REQUIRED_NODE_UNREVIEWED", kind, "blocked", "Required Architect nodes lack CE review units.", "$.coverage.missing_source_nodes", related_ids=missing_source_nodes))
    if orphan_review_units:
        diagnostics.append(_diag("CE_REVIEW_UNIT_ORPHAN_SOURCE_NODE", kind, "blocked", "A CE review unit references an unknown Architect node.", "$.coverage.orphan_review_units", related_ids=orphan_review_units))

    normalized_units.sort(key=lambda item: (str(item.get("architect_node_ref", "")), str(item.get("review_unit_id", ""))))
    traces = [{"architect_node_ref": str(item["architect_node_ref"]), "architect_evidence_refs": _strings(item.get("architect_evidence_refs") or []), "ce_review_unit_id": str(item["review_unit_id"]), "identity_unchanged": item.get("architect_node_ref") in required_nodes} for item in normalized_units]
    derived_data = {
        "required_source_nodes": required_nodes,
        "review_units": normalized_units,
        "review_unit_traces": traces,
        "coverage": {
            "required_count": len(required_nodes),
            "reviewed_count": len(set(source_refs) & set(required_nodes)),
            "missing_source_nodes": missing_source_nodes,
            "orphan_review_units": orphan_review_units,
            "duplicate_review_unit_ids": duplicate_unit_ids,
            "duplicate_source_mappings": duplicate_source_refs,
            "traceability_complete": not (missing_source_nodes or orphan_review_units or duplicate_unit_ids or duplicate_source_refs),
        },
        "payload_projection": {"reviewed_nodes": normalized_units, "review_unit_traces": traces},
    }
    return _carrier(kind, run_id, diagnostics, [
        _source_identity("architect_intake", str(intake.get("schema_id") or "intake"), intake),
        _source_identity("constructability_review", str(constructability_review.get("review_id") or "review"), constructability_review),
    ], derived_data)
