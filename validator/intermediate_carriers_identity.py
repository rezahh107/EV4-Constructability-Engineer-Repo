from __future__ import annotations

from typing import Any

from .intermediate_carriers_common import (
    CarrierDiagnostic, _as_dict, _as_list, _carrier, _diag, _intake_nodes,
    _node_ids, _review_source_ref, _review_unit_id, _sorted_unique_strings,
    _source_bundle_payload, _source_identity, _source_nodes, _unknown_ids,
    canonical_sha256,
)

def derive_architecture_identity_preservation(
    *,
    run_id: str,
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    constructability_review: dict[str, Any],
) -> dict[str, Any]:
    kind = "architecture_identity_preservation_result"
    diagnostics: list[CarrierDiagnostic] = []
    source_payload = _source_bundle_payload(source_bundle)

    if not run_id:
        diagnostics.append(_diag("CE_IDENTITY_RUN_ID_REQUIRED", kind, "invalid", "run_id is required.", "$.run_id"))
    if not intake or not source_payload or not constructability_review:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_SET_INCOMPLETE",
                kind,
                "invalid",
                "Canonical intake, trusted source bundle payload, and constructability review are required.",
            )
        )

    bundle = _as_dict(source_bundle.get("source_bundle"))
    transition = _as_dict(intake.get("project_gate_transition"))
    intake_source_ref = _as_dict(intake.get("source_repository_ref"))
    observed_bundle_id = bundle.get("bundle_id")
    expected_bundle_ids = {
        transition.get("source_bundle_id"),
        intake_source_ref.get("bundle_id"),
    }
    if not observed_bundle_id or expected_bundle_ids != {observed_bundle_id}:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_BUNDLE_ID_MISMATCH",
                kind,
                "invalid",
                "Trusted source bundle identity does not match the accepted intake transition.",
                "$.project_gate_transition.source_bundle_id",
                "architect_or_project_gate",
                [str(value) for value in expected_bundle_ids | {observed_bundle_id} if value],
            )
        )
    declared_hash = _as_dict(transition.get("source_bundle_hash")).get("value")
    observed_hash = canonical_sha256(bundle) if bundle else None
    if not declared_hash or declared_hash != observed_hash:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_BUNDLE_HASH_MISMATCH",
                kind,
                "invalid",
                "Trusted source bundle canonical hash does not match the accepted intake transition.",
                "$.project_gate_transition.source_bundle_hash.value",
                "architect_or_project_gate",
            )
        )

    intake_selected = _as_dict(intake.get("selected_architecture")).get("selected_candidate_id")
    source_selected = _as_dict(source_payload.get("architecture_identity")).get("selected_candidate_id")
    observed_selected = constructability_review.get("selected_candidate_id")
    if intake_selected != source_selected:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_SELECTED_CANDIDATE_CONFLICT",
                kind,
                "invalid",
                "Canonical intake and trusted source bundle disagree on selected_candidate_id.",
                "$.selected_candidate_id",
                "architect_or_project_gate",
            )
        )
    selected_matches = bool(intake_selected) and observed_selected == intake_selected == source_selected
    if not selected_matches:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SELECTED_CANDIDATE_MISMATCH",
                kind,
                "blocked",
                "CE review selected_candidate_id does not match the accepted Architect identity.",
                "$.constructability_review.selected_candidate_id",
                related_ids=[str(value) for value in (intake_selected, source_selected, observed_selected) if value],
            )
        )

    intake_classes = _sorted_unique_strings(
        _as_dict(_as_dict(intake.get("architect_intent_preserved")).get("class_intent")).get(
            "approved_class_names"
        )
        or []
    )
    source_classes = _sorted_unique_strings(
        _as_dict(_as_dict(source_payload.get("architect_intent")).get("class_intent")).get(
            "approved_class_names"
        )
        or []
    )
    observed_classes_value = constructability_review.get("approved_class_names")
    observed_classes = _sorted_unique_strings(observed_classes_value or [])
    if intake_classes != source_classes:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_CLASS_SET_CONFLICT",
                kind,
                "invalid",
                "Canonical intake and trusted source bundle disagree on approved class intent.",
                "$.approved_class_names",
                "architect_or_project_gate",
            )
        )
    if observed_classes_value is None:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_OBSERVED_CLASS_SET_MISSING",
                kind,
                "insufficient_evidence",
                "Constructability review does not carry the observed approved class set.",
                "$.constructability_review.approved_class_names",
            )
        )
    approved_class_set_match = observed_classes_value is not None and observed_classes == intake_classes == source_classes
    if observed_classes_value is not None and not approved_class_set_match:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_APPROVED_CLASS_SET_MISMATCH",
                kind,
                "blocked",
                "Observed approved classes differ from the accepted Architect class intent.",
                "$.constructability_review.approved_class_names",
                related_ids=sorted(set(intake_classes + observed_classes)),
            )
        )

    intake_nodes = _intake_nodes(intake)
    source_nodes = _source_nodes(source_bundle)
    intake_node_ids = _node_ids(intake_nodes, "source_node_id")
    source_node_ids = _node_ids(source_nodes, "node_id")
    review_nodes = [item for item in _as_list(constructability_review.get("reviewed_nodes")) if isinstance(item, dict)]
    observed_node_ids = _sorted_unique_strings(_review_source_ref(item) for item in review_nodes)
    if intake_node_ids != source_node_ids:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_BUILD_TREE_CONFLICT",
                kind,
                "invalid",
                "Canonical intake projection and trusted source Build Tree disagree.",
                "$.build_tree_identity",
                "architect_or_project_gate",
            )
        )
    build_tree_identity_match = observed_node_ids == intake_node_ids == source_node_ids and bool(intake_node_ids)
    if not build_tree_identity_match:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_BUILD_TREE_MISMATCH",
                kind,
                "blocked",
                "CE review units do not preserve the complete accepted Build Tree node identity set.",
                "$.constructability_review.reviewed_nodes",
                related_ids=sorted(set(intake_node_ids).symmetric_difference(observed_node_ids)),
            )
        )

    expected_unknowns = _unknown_ids(source_payload.get("unresolved_evidence"))
    intake_unknowns = _unknown_ids(intake.get("unresolved_evidence"))
    if expected_unknowns != intake_unknowns:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_SOURCE_UNKNOWN_SET_CONFLICT",
                kind,
                "invalid",
                "Canonical intake and trusted source bundle disagree on Architect Unknowns.",
                "$.architect_unknowns",
                "architect_or_project_gate",
            )
        )
    observed_unknowns_value = constructability_review.get("architect_unknowns")
    observed_unknowns = _unknown_ids(observed_unknowns_value)
    if expected_unknowns and observed_unknowns_value is None:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_ARCHITECT_UNKNOWNS_MISSING",
                kind,
                "insufficient_evidence",
                "Architect Unknowns exist but the CE review does not carry an observed Unknown set.",
                "$.constructability_review.architect_unknowns",
                related_ids=expected_unknowns,
            )
        )
    missing_unknowns = sorted(set(expected_unknowns) - set(observed_unknowns))
    extra_unknowns = sorted(set(observed_unknowns) - set(expected_unknowns))
    if missing_unknowns:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_ARCHITECT_UNKNOWN_REMOVED",
                kind,
                "blocked",
                "One or more Architect Unknowns were silently removed.",
                "$.constructability_review.architect_unknowns",
                related_ids=missing_unknowns,
            )
        )

    expected_forbidden = _sorted_unique_strings(intake.get("forbidden_work") or [])
    observed_forbidden_value = constructability_review.get("preserved_forbidden_work")
    observed_forbidden = _sorted_unique_strings(observed_forbidden_value or [])
    if expected_forbidden and observed_forbidden_value is None:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_FORBIDDEN_WORK_CARRIER_MISSING",
                kind,
                "insufficient_evidence",
                "CE review does not expose the preserved forbidden-work set.",
                "$.constructability_review.preserved_forbidden_work",
                related_ids=expected_forbidden,
            )
        )
    weakened_forbidden = sorted(set(expected_forbidden) - set(observed_forbidden))
    if weakened_forbidden:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_FORBIDDEN_WORK_WEAKENED",
                kind,
                "blocked",
                "CE review omitted one or more accepted forbidden-work boundaries.",
                "$.constructability_review.preserved_forbidden_work",
                related_ids=weakened_forbidden,
            )
        )

    unauthorized_redesign_units: list[str] = []
    for item in review_nodes:
        interrogation = _as_dict(item.get("interrogation_result"))
        change_required = interrogation.get("requires_structure_change") is True or interrogation.get(
            "requires_class_change"
        ) is True
        if change_required and interrogation.get("architect_decomposition_permission") is not True:
            unit_id = _review_unit_id(item)
            if unit_id:
                unauthorized_redesign_units.append(unit_id)
    if unauthorized_redesign_units:
        diagnostics.append(
            _diag(
                "CE_IDENTITY_ARCHITECTURE_REDESIGN_DETECTED",
                kind,
                "blocked",
                "A review unit requires class or structure change without Architect permission.",
                "$.constructability_review.reviewed_nodes",
                related_ids=unauthorized_redesign_units,
            )
        )

    traces = [
        {
            "architect_node_ref": source_ref,
            "architect_evidence_refs": _sorted_unique_strings(item.get("architect_evidence_refs") or []),
            "ce_review_unit_id": unit_id,
            "identity_unchanged": source_ref in intake_node_ids,
        }
        for item in review_nodes
        if (unit_id := _review_unit_id(item)) and (source_ref := _review_source_ref(item))
    ]
    traces.sort(key=lambda item: (item["architect_node_ref"], item["ce_review_unit_id"]))

    derived_data = {
        "selected_candidate": {
            "expected": intake_selected,
            "trusted_source": source_selected,
            "observed": observed_selected,
            "matches": selected_matches,
        },
        "approved_class_names": {
            "expected": intake_classes,
            "trusted_source": source_classes,
            "observed": observed_classes,
            "matches": approved_class_set_match,
        },
        "build_tree_identity": {
            "expected_node_ids": intake_node_ids,
            "trusted_source_node_ids": source_node_ids,
            "observed_node_ids": observed_node_ids,
            "matches_or_insufficient": build_tree_identity_match,
        },
        "architect_unknowns": {
            "expected_ids": expected_unknowns,
            "observed_ids": observed_unknowns,
            "missing_ids": missing_unknowns,
            "extra_ids": extra_unknowns,
        },
        "forbidden_work": {
            "expected_ids": expected_forbidden,
            "observed_ids": observed_forbidden,
            "missing_ids": weakened_forbidden,
        },
        "review_unit_trace_coverage": {
            "required_node_ids": intake_node_ids,
            "traced_node_ids": observed_node_ids,
            "missing_node_ids": sorted(set(intake_node_ids) - set(observed_node_ids)),
            "traces": traces,
        },
        "architecture_redesign_absent": not unauthorized_redesign_units,
    }
    return _carrier(
        kind,
        run_id,
        diagnostics,
        [
            _source_identity("architect_intake", intake, str(intake.get("schema_id") or "architect_intake")),
            _source_identity(
                "architect_source_bundle",
                source_bundle,
                str(_as_dict(source_bundle.get("source_bundle")).get("bundle_id") or "architect_source_bundle"),
            ),
            _source_identity(
                "constructability_review",
                constructability_review,
                str(constructability_review.get("review_id") or "constructability_review"),
            ),
        ],
        derived_data,
    )
