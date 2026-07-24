from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .artifact_adapters import (
    ArtifactAdapterError,
    ArtifactBinding,
    evaluate_artifact_source,
)
from .claim_policy_registry import CLAIM_POLICIES, policy_projection
from .runtime_execution import (
    RuntimeExecutionBatch,
    RuntimeExecutionBoundaryError,
    execute_runtime_requests,
    execution_transaction_id,
    select_execution_result,
)


class ClaimEvaluationError(ValueError):
    """Raised when evaluator inputs are malformed rather than insufficient."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _draft_node(review_draft: Mapping[str, Any], subject_ref: str) -> dict[str, Any]:
    for item in review_draft.get("reviewed_nodes") or []:
        if isinstance(item, Mapping) and item.get("node_id") == subject_ref:
            return dict(item)
    return {}


def _semantics(node: Mapping[str, Any], claim_id: str) -> dict[str, Any]:
    raw = node.get("claim_semantics")
    if isinstance(raw, Mapping) and isinstance(raw.get(claim_id), Mapping):
        return dict(raw[claim_id])
    return {}


def _candidate_sources(node: Mapping[str, Any], claim_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    raw = node.get("candidate_source_refs")
    if not isinstance(raw, list):
        return result
    for item in raw:
        if isinstance(item, Mapping) and item.get("claim_id") == claim_id:
            result.append(dict(item))
    return result


def _base_evaluation(
    claim_id: str,
    subject_ref: str,
    *,
    status: str,
    facts: Mapping[str, Any] | None = None,
    evidence_refs: Sequence[str] = (),
    limitations: Sequence[str] = (),
    diagnostics: Sequence[Mapping[str, Any]] = (),
    downstream_obligation: Mapping[str, Any] | None = None,
    evidence_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    policy = CLAIM_POLICIES[claim_id]
    return {
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "status": status,
        "blocking": bool(policy["blocking"])
        and status not in {"satisfied", "not_applicable"},
        "authority_owner": policy["authority_owner"],
        "applicable_rule": policy["applicable_rule"],
        "facts": dict(facts or {}),
        "evidence_refs": sorted(str(value) for value in evidence_refs),
        "limitations": [str(value) for value in limitations],
        "diagnostics": [dict(value) for value in diagnostics],
        "downstream_obligation": (
            dict(downstream_obligation) if downstream_obligation else None
        ),
        "evidence_records": [dict(value) for value in evidence_records],
        "policy": policy_projection(claim_id),
    }


def _semantic_missing(claim_id: str, semantics: Mapping[str, Any]) -> list[str]:
    required = CLAIM_POLICIES[claim_id]["required_semantics"]
    return [
        str(key)
        for key in required
        if semantics.get(key) in (None, "", [], {})
    ]


def _attributed_evaluation(
    claim_id: str,
    subject_ref: str,
    node: Mapping[str, Any],
    semantics: Mapping[str, Any],
) -> dict[str, Any]:
    missing = _semantic_missing(claim_id, semantics)
    rationale = str(node.get("engineering_rationale") or "").strip()
    assumptions = [
        str(item)
        for item in node.get("assumptions") or []
        if str(item).strip()
    ]
    if missing or not rationale or not assumptions:
        details: list[str] = []
        if missing:
            details.append(f"missing semantics: {', '.join(missing)}")
        if not rationale:
            details.append("engineering rationale is missing")
        if not assumptions:
            details.append("explicit premises are missing")
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="insufficient_evidence",
            limitations=details,
            diagnostics=[{"code": "CE_CLAIM_ATTRIBUTED_JUDGMENT_INCOMPLETE"}],
        )
    record = {
        "mode": "ATTRIBUTED_ENGINEERING_JUDGMENT",
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "reviewer_identity": str(
            node.get("reviewer_identity") or "constructability_engineer"
        ),
        "premises": assumptions,
        "derivation_method": rationale,
        "semantic_facts": dict(semantics),
        "limitations": [str(item) for item in node.get("limitations") or []],
    }
    evidence_id = sha256_json(record)
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="satisfied",
        facts=semantics,
        evidence_refs=[evidence_id],
        limitations=record["limitations"],
        evidence_records=[{**record, "evidence_id": evidence_id}],
    )


def _resolve_repo_path(repo_root: Path, source_ref: str) -> Path:
    root = repo_root.resolve(strict=True)
    candidate = Path(source_ref)
    path = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ClaimEvaluationError("Repository source escaped repo root or is unavailable") from exc
    if not resolved.is_file():
        raise ClaimEvaluationError("Repository source is not a file")
    return resolved


def _artifact_source_evaluation(
    claim_id: str,
    subject_ref: str,
    node: Mapping[str, Any],
    semantics: Mapping[str, Any],
    repo_root: Path,
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = _candidate_sources(node, claim_id)
    if not candidates:
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="insufficient_evidence",
            limitations=["No exact repository source was supplied."],
            diagnostics=[{"code": "CE_CLAIM_SOURCE_REQUIRED"}],
        )
    candidate_id = architect_intake.get("selected_architecture", {}).get(
        "selected_candidate_id"
    )
    bundle_id = source_bundle.get("bundle_id")
    if not isinstance(candidate_id, str) or not isinstance(bundle_id, str):
        raise ClaimEvaluationError("Canonical artifact binding identity is incomplete")
    binding = ArtifactBinding(
        claim_id=claim_id,
        subject_ref=subject_ref,
        selected_candidate_id=candidate_id,
        source_bundle_id=bundle_id,
        intake_digest=sha256_json(architect_intake),
    )
    diagnostics: list[dict[str, Any]] = []
    limitations: list[str] = []
    for source in candidates:
        if source.get("mode") != "VERIFIED_ARTIFACT" or not isinstance(
            source.get("source_ref"), str
        ):
            diagnostics.append({"code": "CE_CLAIM_SOURCE_MODE_INVALID"})
            continue
        try:
            path = _resolve_repo_path(repo_root, str(source["source_ref"]))
            facts, adapter_metadata = evaluate_artifact_source(
                claim_id=claim_id,
                path=path,
                semantics=semantics,
                binding=binding,
            )
        except (OSError, ClaimEvaluationError, ArtifactAdapterError) as exc:
            limitations.append(str(exc))
            diagnostics.append(
                {
                    "code": "CE_CLAIM_STRUCTURED_ARTIFACT_UNSUPPORTED_OR_MISMATCHED",
                    "source_ref": str(source.get("source_ref") or ""),
                }
            )
            continue
        record = {
            "mode": "VERIFIED_ARTIFACT",
            "claim_id": claim_id,
            "subject_ref": subject_ref,
            "source_ref": str(source["source_ref"]),
            "source_identity": str(
                source.get("source_identity") or source["source_ref"]
            ),
            "source_bytes_sha256": adapter_metadata["source_bytes_sha256"],
            "source_schema_id": adapter_metadata["schema_id"],
            "source_role": adapter_metadata["source_role"],
            "adapter_id": adapter_metadata["adapter_id"],
            "semantic_facts": facts,
            "verification": "source_type_specific_structured_adapter",
        }
        evidence_id = sha256_json(record)
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="satisfied",
            facts=facts,
            evidence_refs=[evidence_id],
            evidence_records=[{**record, "evidence_id": evidence_id}],
        )
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="insufficient_evidence",
        limitations=limitations
        or ["No supported structured source semantically established the claim."],
        diagnostics=diagnostics,
    )


def evaluate_geometry(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "geometry"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if _candidate_sources(node, claim_id):
        return _artifact_source_evaluation(
            claim_id,
            context["subject_ref"],
            node,
            semantics,
            context["repo_root"],
            context["architect_intake"],
            context["source_bundle"],
        )
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


def evaluate_overlay_strategy(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "overlay_strategy"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if _candidate_sources(node, claim_id):
        return _artifact_source_evaluation(
            claim_id,
            context["subject_ref"],
            node,
            semantics,
            context["repo_root"],
            context["architect_intake"],
            context["source_bundle"],
        )
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


def evaluate_ui_control_path(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "ui_control_path"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    return _artifact_source_evaluation(
        claim_id,
        context["subject_ref"],
        node,
        _semantics(node, claim_id),
        context["repo_root"],
        context["architect_intake"],
        context["source_bundle"],
    )


def evaluate_asset_source(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "asset_source"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    return _artifact_source_evaluation(
        claim_id,
        context["subject_ref"],
        node,
        _semantics(node, claim_id),
        context["repo_root"],
        context["architect_intake"],
        context["source_bundle"],
    )


def evaluate_placeholder_policy(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "placeholder_policy"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if "premises" not in semantics:
        semantics["premises"] = list(node.get("assumptions") or [])
    if "derivation_method" not in semantics:
        semantics["derivation_method"] = str(
            node.get("engineering_rationale") or ""
        )
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


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
    decision_candidate = (
        decision.get("selected_candidate_id", decision.get("candidate_id"))
        if isinstance(decision, Mapping)
        else None
    )
    subject_refs = (
        decision.get("subject_refs", decision.get("node_ids"))
        if isinstance(decision, Mapping)
        else None
    )
    candidate_matches = decision_candidate in {None, candidate}
    subject_matches = (
        subject_refs is None
        or (isinstance(subject_refs, list) and context["subject_ref"] in subject_refs)
        or subject_refs == context["subject_ref"]
    )
    approved_values = {True, "approved", "explicitly_approved"}
    if current not in approved_values or not candidate_matches or not subject_matches:
        diagnostic = (
            "CE_CLAIM_ARCHITECT_DECISION_BINDING_MISMATCH"
            if current in approved_values
            else "CE_CLAIM_ARCHITECT_DECISION_MISSING"
        )
        return _base_evaluation(
            claim_id,
            context["subject_ref"],
            status="architect_decision_required",
            limitations=[
                "Canonical Architect approval is absent or bound to another candidate or subject."
            ],
            diagnostics=[{"code": diagnostic}],
        )
    record = {
        "mode": "VERIFIED_ARCHITECT_DECISION",
        "claim_id": claim_id,
        "subject_ref": context["subject_ref"],
        "selected_candidate_id": candidate,
        "decision_value": current,
        "source_digest": sha256_json(intake),
    }
    evidence_id = sha256_json(record)
    return _base_evaluation(
        claim_id,
        context["subject_ref"],
        status="satisfied",
        facts={"selected_candidate_id": candidate, "decision_value": current},
        evidence_refs=[evidence_id],
        evidence_records=[{**record, "evidence_id": evidence_id}],
    )


KNOWN_RUNTIME_EVALUATORS = {
    "responsive_behavior": {"ce-responsive-evaluator"},
    "accessibility": {"ce-accessibility-evaluator"},
    "QA": {"ce-qa-evaluator"},
}


def _runtime_evaluation(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = str(context["claim_id"])
    subject_ref = str(context["subject_ref"])
    semantics = _semantics(_draft_node(context["review_draft"], subject_ref), claim_id)
    expected_target = str(semantics.get("target_identity") or subject_ref)
    transaction_id = str(context["execution_transaction_id"])
    result = select_execution_result(
        context.get("execution_batch"),
        transaction_id=transaction_id,
        claim_id=claim_id,
        subject_ref=subject_ref,
    )
    if (
        result is not None
        and result.target_identity == expected_target
        and result.execution_status == "success"
        and result.exit_code == 0
        and result.result_digest == sha256_json(result.captured_result)
    ):
        record = {
            "mode": "VERIFIED_TOOL_EXECUTION",
            **result.as_dict(),
        }
        evidence_id = sha256_json(record)
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="satisfied",
            facts={
                "target_identity": result.target_identity,
                "result_digest": result.result_digest,
                "transaction_id": result.transaction_id,
            },
            evidence_refs=[evidence_id],
            limitations=result.limitations,
            evidence_records=[{**record, "evidence_id": evidence_id}],
        )

    obligation = {
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "consumer_stage": "responsive_or_builder_runtime",
        "required_test": (
            f"Execute the repository-owned {claim_id} adapter for {subject_ref} "
            "inside the current CE evaluation transaction."
        ),
        "blocking_behavior": "block_builder_handoff",
        "completion_criteria": (
            "The repository-owned adapter executes successfully for the exact claim, "
            "subject, target, and transaction."
        ),
    }
    diagnostic = (
        "CE_CLAIM_RUNTIME_EXECUTION_FAILED"
        if result is not None
        else "CE_CLAIM_RUNTIME_EXECUTION_REQUIRED"
    )
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="downstream_validation_required",
        limitations=[
            "No successful repository-owned execution result exists in this evaluation transaction."
        ],
        diagnostics=[{"code": diagnostic}],
        downstream_obligation=obligation,
        evidence_records=[
            {
                "mode": "DOWNSTREAM_TEST_OBLIGATION",
                "claim_id": claim_id,
                "subject_ref": subject_ref,
                "evidence_id": sha256_json(obligation),
                **obligation,
            }
        ],
    )


def evaluate_responsive_behavior(context: Mapping[str, Any]) -> dict[str, Any]:
    return _runtime_evaluation({**context, "claim_id": "responsive_behavior"})


def evaluate_accessibility(context: Mapping[str, Any]) -> dict[str, Any]:
    return _runtime_evaluation({**context, "claim_id": "accessibility"})


def evaluate_qa(context: Mapping[str, Any]) -> dict[str, Any]:
    return _runtime_evaluation({**context, "claim_id": "QA"})


EVALUATORS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "geometry": evaluate_geometry,
    "overlay_strategy": evaluate_overlay_strategy,
    "ui_control_path": evaluate_ui_control_path,
    "asset_source": evaluate_asset_source,
    "placeholder_policy": evaluate_placeholder_policy,
    "dynamic_loop_approval": evaluate_architect_decision,
    "interaction_approval": evaluate_architect_decision,
    "responsive_behavior": evaluate_responsive_behavior,
    "accessibility": evaluate_accessibility,
    "QA": evaluate_qa,
}


def evaluate_claim(
    claim_id: str,
    subject: str,
    obligation: Mapping[str, Any],
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    repository_sources: Mapping[str, Any],
    runtime_execution_requests: Sequence[Mapping[str, Any]] = (),
    *,
    execution_batch: RuntimeExecutionBatch | None = None,
    execution_transaction_id_override: str | None = None,
) -> dict[str, Any]:
    if claim_id not in CLAIM_POLICIES or claim_id not in EVALUATORS:
        raise ClaimEvaluationError(f"Unknown claim evaluator: {claim_id}")
    repo_root = repository_sources.get("repo_root")
    if not isinstance(repo_root, Path):
        repo_root = Path(str(repo_root))
    transaction_id = execution_transaction_id_override or execution_transaction_id(
        architect_intake=architect_intake,
        source_bundle=source_bundle,
        review_draft=review_draft,
        requests=runtime_execution_requests,
    )
    if execution_batch is None and runtime_execution_requests:
        try:
            execution_batch = execute_runtime_requests(
                repo_root=repo_root,
                transaction_id=transaction_id,
                requests=runtime_execution_requests,
            )
        except RuntimeExecutionBoundaryError as exc:
            if claim_id in KNOWN_RUNTIME_EVALUATORS:
                return _base_evaluation(
                    claim_id,
                    subject,
                    status="downstream_validation_required",
                    limitations=[str(exc)],
                    diagnostics=[{"code": "CE_CLAIM_RUNTIME_REQUEST_REJECTED"}],
                    downstream_obligation={
                        "claim_id": claim_id,
                        "subject_ref": subject,
                        "consumer_stage": "responsive_or_builder_runtime",
                        "required_test": "Provide a valid repository-owned execution request.",
                        "blocking_behavior": "block_builder_handoff",
                        "completion_criteria": "Repository adapter executes successfully in the current transaction.",
                    },
                )
            raise ClaimEvaluationError(str(exc)) from exc
    context = {
        "claim_id": claim_id,
        "subject_ref": subject,
        "obligation": dict(obligation),
        "architect_intake": architect_intake,
        "source_bundle": source_bundle,
        "review_draft": review_draft,
        "repo_root": repo_root,
        "execution_batch": execution_batch,
        "execution_transaction_id": transaction_id,
    }
    return EVALUATORS[claim_id](context)


__all__ = [
    "ClaimEvaluationError",
    "EVALUATORS",
    "KNOWN_RUNTIME_EVALUATORS",
    "canonical_bytes",
    "evaluate_claim",
    "sha256_json",
]
