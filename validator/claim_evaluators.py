from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .claim_evaluation_support import (
    ClaimEvaluationError,
    _artifact_source_evaluation,
    _attributed_evaluation,
    _base_evaluation,
    _candidate_sources,
    _draft_node,
    _semantics,
    canonical_bytes,
    sha256_json,
)
from .claim_policy_registry import CLAIM_POLICIES, POST_BUILDER_RUNTIME
from .runtime_execution import (
    RuntimeExecutionBatch,
    RuntimeExecutionBoundaryError,
    execute_runtime_requests,
    execution_transaction_id,
    select_execution_result,
)


def evaluate_geometry(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "geometry"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if _candidate_sources(node, claim_id):
        return _artifact_source_evaluation(claim_id, context["subject_ref"], node, semantics, context["repo_root"], context["architect_intake"], context["source_bundle"])
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


def evaluate_overlay_strategy(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "overlay_strategy"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if _candidate_sources(node, claim_id):
        return _artifact_source_evaluation(claim_id, context["subject_ref"], node, semantics, context["repo_root"], context["architect_intake"], context["source_bundle"])
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


def _evaluate_attributed(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = str(context["claim_id"])
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if claim_id == "placeholder_policy":
        semantics.setdefault("premises", list(node.get("assumptions") or []))
        semantics.setdefault("derivation_method", str(node.get("engineering_rationale") or ""))
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


def evaluate_ui_control_path(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "ui_control_path"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    return _artifact_source_evaluation(claim_id, context["subject_ref"], node, _semantics(node, claim_id), context["repo_root"], context["architect_intake"], context["source_bundle"])


def evaluate_asset_source(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "asset_source"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    return _artifact_source_evaluation(claim_id, context["subject_ref"], node, _semantics(node, claim_id), context["repo_root"], context["architect_intake"], context["source_bundle"])


def _architect_decision_path(claim_id: str) -> tuple[str, ...]:
    if claim_id == "dynamic_loop_approval":
        return ("architect_intent_preserved", "dynamic_loop_intent", "status")
    return ("architect_intent_preserved", "interaction_intent", "status")


def evaluate_architect_decision(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = str(context["claim_id"])
    intake = context["architect_intake"]
    path = _architect_decision_path(claim_id)
    decision: Any = intake
    for key in path[:-1]:
        if not isinstance(decision, Mapping) or key not in decision:
            decision = None
            break
        decision = decision[key]
    current = decision.get(path[-1]) if isinstance(decision, Mapping) else None
    candidate = intake.get("selected_architecture", {}).get("selected_candidate_id")
    decision_candidate = decision.get("selected_candidate_id", decision.get("candidate_id")) if isinstance(decision, Mapping) else None
    subject_refs = decision.get("subject_refs", decision.get("node_ids")) if isinstance(decision, Mapping) else None
    candidate_matches = decision_candidate in {None, candidate}
    subject_matches = subject_refs is None or (isinstance(subject_refs, list) and context["subject_ref"] in subject_refs) or subject_refs == context["subject_ref"]
    approved_values = {True, "approved", "explicitly_approved"}
    if current not in approved_values or not candidate_matches or not subject_matches:
        diagnostic = "CE_CLAIM_ARCHITECT_DECISION_BINDING_MISMATCH" if current in approved_values else "CE_CLAIM_ARCHITECT_DECISION_MISSING"
        return _base_evaluation(claim_id, context["subject_ref"], status="architect_decision_required", limitations=["Canonical Architect approval is absent or bound to another candidate or subject."], diagnostics=[{"code": diagnostic}])
    record = {"mode": "VERIFIED_ARCHITECT_DECISION", "claim_id": claim_id, "subject_ref": context["subject_ref"], "selected_candidate_id": candidate, "decision_value": current, "source_digest": sha256_json(intake)}
    evidence_id = sha256_json(record)
    return _base_evaluation(claim_id, context["subject_ref"], status="satisfied", facts={"selected_candidate_id": candidate, "decision_value": current}, evidence_refs=[evidence_id], evidence_records=[{**record, "evidence_id": evidence_id}])


KNOWN_RUNTIME_EVALUATORS = {
    "responsive_behavior": {"ce-responsive-evaluator"},
    "interaction_validation": {"ce-interaction-evaluator"},
    "accessibility": {"ce-accessibility-evaluator"},
    "QA": {"ce-qa-evaluator"},
}


def _obligation_assertions(claim_id: str) -> list[str]:
    return {
        "responsive_behavior": ["render the implemented target at required viewports", "compare observed layout with the CE responsive strategy"],
        "interaction_validation": ["exercise the approved interaction on the implemented target", "capture actual state transitions and failures"],
        "accessibility": ["inspect implemented semantics and accessible names", "exercise keyboard interaction on the implemented target"],
        "QA": ["execute the repository-selected QA scope on the implemented target", "record actual assertion results and exit status"],
    }[claim_id]


def _runtime_obligation(claim_id: str, subject_ref: str, *, target_identity: str, declaration: Mapping[str, Any] | None) -> dict[str, Any]:
    runner = sorted(KNOWN_RUNTIME_EVALUATORS[claim_id])[0]
    required_inputs = ["implemented_target_ref", "implemented_target_digest", "exact claim and subject binding"]
    if declaration is not None:
        required_inputs.extend(str(value) for value in declaration.get("required_inputs") or [])
    expected_assertions = _obligation_assertions(claim_id)
    if declaration is not None:
        expected_assertions.extend(str(value) for value in declaration.get("expected_assertions") or [])
    seed = {"claim_id": claim_id, "subject_ref": subject_ref, "target_identity": target_identity, "required_runner": runner, "required_inputs": sorted(set(required_inputs)), "expected_assertions": list(dict.fromkeys(expected_assertions))}
    return {"obligation_id": f"ce-runtime-obligation-{sha256_json(seed)[:24]}", "claim_id": claim_id, "subject_ref": subject_ref, "consumer_stage": "post_builder_runtime_validation", "required_runner": runner, "target_identity": target_identity, "required_inputs": seed["required_inputs"], "expected_assertions": seed["expected_assertions"], "completion_criteria": "The repository-owned runner executes against the exact implemented target, generates observations internally, returns success, and passes every assertion.", "blocking_boundary": "final_project_gate", "status": "required", "blocks_builder_handoff": False, "blocks_final_completion": True}


def _declaration_for(batch: RuntimeExecutionBatch | None, claim_id: str, subject_ref: str) -> Mapping[str, Any] | None:
    if not isinstance(batch, RuntimeExecutionBatch):
        return None
    return next((item for item in batch.declarations if item.get("claim_id") == claim_id and item.get("subject_ref") == subject_ref), None)


def _runtime_evaluation(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = str(context["claim_id"])
    subject_ref = str(context["subject_ref"])
    node = _draft_node(context["review_draft"], subject_ref)
    semantics = _semantics(node, claim_id)
    expected_target = str(semantics.get("target_identity") or subject_ref)
    batch = context.get("execution_batch")
    declaration = _declaration_for(batch, claim_id, subject_ref)
    if declaration is not None:
        expected_target = str(declaration.get("target_identity") or expected_target)
    execution = select_execution_result(batch if isinstance(batch, RuntimeExecutionBatch) else None, transaction_id=str(context["execution_transaction_id"]), claim_id=claim_id, subject_ref=subject_ref)
    if execution is not None and execution.target_identity == expected_target and execution.execution_status == "success" and execution.exit_code == 0:
        record = {"mode": "VERIFIED_TOOL_EXECUTION", "claim_id": claim_id, "subject_ref": subject_ref, "transaction_id": execution.transaction_id, "evaluator_id": execution.evaluator_id, "method_or_command": execution.method_or_command, "target_identity": execution.target_identity, "execution_status": execution.execution_status, "exit_code": execution.exit_code, "captured_result": execution.captured_result, "result_digest": execution.result_digest, "limitations": list(execution.limitations), "verification": "repository_owned_current_transaction_execution"}
        evidence_id = sha256_json(record)
        return _base_evaluation(claim_id, subject_ref, status="satisfied", facts=dict(execution.captured_result), evidence_refs=[evidence_id], evidence_records=[{**record, "evidence_id": evidence_id}], limitations=list(execution.limitations))
    obligation = _runtime_obligation(claim_id, subject_ref, target_identity=expected_target, declaration=declaration)
    record = {"mode": "DOWNSTREAM_TEST_OBLIGATION", "claim_id": claim_id, "subject_ref": subject_ref, "obligation_id": obligation["obligation_id"], "obligation": obligation, "declaration": dict(declaration) if declaration else None, "verification": "obligation_created_not_executed"}
    record["evidence_id"] = sha256_json(record)
    limitations = ["The implemented target or a successful repository-owned execution is unavailable; no runtime pass is claimed."]
    diagnostics = [{"code": "CE_CLAIM_POST_BUILDER_RUNTIME_OBLIGATION_REQUIRED"}]
    if execution is not None:
        limitations.extend(str(item) for item in execution.limitations)
        diagnostics = [{"code": "CE_CLAIM_RUNTIME_EXECUTION_FAILED"}]
    return _base_evaluation(claim_id, subject_ref, status="downstream_validation_required", limitations=limitations, diagnostics=diagnostics, downstream_obligation=obligation, evidence_records=[record])


EVALUATORS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "geometry": evaluate_geometry,
    "overlay_strategy": evaluate_overlay_strategy,
    "responsive_strategy": _evaluate_attributed,
    "accessibility_strategy": _evaluate_attributed,
    "placeholder_policy": _evaluate_attributed,
    "interaction_approval": evaluate_architect_decision,
    "dynamic_loop_approval": evaluate_architect_decision,
    "asset_source": evaluate_asset_source,
    "ui_control_path": evaluate_ui_control_path,
    "responsive_behavior": _runtime_evaluation,
    "interaction_validation": _runtime_evaluation,
    "accessibility": _runtime_evaluation,
    "QA": _runtime_evaluation,
}


def evaluate_claim(claim_id: str, subject: str, obligation: Mapping[str, Any], architect_intake: Mapping[str, Any], source_bundle: Mapping[str, Any], review_draft: Mapping[str, Any], repository_sources: Mapping[str, Any], runtime_execution_requests: Sequence[Mapping[str, Any]] = (), *, execution_batch: RuntimeExecutionBatch | None = None, execution_transaction_id_override: str | None = None) -> dict[str, Any]:
    if claim_id not in CLAIM_POLICIES or claim_id not in EVALUATORS:
        raise ClaimEvaluationError(f"Unknown claim evaluator: {claim_id}")
    repo_root = repository_sources.get("repo_root")
    if not isinstance(repo_root, Path):
        repo_root = Path(str(repo_root))
    transaction_id = execution_transaction_id_override or execution_transaction_id(architect_intake=architect_intake, source_bundle=source_bundle, review_draft=review_draft, requests=runtime_execution_requests)
    if execution_batch is None and runtime_execution_requests:
        try:
            execution_batch = execute_runtime_requests(repo_root=repo_root, transaction_id=transaction_id, requests=runtime_execution_requests)
        except RuntimeExecutionBoundaryError as exc:
            if CLAIM_POLICIES[claim_id]["lifecycle_phase"] == POST_BUILDER_RUNTIME:
                result = _runtime_evaluation({"claim_id": claim_id, "subject_ref": subject, "obligation": dict(obligation), "architect_intake": architect_intake, "source_bundle": source_bundle, "review_draft": review_draft, "repo_root": repo_root, "execution_batch": None, "execution_transaction_id": transaction_id})
                result["limitations"].append(str(exc))
                result["diagnostics"] = [{"code": "CE_CLAIM_RUNTIME_REQUEST_REJECTED"}]
                return result
            raise ClaimEvaluationError(str(exc)) from exc
    context = {"claim_id": claim_id, "subject_ref": subject, "obligation": dict(obligation), "architect_intake": architect_intake, "source_bundle": source_bundle, "review_draft": review_draft, "repo_root": repo_root, "execution_batch": execution_batch, "execution_transaction_id": transaction_id}
    return EVALUATORS[claim_id](context)


__all__ = ["ClaimEvaluationError", "EVALUATORS", "KNOWN_RUNTIME_EVALUATORS", "canonical_bytes", "evaluate_claim", "sha256_json"]
