from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .claim_policy_registry import CLAIM_POLICIES, policy_projection


class ClaimEvaluationError(ValueError):
    """Raised when evaluator inputs are malformed rather than merely insufficient."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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
        "blocking": bool(policy["blocking"]) and status not in {"satisfied", "not_applicable"},
        "authority_owner": policy["authority_owner"],
        "applicable_rule": policy["applicable_rule"],
        "facts": dict(facts or {}),
        "evidence_refs": sorted(str(value) for value in evidence_refs),
        "limitations": [str(value) for value in limitations],
        "diagnostics": [dict(value) for value in diagnostics],
        "downstream_obligation": dict(downstream_obligation) if downstream_obligation else None,
        "evidence_records": [dict(value) for value in evidence_records],
        "policy": policy_projection(claim_id),
    }


def _semantic_missing(claim_id: str, semantics: Mapping[str, Any]) -> list[str]:
    required = CLAIM_POLICIES[claim_id]["required_semantics"]
    return [str(key) for key in required if semantics.get(key) in (None, "", [], {})]


def _attributed_evaluation(
    claim_id: str,
    subject_ref: str,
    node: Mapping[str, Any],
    semantics: Mapping[str, Any],
) -> dict[str, Any]:
    missing = _semantic_missing(claim_id, semantics)
    rationale = str(node.get("engineering_rationale") or "").strip()
    assumptions = [str(item) for item in node.get("assumptions") or [] if str(item).strip()]
    if missing or not rationale or not assumptions:
        details = []
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
        "reviewer_identity": str(node.get("reviewer_identity") or "constructability_engineer"),
        "premises": assumptions,
        "derivation_method": rationale,
        "semantic_facts": dict(semantics),
        "limitations": [str(item) for item in node.get("limitations") or []],
    }
    digest = sha256_json(record)
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="satisfied",
        facts=semantics,
        evidence_refs=[digest],
        limitations=record["limitations"],
        evidence_records=[{**record, "evidence_id": digest}],
    )


def _resolve_repo_path(repo_root: Path, source_ref: str) -> Path:
    root = repo_root.resolve(strict=True)
    candidate = Path(source_ref)
    path = candidate if candidate.is_absolute() else root / candidate
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ClaimEvaluationError("Repository source escaped repo root") from exc
    if not resolved.is_file():
        raise ClaimEvaluationError("Repository source is not a file")
    return resolved


def _load_semantic_source(path: Path) -> tuple[Any, str, bytes]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError:
        parsed = text
    return parsed, text, raw


def _artifact_source_evaluation(
    claim_id: str,
    subject_ref: str,
    node: Mapping[str, Any],
    semantics: Mapping[str, Any],
    repo_root: Path,
    semantic_check: Callable[[Any, str, Mapping[str, Any]], tuple[bool, dict[str, Any], str]],
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
    diagnostics: list[dict[str, Any]] = []
    limitations: list[str] = []
    for source in candidates:
        if source.get("mode") != "VERIFIED_ARTIFACT" or not isinstance(source.get("source_ref"), str):
            diagnostics.append({"code": "CE_CLAIM_SOURCE_MODE_INVALID"})
            continue
        try:
            path = _resolve_repo_path(repo_root, str(source["source_ref"]))
            parsed, text, raw = _load_semantic_source(path)
        except (OSError, ClaimEvaluationError) as exc:
            limitations.append(str(exc))
            diagnostics.append({"code": "CE_CLAIM_SOURCE_UNAVAILABLE"})
            continue
        supported, facts, reason = semantic_check(parsed, text, semantics)
        source_digest = hashlib.sha256(raw).hexdigest()
        if not supported:
            limitations.append(reason)
            diagnostics.append(
                {
                    "code": "CE_CLAIM_FILE_INTEGRITY_WITHOUT_SEMANTIC_SUPPORT",
                    "source_ref": str(source["source_ref"]),
                    "source_bytes_sha256": source_digest,
                }
            )
            continue
        record = {
            "mode": "VERIFIED_ARTIFACT",
            "claim_id": claim_id,
            "subject_ref": subject_ref,
            "source_ref": str(source["source_ref"]),
            "source_identity": str(source.get("source_identity") or source["source_ref"]),
            "source_bytes_sha256": source_digest,
            "semantic_facts": facts,
            "verification": "claim_specific_semantic_parse",
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
        limitations=limitations or ["No candidate source semantically supported the claim."],
        diagnostics=diagnostics,
    )


def _semantic_tokens(value: Any) -> list[str]:
    tokens: list[str] = []
    if isinstance(value, Mapping):
        for child in value.values():
            tokens.extend(_semantic_tokens(child))
    elif isinstance(value, list):
        for child in value:
            tokens.extend(_semantic_tokens(child))
    elif isinstance(value, (str, int, float)) and str(value).strip():
        tokens.append(str(value))
    return tokens


def _geometry_source_check(parsed: Any, text: str, semantics: Mapping[str, Any]) -> tuple[bool, dict[str, Any], str]:
    missing = _semantic_missing("geometry", semantics)
    if missing:
        return False, {}, f"Geometry semantics are incomplete: {', '.join(missing)}"
    binding_tokens = _semantic_tokens(semantics.get("anchor_model"))
    subject_token = semantics.get("subject_token")
    if isinstance(subject_token, str) and subject_token:
        binding_tokens.append(subject_token)
    if not binding_tokens or not any(token in text for token in binding_tokens):
        return False, {}, "Source file does not contain the claimed geometry subject/anchor semantics."
    return True, dict(semantics), ""


def _overlay_source_check(parsed: Any, text: str, semantics: Mapping[str, Any]) -> tuple[bool, dict[str, Any], str]:
    missing = _semantic_missing("overlay_strategy", semantics)
    if missing:
        return False, {}, f"Overlay semantics are incomplete: {', '.join(missing)}"
    tokens = [
        str(semantics["containment_model"]),
        str(semantics["positioning_model"]),
        str(semantics["stacking_model"]),
    ]
    if not all(token in text for token in tokens):
        return False, {}, "Source lacks containment, positioning, or stacking semantics."
    return True, dict(semantics), ""


def _ui_source_check(parsed: Any, text: str, semantics: Mapping[str, Any]) -> tuple[bool, dict[str, Any], str]:
    control_path = semantics.get("control_path")
    if not isinstance(control_path, str) or not control_path:
        return False, {}, "Exact UI control path is missing from claim semantics."
    if control_path not in text:
        return False, {}, "Repository file exists but does not contain the claimed UI control path."
    return True, {"control_path": control_path}, ""


def _asset_source_check(parsed: Any, text: str, semantics: Mapping[str, Any]) -> tuple[bool, dict[str, Any], str]:
    suitability = semantics.get("subject_suitability")
    subject_token = semantics.get("subject_token")
    if not isinstance(suitability, str) or not suitability:
        return False, {}, "Asset suitability rationale is missing."
    if isinstance(subject_token, str) and subject_token and subject_token not in text:
        return False, {}, "Asset source exists but is not bound to the claimed subject."
    return True, {"subject_suitability": suitability, "subject_token": subject_token}, ""


def evaluate_geometry(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "geometry"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if _candidate_sources(node, claim_id):
        return _artifact_source_evaluation(
            claim_id, context["subject_ref"], node, semantics, context["repo_root"], _geometry_source_check
        )
    return _attributed_evaluation(claim_id, context["subject_ref"], node, semantics)


def evaluate_overlay_strategy(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "overlay_strategy"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if _candidate_sources(node, claim_id):
        return _artifact_source_evaluation(
            claim_id, context["subject_ref"], node, semantics, context["repo_root"], _overlay_source_check
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
        _ui_source_check,
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
        _asset_source_check,
    )


def evaluate_placeholder_policy(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = "placeholder_policy"
    node = _draft_node(context["review_draft"], context["subject_ref"])
    semantics = _semantics(node, claim_id)
    if "premises" not in semantics:
        semantics["premises"] = list(node.get("assumptions") or [])
    if "derivation_method" not in semantics:
        semantics["derivation_method"] = str(node.get("engineering_rationale") or "")
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
                "Canonical Architect approval is absent or is bound to another candidate or subject."
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
    "responsive_behavior": {"ce-responsive-evaluator", "browser-responsive-check"},
    "accessibility": {"ce-accessibility-evaluator", "axe-core"},
    "QA": {"ce-qa-evaluator", "pytest", "playwright"},
}


def _runtime_evaluation(context: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = str(context["claim_id"])
    subject_ref = str(context["subject_ref"])
    expected_target = str(
        _semantics(_draft_node(context["review_draft"], subject_ref), claim_id).get("target_identity")
        or subject_ref
    )
    matching = [
        dict(item)
        for item in context.get("runtime_results") or []
        if isinstance(item, Mapping)
        and item.get("claim_id") == claim_id
        and item.get("subject_ref") == subject_ref
    ]
    for result in matching:
        captured = result.get("captured_result")
        digest = result.get("result_digest")
        evaluator_id = result.get("evaluator_id")
        method = result.get("method_or_command")
        execution_status = result.get("execution_status")
        exit_code = result.get("exit_code")
        target = result.get("target_identity")
        limitations = result.get("limitations")
        structurally_actual = (
            evaluator_id in KNOWN_RUNTIME_EVALUATORS[claim_id]
            and isinstance(method, str)
            and bool(method)
            and execution_status == "success"
            and exit_code == 0
            and target == expected_target
            and isinstance(captured, Mapping)
            and isinstance(digest, str)
            and digest == sha256_json(captured)
            and isinstance(limitations, list)
        )
        if not structurally_actual:
            continue
        record = {
            "mode": "VERIFIED_TOOL_EXECUTION",
            "claim_id": claim_id,
            "subject_ref": subject_ref,
            "evaluator_id": evaluator_id,
            "method_or_command": method,
            "target_identity": target,
            "execution_status": execution_status,
            "exit_code": exit_code,
            "result_digest": digest,
            "captured_result": dict(captured),
            "limitations": list(limitations),
        }
        evidence_id = sha256_json(record)
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="satisfied",
            facts={"target_identity": target, "result_digest": digest},
            evidence_refs=[evidence_id],
            limitations=record["limitations"],
            evidence_records=[{**record, "evidence_id": evidence_id}],
        )

    obligation = {
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "consumer_stage": "responsive_or_builder_runtime",
        "required_test": f"Execute the repository-supported {claim_id} evaluator for {subject_ref}.",
        "blocking_behavior": "block_builder_handoff",
        "completion_criteria": "A known evaluator returns success for the exact target with captured result digest.",
    }
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="downstream_validation_required",
        limitations=["No actual repository-supported execution result was captured."],
        diagnostics=[{"code": "CE_CLAIM_RUNTIME_EXECUTION_REQUIRED"}],
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
    runtime_results: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if claim_id not in CLAIM_POLICIES or claim_id not in EVALUATORS:
        raise ClaimEvaluationError(f"Unknown claim evaluator: {claim_id}")
    repo_root = repository_sources.get("repo_root")
    if not isinstance(repo_root, Path):
        repo_root = Path(str(repo_root))
    context = {
        "claim_id": claim_id,
        "subject_ref": subject,
        "obligation": dict(obligation),
        "architect_intake": architect_intake,
        "source_bundle": source_bundle,
        "review_draft": review_draft,
        "repo_root": repo_root,
        "runtime_results": list(runtime_results),
    }
    return EVALUATORS[claim_id](context)
