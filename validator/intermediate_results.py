from __future__ import annotations

import copy
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .claim_evaluators import evaluate_claim
from .review_obligations import derive_review_obligations


_DECISION_TOKENS = {"tbd", "todo", "choose", "select", "decide", "unknown", "either", "or"}
_DESTRUCTIVE_ACTIONS = {"delete_element", "replace_architecture", "replace_build_tree", "rename_node"}


def _canonical(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _status(diagnostics: Sequence[Mapping[str, Any]], *, incomplete: bool = False) -> str:
    if any(str(item.get("severity")) == "invalid" for item in diagnostics):
        return "invalid"
    if diagnostics:
        return "blocked"
    if incomplete:
        return "insufficient_evidence"
    return "complete"


def _reviewed_by_id(draft: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in draft.get("reviewed_nodes") or []:
        if isinstance(item, Mapping) and isinstance(item.get("node_id"), str):
            result[str(item["node_id"])] = dict(item)
    return result


def _actions(draft: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in draft.get("builder_action_proposals") or [] if isinstance(item, Mapping)]


def _strategies(draft: Mapping[str, Any]) -> list[dict[str, Any]]:
    proposal = draft.get("implementation_strategy_proposal")
    if not isinstance(proposal, Mapping):
        return []
    return [dict(item) for item in proposal.get("strategies") or [] if isinstance(item, Mapping)]


def _contains_unresolved_choice(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_lower = str(key).casefold()
            if key_lower in {"requires_decision", "decision_required"} and child is True:
                findings.append(child_path)
            if key_lower.endswith("_options") and isinstance(child, list) and len(child) > 1:
                findings.append(child_path)
            findings.extend(_contains_unresolved_choice(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_contains_unresolved_choice(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        normalized = value.casefold().strip()
        if normalized in _DECISION_TOKENS or normalized.startswith("choose ") or " tbd" in f" {normalized}":
            findings.append(path)
    return findings


def derive_architecture_identity_preservation(
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    obligations: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    intake_selected = architect_intake.get("selected_architecture") or {}
    intent = architect_intake.get("architect_intent_preserved") or {}
    bundle_payload = source_bundle.get("payload") or {}
    bundle_identity = bundle_payload.get("architecture_identity") or {}
    bundle_intent = bundle_payload.get("architect_intent") or {}
    candidate = intake_selected.get("selected_candidate_id")
    source_candidate = bundle_identity.get("selected_candidate_id")
    classes = sorted(str(value) for value in (intent.get("class_intent") or {}).get("approved_class_names") or [])
    source_classes = sorted(
        str(value) for value in (bundle_intent.get("class_intent") or {}).get("approved_class_names") or []
    )
    if not isinstance(candidate, str) or candidate != source_candidate:
        diagnostics.append({"code": "CE_IDENTITY_SELECTED_CANDIDATE_MISMATCH"})
    if classes != source_classes:
        diagnostics.append({"code": "CE_IDENTITY_APPROVED_CLASSES_MISMATCH"})

    required_nodes = [item["node_id"] for item in obligations["required_architect_nodes"]]
    reviewed_ids = [
        str(item.get("node_id"))
        for item in review_draft.get("reviewed_nodes") or []
        if isinstance(item, Mapping) and isinstance(item.get("node_id"), str)
    ]
    build_tree_nodes_preserved = sorted(set(reviewed_ids)) == sorted(required_nodes) and not obligations[
        "duplicate_nodes"
    ]
    if not build_tree_nodes_preserved:
        diagnostics.append({"code": "CE_IDENTITY_BUILD_TREE_NOT_PRESERVED"})

    unknown_ids = sorted(
        str(item.get("unresolved_id"))
        for item in architect_intake.get("unresolved_evidence") or []
        if isinstance(item, Mapping) and isinstance(item.get("unresolved_id"), str)
    )
    forbidden_work = sorted(str(value) for value in architect_intake.get("forbidden_work") or [])
    echo = review_draft.get("architecture_echo")
    if not isinstance(echo, Mapping):
        echo = {}
    echoed_unknowns = echo.get("architect_unknown_ids")
    unknowns_preserved = echoed_unknowns is None or sorted(str(value) for value in echoed_unknowns) == unknown_ids
    if not unknowns_preserved:
        diagnostics.append({"code": "CE_IDENTITY_ARCHITECT_UNKNOWNS_REMOVED"})
    echoed_forbidden = echo.get("forbidden_work")
    forbidden_preserved = echoed_forbidden is None or sorted(str(value) for value in echoed_forbidden) == forbidden_work
    if not forbidden_preserved:
        diagnostics.append({"code": "CE_IDENTITY_FORBIDDEN_WORK_WEAKENED"})
    echoed_candidate = echo.get("selected_candidate_id")
    if echoed_candidate is not None and echoed_candidate != candidate:
        diagnostics.append({"code": "CE_IDENTITY_DRAFT_CANDIDATE_CHANGED"})
    echoed_classes = echo.get("approved_class_names")
    if echoed_classes is not None and sorted(str(value) for value in echoed_classes) != classes:
        diagnostics.append({"code": "CE_IDENTITY_DRAFT_CLASSES_CHANGED"})
    echoed_nodes = echo.get("build_tree_node_ids")
    if echoed_nodes is not None and sorted(str(value) for value in echoed_nodes) != sorted(required_nodes):
        diagnostics.append({"code": "CE_IDENTITY_DRAFT_BUILD_TREE_CHANGED"})

    reviewed = _reviewed_by_id(review_draft)
    unauthorized_nodes = sorted(
        node_id
        for node_id, node in reviewed.items()
        if (node.get("requires_class_change") is True or node.get("requires_structure_change") is True)
        and node.get("architect_decomposition_permission") is not True
    )
    destructive_actions = sorted(
        str(action.get("action_id"))
        for action in _actions(review_draft)
        if action.get("action_type") in _DESTRUCTIVE_ACTIONS
    )
    if unauthorized_nodes or destructive_actions:
        diagnostics.append(
            {
                "code": "CE_IDENTITY_UNAUTHORIZED_REDESIGN",
                "nodes": unauthorized_nodes,
                "actions": destructive_actions,
            }
        )
    traces = [
        {
            "architect_node_ref": item["node_id"],
            "architect_evidence_refs": list(item.get("evidence_refs") or []),
            "ce_review_unit_id": f"ce-unit-{item['node_id']}",
            "identity_unchanged": (
                item["node_id"] in reviewed
                and item["node_id"] not in unauthorized_nodes
                and bool(item.get("evidence_refs"))
            ),
        }
        for item in obligations["required_architect_nodes"]
    ]
    missing_trace_evidence = sorted(
        item["architect_node_ref"]
        for item in traces
        if not item["architect_evidence_refs"]
    )
    if missing_trace_evidence:
        diagnostics.append(
            {
                "code": "CE_IDENTITY_ARCHITECT_EVIDENCE_REFS_MISSING",
                "nodes": missing_trace_evidence,
            }
        )
    review_trace_complete = all(item["identity_unchanged"] for item in traces)
    if not review_trace_complete:
        diagnostics.append({"code": "CE_IDENTITY_REVIEW_TRACE_INCOMPLETE"})

    result = {
        "result_kind": "architecture_identity_preservation_result",
        "selected_candidate_preserved": candidate == source_candidate and echoed_candidate in {None, candidate},
        "approved_classes_preserved": classes == source_classes
        and (echoed_classes is None or sorted(str(value) for value in echoed_classes) == classes),
        "build_tree_nodes_preserved": build_tree_nodes_preserved
        and (echoed_nodes is None or sorted(str(value) for value in echoed_nodes) == sorted(required_nodes)),
        "architect_unknowns_preserved": unknowns_preserved,
        "forbidden_work_preserved": forbidden_preserved,
        "unauthorized_redesign_absent": not unauthorized_nodes and not destructive_actions,
        "review_unit_trace_complete": review_trace_complete,
        "selected_candidate_id": candidate,
        "approved_class_names": classes,
        "build_tree_node_ids": sorted(required_nodes),
        "architect_unknown_ids": unknown_ids,
        "forbidden_work": forbidden_work,
        "review_unit_traces": traces,
        "diagnostics": diagnostics,
    }
    result["status"] = _status(diagnostics)
    return _canonical(result)


def derive_review_units_and_interrogation_results(
    review_draft: Mapping[str, Any], obligations: Mapping[str, Any]
) -> dict[str, Any]:
    required = [item["node_id"] for item in obligations["required_architect_nodes"]]
    reviewed = [
        str(item.get("node_id"))
        for item in review_draft.get("reviewed_nodes") or []
        if isinstance(item, Mapping) and isinstance(item.get("node_id"), str)
    ]
    counts = Counter(reviewed)
    incomplete: list[str] = []
    by_id = _reviewed_by_id(review_draft)
    for node_id in required:
        item = by_id.get(node_id)
        if not item or not isinstance(item.get("proposed_action"), str) or not isinstance(
            item.get("engineering_rationale"), str
        ):
            incomplete.append(node_id)
    diagnostics: list[dict[str, Any]] = []
    if obligations["missing_nodes"]:
        diagnostics.append({"code": "CE_REVIEW_UNIT_REQUIRED_NODES_MISSING", "nodes": obligations["missing_nodes"]})
    if obligations["orphan_nodes"]:
        diagnostics.append({"code": "CE_REVIEW_UNIT_ORPHAN_NODES", "nodes": obligations["orphan_nodes"]})
    duplicates = sorted(node_id for node_id, count in counts.items() if count > 1)
    if duplicates:
        diagnostics.append({"code": "CE_REVIEW_UNIT_DUPLICATE_NODES", "nodes": duplicates})
    if incomplete:
        diagnostics.append({"code": "CE_REVIEW_UNIT_INCOMPLETE", "nodes": incomplete})
    coverage = {
        node_id: list(obligations["required_claims_by_node"].get(node_id, [])) for node_id in required
    }
    result = {
        "result_kind": "review_units_and_interrogation_result",
        "required_nodes": sorted(required),
        "reviewed_nodes": sorted(set(reviewed)),
        "missing_nodes": list(obligations["missing_nodes"]),
        "orphan_nodes": list(obligations["orphan_nodes"]),
        "duplicate_nodes": duplicates,
        "incomplete_review_units": sorted(incomplete),
        "claim_coverage_by_node": coverage,
        "explicit_no_claim_nodes": list(obligations["explicit_no_claim_nodes"]),
        "complete": not diagnostics and obligations["complete"],
        "diagnostics": diagnostics,
    }
    result["status"] = _status(diagnostics, incomplete=not obligations["complete"])
    return _canonical(result)


def derive_dependency_classification(
    *,
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    obligations: Mapping[str, Any],
    repo_root: Any,
    runtime_results: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for node_id in sorted(obligations["required_claims_by_node"]):
        for claim_id in obligations["required_claims_by_node"][node_id]:
            evaluation = evaluate_claim(
                claim_id,
                node_id,
                {"required": True, "applicable_rule": None},
                architect_intake,
                source_bundle,
                review_draft,
                {"repo_root": repo_root},
                runtime_results,
            )
            candidate = architect_intake.get("selected_architecture", {}).get("selected_candidate_id")
            bundle_id = source_bundle.get("bundle_id")
            intake_digest = __import__("hashlib").sha256(
                json.dumps(architect_intake, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            bound_records: list[dict[str, Any]] = []
            for record in evaluation.get("evidence_records") or []:
                if not isinstance(record, Mapping):
                    continue
                bound = dict(record)
                bound["target_binding"] = {
                    "subject_ref": node_id,
                    "selected_candidate_id": candidate,
                    "source_bundle_id": bundle_id,
                    "intake_digest": intake_digest,
                }
                bound.pop("evidence_id", None)
                evidence_id = __import__("hashlib").sha256(
                    json.dumps(bound, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                bound["evidence_id"] = evidence_id
                bound_records.append(bound)
            evaluation["evidence_records"] = bound_records
            evaluation["evidence_refs"] = (
                [record["evidence_id"] for record in bound_records]
                if evaluation.get("status") == "satisfied"
                else []
            )
            rows.append(evaluation)
    expected = sum(len(values) for values in obligations["required_claims_by_node"].values())
    matrix_complete = len(rows) == expected
    if not matrix_complete:
        diagnostics.append({"code": "CE_DEPENDENCY_REQUIRED_ROW_MISSING"})
    if not rows and not obligations["explicit_no_claim_nodes"]:
        diagostics.append({"code": "CE_DEPENDENCY_EMPTY_MATRIX_UNPROVEN"})
    blocking = sorted(
        f"{item['subject_ref']}:{item['claim_id']}:{item['status']}" for item in rows if item["blocking"]
    )
    unresolved = [
        {
            "unresolved_id": f"unresolved-{item['subject_ref']}-{item['claim_id']}",
            "claim_ref": f"{item['subject_ref']}:{item['claim_id']}",
            "owner": item["authority_owner"],
            "reason": item["status"],
            "evidence_refs": list(item["evidence_refs"]),
            "limitations": list(item["limitations"]),
        }
        for item in rows
        if item["status"] not in {"satisfied", "not_applicable"}
    ]
    downstream = [
        item["downstream_obligation"] for item in rows if item.get("downstream_obligation") is not None
    ]
    evidence = [record for item in rows for record in item.get("evidence_records") or []]
    result = {
        "result_kind": "dependency_classification_result",
        "required_row_count": expected,
        "rows": rows,
        "matrix_complete": matrix_complete,
        "blocking_dependencies": blocking,
        "unresolved_evidence": unresolved,
        "downstream_test_obligations": downstream,
        "evidence_records": evidence,
        "diagnostics": diagnostics,
    }
    result["status"] = "blocked" if blocking else _status(diagnostics)
    return _canonical(result)


def derive_implementation_strategy_coverage(
    review_draft: Mapping[str, Any],
    obligations: Mapping[str, Any],
    identity_result: Mapping[str, Any],
    dependency_result: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    required_nodes = set(obligations["required_strategy_coverage"])
    strategies = _strategies(review_draft)
    strategy_nodes = [str(item.get("node_id")) for item in strategies if isinstance(item.get("node_id"), str)]
    missing_strategy_nodes = sorted(required_nodes - set(strategy_nodes))
    duplicate_strategy_nodes = sorted(
        node_id for node_id, count in Counter(strategy_nodes).items() if count > 1
    )
    if missing_strategy_nodes:
        diagnostics.append({"code": "CE_STRATEGY_REQUIRED_NODE_MISSING", "nodes": missing_strategy_nodes})
    if duplicate_strategy_nodes:
        diagnostics.append({"code": "CE_STRATEGY_DUPLICATE_NODE", "nodes": duplicate_strategy_nodes})

    actions = _actions(review_draft)
    invalid_targets = sorted(
        str(item.get("action_id")) for item in actions if item.get("target_node") not in required_nodes
    )
    if invalid_targets:
        diagnostics.append({"code": "CE_STRATEGY_BUILDER_ACTION_TARGET_INVALID", "actions": invalid_targets})
    uncovered_actions = sorted(
        str(item.get("action_id")) for item in actions if item.get("target_node") not in set(strategy_nodes)
    )
    if uncovered_actions:
        diagnostics.append({"code": "CE_STRATEGY_BUILDER_ACTION_UNCOVERED", "actions": uncovered_actions})

    hidden_paths: list[str] = []
    for index, action in enumerate(actions):
        hidden_paths.extend(_contains_unresolved_choice(action.get("parameters"), f"$.actions[{index}].parameters"))
    for index, strategy in enumerate(strategies):
        hidden_paths.extend(_contains_unresolved_choice(strategy, f"$.strategies[{index}]"))
    if hidden_paths:
        diagnostics.append({"code": "CE_STRATEGY_HIDDEN_BUILDER_DECISION", "paths": sorted(hidden_paths)})

    reviewed = _reviewed_by_id(review_draft)
    amendment_nodes = sorted(
        node_id
        for node_id, item in reviewed.items()
        if (item.get("requires_class_change") is True or item.get("requires_structure_change") is True)
        and item.get("architect_decomposition_permission") is not True
    )
    if amendment_nodes:
        diagnostics.append({"code": "CE_STRATEGY_ARCHITECT_AMENDMENT_REQUIRED", "nodes": amendment_nodes})

    proposal = review_draft.get("implementation_strategy_proposal")
    proposal = proposal if isinstance(proposal, Mapping) else {}
    candidate_preserved = proposal.get("selected_candidate_id") in {
        None,
        identity_result.get("selected_candidate_id"),
    }
    classes_value = proposal.get("approved_class_names")
    classes_preserved = classes_value is None or sorted(str(value) for value in classes_value) == list(
        identity_result.get("approved_class_names") or []
   )
    if not candidate_preserved:
        diagnostics.append({"code": "CE_STRATEGY_SELECTED_CANDIDATE_CHANGED"})
    if not classes_preserved:
        diagnostics.append({"code": "CE_STRATEGY_APPROVED_CLASSES_CHANGED"})

    dependency_rows = dependency_result.get("rows") or []
    explicit_no_claim_complete = set(obligations.get("explicit_no_claim_nodes") or []) == required_nodes
    non_blocking_covered = (
        bool(dependency_rows)
        and all(
            item.get("status") == "satisfied"
            or item.get("status") == "not_applicable"
            or item.get("downstream_obligation") is not None
            for item in dependency_rows
            if isinstance(item, Mapping)
        )
    ) or explicit_no_claim_complete
    if not non_blocking_covered:
        diagnostics.append({"code": "CE_STRATEGY_NONBLOCKING_OBLIGATION_HIDDEN"})

    first_safe_batch_complete = bool(actions) and not invalid_targets and not uncovered_actions and not hidden_paths
    result = {
        "result_kind": "implementation_strategy_coverage_result",
        "required_review_units_covered": not missing_strategy_nodes and not duplicate_strategy_nodes,
        "non_blocking_obligations_covered": non_blocking_covered,
        "blocked_dependencies_visible": bool(dependency_result.get("blocking_dependencies"))
        == bool(dependency_result.get("unresolved_evidence")),
        "builder_actions_valid": not invalid_targets and not uncovered_actions,
        "builder_decisions_required": len(hidden_paths),
        "hidden_builder_decisions": sorted(hidden_paths),
        "architect_amendment_required": bool(amendment_nodes),
        "architect_amendment_nodes": amendment_nodes,
        "first_safe_batch_complete": first_safe_batch_complete,
        "selected_candidate_preserved": candidate_preserved,
        "approved_classes_preserved": classes_preserved,
        "strategies": copy.deepcopy(strategies),
        "builder_actions": copy.deepcopy(actions),
        "diagnostics": diagnostics,
    }
    result["status"] = "blocked" if dependency_result.get("blocking_dependencies") else _status(diagnostics)
    return _canonical(result)


def evaluate_all(
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    *,
    repo_root: Any,
    runtime_results: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    obligations = derive_review_obligations(architect_intake, source_bundle, review_draft)
    identity = derive_architecture_identity_preservation(
        architect_intake, source_bundle, review_draft, obligations
    )
    review = derive_review_units_and_interrogation_results(review_draft, obligations)
    dependency = derive_dependency_classification(
        architect_intake=architect_intake,
        source_bundle=source_bundle,
        review_draft=review_draft,
        obligations=obligations,
        repo_root=repo_root,
        runtime_results=runtime_results,
    )
    strategy = derive_implementation_strategy_coverage(
        review_draft, obligations, identity, dependency
    )
    return _canonical(
        {
            "obligations": obligations,
            "identity_result": identity,
            "review_result": review,
            "dependency_result": dependency,
            "strategy_result": strategy,
        }
    )
