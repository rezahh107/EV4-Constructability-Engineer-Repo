from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .action_ir import ActionIRValidationError, normalized_review_draft
from .claim_policy_registry import CLAIM_POLICIES, POST_BUILDER_RUNTIME
from .intermediate_results import derive_implementation_strategy_coverage, evaluate_all
from .payload_assembler import assemble_ce_stage_payload, canonical_bytes, sha256_json
from .runtime_obligations import RuntimeObligationError, derive_runtime_obligations, lifecycle_status


class PayloadFidelityError(ValueError):
    """Raised when persisted output differs from deterministic CE recomputation."""


def _phase_aware_dependency_result(dependency_result: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(dict(dependency_result))
    rows = [copy.deepcopy(dict(item)) for item in result.get("rows") or [] if isinstance(item, Mapping)]
    runtime_pending_rows: list[dict[str, Any]] = []
    for row in rows:
        policy = CLAIM_POLICIES[str(row["claim_id"])]
        row["lifecycle_phase"] = policy["lifecycle_phase"]
        if policy["lifecycle_phase"] != POST_BUILDER_RUNTIME:
            continue
        if row.get("status") == "satisfied":
            row["blocking"] = False
            row["downstream_obligation"] = None
        else:
            row["blocking"] = False
            row["evidence_refs"] = []
            runtime_pending_rows.append(row)
    obligations = derive_runtime_obligations(runtime_pending_rows)
    pre_builder_rows = [row for row in rows if row["lifecycle_phase"] != POST_BUILDER_RUNTIME]
    result["rows"] = rows
    result["blocking_dependencies"] = sorted(f"{row['subject_ref']}:{row['claim_id']}:{row['status']}" for row in pre_builder_rows if row.get("status") not in {"satisfied", "not_applicable"})
    result["unresolved_evidence"] = [{"unresolved_id": f"unresolved-{row['subject_ref']}-{row['claim_id']}", "claim_ref": f"{row['subject_ref']}:{row['claim_id']}", "owner": row["authority_owner"], "reason": row["status"], "evidence_refs": list(row.get("evidence_refs") or []), "limitations": list(row.get("limitations") or [])} for row in pre_builder_rows if row.get("status") not in {"satisfied", "not_applicable"}]
    result["downstream_test_obligations"] = obligations
    result["status"] = "blocked" if result["blocking_dependencies"] or result.get("diagnostics") else "complete"
    return json.loads(canonical_bytes(result)), obligations


def _action_ir_with_effects(action_ir: Sequence[Mapping[str, Any]], obligations: Mapping[str, Any]) -> list[dict[str, Any]]:
    effects = obligations.get("action_effects")
    records = effects.get("records") if isinstance(effects, Mapping) else []
    by_id = {str(item.get("action_id")): dict(item) for item in records or [] if isinstance(item, Mapping) and isinstance(item.get("action_id"), str)}
    result: list[dict[str, Any]] = []
    for item in action_ir:
        value = copy.deepcopy(dict(item))
        effect = by_id.get(str(value["action_id"]), {})
        value["derived_effects"] = {**copy.deepcopy(dict(value.get("derived_effects") or {})), "class_result": copy.deepcopy(effect.get("class_effect")), "structure_result": copy.deepcopy(effect.get("structure_effect")), "forbidden_work_conflicts": copy.deepcopy(list(effect.get("forbidden_work_conflicts") or [])), "blocked": bool(effect.get("blocked"))}
        result.append(value)
    return json.loads(canonical_bytes(result))


def _extension(payload: dict[str, Any], kind: str, value: Any) -> None:
    payload.setdefault("extension_records", []).append({"kind": kind, "result": copy.deepcopy(value)})


def evaluate_ce_transaction(*, architect_intake: Mapping[str, Any], source_bundle: Mapping[str, Any], review_draft: Mapping[str, Any], repo_root: Path, runtime_execution_requests: Sequence[Mapping[str, Any]] = (), input_metadata: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Canonical API, CLI, fidelity-replay, and exporter evaluation path."""
    normalized_draft, raw_action_ir = normalized_review_draft(review_draft)
    results = evaluate_all(architect_intake, source_bundle, normalized_draft, repo_root=repo_root, runtime_execution_requests=runtime_execution_requests)
    dependency, runtime_obligations = _phase_aware_dependency_result(results["dependency_result"])
    results["dependency_result"] = dependency
    action_ir = _action_ir_with_effects(raw_action_ir, results["obligations"])
    results["obligations"] = copy.deepcopy(dict(results["obligations"]))
    results["obligations"]["action_ir"] = action_ir
    strategy = derive_implementation_strategy_coverage(normalized_draft, results["obligations"], results["identity_result"], dependency)
    ir_hidden = sorted({str(path) for item in action_ir for path in item.get("hidden_decision_paths") or []})
    if ir_hidden:
        strategy["hidden_builder_decisions"] = ir_hidden
        strategy["builder_decisions_required"] = len(ir_hidden)
        strategy["first_safe_batch_complete"] = False
        strategy.setdefault("diagnostics", []).append({"code": "CE_STRATEGY_HIDDEN_BUILDER_DECISION", "paths": ir_hidden})
        strategy["status"] = "blocked"
    strategy["action_ir"] = action_ir
    results["strategy_result"] = json.loads(canonical_bytes(strategy))
    results["runtime_obligations"] = runtime_obligations
    results["claim_classification"] = {claim_id: {"lifecycle_phase": policy["lifecycle_phase"], "builder_handoff_effect": policy["builder_handoff_effect"], "final_completion_effect": policy["final_completion_effect"]} for claim_id, policy in sorted(CLAIM_POLICIES.items())}
    payload = assemble_ce_stage_payload(results["identity_result"], results["review_result"], dependency, results["strategy_result"], {"architect_intake": architect_intake, "source_bundle": source_bundle, "review_draft": normalized_draft, "runtime_execution_requests": [dict(item) for item in runtime_execution_requests], "input_metadata": dict(input_metadata or {})})
    payload["downstream_test_obligations"] = copy.deepcopy(runtime_obligations)
    builder_ready = payload.get("builder_package_emitted") is True
    lifecycle = lifecycle_status(builder_ready=builder_ready, obligations=runtime_obligations)
    package = payload.get("builder_executable_package")
    if isinstance(package, dict):
        package["normalized_action_ir"] = copy.deepcopy(action_ir)
        package["runtime_obligations"] = copy.deepcopy(runtime_obligations)
        package["first_safe_builder_batch"]["actions"] = [{"action_id": item["action_id"], "action_type": item["action_type"], "target_node": item["target_node"], "parameters": copy.deepcopy(item["normalized_parameters"]), "requires_decision": item["decision_state"] != "resolved"} for item in action_ir]
    payload["boundary_assertions"]["ce_did_not_claim_responsive_completion"] = not any(row.get("claim_id") == "responsive_behavior" and row.get("status") == "satisfied" for row in dependency.get("rows") or [] if isinstance(row, Mapping))
    payload["boundary_assertions"]["production_ready"] = False
    _extension(payload, "normalized_action_ir", action_ir)
    _extension(payload, "runtime_obligations", runtime_obligations)
    _extension(payload, "lifecycle_status", lifecycle)
    payload["authority_resolution_digest"] = sha256_json(payload["authority_resolution"])
    payload = json.loads(canonical_bytes(payload))
    results["lifecycle_status"] = lifecycle
    results["normalized_review_draft"] = normalized_draft
    return payload, json.loads(canonical_bytes(results))


def recompute_expected_payload(*, architect_intake: Mapping[str, Any], source_bundle: Mapping[str, Any], review_draft: Mapping[str, Any], repo_root: Path, runtime_execution_requests: Sequence[Mapping[str, Any]] = (), input_metadata: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        return evaluate_ce_transaction(architect_intake=architect_intake, source_bundle=source_bundle, review_draft=review_draft, repo_root=repo_root, runtime_execution_requests=runtime_execution_requests, input_metadata=input_metadata)
    except (ActionIRValidationError, RuntimeObligationError) as exc:
        raise PayloadFidelityError(str(exc)) from exc


def compare_persisted_payload(persisted_payload: Mapping[str, Any], expected_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    if canonical_bytes(persisted_payload) == canonical_bytes(expected_payload):
        return []
    diagnostics: list[dict[str, Any]] = []
    for key in ("payload_status", "architecture_identity", "constructability_review", "implementation_strategy_map", "builder_executable_package", "builder_package_emitted", "authority_resolution", "unresolved_evidence", "downstream_test_obligations", "boundary_assertions"):
        if canonical_bytes(persisted_payload.get(key)) != canonical_bytes(expected_payload.get(key)):
            diagnostics.append({"code": "CE_PAYLOAD_FIDELITY_MISMATCH", "path": f"$.{key}", "message": f"Persisted {key} differs from deterministic recomputation."})
    if not diagnostics:
        diagnostics.append({"code": "CE_PAYLOAD_FIDELITY_MISMATCH", "path": "$", "message": "Persisted payload differs from deterministic recomputation."})
    return diagnostics


def validate_payload_fidelity(persisted_payload: Mapping[str, Any], *, architect_intake: Mapping[str, Any], source_bundle: Mapping[str, Any], review_draft: Mapping[str, Any], repo_root: Path, runtime_execution_requests: Sequence[Mapping[str, Any]] = (), input_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    expected, results = recompute_expected_payload(architect_intake=architect_intake, source_bundle=source_bundle, review_draft=review_draft, repo_root=repo_root, runtime_execution_requests=runtime_execution_requests, input_metadata=input_metadata)
    diagnostics = compare_persisted_payload(persisted_payload, expected)
    return {"passed": not diagnostics, "diagnostics": diagnostics, "expected_payload": expected, "evaluation_results": results}


def validate_export_fidelity(export: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    payload = export.get("final_stage_bundle", {}).get("payload", {}).get("data") if isinstance(export.get("final_stage_bundle"), Mapping) else None
    if not isinstance(payload, Mapping):
        return {"passed": False, "diagnostics": [{"code": "CE_EXPORT_FIDELITY_PAYLOAD_MISSING", "path": "$.final_stage_bundle.payload.data", "message": "Export does not contain a CE Payload to compare."}]}
    return validate_payload_fidelity(payload, **kwargs)


def assert_payload_fidelity(*args: Any, **kwargs: Any) -> None:
    report = validate_payload_fidelity(*args, **kwargs)
    if report["diagnostics"]:
        first = report["diagnostics"][0]
        raise PayloadFidelityError(f"{first['code']} at {first['path']}: {first['message']}")


def cloned(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


__all__ = ["PayloadFidelityError", "assert_payload_fidelity", "compare_persisted_payload", "evaluate_ce_transaction", "recompute_expected_payload", "validate_export_fidelity", "validate_payload_fidelity"]
