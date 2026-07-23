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
    validate_carrier,
    validate_ce_payload_against_intermediate_carriers,
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
        implementation_strategy_map=strategy,
        builder_executable_package=package,
    )
    return identity, review_carrier, dependency, strategy_carrier


@pytest.mark.parametrize(
    ("expected_file", "index"),
    [
        ("expected-architecture-identity-preservation-result.json", 0),
        ("expected-ce-review-units-and-interrogation-results.json", 1),
        ("expected-dependency-classification.json", 2),
        ("expected-implementation-strategy-coverage-result.json", 3),
    ],
)
def test_positive_carriers_match_expected(expected_file, index):
    carriers = derive_all()
    assert carriers[index] == load(expected_file)
    assert carriers[index]["status"] == "complete"


@pytest.mark.parametrize("index", range(4))
def test_each_carrier_is_byte_deterministic(index):
    first = derive_all()[index]
    second = derive_all()[index]
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


@pytest.mark.parametrize("index", range(4))
def test_each_carrier_passes_schema_and_semantic_validation(index):
    assert validate_carrier(derive_all()[index], repo_root=ROOT) == []


def test_final_positive_payload_fidelity_passes():
    identity, review, dependency, strategy = derive_all()
    result = validate_ce_payload_against_intermediate_carriers(
        payload=load("final-ce-stage-payload.json"),
        identity_carrier=identity,
        review_carrier=review,
        dependency_carrier=dependency,
        strategy_carrier=strategy,
    )
    assert result["passed"] is True
    assert result["diagnostics"] == []


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
    assert "CE_IDENTITY_ARCHITECT_UNKNOWN_REMOVED" in code_set(derive_all(intake=intake, source_bundle=source, review=review)[0])


def test_identity_forbidden_work_weakened():
    review = load("constructability-review.json")
    review["preserved_forbidden_work"].pop()
    assert "CE_IDENTITY_FORBIDDEN_WORK_WEAKENED" in code_set(derive_all(review=review)[0])


def test_identity_review_trace_points_to_unknown_node():
    review = load("constructability-review.json")
    review["reviewed_nodes"][0]["architect_node_ref"] = "node-unknown"
    assert "CE_IDENTITY_BUILD_TREE_MISMATCH" in code_set(derive_all(review=review)[0])


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


def test_review_required_source_node_missing():
    review = load("constructability-review.json")
    review["reviewed_nodes"].pop()
    assert "CE_REVIEW_UNIT_REQUIRED_NODE_UNREVIEWED" in code_set(derive_all(review=review)[1])


def test_review_duplicate_review_unit_id():
    review = load("constructability-review.json")
    review["reviewed_nodes"][1]["review_unit_id"] = review["reviewed_nodes"][0]["review_unit_id"]
    assert "CE_REVIEW_UNIT_DUPLICATE_ID" in code_set(derive_all(review=review)[1])


def test_review_duplicate_source_mapping():
    review = load("constructability-review.json")
    review["reviewed_nodes"][1]["architect_node_ref"] = review["reviewed_nodes"][0]["architect_node_ref"]
    assert "CE_REVIEW_UNIT_DUPLICATE_SOURCE_MAPPING" in code_set(derive_all(review=review)[1])


def test_review_orphan_unit():
    review = load("constructability-review.json")
    review["reviewed_nodes"][0]["architect_node_ref"] = "orphan-node"
    assert "CE_REVIEW_UNIT_ORPHAN_SOURCE_NODE" in code_set(derive_all(review=review)[1])


def test_review_missing_interrogation_result():
    review = load("constructability-review.json")
    del review["reviewed_nodes"][0]["interrogation_result"]
    assert "CE_REVIEW_UNIT_INTERROGATION_MISSING" in code_set(derive_all(review=review)[1])


def test_review_missing_required_interrogation_field():
    review = load("constructability-review.json")
    del review["reviewed_nodes"][0]["interrogation_result"]["geometry_required"]
    assert "CE_REVIEW_UNIT_INTERROGATION_FIELD_MISSING" in code_set(derive_all(review=review)[1])


def test_dependency_geometry_evidence_gap_is_preserved():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False
    carrier = derive_all(review=review)[2]
    assert carrier["status"] == "insufficient_evidence"
    assert "CE_DEPENDENCY_EVIDENCE_UNRESOLVED" in code_set(carrier)


@pytest.mark.parametrize(
    ("field_updates", "expected_code"),
    [
        ({"overlay_strategy_required": True, "overlay_strategy_proven": False}, "CE_DEPENDENCY_BLOCKING_PRESENT"),
        ({"dynamic_loop_implied": True, "dynamic_loop_approved": False}, "CE_DEPENDENCY_BLOCKING_PRESENT"),
        ({"accessibility_claimed": True, "accessibility_evidenced": False}, "CE_DEPENDENCY_BLOCKING_PRESENT"),
        ({"requires_class_change": True, "architect_decomposition_permission": False}, "CE_DEPENDENCY_BLOCKING_PRESENT"),
    ],
)
def test_dependency_blocking_dimensions(field_updates, expected_code):
    review = load("constructability-review.json")
    review["reviewed_nodes"][0]["interrogation_result"].update(field_updates)
    carrier = derive_all(review=review)[2]
    assert expected_code in code_set(carrier)
    assert "CE_DEPENDENCY_BLOCKING_SUPPRESSED" in code_set(carrier)


def test_dependency_responsive_not_applicable_is_unsupported_when_targeted():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["action_targets_responsive"] = True
    interrogation["responsive_behavior"] = "not_applicable"
    assert "CE_DEPENDENCY_RESPONSIVE_NOT_APPLICABLE_UNSUPPORTED" in code_set(derive_all(review=review)[2])


def test_dependency_exact_ui_path_evidence_gap_is_preserved():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["exact_ui_control_path_used"] = True
    interrogation["ui_control_evidence_present"] = False
    carrier = derive_all(review=review)[2]
    assert carrier["status"] == "insufficient_evidence"
    assert "CE_DEPENDENCY_EVIDENCE_UNRESOLVED" in code_set(carrier)


def test_dependency_non_blocking_obligation_is_preserved():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = True
    interrogation["overlay_strategy"] = {"positioning": "absolute", "containment": "node-root"}
    carrier = derive_all(review=review)[2]
    assert carrier["status"] == "complete"
    assert carrier["derived_data"]["non_blocking_obligations"]


def test_dependency_mutated_carrier_duplicate_classification_is_rejected():
    carrier = copy.deepcopy(derive_all()[2])
    carrier["derived_data"]["classifications"].append(copy.deepcopy(carrier["derived_data"]["classifications"][0]))
    assert "CE_DEPENDENCY_DUPLICATE_CLASSIFICATION" in {item["code"] for item in validate_carrier(carrier, repo_root=ROOT)}


def test_dependency_mutated_carrier_missing_dimension_is_rejected():
    carrier = copy.deepcopy(derive_all()[2])
    carrier["derived_data"]["classifications"].pop()
    assert "CE_DEPENDENCY_CLASSIFICATION_COVERAGE_INCOMPLETE" in {item["code"] for item in validate_carrier(carrier, repo_root=ROOT)}


def test_strategy_review_unit_uncovered():
    strategy = load("implementation-strategy-map.json")
    strategy["strategies"].pop()
    assert "CE_STRATEGY_COVERAGE_REVIEW_UNIT_UNCOVERED" in code_set(derive_all(strategy=strategy)[3])


def test_strategy_builder_decision_remains():
    strategy = load("implementation-strategy-map.json")
    strategy["strategies"][0]["builder_decisions_required"] = 1
    assert "CE_STRATEGY_COVERAGE_BUILDER_DECISION_REMAINS" in code_set(derive_all(strategy=strategy)[3])


def test_strategy_first_safe_batch_missing():
    package = load("builder-executable-package.json")
    del package["first_safe_builder_batch"]
    assert "CE_STRATEGY_COVERAGE_FIRST_SAFE_BATCH_MISSING" in code_set(derive_all(package=package)[3])


def test_strategy_confirmation_data_missing():
    package = load("builder-executable-package.json")
    del package["confirmation_request"]["expected_user_token"]
    assert "CE_STRATEGY_COVERAGE_CONFIRMATION_DATA_MISSING" in code_set(derive_all(package=package)[3])


def test_strategy_architect_amendment_hidden():
    strategy = load("implementation-strategy-map.json")
    strategy["strategies"][0]["architect_amendment_required"] = True
    assert "CE_STRATEGY_COVERAGE_ARCHITECT_AMENDMENT_HIDDEN" in code_set(derive_all(strategy=strategy)[3])


def test_strategy_first_batch_hidden_decision():
    package = load("builder-executable-package.json")
    package["first_safe_builder_batch"]["actions"][0]["parameters"]["tbd"] = True
    assert "CE_STRATEGY_COVERAGE_FIRST_BATCH_DECISION_HIDDEN" in code_set(derive_all(package=package)[3])


def test_strategy_absence_reason_is_independently_derived():
    identity, review_carrier, dependency, _ = derive_all()
    carrier = derive_implementation_strategy_coverage(
        run_id=RUN_ID,
        identity_carrier=identity,
        review_carrier=review_carrier,
        dependency_carrier=dependency,
        implementation_strategy_map=None,
        builder_executable_package=None,
    )
    assert carrier["derived_data"]["absence_reason"] == "strategy_missing_without_repository_supported_absence_basis"
    assert carrier["derived_data"]["absence_reason"] != "builder package not emitted"


def test_strategy_dependency_obligation_is_covered_by_same_unit_strategy():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = True
    interrogation["overlay_strategy"] = {"positioning": "absolute"}
    carrier = derive_all(review=review)[3]
    assert carrier["status"] == "complete"
    assert all(row["covered"] for row in carrier["derived_data"]["coverage_by_dependency"] if row["classification"] == "non_blocking_obligation")


def fidelity(payload=None, carriers=None):
    identity, review, dependency, strategy = carriers or derive_all()
    return validate_ce_payload_against_intermediate_carriers(
        payload=copy.deepcopy(payload or load("final-ce-stage-payload.json")),
        identity_carrier=identity,
        review_carrier=review,
        dependency_carrier=dependency,
        strategy_carrier=strategy,
    )


def test_fidelity_identity_drift():
    payload = load("final-ce-stage-payload.json")
    payload["architecture_identity"]["selected_candidate_id"] = "ARCH-FAM-X"
    assert "CE_INTERMEDIATE_FIDELITY_ARCHITECTURE_IDENTITY_MISMATCH" in code_set(fidelity(payload))


def test_fidelity_reviewed_nodes_drift():
    payload = load("final-ce-stage-payload.json")
    payload["constructability_review"]["reviewed_nodes"].pop()
    assert "CE_INTERMEDIATE_FIDELITY_REVIEWED_NODES_MISMATCH" in code_set(fidelity(payload))


def test_fidelity_blocking_dependencies_drift():
    payload = load("final-ce-stage-payload.json")
    payload["constructability_review"]["blocking_dependencies"] = ["fake-blocker"]
    assert "CE_INTERMEDIATE_FIDELITY_BLOCKING_DEPENDENCIES_MISMATCH" in code_set(fidelity(payload))


def test_fidelity_strategy_map_drift():
    payload = load("final-ce-stage-payload.json")
    payload["implementation_strategy_map"]["strategies"][0]["strategy_selected"] = "drifted"
    assert "CE_INTERMEDIATE_FIDELITY_STRATEGY_MAP_MISMATCH" in code_set(fidelity(payload))


def test_fidelity_run_id_drift():
    payload = load("final-ce-stage-payload.json")
    payload["payload_identity"]["run_id"] = "different-run"
    assert "CE_INTERMEDIATE_FIDELITY_RUN_ID_MISMATCH" in code_set(fidelity(payload))


def test_fidelity_false_complete_when_dependency_carrier_incomplete():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False
    assert "CE_INTERMEDIATE_FIDELITY_FALSE_COMPLETE" in code_set(fidelity(carriers=derive_all(review=review)))


def test_fidelity_unresolved_dependency_omission():
    review = load("constructability-review.json")
    interrogation = review["reviewed_nodes"][0]["interrogation_result"]
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False
    assert "CE_INTERMEDIATE_FIDELITY_UNRESOLVED_DEPENDENCY_OMITTED" in code_set(fidelity(carriers=derive_all(review=review)))


def test_fidelity_strategy_absence_reason_conflation_rejected():
    identity, review, dependency, _ = derive_all()
    strategy = derive_implementation_strategy_coverage(
        run_id=RUN_ID,
        identity_carrier=identity,
        review_carrier=review,
        dependency_carrier=dependency,
        implementation_strategy_map=None,
        builder_executable_package=None,
    )
    payload = load("final-ce-stage-payload.json")
    payload["implementation_strategy_map"] = None
    payload["builder_executable_package"] = None
    payload["builder_package_emitted"] = False
    payload["builder_package_not_emitted_reason"] = "builder package not emitted"
    result = fidelity(payload=payload, carriers=(identity, review, dependency, strategy))
    assert "CE_INTERMEDIATE_FIDELITY_STRATEGY_ABSENCE_REASON_MISMATCH" in code_set(result)
