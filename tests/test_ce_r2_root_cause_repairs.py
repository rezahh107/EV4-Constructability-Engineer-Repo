from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from validator.claim_evaluators import evaluate_claim, sha256_json
from validator.intermediate_results import evaluate_all
from validator.payload_fidelity import compare_persisted_payload, recompute_expected_payload
from validator.runtime_execution import (
    execute_runtime_requests,
    execution_transaction_id,
)
from deterministic_runtime_support import (
    canonical_bundle,
    canonical_draft,
    canonical_intake,
)

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


def _binding(claim_id: str, subject_ref: str = "node-root") -> dict[str, Any]:
    intake = canonical_intake()
    return {
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "selected_candidate_id": "ARCH-FAM-C",
        "source_bundle_id": "bundle-1",
        "intake_digest": sha256_json(intake),
    }


def _artifact_row(
    tmp_path: Path,
    *,
    claim_id: str,
    filename: str,
    content: str,
    semantics: dict[str, Any],
) -> dict[str, Any]:
    (tmp_path / filename).write_text(content, encoding="utf-8")
    draft = canonical_draft()
    node = draft["reviewed_nodes"][0]
    node["candidate_source_refs"] = [
        {
            "claim_id": claim_id,
            "mode": "VERIFIED_ARTIFACT",
            "source_ref": filename,
        }
    ]
    node.setdefault("claim_semantics", {})[claim_id] = semantics
    return evaluate_claim(
        claim_id,
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        draft,
        {"repo_root": tmp_path},
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


def test_allowlisted_evaluator_and_success_exit_do_not_make_description_executed() -> None:
    record = _completed_runtime_record(digest_matches=True)
    assert record["evaluator_id"] == "ce-responsive-evaluator"
    assert record["exit_code"] == 0
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": ROOT},
        [record],
    )
    assert row["status"] == "downstream_validation_required"


def test_runtime_result_copied_from_another_transaction_is_ignored(
    tmp_path: Path,
) -> None:
    target = tmp_path / "responsive-target.json"
    target.write_text(
        json.dumps(
            {
                "schema_id": "ev4-ce-responsive-evaluation-target@1.0.0",
                "claim_id": "responsive_behavior",
                "subject_ref": "node-root",
                "target_identity": "node-root",
                "cases": [
                    {
                        "viewport": "mobile",
                        "expected_layout": "stacked",
                        "observed_layout": "stacked",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    request = {
        "claim_id": "responsive_behavior",
        "subject_ref": "node-root",
        "evaluator_id": "ce-responsive-evaluator",
        "target_identity": "node-root",
        "input_ref": target.name,
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
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": tmp_path},
        execution_batch=batch,
        execution_transaction_id_override="ce-execution-different-transaction",
    )
    assert row["status"] == "downstream_validation_required"
    assert row["evidence_refs"] == []


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
    assert result["identity_result"]["approved_classes_preserved"] is False


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
    result = _results(draft)
    effect = _effect(result, "action-root")
    assert "smart-home__section" in effect["class_effect"][
        "removed_approved_class_names"
    ]
    assert result["strategy_result"]["builder_actions_valid"] is False


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
    draft["reviewed_nodes"][0]["requires_structure_change"] = False
    result = _results(draft)
    effect = _effect(result, "action-root")
    assert effect["changes_structure"] is True
    assert effect["structure_effect"]["permission_granted"] is False
    assert result["identity_result"]["build_tree_nodes_preserved"] is False
    assert result["strategy_result"]["architect_amendment_required"] is True


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
    result = _results(draft, bundle=bundle, intake=intake)
    effect = _effect(result, "action-child")
    assert effect["structure_effect"]["parent_changes"] == [
        {
            "node_id": "node-child",
            "from_parent": "node-root",
            "to_parent": "node-sibling",
        }
    ]
    assert result["identity_result"]["build_tree_nodes_preserved"] is False


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
        "parameters": {"produced_node_id": "node-new", "parent_node_id": "node-root"},
    }
    result = _results(draft, bundle=bundle, intake=intake)
    effect = _effect(result, "action-root")
    assert effect["structure_effect"]["permission_granted"] is True
    assert "no_hidden_redesign" in effect["forbidden_work_conflicts"]
    assert "CE_ACTION_EFFECT_FORBIDDEN_WORK_CONFLICT" in {
        item["code"] for item in effect["diagnostics"]
    }


def test_unrelated_geometry_extract_with_node_token_fails_closed(tmp_path: Path) -> None:
    document = {
        "schema_id": "ev4-ce-geometry-extract@1.0.0",
        "source_role": "geometry_extract",
        "binding": _binding("geometry"),
        "facts": {"note": "node-root appears in unrelated prose"},
    }
    row = _artifact_row(
        tmp_path,
        claim_id="geometry",
        filename="geometry.json",
        content=json.dumps(document),
        semantics=canonical_draft()["reviewed_nodes"][0]["claim_semantics"]["geometry"],
    )
    assert row["status"] == "insufficient_evidence"


def test_overlay_words_in_unrelated_context_do_not_prove_overlay(tmp_path: Path) -> None:
    semantics = {
        "containment_model": "contained",
        "positioning_model": "absolute",
        "stacking_model": "z-index-10",
        "derivation_method": "structured extract",
    }
    document = {
        "schema_id": "ev4-ce-overlay-extract@1.0.0",
        "source_role": "overlay_extract",
        "binding": _binding("overlay_strategy"),
        "facts": {"note": "contained absolute z-index-10 in unrelated context"},
    }
    row = _artifact_row(
        tmp_path,
        claim_id="overlay_strategy",
        filename="overlay.json",
        content=json.dumps(document),
        semantics=semantics,
    )
    assert row["status"] == "insufficient_evidence"


def test_asset_exists_but_draft_only_suitability_fails_closed(tmp_path: Path) -> None:
    document = {
        "schema_id": "ev4-ce-asset-extract@1.0.0",
        "source_role": "asset_inventory_extract",
        "binding": _binding("asset_source"),
        "facts": {
            "asset_id": "asset-1",
            "intended_subject_ref": "node-root",
        },
    }
    row = _artifact_row(
        tmp_path,
        claim_id="asset_source",
        filename="asset.json",
        content=json.dumps(document),
        semantics={"subject_suitability": "Draft asserts this asset is suitable."},
    )
    assert row["status"] == "insufficient_evidence"


def test_unsupported_artifact_format_fails_closed(tmp_path: Path) -> None:
    row = _artifact_row(
        tmp_path,
        claim_id="geometry",
        filename="unsupported.txt",
        content="node-root css-grid parent-child layout reasoning",
        semantics=canonical_draft()["reviewed_nodes"][0]["claim_semantics"]["geometry"],
    )
    assert row["status"] == "insufficient_evidence"
    assert row["evidence_refs"] == []


def test_empty_dependency_matrix_returns_structured_blocked_diagnostics() -> None:
    bundle = canonical_bundle()
    bundle["payload"]["approved_structure_model"]["structure_nodes"] = [
        {
            "node_id": "node-root",
            "node_kind": "section",
            "parent_node_id": None,
            "children": [],
            "evidence_refs": ["architect-structure-root"],
        }
    ]
    intake = canonical_intake(bundle=bundle)
    intake["structure_projection"]["nodes"] = [
        {
            "source_node_id": "node-root",
            "node_kind": "section",
            "parent_node_id": None,
            "children": [],
        }
    ]
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = sha256_json(
        bundle
    )
    draft = canonical_draft()
    draft["architecture_echo"]["build_tree_node_ids"] = ["node-root"]
    draft["reviewed_nodes"] = [draft["reviewed_nodes"][0]]
    draft["implementation_strategy_proposal"]["strategies"] = [
        draft["implementation_strategy_proposal"]["strategies"][0]
    ]
    draft["builder_action_proposals"] = [
        {
            "action_id": "action-root",
            "action_type": "unknown_action",
            "target_node": "node-root",
            "parameters": {},
        }
    ]
    draft["reviewed_nodes"][0]["proposed_action"] = "perform unknown action"
    draft["reviewed_nodes"][0]["requested_claims"] = []
    draft["reviewed_nodes"][0]["claim_semantics"] = {}
    result = evaluate_all(intake, bundle, draft, repo_root=ROOT)
    assert result["dependency_result"]["status"] == "blocked"
    assert "CE_DEPENDENCY_EMPTY_MATRIX_UNPROVEN" in {
        item["code"] for item in result["dependency_result"]["diagnostics"]
    }


def test_persisted_payload_cannot_claim_class_or_build_tree_preservation() -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "apply_class",
        "target_node": "node-root",
        "parameters": {"class_name": "unapproved__class"},
    }
    draft["builder_action_proposals"].append(
        {
            "action_id": "action-new",
            "action_type": "create_element",
            "target_node": "node-root",
            "parameters": {
                "produced_node_id": "node-new",
                "parent_node_id": "node-root",
            },
        }
    )
    payload, _ = recompute_expected_payload(
        architect_intake=canonical_intake(),
        source_bundle=canonical_bundle(),
        review_draft=draft,
        repo_root=ROOT,
    )
    assert payload["architecture_identity"]["approved_class_names_unchanged"] is False
    assert payload["architecture_identity"]["build_tree_identity_preserved"] is False
    assert payload["builder_executable_package"] is None
    tampered = copy.deepcopy(payload)
    tampered["architecture_identity"]["approved_class_names_unchanged"] = True
    tampered["architecture_identity"]["build_tree_identity_preserved"] = True
    assert compare_persisted_payload(tampered, payload)[0]["path"] == (
        "$.architecture_identity"
    )


def test_actual_repository_owned_runtime_execution_is_positive(tmp_path: Path) -> None:
    target = tmp_path / "responsive.json"
    target.write_text(
        json.dumps(
            {
                "schema_id": "ev4-ce-responsive-evaluation-target@1.0.0",
                "claim_id": "responsive_behavior",
                "subject_ref": "node-root",
                "target_identity": "node-root",
                "cases": [
                    {
                        "viewport": "desktop",
                        "expected_layout": {"columns": 3},
                        "observed_layout": {"columns": 3},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    request = {
        "claim_id": "responsive_behavior",
        "subject_ref": "node-root",
        "evaluator_id": "ce-responsive-evaluator",
        "target_identity": "node-root",
        "input_ref": target.name,
    }
    row = evaluate_claim(
        "responsive_behavior",
        "node-root",
        {},
        canonical_intake(),
        canonical_bundle(),
        canonical_draft(),
        {"repo_root": tmp_path},
        [request],
    )
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["execution_status"] == "success"


def test_approved_class_application_preserves_architect_class_set() -> None:
    draft = canonical_draft()
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "apply_class",
        "target_node": "node-root",
        "parameters": {"class_name": "smart-home__section"},
    }
    result = _results(draft)
    effect = _effect(result, "action-root")
    assert effect["class_effect"]["applied_class_names"] == [
        "smart-home__section"
    ]
    assert effect["changes_approved_class_set"] is False
    assert effect["blocked"] is False
    assert result["identity_result"]["approved_classes_preserved"] is True


def test_explicit_architect_structure_permission_is_recognized() -> None:
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
    intake["forbidden_work"] = ["no_hidden_builder_decisions"]
    draft = canonical_draft()
    draft["architecture_echo"]["forbidden_work"] = ["no_hidden_builder_decisions"]
    draft["builder_action_proposals"][0] = {
        "action_id": "action-root",
        "action_type": "create_element",
        "target_node": "node-root",
        "parameters": {"produced_node_id": "node-new", "parent_node_id": "node-root"},
    }
    result = _results(draft, bundle=bundle, intake=intake)
    effect = _effect(result, "action-root")
    assert effect["structure_effect"]["permission_granted"] is True
    assert effect["blocked"] is False
    assert result["identity_result"]["unauthorized_redesign_absent"] is True
    assert result["strategy_result"]["architect_amendment_required"] is False
    # Public Builder contract still requires unchanged Build Tree identity, so the package remains blocked.
    assert result["identity_result"]["build_tree_nodes_preserved"] is False


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


def test_supported_structured_geometry_adapter_positive(tmp_path: Path) -> None:
    semantics = canonical_draft()["reviewed_nodes"][0]["claim_semantics"]["geometry"]
    document = {
        "schema_id": "ev4-ce-geometry-extract@1.0.0",
        "source_role": "geometry_extract",
        "binding": _binding("geometry"),
        "facts": copy.deepcopy(semantics),
    }
    row = _artifact_row(
        tmp_path,
        claim_id="geometry",
        filename="valid-geometry.json",
        content=json.dumps(document),
        semantics=semantics,
    )
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["adapter_id"].startswith(
        "ce-geometry-artifact-adapter"
    )


def test_deterministic_output_is_retained() -> None:
    first = _results(canonical_draft())
    second = _results(canonical_draft())
    assert first == second
