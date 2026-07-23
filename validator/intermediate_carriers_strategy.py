from __future__ import annotations

import copy
from typing import Any

from .intermediate_carriers_common import *  # noqa: F403

def derive_implementation_strategy_coverage(
    *,
    run_id: str,
    identity_carrier: dict[str, Any],
    review_carrier: dict[str, Any],
    dependency_carrier: dict[str, Any],
    implementation_strategy_map: dict[str, Any] | None,
    builder_executable_package: dict[str, Any] | None,
) -> dict[str, Any]:
    kind = "implementation_strategy_coverage_result"
    diagnostics: list[CarrierDiagnostic] = []
    for expected_kind, carrier, code in (
        ("architecture_identity_preservation_result", identity_carrier, "CE_STRATEGY_COVERAGE_IDENTITY_CARRIER_INVALID"),
        ("ce_review_units_and_interrogation_results", review_carrier, "CE_STRATEGY_COVERAGE_REVIEW_CARRIER_INVALID"),
        ("dependency_classification", dependency_carrier, "CE_STRATEGY_COVERAGE_DEPENDENCY_CARRIER_INVALID"),
    ):
        if carrier.get("carrier_kind") != expected_kind:
            diagnostics.append(_diag(code, kind, "invalid", f"Expected {expected_kind}.", "$.source_carriers"))
        elif carrier.get("status") != "complete":
            severity = carrier.get("status") if carrier.get("status") in LEGAL_STATUSES else "invalid"
            diagnostics.append(_diag(f"{code}_INCOMPLETE", kind, str(severity), f"{expected_kind} must be complete before ready Strategy coverage.", "$.source_carriers"))

    required_units = _strings(_as_dict(review_carrier.get("derived_data")).get("required_source_nodes") or [])
    expected_candidate = _as_dict(_as_dict(identity_carrier.get("derived_data")).get("selected_candidate")).get("expected")
    dep_data = _as_dict(dependency_carrier.get("derived_data"))
    classifications = [item for item in _as_list(dep_data.get("classifications")) if isinstance(item, dict)]

    if not isinstance(implementation_strategy_map, dict):
        blockers = _strings(dep_data.get("blocking_dependencies") or [])
        unresolved = _strings(dep_data.get("unresolved_dependencies") or [])
        absence_reason = "strategy_unavailable_due_to_blocking_dependencies" if blockers else "strategy_unavailable_due_to_insufficient_evidence" if unresolved else "strategy_missing_without_repository_supported_absence_basis"
        diagnostics.append(_diag("CE_STRATEGY_COVERAGE_STRATEGY_ABSENT", kind, "insufficient_evidence" if unresolved else "blocked", "Implementation Strategy Map is absent.", "$.implementation_strategy_map", related_ids=blockers + unresolved))
        return _carrier(kind, run_id, diagnostics, [
            _source_identity("identity_carrier", "architecture_identity_preservation_result", identity_carrier),
            _source_identity("review_carrier", "ce_review_units_and_interrogation_results", review_carrier),
            _source_identity("dependency_carrier", "dependency_classification", dependency_carrier),
        ], {
            "strategy_present": False,
            "absence_reason": absence_reason,
            "strategy_identity": None,
            "strategy_map": None,
            "coverage_by_review_unit": [],
            "coverage_by_dependency": [],
            "uncovered_review_units": required_units,
            "uncovered_dependencies": sorted(set(blockers + unresolved)),
            "builder_decisions_remaining": None,
            "first_safe_batch_status": "not_available",
            "payload_projection": {"implementation_strategy_map": None, "builder_package_not_emitted_reason": absence_reason, "required_unresolved_ids": unresolved},
        })

    strategy_map = copy.deepcopy(implementation_strategy_map)
    strategies = [item for item in _as_list(strategy_map.get("strategies")) if isinstance(item, dict)]
    strategies.sort(key=lambda item: (str(item.get("node_id", "")), str(item.get("strategy_id", ""))))
    strategy_map["strategies"] = strategies
    strategy_id = strategy_map.get("strategy_map_id")
    if strategy_map.get("selected_candidate_id") != expected_candidate:
        diagnostics.append(_diag("CE_STRATEGY_COVERAGE_SELECTED_CANDIDATE_MISMATCH", kind, "blocked", "Strategy selected_candidate_id differs from Carrier 1.", "$.implementation_strategy_map.selected_candidate_id"))

    by_unit: dict[str, list[dict[str, Any]]] = {}
    builder_decisions = 0
    for index, strategy in enumerate(strategies):
        node_id = strategy.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_NODE_ID_MISSING", kind, "invalid", "Every strategy requires node_id.", f"$.implementation_strategy_map.strategies[{index}].node_id"))
            continue
        by_unit.setdefault(node_id, []).append(strategy)
        decisions = strategy.get("builder_decisions_required")
        if not isinstance(decisions, int):
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_BUILDER_DECISION_COUNT_INVALID", kind, "invalid", "builder_decisions_required must be an integer.", f"$.implementation_strategy_map.strategies[{index}].builder_decisions_required", related_ids=[node_id]))
        else:
            builder_decisions += max(decisions, 0)
            if decisions != 0:
                diagnostics.append(_diag("CE_STRATEGY_COVERAGE_BUILDER_DECISION_REMAINS", kind, "blocked", "Ready Strategy requires zero Builder decisions.", f"$.implementation_strategy_map.strategies[{index}].builder_decisions_required", related_ids=[node_id]))
        if strategy.get("architect_amendment_required") is True:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_ARCHITECT_AMENDMENT_HIDDEN", kind, "blocked", "Strategy cannot hide an Architect amendment requirement.", f"$.implementation_strategy_map.strategies[{index}].architect_amendment_required", related_ids=[node_id]))
        if _contains_unresolved_decision(strategy):
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_UNRESOLVED_DECISION_HIDDEN", kind, "blocked", "Strategy contains an unresolved decision.", f"$.implementation_strategy_map.strategies[{index}]", related_ids=[node_id]))

    missing_units = sorted(set(required_units) - set(by_unit))
    orphan_units = sorted(set(by_unit) - set(required_units))
    if missing_units:
        diagnostics.append(_diag("CE_STRATEGY_COVERAGE_REVIEW_UNIT_UNCOVERED", kind, "blocked", "Every required review unit must have Strategy coverage.", "$.coverage_by_review_unit", related_ids=missing_units))
    if orphan_units:
        diagnostics.append(_diag("CE_STRATEGY_COVERAGE_ORPHAN_STRATEGY", kind, "invalid", "Strategy references an unknown review unit.", "$.coverage_by_review_unit", related_ids=orphan_units))

    coverage_by_unit = [{"review_unit_id": unit_id, "strategy_ids": _strings(item.get("strategy_id") for item in by_unit.get(unit_id, [])), "covered": bool(by_unit.get(unit_id))} for unit_id in required_units]
    coverage_by_dependency: list[dict[str, Any]] = []
    uncovered_dependencies: list[str] = []
    for item in classifications:
        dependency_id = str(item.get("dependency_id"))
        unit_id = str(item.get("review_unit_id"))
        classification = item.get("classification")
        requires_strategy = classification == "non_blocking_obligation"
        covered = bool(by_unit.get(unit_id)) if requires_strategy else classification in {"satisfied", "not_applicable"}
        if classification in {"blocking", "insufficient_evidence"} or (requires_strategy and not covered):
            uncovered_dependencies.append(dependency_id)
        coverage_by_dependency.append({"dependency_id": dependency_id, "review_unit_id": unit_id, "classification": classification, "strategy_ids": _strings(value.get("strategy_id") for value in by_unit.get(unit_id, [])), "covered": covered})
    coverage_by_dependency.sort(key=lambda item: item["dependency_id"])
    if uncovered_dependencies:
        has_blocking = any(item.get("classification") == "blocking" and item.get("dependency_id") in uncovered_dependencies for item in classifications)
        has_insufficient = any(item.get("classification") == "insufficient_evidence" and item.get("dependency_id") in uncovered_dependencies for item in classifications)
        diagnostics.append(_diag("CE_STRATEGY_COVERAGE_DEPENDENCY_UNCOVERED", kind, "blocked" if has_blocking else "insufficient_evidence" if has_insufficient else "blocked", "Dependencies or obligations remain uncovered.", "$.coverage_by_dependency", related_ids=uncovered_dependencies))

    first_safe_batch_status = "not_available"
    if not isinstance(builder_executable_package, dict):
        diagnostics.append(_diag("CE_STRATEGY_COVERAGE_BUILDER_PACKAGE_MISSING", kind, "blocked", "Ready Strategy coverage requires Builder package confirmation and first safe batch.", "$.builder_executable_package"))
    else:
        package = builder_executable_package
        if package.get("schema") != "ev4-builder-executable-package@1.0.0":
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_SCHEMA_INVALID", kind, "blocked", "Builder package schema is unsupported.", "$.builder_executable_package.schema"))
        if package.get("builder_package_status") != "executable_ready":
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_STATUS_INVALID", kind, "blocked", "Ready Strategy requires executable_ready Builder package.", "$.builder_executable_package.builder_package_status"))
        if package.get("selected_candidate_id") != expected_candidate:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_CANDIDATE_MISMATCH", kind, "blocked", "Builder package candidate differs from Carrier 1.", "$.builder_executable_package.selected_candidate_id"))
        expected_classes = _strings(_as_dict(_as_dict(identity_carrier.get("derived_data")).get("approved_class_names")).get("expected") or [])
        contract = _as_dict(package.get("architect_contract"))
        if _strings(package.get("approved_class_names") or []) != expected_classes or _strings(contract.get("approved_class_names") or []) != expected_classes:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_CLASS_SET_MISMATCH", kind, "blocked", "Builder package and architect_contract must preserve Carrier 1 classes.", "$.builder_executable_package.approved_class_names"))
        if contract.get("selected_candidate_id") != expected_candidate:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_ARCHITECT_CONTRACT_MISMATCH", kind, "blocked", "Builder package architect_contract candidate differs from Carrier 1.", "$.builder_executable_package.architect_contract.selected_candidate_id"))
        if package.get("strategy_map_ref") != strategy_id:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_STRATEGY_REF_MISMATCH", kind, "blocked", "Builder package strategy_map_ref differs from validated Strategy Map.", "$.builder_executable_package.strategy_map_ref"))
        if package.get("builder_decisions_required") != 0:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_BUILDER_DECISION_REMAINS", kind, "blocked", "Builder package must require zero Builder decisions.", "$.builder_executable_package.builder_decisions_required"))
        if package.get("blocking_dependencies") != []:
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_PACKAGE_BLOCKERS_PRESENT", kind, "blocked", "Ready Builder package must have no blocking dependencies.", "$.builder_executable_package.blocking_dependencies"))
        confirmation = package.get("confirmation_request")
        first_batch = package.get("first_safe_builder_batch")
        if not isinstance(confirmation, dict) or not all(key in confirmation for key in ("confirmation_id", "confirmed_action_ids", "expected_user_token")):
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_CONFIRMATION_DATA_MISSING", kind, "blocked", "Structured confirmation data is missing.", "$.builder_executable_package.confirmation_request"))
        if not isinstance(first_batch, dict) or not isinstance(first_batch.get("actions"), list) or not first_batch.get("actions"):
            diagnostics.append(_diag("CE_STRATEGY_COVERAGE_FIRST_SAFE_BATCH_MISSING", kind, "blocked", "First safe Builder batch is missing.", "$.builder_executable_package.first_safe_builder_batch"))
        else:
            bad_actions: list[str] = []
            for action in first_batch["actions"]:
                if not isinstance(action, dict):
                    continue
                action_id = str(action.get("action_id") or "unknown-action")
                if action.get("requires_decision") is not False or _contains_unresolved_decision(action.get("parameters")):
                    bad_actions.append(action_id)
            if bad_actions:
                diagnostics.append(_diag("CE_STRATEGY_COVERAGE_FIRST_BATCH_DECISION_HIDDEN", kind, "blocked", "First safe Builder batch contains unresolved decisions.", "$.builder_executable_package.first_safe_builder_batch.actions", related_ids=bad_actions))
            else:
                first_safe_batch_status = "complete"

    derived_data = {
        "strategy_present": True,
        "absence_reason": None,
        "strategy_identity": strategy_id,
        "strategy_map": strategy_map,
        "coverage_by_review_unit": coverage_by_unit,
        "coverage_by_dependency": coverage_by_dependency,
        "uncovered_review_units": missing_units,
        "uncovered_dependencies": sorted(set(uncovered_dependencies)),
        "builder_decisions_remaining": builder_decisions,
        "first_safe_batch_status": first_safe_batch_status,
        "payload_projection": {"implementation_strategy_map": strategy_map, "builder_package_not_emitted_reason": None, "required_unresolved_ids": _strings(dep_data.get("unresolved_dependencies") or [])},
    }
    return _carrier(kind, run_id, diagnostics, [
        _source_identity("identity_carrier", "architecture_identity_preservation_result", identity_carrier),
        _source_identity("review_carrier", "ce_review_units_and_interrogation_results", review_carrier),
        _source_identity("dependency_carrier", "dependency_classification", dependency_carrier),
        _source_identity("implementation_strategy_map", str(strategy_id or "strategy"), implementation_strategy_map),
        _source_identity("builder_executable_package", str(_as_dict(builder_executable_package).get("package_id") or "package"), builder_executable_package or {}),
    ], derived_data)
