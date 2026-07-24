from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from validator.action_contract_registry import ACTION_CONTRACTS
from validator.action_ir import ActionIRValidationError, normalize_action
from validator.artifact_adapters import (
    ArtifactAdapterError,
    ArtifactBinding,
    evaluate_artifact_source,
)
from validator.claim_evaluators import evaluate_claim
from validator.claim_policy_registry import (
    CLAIM_POLICIES,
    POST_BUILDER_RUNTIME,
    PRE_BUILDER_CAPABILITY,
    PRE_BUILDER_STATIC,
)
from validator.payload_fidelity import (
    compare_persisted_payload,
    evaluate_ce_transaction,
)
from validator.runtime_execution import RuntimeExecutionBoundaryError, execute_runtime_requests
from validator.runtime_obligations import RuntimeObligationError, derive_runtime_obligations
from deterministic_runtime_support import (
    canonical_bundle,
    canonical_draft,
    canonical_intake,
    evaluation_run,
)

ROOT = Path(__file__).resolve().parents[1]


def _lifecycle(payload: dict) -> dict:
    return next(
        item["result"]
        for item in payload["extension_records"]
        if item.get("kind") == "lifecycle_status"
    )


def _responsive_draft() -> dict:
    draft = canonical_draft()
    node = draft["reviewed_nodes"][0]
    node["proposed_action"] = "configure responsive behavior"
    node["claim_semantics"]["responsive_strategy"] = {
        "breakpoint_strategy": "mobile-first at project breakpoints",
        "layout_adaptation": "stack root content below 768px",
        "derivation_method": "derive from retained parent-child layout",
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


def test_one_phase_aware_claim_registry() -> None:
    phases = {policy["lifecycle_phase"] for policy in CLAIM_POLICIES.values()}
    assert phases == {
        PRE_BUILDER_STATIC,
        PRE_BUILDER_CAPABILITY,
        POST_BUILDER_RUNTIME,
    }
    assert CLAIM_POLICIES["responsive_strategy"]["lifecycle_phase"] == PRE_BUILDER_STATIC
    assert CLAIM_POLICIES["responsive_behavior"]["lifecycle_phase"] == POST_BUILDER_RUNTIME
    assert CLAIM_POLICIES["asset_source"]["lifecycle_phase"] == PRE_BUILDER_CAPABILITY


def test_one_closed_action_contract_registry() -> None:
    assert ACTION_CONTRACTS["configure_layout"]["required_parameter_keys"] == (
        "layout_model",
    )
    assert ACTION_CONTRACTS["apply_class"]["derived_class_effects"]
    assert ACTION_CONTRACTS["create_element"]["derived_structure_effects"]


def test_action_ir_alias_is_normalized_and_idempotent() -> None:
    action = {
        "action_id": "action-root",
        "action_type": "configure_layout",
        "target_node": "node-root",
        "parameters": {"layout": "grid", "gap": "8px"},
    }
    first = normalize_action(action)
    assert first["normalized_parameters"] == {
        "gap": "8px",
        "layout_model": "grid",
    }
    assert normalize_action(first) == first


@pytest.mark.parametrize(
    "action_type,parameters",
    [
        ("configure_layout", {"layout_model": "grid", "remove_class": "approved"}),
        ("configure_layout", {"layout_model": "grid", "produced_node_id": "new"}),
        ("apply_class", {"class_names": ["approved"], "new_parent_node_id": "other"}),
        (
            "create_element",
            {
                "produced_node_id": "new",
                "parent_node_id": "node-root",
                "element_type": "Container",
                "class_names": ["x"],
            },
        ),
        ("configure_layout", {"layout_model": "grid", "unknown": True}),
    ],
)
def test_effect_bearing_or_unknown_parameters_fail_closed(
    action_type: str, parameters: dict
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


def test_unknown_action_and_ambiguous_alias_fail_closed() -> None:
    with pytest.raises(ActionIRValidationError):
        normalize_action(
            {
                "action_id": "a",
                "action_type": "invent_magic",
                "target_node": "node-root",
                "parameters": {},
            }
        )
    with pytest.raises(ActionIRValidationError):
        normalize_action(
            {
                "action_id": "a",
                "action_type": "configure_layout",
                "target_node": "node-root",
                "parameters": {"layout": "grid", "layout_model": "flex"},
            }
        )


def test_nested_builder_choice_is_carried_as_unresolved_ir() -> None:
    ir = normalize_action(
        {
            "action_id": "a",
            "action_type": "configure_layout",
            "target_node": "node-root",
            "parameters": {"layout": "grid", "layout_options": ["grid", "flex"]},
        }
    )
    assert ir["decision_state"] == "unresolved"
    assert ir["hidden_decision_paths"]
    assert "layout_options" not in ir["normalized_parameters"]


@pytest.mark.parametrize(
    "forged",
    [
        {"observed_layout": "stacked"},
        {"passed": True},
        {"accessible_name": "Menu"},
        {"execution_status": "success", "exit_code": 0},
    ],
)
def test_caller_authored_runtime_observation_is_rejected(forged: dict) -> None:
    request = {
        "claim_id": "responsive_behavior",
        "subject_ref": "node-root",
        "evaluator_id": "ce-responsive-evaluator",
        "target_identity": "node-root",
        **forged,
    }
    with pytest.raises(RuntimeExecutionBoundaryError):
        execute_runtime_requests(repo_root=ROOT, transaction_id="trx", requests=[request])


def test_runtime_specification_is_not_execution_evidence() -> None:
    batch = execute_runtime_requests(
        repo_root=ROOT,
        transaction_id="trx",
        requests=[
            {
                "claim_id": "responsive_behavior",
                "subject_ref": "node-root",
                "evaluator_id": "ce-responsive-evaluator",
                "target_identity": "node-root",
                "expected_assertions": ["mobile layout stacks"],
            }
        ],
    )
    assert batch.results == ()
    assert batch.declarations[0]["declaration_kind"] == "RUNTIME_TEST_SPECIFICATION"


def test_runtime_claim_without_real_runner_emits_complete_obligation() -> None:
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
    assert row["evidence_refs"] == []
    obligation = row["downstream_obligation"]
    assert obligation["status"] == "required"
    assert obligation["blocking_boundary"] == "final_project_gate"
    assert obligation["blocks_builder_handoff"] is False
    assert obligation["blocks_final_completion"] is True


def test_post_builder_claim_without_obligation_fails_closed() -> None:
    with pytest.raises(RuntimeObligationError, match="has no obligation"):
        derive_runtime_obligations(
            [
                {
                    "claim_id": "responsive_behavior",
                    "subject_ref": "node-root",
                    "status": "downstream_validation_required",
                    "downstream_obligation": None,
                }
            ]
        )


def test_builder_ready_is_separate_from_runtime_and_production() -> None:
    run, _, _ = evaluation_run(ROOT, draft=_responsive_draft())
    payload = run["payload"]
    assert payload["payload_status"] == "complete"
    assert payload["builder_package_emitted"] is True
    assert payload["downstream_test_obligations"][0]["status"] == "required"
    lifecycle = _lifecycle(payload)
    assert lifecycle == {
        "ce_builder_ready": True,
        "final_project_gate": "blocked",
        "production_ready": False,
        "runtime_validated": False,
        "runtime_validation": "pending",
    }


def test_builder_package_uses_only_normalized_action_ir() -> None:
    run, _, _ = evaluation_run(ROOT, draft=_responsive_draft())
    package = run["payload"]["builder_executable_package"]
    action = package["first_safe_builder_batch"]["actions"][0]
    assert action["parameters"] == {
        "breakpoint_strategy": "mobile-first",
        "layout_adaptation": "stacked",
        "target_identity": "node-root",
    }
    assert "layout" not in action["parameters"]
    assert package["normalized_action_ir"][0]["normalized_parameters"] == action["parameters"]


def test_open_runtime_obligation_removal_is_detected() -> None:
    run, _, _ = evaluation_run(ROOT, draft=_responsive_draft())
    expected = run["payload"]
    tampered = copy.deepcopy(expected)
    tampered["downstream_test_obligations"] = []
    diagnostics = compare_persisted_payload(tampered, expected)
    assert diagnostics[0]["path"] == "$.downstream_test_obligations"


def test_builder_ready_cannot_be_forged_to_production_ready() -> None:
    run, _, _ = evaluation_run(ROOT, draft=_responsive_draft())
    expected = run["payload"]
    tampered = copy.deepcopy(expected)
    tampered["boundary_assertions"]["production_ready"] = True
    assert compare_persisted_payload(tampered, expected)[0]["path"] == "$.boundary_assertions"


def _binding(claim_id: str) -> ArtifactBinding:
    return ArtifactBinding(
        claim_id=claim_id,
        subject_ref="node-root",
        selected_candidate_id="ARCH-FAM-C",
        source_bundle_id="bundle-1",
        intake_digest="a" * 64,
    )


def test_facts_envelope_alone_cannot_satisfy_artifact_claim(tmp_path: Path) -> None:
    path = tmp_path / "facts.json"
    path.write_text(
        json.dumps(
            {
                "facts": {
                    "anchor_model": {"root": "node-root"},
                    "coordinate_or_layout_model": "grid",
                    "derivation_method": "copied",
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ArtifactAdapterError):
        evaluate_artifact_source(
            claim_id="geometry",
            path=path,
            semantics={
                "anchor_model": {"root": "node-root"},
                "coordinate_or_layout_model": "grid",
                "derivation_method": "CE analysis",
            },
            binding=_binding("geometry"),
        )


def test_original_json_source_derives_geometry(tmp_path: Path) -> None:
    path = tmp_path / "model.json"
    path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "node-root",
                        "layout": {
                            "model": "grid",
                            "anchors": {"root": "node-root"},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    facts, metadata = evaluate_artifact_source(
        claim_id="geometry",
        path=path,
        semantics={
            "anchor_model": {"root": "node-root"},
            "coordinate_or_layout_model": "grid",
            "derivation_method": "CE analysis",
        },
        binding=_binding("geometry"),
    )
    assert facts["coordinate_or_layout_model"] == "grid"
    assert metadata["source_role"] == "original_source"
    assert len(metadata["source_bytes_sha256"]) == 64


def test_cached_extract_requires_exact_regeneration(tmp_path: Path) -> None:
    source = tmp_path / "model.json"
    cache = tmp_path / "cache.json"
    source.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "node-root",
                        "layout": {
                            "model": "grid",
                            "anchors": {"root": "node-root"},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cache.write_text(
        json.dumps(
            {
                "anchor_model": {"root": "other"},
                "coordinate_or_layout_model": "grid",
                "derivation_method": "ce-original-json-geometry-parser@1.0.0",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ArtifactAdapterError, match="cannot be regenerated"):
        evaluate_artifact_source(
            claim_id="geometry",
            path=source,
            cached_extract_path=cache,
            semantics={
                "anchor_model": {"root": "node-root"},
                "coordinate_or_layout_model": "grid",
                "derivation_method": "CE analysis",
            },
            binding=_binding("geometry"),
        )


def test_html_parser_handles_gt_inside_quoted_attribute(tmp_path: Path) -> None:
    source = tmp_path / "control.html"
    source.write_text(
        '<div id="node-root" data-control-path="Panel/>/Control"></div>',
        encoding="utf-8",
    )
    facts, _ = evaluate_artifact_source(
        claim_id="ui_control_path",
        path=source,
        semantics={"control_path": "Panel/>/Control"},
        binding=_binding("ui_control_path"),
    )
    assert facts["control_path"] == "Panel/>/Control"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"nodes": {}, "nodes": []}',
        b'{"value": NaN}',
        b'[]',
    ],
)
def test_invalid_authority_json_fails_closed(tmp_path: Path, raw: bytes) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(raw)
    with pytest.raises(ArtifactAdapterError):
        evaluate_artifact_source(
            claim_id="geometry",
            path=source,
            semantics={
                "anchor_model": {"root": "node-root"},
                "coordinate_or_layout_model": "grid",
                "derivation_method": "CE analysis",
            },
            binding=_binding("geometry"),
        )


def test_api_results_are_deterministic() -> None:
    draft = _responsive_draft()
    first, first_results = evaluate_ce_transaction(
        architect_intake=canonical_intake(),
        source_bundle=canonical_bundle(),
        review_draft=draft,
        repo_root=ROOT,
    )
    second, second_results = evaluate_ce_transaction(
        architect_intake=canonical_intake(),
        source_bundle=canonical_bundle(),
        review_draft=draft,
        repo_root=ROOT,
    )
    assert first == second
    assert first_results == second_results
