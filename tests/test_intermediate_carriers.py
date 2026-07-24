from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from validator.intermediate_carriers import (
    canonical_json_bytes,
    canonical_sha256,
    derive_architecture_identity_preservation,
    derive_dependency_classification,
    derive_implementation_strategy_coverage,
    derive_review_units_and_interrogation_results,
    evaluate_ce_intermediate_validation,
    validate_carrier,
)
from validator.intermediate_carriers_fidelity import (
    _diagnose_ce_payload_against_serialized_carriers,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/intermediate-carriers/valid/minimal-complete"
RUN_ID = "ce-intermediate-fixture-001"


def load(name: str):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def code_set(carrier_or_result):
    return {item["code"] for item in carrier_or_result["diagnostics"]}


def bind_source(intake, source_bundle):
    bundle = source_bundle["source_bundle"]
    intake["source_repository_ref"]["bundle_id"] = bundle["bundle_id"]
    intake["project_gate_transition"]["source_bundle_id"] = bundle["bundle_id"]
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = canonical_sha256(bundle)


def derive_all(*, intake=None, source_bundle=None, review=None, strategy=None, package=None):
    intake = copy.deepcopy(intake or load("architect-intake.json"))
    source_bundle = copy.deepcopy(source_bundle or load("source-bundle.json"))
    review = copy.deepcopy(review or load("constructability-review.json"))
    strategy = copy.deepcopy(strategy if strategy is not None else load("implementation-strategy-map.json"))
    package = copy.deepcopy(package if package is not None else load("builder-executable-package.json"))
    identity = derive_architecture_identity_preservation(
        run_id=RUN_ID,
        intake=intake,
        source_bundle=source_bundle,
        constructability_review=review,
    )
    review_carrier = derive_review_units_and_interrogation_results(
        run_id=RUN_ID,
        intake=intake,
        constructability_review=review,
    )
    dependency = derive_dependency_classification(
        run_id=RUN_ID,
        review_carrier=review_carrier,
        constructability_review=review,
    )
    strategy_carrier = derive_implementation_strategy_coverage(
        run_id=RUN_ID,
        identity_carrier=identity,
        review_carrier=review_carrier,
        dependency_carrier=dependency,
        constructability_review=review,
        implementation_strategy_map=strategy,
        builder_executable_package=package,
        repo_root=ROOT,
    )
    return identity, review_carrier, dependency, strategy_carrier


def transaction_inputs():
    return {
        "run_id": RUN_ID,
        "intake": load("architect-intake.json"),
        "source_bundle": load("source-bundle.json"),
        "constructability_review": load("constructability-review.json"),
        "implementation_strategy_map": load("implementation-strategy-map.json"),
        "builder_executable_package": load("builder-executable-package.json"),
        "final_payload": load("final-ce-stage-payload.json"),
        "repo_root": ROOT,
    }


def evaluate(values=None):
    return evaluate_ce_intermediate_validation(**(values or transaction_inputs()))


def test_positive_carriers_are_complete_deterministic_and_schema_valid():
    first = derive_all()
    second = derive_all()
    assert [item["status"] for item in first] == ["complete"] * 4
    for index, carrier in enumerate(first):
        assert canonical_json_bytes(carrier) == canonical_json_bytes(second[index])
        assert validate_carrier(carrier, repo_root=ROOT) == []


def test_authoritative_complete_transaction_is_ready():
    result = evaluate()
    assert result["transaction_status"] == "complete"
    assert result["fidelity_passed"] is True
    assert result["builder_ready"] is True
    assert set(result["carriers"]) == {
        "architecture_identity_preservation_result",
        "ce_review_units_and_interrogation_results",
        "dependency_classification",
        "implementation_strategy_coverage_result",
    }


def test_private_serialized_carrier_diagnostic_has_no_success_shape():
    result = evaluate()
    carriers = result["carriers"]
    diagnostic = _diagnose_ce_payload_against_serialized_carriers(
        payload=transaction_inputs()["final_payload"],
        identity_carrier=carriers["architecture_identity_preservation_result"],
        review_carrier=carriers["ce_review_units_and_interrogation_results"],
        dependency_carrier=carriers["dependency_classification"],
        strategy_carrier=carriers["implementation_strategy_coverage_result"],
    )
    assert diagnostic["diagnostic_match"] is True
    assert diagnostic["authoritative"] is False
    assert "passed" not in diagnostic
    assert "fidelity_passed" not in diagnostic
    assert "builder_ready" not in diagnostic


def test_identity_selected_candidate_changed():
    review = load("constructability-review.json")
    review["selected_candidate_id"] = "ARCH-FAM-X"
    assert "CE_IDENTITY_SELECTED_CANDIDATE_MISMATCH" in code_set(derive_all(review=review)[0])


@pytest.mark.parametrize("mutation", ["removed", "added"])
def test_identity_approved_class_set_changed(mutation):
    review = load("constructability-review.json")
    if mutation == "removed":
        review["approved_class_names"].pop()
    else:
        review["approved_class_names"].append("unauthorized-class")
    assert "CE_IDENTITY_APPROVED_CLASS_SET_MISMATCH" in code_set(derive_all(review=review)[0])


def test_identity_build_tree_changed():
    review = load("constructability-review.json")
    review["reviewed_nodes"].pop()
    assert "CE_IDENTITY_BUILD_TREE_MISMATCH" in code_set(derive_all(review=review)[0])


def test_identity_architect_unknown_removed():
    intake = load("architect-intake.json")
    source = load("source-bundle.json")
    unknown = {"unresolved_id": "unknown-layout", "state": "insufficient_evidence"}
    intake["unresolved_evidence"] = [unknown]
    source["source_bundle"]["payload"]["unresolved_evidence"] = [unknown]
    bind_source(intake, source)
    review = load("constructability-review.json")
    review["architect_unknowns"] = []
    assert "CE_IDENTITY_ARCHITECT_UNKNOWN_REMOVED" in code_set(
        derive_all(intake=intake, source_bundle=source, review=review)[0]
    )


def test_identity_forbidden_work_weakened():
    review = load("constructability-review.json")
    review["preserved_forbidden_work"].pop()
    assert "CE_IDENTITY_FORBIDDEN_WORK_WEAKENED" in code_set(derive_all(review=review)[0])


def test_identity_source_hash_mismatch_is_invalid():
    intake = load("architect-intake.json")
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = "0" * 64
    carrier = derive_all(intake=intake)[0]
    assert carrier["status"] == "invalid"
    assert "CE_IDENTITY_SOURCE_BUNDLE_HASH_MISMATCH" in code_set(carrier)


def test_identity_unauthorized_architecture_redesign():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["requires_structure_change"] = True
    interrogation["architect_decomposition_permission"] = False
    assert "CE_IDENTITY_ARCHITECTURE_REDESIGN_DETECTED" in code_set(derive_all(review=review)[0])


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("missing", "CE_REVIEW_UNIT_REQUIRED_NODE_UNREVIEWED"),
        ("duplicate_id", "CE_REVIEW_UNIT_DUPLICATE_ID"),
        ("duplicate_source", "CE_REVIEW_UNIT_DUPLICATE_SOURCE_MAPPING"),
        ("orphan", "CE_REVIEW_UNIT_ORPHAN_SOURCE_NODE"),
        ("missing_interrogation", "CE_REVIEW_UNIT_INTERROGATION_MISSING"),
    ],
)
def test_review_unit_fail_closed_mutations(mutation, code):
    review = load("constructability-review.json")
    if mutation == "missing":
        review["reviewed_nodes"].pop()
    elif mutation == "duplicate_id":
        review["reviewed_nodes"][1]["review_unit_id"] = review["reviewed_nodes"][0]["review_unit_id"]
    elif mutation == "duplicate_source":
        review["reviewed_nodes"][1]["architect_node_ref"] = review["reviewed_nodes"][0]["architect_node_ref"]
    elif mutation == "orphan":
        review["reviewed_nodes"][0]["architect_node_ref"] = "orphan-node"
    else:
        del review["reviewed_nodes"][0]["interrogation_result"]
    assert code in code_set(derive_all(review=review)[1])


def test_dependency_geometry_evidence_gap_is_preserved():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False
    carrier = derive_all(review=review)[2]
    assert carrier["status"] == "insufficient_evidence"
    assert "CE_DEPENDENCY_EVIDENCE_UNRESOLVED" in code_set(carrier)


def test_dependency_blocker_suppression_is_rejected():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = False
    carrier = derive_all(review=review)[2]
    assert "CE_DEPENDENCY_BLOCKING_PRESENT" in code_set(carrier)
    assert "CE_DEPENDENCY_BLOCKING_SUPPRESSED" in code_set(carrier)


def test_strategy_uses_review_unit_id_not_architect_node_ref():
    values = transaction_inputs()
    review = values["constructability_review"]
    strategy = values["implementation_strategy_map"]
    payload = values["final_payload"]
    mapping = {"node-root": "CE-RU-001", "node-wrapper": "CE-RU-002"}
    for item in review["reviewed_nodes"]:
        item["review_unit_id"] = mapping[item["architect_node_ref"]]
        item["node_id"] = mapping[item["architect_node_ref"]]
    for item in strategy["strategies"]:
        item["node_id"] = mapping[item["node_id"]]
    payload["constructability_review"] = copy.deepcopy(review)
    payload["implementation_strategy_map"] = copy.deepcopy(strategy)
    for trace in payload["architecture_identity"]["review_unit_traces"]:
        trace["ce_review_unit_id"] = mapping[trace["architect_node_ref"]]
    result = evaluate(values)
    assert result["builder_ready"] is True
    carrier = result["carriers"]["implementation_strategy_coverage_result"]
    assert carrier["derived_data"]["uncovered_review_units"] == []


def test_strategy_using_architect_node_ref_is_rejected():
    values = transaction_inputs()
    review = values["constructability_review"]
    payload = values["final_payload"]
    mapping = {"node-root": "CE-RU-001", "node-wrapper": "CE-RU-002"}
    for item in review["reviewed_nodes"]:
        item["review_unit_id"] = mapping[item["architect_node_ref"]]
        item["node_id"] = mapping[item["architect_node_ref"]]
    payload["constructability_review"] = copy.deepcopy(review)
    for trace in payload["architecture_identity"]["review_unit_traces"]:
        trace["ce_review_unit_id"] = mapping[trace["architect_node_ref"]]
    result = evaluate(values)
    assert "CE_STRATEGY_COVERAGE_REVIEW_UNIT_UNCOVERED" in code_set(result)
    assert "CE_STRATEGY_COVERAGE_ORPHAN_STRATEGY" in code_set(result)
    assert result["builder_ready"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_package_id",
        "missing_review_ref",
        "identity_lock_false",
        "architect_contract",
        "confirmed_actions_empty",
        "missing_batch_id",
        "non_object_action",
        "missing_action_type",
        "missing_target_node",
        "missing_parameters",
        "parameters_not_object",
        "visual_parity_missing_structures",
    ],
)
def test_raw_builder_package_requires_complete_official_schema(mutation):
    values = transaction_inputs()
    package = values["builder_executable_package"]
    if mutation == "missing_package_id":
        package.pop("package_id")
    elif mutation == "missing_review_ref":
        package.pop("review_ref")
    elif mutation == "identity_lock_false":
        package["selected_candidate_locked"] = False
    elif mutation == "architect_contract":
        package["architect_contract"] = {"source_ref": "x"}
    elif mutation == "confirmed_actions_empty":
        package["confirmation_request"]["confirmed_action_ids"] = []
    elif mutation == "missing_batch_id":
        package["first_safe_builder_batch"].pop("batch_id")
    elif mutation == "non_object_action":
        package["first_safe_builder_batch"]["actions"] = ["bad"]
    elif mutation == "missing_action_type":
        package["first_safe_builder_batch"]["actions"][0].pop("action_type")
    elif mutation == "missing_target_node":
        package["first_safe_builder_batch"]["actions"][0].pop("target_node")
    elif mutation == "missing_parameters":
        package["first_safe_builder_batch"]["actions"][0].pop("parameters")
    elif mutation == "parameters_not_object":
        package["first_safe_builder_batch"]["actions"][0]["parameters"] = []
    else:
        package["visual_parity_build"] = True
        package.pop("reference_paradigm_lock", None)
        package.pop("paradigm_to_structure_map", None)
    result = evaluate(values)
    assert result["builder_ready"] is False
    assert "CE_STRATEGY_COVERAGE_PACKAGE_SCHEMA_VALIDATION_FAILED" in code_set(result)


def test_same_invalid_package_in_raw_and_payload_hits_official_payload_validation():
    values = transaction_inputs()
    values["builder_executable_package"].pop("package_id")
    values["final_payload"]["builder_executable_package"] = copy.deepcopy(
        values["builder_executable_package"]
    )
    result = evaluate(values)
    assert result["transaction_status"] == "invalid"
    assert result["fidelity_passed"] is False
    assert result["builder_ready"] is False
    assert "CE_INTERMEDIATE_PAYLOAD_SCHEMA_INVALID" in code_set(result)


@pytest.mark.parametrize(
    "mutation",
    ["emission_false", "package_null", "reason", "candidate", "nested"],
)
def test_final_payload_must_equal_validated_raw_package(mutation):
    values = transaction_inputs()
    payload = values["final_payload"]
    if mutation == "emission_false":
        payload["builder_package_emitted"] = False
        payload["builder_executable_package"] = None
        payload["builder_package_not_emitted_reason"] = "unexpected"
    elif mutation == "package_null":
        payload["builder_executable_package"] = None
    elif mutation == "reason":
        payload["builder_package_not_emitted_reason"] = "unexpected"
    elif mutation == "candidate":
        payload["builder_executable_package"]["selected_candidate_id"] = "ARCH-FAM-X"
    else:
        payload["builder_executable_package"]["first_safe_builder_batch"]["actions"][0]["parameters"]["drift"] = True
    result = evaluate(values)
    assert result["fidelity_passed"] is False
    assert result["builder_ready"] is False


def test_serialized_forged_carriers_cannot_be_passed_to_authoritative_api():
    forged = {"status": "complete", "diagnostics": [], "source_identities": [{"sha256": "0" * 64}]}
    with pytest.raises(TypeError):
        evaluate_ce_intermediate_validation(**transaction_inputs(), identity_carrier=forged)


@pytest.mark.parametrize(
    "mutation",
    [
        "unsupported_status",
        "missing_required",
        "boundary",
        "payload_identity",
        "evidence",
        "semantic",
    ],
)
def test_official_payload_validation_is_mandatory(mutation):
    values = transaction_inputs()
    payload = values["final_payload"]
    if mutation == "unsupported_status":
        payload["payload_status"] = "blocked"
    elif mutation == "missing_required":
        payload.pop("repair_routing")
    elif mutation == "boundary":
        payload["boundary_assertions"]["production_ready"] = True
    elif mutation == "payload_identity":
        payload["payload_identity"]["pipeline_id"] = "wrong"
    elif mutation == "evidence":
        payload["evidence_register"][0].pop("source")
    else:
        payload["constructability_review"]["constructability_status"] = "blocked"
    result = evaluate(values)
    assert result["transaction_status"] == "invalid"
    assert result["fidelity_passed"] is False
    assert result["builder_ready"] is False
    assert {
        "CE_INTERMEDIATE_PAYLOAD_SCHEMA_INVALID",
        "CE_INTERMEDIATE_PAYLOAD_SEMANTIC_INVALID",
    } & code_set(result)


def test_repo_root_is_required_by_authoritative_evaluator():
    values = transaction_inputs()
    values.pop("repo_root")
    with pytest.raises(TypeError):
        evaluate_ce_intermediate_validation(**values)


def _nonready_payload(values, first, status):
    payload = copy.deepcopy(values["final_payload"])
    carriers = first["carriers"]
    identity = carriers["architecture_identity_preservation_result"]["derived_data"]["payload_projection"]
    review = carriers["ce_review_units_and_interrogation_results"]["derived_data"]["payload_projection"]
    dependency = carriers["dependency_classification"]["derived_data"]["payload_projection"]
    strategy = carriers["implementation_strategy_coverage_result"]["derived_data"]["payload_projection"]
    payload["payload_status"] = "insufficient_evidence"
    payload["architecture_identity"].update(identity)
    payload["constructability_review"] = copy.deepcopy(values["constructability_review"])
    payload["constructability_review"]["reviewed_nodes"] = review["reviewed_nodes"]
    payload["constructability_review"]["blocking_dependencies"] = dependency["blocking_dependencies"]
    payload["implementation_strategy_map"] = None
    payload["builder_executable_package"] = None
    payload["builder_package_emitted"] = False
    payload["builder_package_not_emitted_reason"] = strategy["builder_package_not_emitted_reason"]
    unresolved = dependency["required_unresolved_ids"] or [f"reported-{status}"]
    payload["unresolved_evidence"] = [{"id": value} for value in unresolved]
    return payload


def test_faithful_blocked_payload_is_schema_valid_but_not_ready():
    values = transaction_inputs()
    interrogation = values["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = False
    values["constructability_review"]["blocking_dependencies"] = [
        "node-root:R05_OVERLAY_STRATEGY_MUST_BE_PROVEN:overlay"
    ]
    values["constructability_review"]["constructability_status"] = "blocked"
    values["constructability_review"]["reviewed_nodes"][0]["node_status"] = "blocked"
    values["implementation_strategy_map"] = None
    values["builder_executable_package"] = None
    first = evaluate(values)
    values["final_payload"] = _nonready_payload(values, first, "blocked")
    result = evaluate(values)
    assert result["fidelity_passed"] is True
    assert result["builder_ready"] is False
    assert result["transaction_status"] == "blocked"
    assert values["final_payload"]["payload_status"] == "insufficient_evidence"


def test_faithful_insufficient_payload_is_not_ready():
    values = transaction_inputs()
    interrogation = values["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False
    values["constructability_review"]["constructability_status"] = "needs_user_evidence"
    values["constructability_review"]["reviewed_nodes"][0]["node_status"] = "needs_user_evidence"
    values["implementation_strategy_map"] = None
    values["builder_executable_package"] = None
    first = evaluate(values)
    values["final_payload"] = _nonready_payload(values, first, "insufficient")
    result = evaluate(values)
    assert result["fidelity_passed"] is True
    assert result["builder_ready"] is False
    assert result["transaction_status"] == "insufficient_evidence"
