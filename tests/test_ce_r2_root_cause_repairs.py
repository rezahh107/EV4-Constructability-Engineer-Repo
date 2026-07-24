from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from validator.action_ir import ActionIRValidationError, normalize_action
from validator.claim_evaluators import evaluate_claim, sha256_json
from validator.intermediate_results import evaluate_all
from validator.payload_fidelity import compare_persisted_payload, recompute_expected_payload
from validator.runtime_execution import execute_runtime_requests, execution_transaction_id
from deterministic_runtime_support import canonical_bundle, canonical_draft, canonical_intake

ROOT = Path(__file__).resolve().parents[1]


def _results(
    draft: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
    intake: dict[str, Any] | None = None,
):
    bundle = bundle or canonical_bundle()
    intake = intake or canonical_intake(bundle=bundle)
    return evaluate_all(intake, bundle, draft, repo_root=ROOT)


def _effect(result: dict[str, Any], action_id: str) -> dict[str, Any]:
    return next(
        item
        for item in result["obligations"]["action_effects"]["records"]
        if item["action_id"] == action_id
    )


def _completed_runtime_record(*, digest_matches: bool) -> dict[str, Any]:
    captured = {"passed": True, "cases": [{"viewport": "mobile"}]}
    return {
        "claim_id": "responsive_behavior",
        "subject_ref": "node-root",
        "evaluator_id": "ce-responsive-evaluator",
        "method_or_command": "caller-described command",
        "target_identity": "node-root",
        "execution_status": "success",
        "exit_code": 0,
        "captured_result": captured,
        "result_digest": sha256_json(captured) if digest_matches else "0" * 64,
        "limitations": [],
    }


@pytest.mark.parametrize("digest_matches", [True, False])
def test_caller_created_completed_runtime_mapping_fails_closed(
    digest_matches: bool,
) -> None:
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": ROOT},
        [_completed_runtime_record(digest_matches=digest_matches)],
    )
    assert row["status"] == "downstream_validation_required"
    assert row["evidence_refs"] == []
    assert row["diagnostics"][0]["code"] == "CE_CLAIM_RUNTIME_REQUEST_REJECTED"


def test_runtime_declaration_batch_has_no_execution_results(tmp_path: Path) -> None:
    request = {
        "claim_id": "responsive_behavior",
        "subject_ref": "node-root",
        "evaluator_id": "ce-responsive-evaluator",
        "target_identity": "node-root",
        "input_ref": "responsive-spec.json",
    }
    transaction = execution_transaction_id(
        architect_intake=canonical_intake(),
        source_bundle=canonical_bundle(),
        review_draft=canonical_draft(),
        requests=[request],
    )
    batch = execute_runtime_requests(
        repo_root=tmp_path, transaction_id=transaction, requests=[request]
    )
    assert batch.results == ()
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": tmp_path},
        execution_batch=batch,
        execution_transaction_id_override=transaction,
    )
    assert row["status"] == "downstream_validation_required"
    assert row["downstream_obligation"]["status"] == "required"


def test_apply_class_unapproved_class_is_derived_when_draft_flags_are_false() -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "apply_class",
        "target_node": "node-root",
        "parameters": {"class_name": "unapproved__class"},
    }
    draft["reviewed_nodes"][0]["requires_class_change"] = False
    result = _results(draft)
    effect = _effect(result, "action-root")
    assert effect["changes_approved_class_set"] is True
    assert effect["blocked"] is True
    assert "CE_ACTION_EFFECT_UNAPPROVED_CLASS" in {
        item["code"] for item in effect["diagnostics"]
    }


@pytest.mark.parametrize(
    "parameters",
    [
        {"remove_class": "smart-home__section"},
        {
            "replace_class": {
                "from": "smart-home__section",
                "to": "replacement__class",
            }
        },
    ],
)
def test_apply_class_remove_or_replace_approved_class_fails_closed(
    parameters: dict[str, Any],
) -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "apply_class",
        "target_node": "node-root",
        "parameters": parameters,
    }
    effect = _effect(_results(draft), "action-root")
    assert "smart-home__section" in effect["class_effect"][
        "removed_approved_class_names"
    ]
    assert effect["blocked"] is True


def test_approved_class_application_preserves_architect_class_set() -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "apply_class",
        "target_node": "node-root",
        "parameters": {"class_name": "smart-home__section"},
    }
    effect = _effect(_results(draft), "action-root")
    assert effect["class_effect"]["applied_class_names"] == [
        "smart-home__section"
    ]
    assert effect["changes_approved_class_set"] is False
    assert effect["blocked"] is False


def test_create_element_outside_build_tree_without_permission_fails_closed() -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "create_element",
        "target_node": "node-root",
        "parameters": {
            "produced_node_id": "node-new",
            "parent_node_id": "node-root",
            "element_type": "Container",
        },
    }
    effect = _effect(_results(draft), "action-root")
    assert effect["changes_structure"] is True
    assert effect["structure_effect"]["permission_granted"] is False


def _three_node_context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bundle = canonical_bundle()
    nodes = bundle["payload"]["approved_structure_model"]["structure_nodes"]
    nodes[0]["children"].append("node-sibling")
    nodes.append(
        {
            "node_id": "node-sibling",
            "node_kind": "container",
            "parent_node_id": "node-root",
            "children": [],
            "evidence_refs": ["architect-structure-sibling"],
        }
    )
    intake = canonical_intake(bundle=bundle)
    intake["structure_projection"]["nodes"][0]["children"].append("node-sibling")
    intake["structure_projection"]["nodes"].append(
        {
            "source_node_id": "node-sibling",
            "node_kind": "container",
            "parent_node_id": "node-root",
            "children": [],
        }
    )
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = sha256_json(
        bundle
    )
    draft = canonical_draft()
    draft["architecture_echo"]["build_tree_node_ids"] = [
        "node-child",
        "node-root",
        "node-sibling",
    ]
    sibling_review = copy.deepcopy(draft["reviewed_nodes"][1])
    sibling_review["node_id"] = "node-sibling"
    draft["reviewed_nodes"].append(sibling_review)
    draft["implementation_strategy_proposal"]["strategies"].append(
        {
            "strategy_id": "strategy-sibling",
            "node_id": "node-sibling",
            "strategy_selected": "preserve",
            "rationale": "Retain the accepted sibling node.",
        }
    )
    draft["builder_action_proposals"].append(
        {
            "action_id": "action-sibling",
            "action_type": "preserve_existing",
            "target_node": "node-sibling",
            "parameters": {},
        }
    )
    return bundle, intake, draft


def test_parent_child_identity_change_is_derived_despite_false_draft_flag() -> None:
    bundle, intake, draft = _three_node_context()
    draft["builder_action_proposals"][1] = {
        "action_id": "action-child",
        "action_type": "reparent_element",
        "target_node": "node-child",
        "parameters": {"new_parent_node_id": "node-sibling"},
    }
    draft["reviewed_nodes"][1]["requires_structure_change"] = False
    effect = _effect(_results(draft, bundle=bundle, intake=intake), "action-child")
    assert effect["structure_effect"]["parent_changes"] == [
        {
            "node_id": "node-child",
            "from_parent": "node-root",
            "to_parent": "node-sibling",
        }
    ]


def test_action_contradicting_canonical_forbidden_work_remains_blocked() -> None:
    bundle = canonical_bundle()
    bundle["payload"]["architect_intent"]["extension_permissions"] = [
        {
            "status": "approved",
            "selected_candidate_id": "ARCH-FAM-C",
            "subject_ref": "node-root",
            "effect_kind": "structure",
            "allowed_action_types": ["create_element"],
            "allowed_node_ids": ["node-new"],
        }
    ]
    intake = canonical_intake(bundle=bundle)
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "create_element",
        "target_node": "node-root",
        "parameters": {
            "produced_node_id": "node-new",
            "parent_node_id": "node-root",
            "element_type": "Container",
        },
    }
    effect = _effect(_results(draft, bundle=bundle, intake=intake), "action-root")
    assert effect["structure_effect"]["permission_granted"] is True
    assert "no_hidden_redesign" in effect["forbidden_work_conflicts"]
    assert effect["blocked"] is True


@pytest.mark.parametrize(
    "action_type,parameters",
    [
        ("configure_layout", {"layout_model": "grid", "remove_class": "x"}),
        ("configure_layout", {"layout_model": "grid", "produced_node_id": "new"}),
        ("apply_class", {"class_names": ["x"], "new_parent_node_id": "other"}),
    ],
)
def test_effect_parameter_smuggling_is_rejected(
    action_type: str, parameters: dict[str, Any]
) -> None:
    with pytest.raises(ActionIRValidationError):
        normalize_action(
            {
                "action_id": "action-root",
                "action_type": action_type,
                "target_node": "node-root",
                "parameters": parameters,
            }
        )


def test_facts_envelope_copied_from_draft_is_not_verified(tmp_path: Path) -> None:
    semantics = canonical_draft()["reviewed_nodes"][0]["claim_semantics"]["geometry"]
    source = tmp_path / "geometry.json"
    source.write_text(json.dumps({"facts": copy.deepcopy(semantics)}), encoding="utf-8")
    draft = canonical_draft()
    draft["reviewed_nodes"][0]["candidate_source_refs"] = [
        {
            "claim_id": "geometry",
            "mode": "VERIFIED_ARTIFACT",
            "source_ref": "geometry.json",
        }
    ]
    row = evaluate_claim(
        "geometry",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        draft,
        {"repo_root": tmp_path},
    )
    assert row["status"] == "insufficient_evidence"
    assert row["evidence_refs"] == []


def test_original_geometry_source_positive(tmp_path: Path) -> None:
    source = tmp_path / "geometry.json"
    source.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "node-root",
                        "layout": {
                            "model": "css-grid",
                            "anchors": {"root": "node-root"},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    draft = canonical_draft()
    draft["reviewed_nodes"][0]["candidate_source_refs"] = [
        {
            "claim_id": "geometry",
            "mode": "VERIFIED_ARTIFACT",
            "source_ref": "geometry.json",
            "source_type": "json",
        }
    ]
    row = evaluate_claim(
        "geometry",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        draft,
        {"repo_root": tmp_path},
    )
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["verification"] == (
        "original_source_claim_specific_parser"
    )


def test_original_source_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "geometry.json"
    source.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "node-root",
                        "layout": {
                            "model": "css-grid",
                            "anchors": {"root": "node-root"},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    draft = canonical_draft()
    draft["reviewed_nodes"][0]["candidate_source_refs"] = [
        {
            "claim_id": "geometry",
            "mode": "VERIFIED_ARTIFACT",
            "source_ref": "geometry.json",
            "source_bytes_sha256": "0" * 64,
        }
    ]
    row = evaluate_claim(
        "geometry",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        draft,
        {"repo_root": tmp_path},
    )
    assert row["status"] == "insufficient_evidence"


def test_persisted_payload_cannot_claim_class_or_build_tree_preservation() -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "apply_class",
        "target_node": "node-root",
        "parameters": {"class_name": "unapproved__class"},
    }
    payload, _ = recompute_expected_payload(
        architect_intake=canonical_intake(),
        source_bundle=canonical_bundle(),
        review_draft=draft,
        repo_root=ROOT,
    )
    assert payload["architecture_identity"]["approved_class_names_unchanged"] is False
    assert payload["builder_executable_package"] is None
    tampered = copy.deepcopy(payload)
    tampered["architecture_identity"]["approved_class_names_unchanged"] = True
    assert compare_persisted_payload(tampered, payload)[0]["path"] == (
        "$.architecture_identity"
    )


def test_attributed_ce_engineering_judgment_remains_supported() -> None:
    row = evaluate_claim(
        "geometry",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": ROOT},
    )
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["mode"] == "ATTRIBUTED_ENGINEERING_JUDGMENT"


def test_deterministic_output_is_retained() -> None:
    first = _results(canonical_draft())
    second = _results(canonical_draft())
    assert first == second
