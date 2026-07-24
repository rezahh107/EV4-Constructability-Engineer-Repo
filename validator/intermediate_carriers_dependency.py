from __future__ import annotations

from typing import Any, Iterable

from .intermediate_carriers_common import *  # noqa: F403

def _dependency_record(unit_id: str, source_ref: str, dependency_kind: str, classification: str, reason: str, evidence_refs: Iterable[str] = (), downstream_owner: str = "ce") -> dict[str, Any]:
    rule_id = DEPENDENCY_RULES[dependency_kind]
    return {"review_unit_id": unit_id, "architect_node_ref": source_ref, "dependency_id": f"{unit_id}:{rule_id}:{dependency_kind}", "dependency_kind": dependency_kind, "rule_id": rule_id, "classification": classification, "evidence_refs": _strings(evidence_refs), "reason": reason, "downstream_owner": downstream_owner}

def _classify_unit(unit: dict[str, Any]) -> tuple[list[dict[str, Any]], list[CarrierDiagnostic]]:
    kind = "dependency_classification"
    diagnostics: list[CarrierDiagnostic] = []
    unit_id = str(unit.get("review_unit_id"))
    source_ref = str(unit.get("architect_node_ref"))
    interrogation = _as_dict(unit.get("interrogation_result"))
    evidence_refs = _strings(unit.get("architect_evidence_refs") or [])
    records: list[dict[str, Any]] = []

    if interrogation.get("geometry_required") is not True:
        records.append(_dependency_record(unit_id, source_ref, "geometry", "not_applicable", "Geometry is not required."))
    elif interrogation.get("geometry_proven") is True and isinstance(interrogation.get("geometry_proof"), dict):
        records.append(_dependency_record(unit_id, source_ref, "geometry", "satisfied", "Geometry proof is present.", evidence_refs))
    elif interrogation.get("geometry_proven") is True:
        records.append(_dependency_record(unit_id, source_ref, "geometry", "blocking", "geometry_proven lacks geometry_proof."))
        diagnostics.append(_diag("CE_DEPENDENCY_GEOMETRY_PROOF_MISSING", kind, "blocked", "geometry_proven requires geometry_proof.", f"$.review_units[{unit_id}].geometry_proof", related_ids=[unit_id]))
    else:
        records.append(_dependency_record(unit_id, source_ref, "geometry", "insufficient_evidence", "Required geometry is not proven.", downstream_owner="user_or_ce"))

    if interrogation.get("asset_required") is not True:
        records.append(_dependency_record(unit_id, source_ref, "asset", "not_applicable", "Asset evidence is not required."))
    elif interrogation.get("asset_source_present") is True or interrogation.get("placeholder_policy_present") is True:
        records.append(_dependency_record(unit_id, source_ref, "asset", "satisfied", "Asset source or placeholder policy is present.", evidence_refs))
    else:
        records.append(_dependency_record(unit_id, source_ref, "asset", "insufficient_evidence", "Required asset source or placeholder policy is missing.", downstream_owner="user_or_ce"))

    if interrogation.get("overlay_strategy_required") is not True:
        records.append(_dependency_record(unit_id, source_ref, "overlay", "not_applicable", "Overlay strategy is not required."))
    elif interrogation.get("overlay_strategy_proven") is True and isinstance(interrogation.get("overlay_strategy"), dict):
        records.append(_dependency_record(unit_id, source_ref, "overlay", "non_blocking_obligation", "Proven overlay strategy must be implemented.", evidence_refs, "builder"))
    else:
        records.append(_dependency_record(unit_id, source_ref, "overlay", "blocking", "Required overlay strategy is not proven."))

    responsive = interrogation.get("responsive_behavior")
    if interrogation.get("action_targets_responsive") is not True:
        records.append(_dependency_record(unit_id, source_ref, "responsive", "not_applicable", "Action does not target responsive behavior."))
    elif responsive == "evidence_backed":
        records.append(_dependency_record(unit_id, source_ref, "responsive", "non_blocking_obligation", "Evidence-backed responsive behavior transfers downstream.", evidence_refs, "responsive"))
    elif responsive == "blocked":
        records.append(_dependency_record(unit_id, source_ref, "responsive", "blocking", "Responsive behavior is explicitly blocked.", downstream_owner="responsive"))
    elif responsive == "not_applicable":
        records.append(_dependency_record(unit_id, source_ref, "responsive", "blocking", "Responsive-targeted action cannot be not_applicable.", downstream_owner="responsive"))
        diagnostics.append(_diag("CE_DEPENDENCY_RESPONSIVE_NOT_APPLICABLE_UNSUPPORTED", kind, "blocked", "Responsive-targeted action cannot be not_applicable.", f"$.review_units[{unit_id}].responsive_behavior", related_ids=[unit_id]))
    else:
        records.append(_dependency_record(unit_id, source_ref, "responsive", "insufficient_evidence", "Responsive behavior remains unknown.", downstream_owner="responsive"))

    if interrogation.get("interaction_implied") is not True:
        records.append(_dependency_record(unit_id, source_ref, "interaction", "not_applicable", "No interaction is implied."))
    elif interrogation.get("interaction_approved") is True:
        records.append(_dependency_record(unit_id, source_ref, "interaction", "non_blocking_obligation", "Approved interaction must be implemented.", evidence_refs, "builder"))
    else:
        records.append(_dependency_record(unit_id, source_ref, "interaction", "blocking", "Implied interaction lacks Architect approval.", downstream_owner="architect"))

    if interrogation.get("dynamic_loop_implied") is not True:
        records.append(_dependency_record(unit_id, source_ref, "dynamic_loop", "not_applicable", "No Dynamic Loop is implied."))
    elif interrogation.get("dynamic_loop_approved") is True and isinstance(interrogation.get("dynamic_loop_binding_map"), dict):
        records.append(_dependency_record(unit_id, source_ref, "dynamic_loop", "non_blocking_obligation", "Approved Dynamic Loop binding must be implemented.", evidence_refs, "builder"))
    elif interrogation.get("dynamic_loop_approved") is True:
        records.append(_dependency_record(unit_id, source_ref, "dynamic_loop", "blocking", "Approved Dynamic Loop lacks binding map."))
    else:
        records.append(_dependency_record(unit_id, source_ref, "dynamic_loop", "blocking", "Implied Dynamic Loop lacks Architect approval.", downstream_owner="architect"))

    if interrogation.get("accessibility_claimed") is not True:
        records.append(_dependency_record(unit_id, source_ref, "accessibility", "not_applicable", "No accessibility claim is made."))
    elif interrogation.get("accessibility_evidenced") is True:
        records.append(_dependency_record(unit_id, source_ref, "accessibility", "non_blocking_obligation", "Accessibility evidence and obligation must be preserved.", evidence_refs, "builder_and_responsive"))
    else:
        records.append(_dependency_record(unit_id, source_ref, "accessibility", "blocking", "Accessibility claim lacks evidence."))

    if interrogation.get("exact_ui_control_path_used") is not True:
        records.append(_dependency_record(unit_id, source_ref, "exact_ui_control_path", "not_applicable", "No exact UI path is asserted."))
    elif interrogation.get("ui_control_evidence_present") is True and isinstance(interrogation.get("ui_control_evidence"), dict):
        records.append(_dependency_record(unit_id, source_ref, "exact_ui_control_path", "non_blocking_obligation", "Exact UI path evidence must be preserved.", evidence_refs, "builder"))
    elif interrogation.get("ui_control_evidence_present") is True:
        records.append(_dependency_record(unit_id, source_ref, "exact_ui_control_path", "blocking", "UI evidence flag lacks structured evidence."))
    else:
        records.append(_dependency_record(unit_id, source_ref, "exact_ui_control_path", "insufficient_evidence", "Exact UI path lacks current evidence.", downstream_owner="user_or_ce"))

    for field, dependency_kind in (("requires_class_change", "class_change"), ("requires_structure_change", "structure_change")):
        if interrogation.get(field) is not True:
            records.append(_dependency_record(unit_id, source_ref, dependency_kind, "not_applicable", f"{dependency_kind} is not required."))
        elif interrogation.get("architect_decomposition_permission") is True:
            records.append(_dependency_record(unit_id, source_ref, dependency_kind, "non_blocking_obligation", f"Architect-authorized {dependency_kind} must be implemented.", downstream_owner="builder"))
        else:
            records.append(_dependency_record(unit_id, source_ref, dependency_kind, "blocking", f"{dependency_kind} lacks Architect permission.", downstream_owner="architect"))
    return records, diagnostics

def derive_dependency_classification(*, run_id: str, review_carrier: dict[str, Any], constructability_review: dict[str, Any]) -> dict[str, Any]:
    kind = "dependency_classification"
    diagnostics: list[CarrierDiagnostic] = []
    if review_carrier.get("carrier_kind") != "ce_review_units_and_interrogation_results":
        diagnostics.append(_diag("CE_DEPENDENCY_REVIEW_CARRIER_INVALID", kind, "invalid", "Carrier 2 is required.", "$.review_carrier"))
    elif review_carrier.get("status") != "complete":
        severity = review_carrier.get("status") if review_carrier.get("status") in LEGAL_STATUSES else "invalid"
        diagnostics.append(_diag("CE_DEPENDENCY_REVIEW_CARRIER_INCOMPLETE", kind, str(severity), "Carrier 2 must be complete before dependency classification can be complete.", "$.review_carrier.status"))
    units = [item for item in _as_list(_as_dict(review_carrier.get("derived_data")).get("review_units")) if isinstance(item, dict)]
    classifications: list[dict[str, Any]] = []
    for unit in units:
        records, unit_diagnostics = _classify_unit(unit)
        classifications.extend(records)
        diagnostics.extend(unit_diagnostics)
    classifications.sort(key=lambda item: (item["review_unit_id"], item["dependency_kind"], item["dependency_id"]))
    ids = [item["dependency_id"] for item in classifications]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    if duplicate_ids:
        diagnostics.append(_diag("CE_DEPENDENCY_DUPLICATE_CLASSIFICATION", kind, "invalid", "Dependency classifications must be unique.", "$.classifications", related_ids=duplicate_ids))
    derived_blockers = _strings(item["dependency_id"] for item in classifications if item["classification"] == "blocking")
    unresolved = _strings(item["dependency_id"] for item in classifications if item["classification"] == "insufficient_evidence")
    obligations = _strings(item["dependency_id"] for item in classifications if item["classification"] == "non_blocking_obligation")
    declared_blockers = _strings(constructability_review.get("blocking_dependencies") or [])
    missing_declared = sorted(set(derived_blockers) - set(declared_blockers))
    extra_declared = sorted(set(declared_blockers) - set(derived_blockers))
    if missing_declared:
        diagnostics.append(_diag("CE_DEPENDENCY_BLOCKING_SUPPRESSED", kind, "blocked", "Derived blockers are missing from constructability_review.blocking_dependencies.", "$.constructability_review.blocking_dependencies", related_ids=missing_declared))
    if extra_declared:
        diagnostics.append(_diag("CE_DEPENDENCY_DECLARED_BLOCKER_UNTRACEABLE", kind, "blocked", "Declared blockers are not traceable to current interrogation semantics.", "$.constructability_review.blocking_dependencies", related_ids=extra_declared))
    if derived_blockers:
        diagnostics.append(_diag("CE_DEPENDENCY_BLOCKING_PRESENT", kind, "blocked", "One or more dependency dimensions are blocking.", "$.classifications", related_ids=derived_blockers))
    elif unresolved:
        diagnostics.append(_diag("CE_DEPENDENCY_EVIDENCE_UNRESOLVED", kind, "insufficient_evidence", "One or more dependency dimensions require evidence.", "$.classifications", related_ids=unresolved))
    expected_count = len(units) * len(DEPENDENCY_RULES)
    if len(classifications) != expected_count:
        diagnostics.append(_diag("CE_DEPENDENCY_CLASSIFICATION_COVERAGE_INCOMPLETE", kind, "invalid", "Every review unit requires exactly one classification per dependency dimension.", "$.classifications"))
    derived_data = {
        "review_unit_ids": _strings(item.get("review_unit_id") for item in units),
        "dependency_dimensions": sorted(DEPENDENCY_RULES),
        "classifications": classifications,
        "blocking_dependencies": derived_blockers,
        "non_blocking_obligations": obligations,
        "unresolved_dependencies": unresolved,
        "coverage": {"review_unit_count": len(units), "expected_classification_count": expected_count, "actual_classification_count": len(classifications), "every_review_unit_classified": len(classifications) == expected_count, "classification_traceability_complete": all(item.get("architect_node_ref") for item in classifications)},
        "payload_projection": {"blocking_dependencies": derived_blockers, "required_unresolved_ids": unresolved, "required_evidence_refs": _strings(ref for item in classifications for ref in item.get("evidence_refs", []))},
    }
    return _carrier(kind, run_id, diagnostics, [
        _source_identity("review_carrier", "ce_review_units_and_interrogation_results", review_carrier),
        _source_identity("constructability_review", str(constructability_review.get("review_id") or "review"), constructability_review),
    ], derived_data)
