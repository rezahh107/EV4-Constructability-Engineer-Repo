from __future__ import annotations

from typing import Any

from .intermediate_carriers_common import *  # noqa: F403

def derive_architecture_identity_preservation(
    *,
    run_id: str,
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    constructability_review: dict[str, Any],
) -> dict[str, Any]:
    kind = "architecture_identity_preservation_result"
    diagnostics: list[CarrierDiagnostic] = []
    source_payload = _bundle_payload(source_bundle)
    bundle = _bundle_object(source_bundle)

    if not run_id:
        diagnostics.append(_diag("CE_IDENTITY_RUN_ID_REQUIRED", kind, "invalid", "run_id is required.", "$.run_id"))
    if not intake or not bundle or not constructability_review:
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_SET_INCOMPLETE", kind, "invalid", "Canonical intake, trusted source bundle, and constructability review are required."))

    transition = _as_dict(intake.get("project_gate_transition"))
    source_ref = _as_dict(intake.get("source_repository_ref"))
    bundle_id = bundle.get("bundle_id")
    expected_bundle_ids = {transition.get("source_bundle_id"), source_ref.get("bundle_id")}
    if not bundle_id or expected_bundle_ids != {bundle_id}:
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_BUNDLE_ID_MISMATCH", kind, "invalid", "Trusted source bundle identity does not match the accepted intake.", "$.project_gate_transition.source_bundle_id", "architect_or_project_gate", [str(value) for value in expected_bundle_ids | {bundle_id} if value]))
    declared_hash = _as_dict(transition.get("source_bundle_hash")).get("value")
    if not bundle or declared_hash != canonical_sha256(bundle):
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_BUNDLE_HASH_MISMATCH", kind, "invalid", "Trusted source bundle canonical hash does not match the accepted intake.", "$.project_gate_transition.source_bundle_hash.value", "architect_or_project_gate"))

    intake_selected = _as_dict(intake.get("selected_architecture")).get("selected_candidate_id")
    source_selected = _as_dict(source_payload.get("architecture_identity")).get("selected_candidate_id")
    observed_selected = constructability_review.get("selected_candidate_id")
    selected_matches = bool(intake_selected) and observed_selected == intake_selected == source_selected
    if intake_selected != source_selected:
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_SELECTED_CANDIDATE_CONFLICT", kind, "invalid", "Canonical intake and trusted source bundle disagree on selected_candidate_id.", "$.selected_candidate_id", "architect_or_project_gate"))
    if not selected_matches:
        diagnostics.append(_diag("CE_IDENTITY_SELECTED_CANDIDATE_MISMATCH", kind, "blocked", "CE review selected_candidate_id differs from the accepted Architect identity.", "$.constructability_review.selected_candidate_id", related_ids=[str(value) for value in (intake_selected, source_selected, observed_selected) if value]))

    intake_classes = _strings(_as_dict(_as_dict(intake.get("architect_intent_preserved")).get("class_intent")).get("approved_class_names") or [])
    source_classes = _strings(_as_dict(_as_dict(source_payload.get("architect_intent")).get("class_intent")).get("approved_class_names") or [])
    observed_classes_value = constructability_review.get("approved_class_names")
    observed_classes = _strings(observed_classes_value or [])
    class_matches = observed_classes_value is not None and observed_classes == intake_classes == source_classes
    if intake_classes != source_classes:
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_CLASS_SET_CONFLICT", kind, "invalid", "Canonical intake and trusted source bundle disagree on approved classes.", "$.approved_class_names", "architect_or_project_gate"))
    if observed_classes_value is None:
        diagnostics.append(_diag("CE_IDENTITY_OBSERVED_CLASS_SET_MISSING", kind, "insufficient_evidence", "Constructability review does not carry the observed approved class set.", "$.constructability_review.approved_class_names"))
    elif not class_matches:
        diagnostics.append(_diag("CE_IDENTITY_APPROVED_CLASS_SET_MISMATCH", kind, "blocked", "Observed approved classes differ from the accepted class intent.", "$.constructability_review.approved_class_names", related_ids=sorted(set(intake_classes + observed_classes))))

    intake_node_ids = _strings(item.get("source_node_id") for item in _intake_nodes(intake))
    source_node_ids = _strings(item.get("node_id") for item in _source_nodes(source_bundle))
    review_nodes = _normalized_review_nodes(constructability_review)
    observed_node_ids = _strings(item.get("architect_node_ref") for item in review_nodes)
    build_tree_matches = bool(intake_node_ids) and observed_node_ids == intake_node_ids == source_node_ids
    if intake_node_ids != source_node_ids:
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_BUILD_TREE_CONFLICT", kind, "invalid", "Canonical intake projection and trusted source Build Tree disagree.", "$.build_tree_identity", "architect_or_project_gate"))
    if not build_tree_matches:
        diagnostics.append(_diag("CE_IDENTITY_BUILD_TREE_MISMATCH", kind, "blocked", "CE review units do not preserve the accepted Build Tree node set.", "$.constructability_review.reviewed_nodes", related_ids=sorted(set(intake_node_ids).symmetric_difference(observed_node_ids))))

    source_unknowns = _unknown_ids(source_payload.get("unresolved_evidence"))
    intake_unknowns = _unknown_ids(intake.get("unresolved_evidence"))
    observed_unknowns_value = constructability_review.get("architect_unknowns")
    observed_unknowns = _unknown_ids(observed_unknowns_value)
    missing_unknowns = sorted(set(source_unknowns) - set(observed_unknowns))
    extra_unknowns = sorted(set(observed_unknowns) - set(source_unknowns))
    if source_unknowns != intake_unknowns:
        diagnostics.append(_diag("CE_IDENTITY_SOURCE_UNKNOWN_SET_CONFLICT", kind, "invalid", "Canonical intake and trusted source bundle disagree on Architect Unknowns.", "$.architect_unknowns", "architect_or_project_gate"))
    if source_unknowns and observed_unknowns_value is None:
        diagnostics.append(_diag("CE_IDENTITY_ARCHITECT_UNKNOWNS_MISSING", kind, "insufficient_evidence", "Architect Unknowns exist but CE review does not carry them.", "$.constructability_review.architect_unknowns", related_ids=source_unknowns))
    if missing_unknowns:
        diagnostics.append(_diag("CE_IDENTITY_ARCHITECT_UNKNOWN_REMOVED", kind, "blocked", "One or more Architect Unknowns were silently removed.", "$.constructability_review.architect_unknowns", related_ids=missing_unknowns))

    expected_forbidden = _strings(intake.get("forbidden_work") or [])
    observed_forbidden_value = constructability_review.get("preserved_forbidden_work")
    observed_forbidden = _strings(observed_forbidden_value or [])
    weakened_forbidden = sorted(set(expected_forbidden) - set(observed_forbidden))
    if expected_forbidden and observed_forbidden_value is None:
        diagnostics.append(_diag("CE_IDENTITY_FORBIDDEN_WORK_CARRIER_MISSING", kind, "insufficient_evidence", "CE review does not expose preserved forbidden work.", "$.constructability_review.preserved_forbidden_work", related_ids=expected_forbidden))
    if weakened_forbidden:
        diagnostics.append(_diag("CE_IDENTITY_FORBIDDEN_WORK_WEAKENED", kind, "blocked", "CE review omitted accepted forbidden-work boundaries.", "$.constructability_review.preserved_forbidden_work", related_ids=weakened_forbidden))

    unauthorized_redesign: list[str] = []
    for item in review_nodes:
        interrogation = _as_dict(item.get("interrogation_result"))
        change_required = interrogation.get("requires_class_change") is True or interrogation.get("requires_structure_change") is True
        if change_required and interrogation.get("architect_decomposition_permission") is not True:
            unit_id = _review_unit_id(item)
            if unit_id:
                unauthorized_redesign.append(unit_id)
    if unauthorized_redesign:
        diagnostics.append(_diag("CE_IDENTITY_ARCHITECTURE_REDESIGN_DETECTED", kind, "blocked", "A review unit changes class or structure without Architect permission.", "$.constructability_review.reviewed_nodes", related_ids=unauthorized_redesign))

    traces = [{
        "architect_node_ref": str(item["architect_node_ref"]),
        "architect_evidence_refs": _strings(item.get("architect_evidence_refs") or []),
        "ce_review_unit_id": str(item["review_unit_id"]),
        "identity_unchanged": item.get("architect_node_ref") in intake_node_ids,
    } for item in review_nodes if item.get("review_unit_id") and item.get("architect_node_ref")]
    traces.sort(key=lambda item: (item["architect_node_ref"], item["ce_review_unit_id"]))

    derived_data = {
        "selected_candidate": {"expected": intake_selected, "trusted_source": source_selected, "observed": observed_selected, "matches": selected_matches},
        "approved_class_names": {"expected": intake_classes, "trusted_source": source_classes, "observed": observed_classes, "matches": class_matches},
        "build_tree_identity": {"expected_node_ids": intake_node_ids, "trusted_source_node_ids": source_node_ids, "observed_node_ids": observed_node_ids, "matches_or_insufficient": build_tree_matches},
        "architect_unknowns": {"expected_ids": source_unknowns, "observed_ids": observed_unknowns, "missing_ids": missing_unknowns, "extra_ids": extra_unknowns},
        "forbidden_work": {"expected_ids": expected_forbidden, "observed_ids": observed_forbidden, "missing_ids": weakened_forbidden},
        "review_unit_trace_coverage": {"required_node_ids": intake_node_ids, "traced_node_ids": observed_node_ids, "missing_node_ids": sorted(set(intake_node_ids) - set(observed_node_ids)), "traces": traces},
        "architecture_redesign_absent": not unauthorized_redesign,
        "payload_projection": {
            "selected_candidate_id": intake_selected,
            "selected_candidate_locked": selected_matches,
            "selected_candidate_id_unchanged": selected_matches,
            "approved_class_names": intake_classes,
            "approved_class_names_unchanged": class_matches,
            "build_tree_identity_preserved": build_tree_matches,
            "architect_unknowns_preserved": not missing_unknowns,
            "architect_forbidden_work_weakened": bool(weakened_forbidden),
            "review_unit_traces": traces,
        },
    }
    return _carrier(kind, run_id, diagnostics, [
        _source_identity("architect_intake", str(intake.get("schema_id") or "intake"), intake),
        _source_identity("architect_source_bundle", str(bundle_id or "bundle"), source_bundle),
        _source_identity("constructability_review", str(constructability_review.get("review_id") or "review"), constructability_review),
    ], derived_data)
