from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from validator.claim_evaluators import evaluate_claim
from validator.engine import validate_document
from validator.intermediate_results import evaluate_all
from validator.payload_assembler import canonical_bytes
from validator.verified_constructability import (
    EvaluationBoundaryError,
    assemble_verified_ce_stage_payload,
    verified_payload_data,
)
from deterministic_runtime_support import (
    canonical_bundle,
    canonical_draft,
    canonical_intake,
    evaluation_run,
    verified_inputs,
)

ROOT = Path(__file__).resolve().parents[1]


def _responsive_draft() -> dict:
    draft = canonical_draft()
    node = draft["reviewed_nodes"][0]
    node["proposed_action"] = "responsive behavior"
    node["claim_semantics"]["responsive_strategy"] = {
        "breakpoint_strategy": "mobile-first",
        "layout_adaptation": "stack below 768px",
        "derivation_method": "retained layout analysis",
    }
    node["claim_semantics"]["responsive_behavior"] = {
        "target_identity": "node-root"
    }
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "set_responsive",
        "target_node": "node-root",
        "parameters": {
            "layout": "stacked",
            "breakpoints": "mobile-first",
            "target_identity": "node-root",
        },
    }
    return draft


def test_requested_claims_are_additive_and_vacuous_success_is_impossible() -> None:
    verified_intake, verified_bundle, _, _ = verified_inputs()
    draft = canonical_draft()
    results = evaluate_all(
        verified_intake["data"], verified_bundle["data"], draft, repo_root=ROOT
    )
    assert results["obligations"]["required_claims_by_node"]["node-root"] == [
        "geometry"
    ]
    assert results["dependency_result"]["rows"][0]["status"] == "satisfied"


def test_plain_data_run_recomputes_to_verified_payload() -> None:
    run, intake_bytes, bundle_bytes = evaluation_run(ROOT)
    payload = verified_payload_data(
        run,
        repo_root=ROOT,
        source_intake_bytes=intake_bytes,
        source_bundle_bytes=bundle_bytes,
    )
    assert payload["schema_id"] == "ev4-ce-stage-payload@1.1.0"
    assert payload["payload_status"] == "complete"
    assert payload["builder_package_emitted"] is True
    assert (
        payload["builder_executable_package"]["schema"]
        == "ev4-builder-executable-package@1.0.0"
    )


def test_successor_payload_schema_and_semantics_validate() -> None:
    run, intake_bytes, bundle_bytes = evaluation_run(ROOT)
    payload = verified_payload_data(
        run,
        repo_root=ROOT,
        source_intake_bytes=intake_bytes,
        source_bundle_bytes=bundle_bytes,
    )
    result = validate_document(payload, repo_root=ROOT, mode="full")
    assert result["passed"], result


def test_identical_inputs_produce_byte_identical_results_and_payload() -> None:
    verified_intake, verified_bundle, _, _ = verified_inputs()
    first = assemble_verified_ce_stage_payload(
        draft=canonical_draft(),
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    second = assemble_verified_ce_stage_payload(
        draft=canonical_draft(),
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    assert canonical_bytes(first) == canonical_bytes(second)


def test_modified_final_payload_cannot_authorize_handoff() -> None:
    run, intake_bytes, bundle_bytes = evaluation_run(ROOT)
    tampered = copy.deepcopy(run)
    tampered["payload"]["builder_package_emitted"] = False
    with pytest.raises(EvaluationBoundaryError, match="CE_PAYLOAD_FIDELITY_MISMATCH"):
        verified_payload_data(
            tampered,
            repo_root=ROOT,
            source_intake_bytes=intake_bytes,
            source_bundle_bytes=bundle_bytes,
        )


def test_source_bytes_are_rechecked_before_projection() -> None:
    run, intake_bytes, bundle_bytes = evaluation_run(ROOT)
    with pytest.raises(EvaluationBoundaryError, match="intake bytes changed"):
        verified_payload_data(
            run,
            repo_root=ROOT,
            source_intake_bytes=intake_bytes + b"\n",
            source_bundle_bytes=bundle_bytes,
        )


def test_review_draft_schema_contains_no_authoritative_result_fields() -> None:
    schema = json.loads(
        (ROOT / "schemas/ce_review_draft.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    serialized = json.dumps(schema, sort_keys=True)
    for forbidden in (
        "geometry_proven",
        "constructability_status",
        "builder_package_emitted",
        "payload_status",
        "handoff_allowed",
    ):
        assert forbidden not in serialized


def test_explicit_no_claim_node_is_derived_not_vacuously_assumed() -> None:
    results = evaluate_all(
        canonical_intake(), canonical_bundle(), canonical_draft(), repo_root=ROOT
    )
    assert results["obligations"]["required_claims_by_node"]["node-child"] == []
    assert results["obligations"]["explicit_no_claim_nodes"] == ["node-child"]


def test_complete_overlay_engineering_evaluation_is_supported() -> None:
    draft = canonical_draft()
    node = draft["reviewed_nodes"][0]
    node["claim_semantics"]["overlay_strategy"] = {
        "containment_model": "node-root contains overlay-layer",
        "positioning_model": "absolute within retained relative parent",
        "stacking_model": "z-index 2 below controls",
        "derivation_method": "bounded containment and stacking analysis",
    }
    row = evaluate_claim(
        "overlay_strategy",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        draft,
        {"repo_root": ROOT},
    )
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["mode"] == "ATTRIBUTED_ENGINEERING_JUDGMENT"


def test_architect_owned_interaction_approval_is_read_from_canonical_intake() -> None:
    bundle = canonical_bundle()
    intake = canonical_intake(bundle=bundle)
    intake["architect_intent_preserved"]["interaction_intent"] = {
        "status": "approved",
        "selected_candidate_id": "ARCH-FAM-C",
        "subject_refs": ["node-root"],
    }
    row = evaluate_claim(
        "interaction_approval",
        "node-root",
        {},
        intake,
        bundle,
        canonical_draft(),
        {"repo_root": ROOT},
    )
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["mode"] == "VERIFIED_ARCHITECT_DECISION"


def test_architect_decision_for_another_candidate_does_not_satisfy_claim() -> None:
    bundle = canonical_bundle()
    intake = canonical_intake(bundle=bundle)
    intake["architect_intent_preserved"]["interaction_intent"] = {
        "status": "approved",
        "selected_candidate_id": "OTHER",
        "subject_refs": ["node-root"],
    }
    row = evaluate_claim(
        "interaction_approval",
        "node-root",
        {},
        intake,
        bundle,
        canonical_draft(),
        {"repo_root": ROOT},
    )
    assert row["status"] == "architect_decision_required"


def test_responsive_without_execution_becomes_final_gate_obligation() -> None:
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": ROOT},
    )
    assert row["status"] == "downstream_validation_required"
    assert row["blocking"] is False
    assert row["downstream_obligation"]["blocking_boundary"] == "final_project_gate"
    assert row["downstream_obligation"]["blocks_builder_handoff"] is False


def test_authored_equal_expected_and_observed_values_are_not_execution() -> None:
    request = {
        "claim_id": "responsive_behavior",
        "subject_ref": "node-root",
        "evaluator_id": "ce-responsive-evaluator",
        "target_identity": "node-root",
        "input_ref": "declared-responsive.json",
    }
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": ROOT},
        [request],
    )
    assert row["status"] == "downstream_validation_required"
    assert row["evidence_refs"] == []
    assert row["evidence_records"][0]["mode"] == "DOWNSTREAM_TEST_OBLIGATION"


def test_complete_multi_node_review_and_first_safe_batch_are_derived() -> None:
    run, _, _ = evaluation_run(ROOT)
    results = run["evaluation_results"]
    assert results["review_result"]["required_nodes"] == ["node-child", "node-root"]
    assert results["strategy_result"]["first_safe_batch_complete"] is True
    package = run["payload"]["builder_executable_package"]
    assert [
        action["target_node"]
        for action in package["first_safe_builder_batch"]["actions"]
    ] == ["node-root", "node-child"]


def test_runtime_obligation_allows_builder_but_blocks_final_completion() -> None:
    run, _, _ = evaluation_run(ROOT, draft=_responsive_draft())
    payload = run["payload"]
    assert payload["builder_package_emitted"] is True
    assert payload["downstream_test_obligations"][0]["status"] == "required"
    lifecycle = next(
        item["result"]
        for item in payload["extension_records"]
        if item.get("kind") == "lifecycle_status"
    )
    assert lifecycle["runtime_validated"] is False
    assert lifecycle["final_project_gate"] == "blocked"
    assert lifecycle["production_ready"] is False


def test_architect_unknown_is_preserved_and_blocks_builder_handoff() -> None:
    verified_intake, verified_bundle, _, _ = verified_inputs()
    verified_intake = copy.deepcopy(verified_intake)
    verified_intake["data"]["unresolved_evidence"] = [
        {
            "unresolved_id": "ARCH-UNK-1",
            "owner": "architect",
            "reason": "Source geometry remains unresolved.",
            "state": "insufficient_evidence",
            "evidence_refs": ["architect-structure-root"],
        }
    ]
    verified_intake["canonical_sha256"] = __import__("hashlib").sha256(
        canonical_bytes(verified_intake["data"])
    ).hexdigest()
    draft = canonical_draft()
    draft["architecture_echo"]["architect_unknown_ids"] = ["ARCH-UNK-1"]
    run = assemble_verified_ce_stage_payload(
        draft=draft,
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    assert run["payload"]["builder_package_emitted"] is False
    assert "ARCH-UNK-1" in {
        item["unresolved_id"] for item in run["payload"]["unresolved_evidence"]
    }
