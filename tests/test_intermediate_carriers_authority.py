from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from validator.intermediate_carriers import (
    canonical_json_bytes,
    evaluate_ce_intermediate_validation,
)
from validator.intermediate_carriers_fidelity import (
    validate_ce_payload_against_intermediate_carriers,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "fixtures/intermediate-carriers/valid/minimal-complete"
DISTINCT = ROOT / "fixtures/intermediate-carriers/valid/distinct-review-unit-ids"
RUN_ID = "ce-intermediate-fixture-001"


def load_base(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def transaction_inputs(*, distinct_ids: bool = False):
    values = {
        "run_id": RUN_ID,
        "intake": load_base("architect-intake.json"),
        "source_bundle": load_base("source-bundle.json"),
        "constructability_review": load_base("constructability-review.json"),
        "implementation_strategy_map": load_base("implementation-strategy-map.json"),
        "builder_executable_package": load_base("builder-executable-package.json"),
        "final_payload": load_base("final-ce-stage-payload.json"),
        "repo_root": ROOT,
    }
    if not distinct_ids:
        return values

    overlay = json.loads(
        (DISTINCT / "transaction-overrides.json").read_text(encoding="utf-8")
    )
    mappings = overlay["review_unit_mappings"]
    by_architect = {
        item["architect_node_ref"]: item["review_unit_id"] for item in mappings
    }

    for review_unit in values["constructability_review"]["reviewed_nodes"]:
        review_unit["review_unit_id"] = by_architect[
            review_unit["architect_node_ref"]
        ]
    for strategy in values["implementation_strategy_map"]["strategies"]:
        strategy["node_id"] = by_architect[strategy["node_id"]]

    payload = values["final_payload"]
    for review_unit in payload["constructability_review"]["reviewed_nodes"]:
        review_unit["review_unit_id"] = by_architect[
            review_unit["architect_node_ref"]
        ]
    for trace in payload["architecture_identity"]["review_unit_traces"]:
        trace["ce_review_unit_id"] = by_architect[trace["architect_node_ref"]]
    for strategy in payload["implementation_strategy_map"]["strategies"]:
        strategy["node_id"] = by_architect[strategy["node_id"]]
    return values


def evaluate(values):
    return evaluate_ce_intermediate_validation(**copy.deepcopy(values))


def codes(result):
    return {item["code"] for item in result["diagnostics"]}


def faithful_nonready_payload(values, first_result, status: str):
    payload = copy.deepcopy(values["final_payload"])
    carriers = first_result["carriers"]
    identity = carriers["architecture_identity_preservation_result"]["derived_data"]
    review = carriers["ce_review_units_and_interrogation_results"]["derived_data"]
    dependency = carriers["dependency_classification"]["derived_data"]
    strategy = carriers["implementation_strategy_coverage_result"]["derived_data"]

    payload["payload_status"] = status
    payload["architecture_identity"].update(identity["payload_projection"])
    payload["constructability_review"] = copy.deepcopy(
        values["constructability_review"]
    )
    payload["constructability_review"]["reviewed_nodes"] = copy.deepcopy(
        review["payload_projection"]["reviewed_nodes"]
    )
    payload["constructability_review"]["blocking_dependencies"] = copy.deepcopy(
        dependency["payload_projection"]["blocking_dependencies"]
    )
    payload["implementation_strategy_map"] = strategy["payload_projection"][
        "implementation_strategy_map"
    ]
    payload["builder_package_emitted"] = False
    payload["builder_executable_package"] = None
    payload["builder_package_not_emitted_reason"] = strategy["payload_projection"][
        "builder_package_not_emitted_reason"
    ]
    payload["unresolved_evidence"] = [
        {"id": value}
        for value in dependency["payload_projection"]["required_unresolved_ids"]
    ]
    return payload


def test_authoritative_evaluator_derives_all_carriers_from_raw_inputs():
    result = evaluate(transaction_inputs())
    assert result["transaction_status"] == "complete"
    assert result["fidelity_passed"] is True
    assert result["builder_ready"] is True
    assert set(result["carriers"]) == {
        "architecture_identity_preservation_result",
        "ce_review_units_and_interrogation_results",
        "dependency_classification",
        "implementation_strategy_coverage_result",
    }
    assert all(value == "complete" for value in result["carrier_statuses"].values())


def test_authoritative_evaluator_is_byte_deterministic():
    first = evaluate(transaction_inputs())
    second = evaluate(transaction_inputs())
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_serialized_carriers_are_not_authoritative_inputs():
    signature = inspect.signature(evaluate_ce_intermediate_validation)
    assert "identity_carrier" not in signature.parameters
    forged = {
        "status": "complete",
        "diagnostics": [],
        "source_identities": [{"sha256": "0" * 64}],
    }
    with pytest.raises(TypeError):
        evaluate_ce_intermediate_validation(
            **transaction_inputs(),
            identity_carrier=forged,
        )


def test_compatibility_comparator_is_explicitly_non_authoritative():
    result = evaluate(transaction_inputs())
    carriers = result["carriers"]
    diagnostic = validate_ce_payload_against_intermediate_carriers(
        payload=transaction_inputs()["final_payload"],
        identity_carrier=carriers["architecture_identity_preservation_result"],
        review_carrier=carriers["ce_review_units_and_interrogation_results"],
        dependency_carrier=carriers["dependency_classification"],
        strategy_carrier=carriers["implementation_strategy_coverage_result"],
    )
    assert diagnostic["authoritative"] is False


def test_distinct_review_unit_ids_are_canonical_strategy_keys():
    result = evaluate(transaction_inputs(distinct_ids=True))
    strategy = result["carriers"]["implementation_strategy_coverage_result"]
    assert result["carrier_statuses"]["ce_review_units_and_interrogation_results"] == "complete"
    assert result["carrier_statuses"]["dependency_classification"] == "complete"
    assert strategy["status"] == "complete"
    assert strategy["derived_data"]["uncovered_review_units"] == []
    assert "CE_STRATEGY_COVERAGE_ORPHAN_STRATEGY" not in codes(result)


def test_strategy_using_architect_node_ref_is_rejected():
    values = transaction_inputs(distinct_ids=True)
    for strategy in values["implementation_strategy_map"]["strategies"]:
        strategy["node_id"] = {
            "CE-RU-001": "node-root",
            "CE-RU-002": "node-wrapper",
        }[strategy["node_id"]]
    values["final_payload"]["implementation_strategy_map"] = copy.deepcopy(
        values["implementation_strategy_map"]
    )
    result = evaluate(values)
    assert "CE_STRATEGY_COVERAGE_REVIEW_UNIT_UNCOVERED" in codes(result)
    assert "CE_STRATEGY_COVERAGE_ORPHAN_STRATEGY" in codes(result)
    assert result["builder_ready"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "emission_false",
        "package_null",
        "reason_present",
        "schema",
        "status",
        "candidate",
        "classes",
        "strategy_ref",
        "blockers",
        "decisions",
        "confirmation",
        "first_safe_batch",
        "nested",
    ],
)
def test_ready_payload_requires_exact_raw_builder_package(mutation):
    values = transaction_inputs()
    payload = values["final_payload"]
    package = payload["builder_executable_package"]
    if mutation == "emission_false":
        payload["builder_package_emitted"] = False
    elif mutation == "package_null":
        payload["builder_executable_package"] = None
    elif mutation == "reason_present":
        payload["builder_package_not_emitted_reason"] = "unexpected"
    elif mutation == "schema":
        package["schema"] = "ev4-builder-executable-package@9.9.9"
    elif mutation == "status":
        package["builder_package_status"] = "blocked"
    elif mutation == "candidate":
        package["selected_candidate_id"] = "ARCH-FAM-X"
    elif mutation == "classes":
        package["approved_class_names"].append("drift")
    elif mutation == "strategy_ref":
        package["strategy_map_ref"] = "ISM-DRIFT"
    elif mutation == "blockers":
        package["blocking_dependencies"] = ["fake-blocker"]
    elif mutation == "decisions":
        package["builder_decisions_required"] = 1
    elif mutation == "confirmation":
        package["confirmation_request"]["expected_user_token"] = "drift"
    elif mutation == "first_safe_batch":
        package["first_safe_builder_batch"]["batch_id"] = "BATCH-DRIFT"
    elif mutation == "nested":
        package["first_safe_builder_batch"]["actions"][0]["parameters"][
            "arbitrary_nested_field"
        ] = "drift"

    result = evaluate(values)
    assert result["fidelity_passed"] is False
    assert result["builder_ready"] is False
    assert {
        "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_MISMATCH",
        "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_EMISSION_MISMATCH",
        "CE_INTERMEDIATE_FIDELITY_STRATEGY_ABSENCE_REASON_MISMATCH",
        "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_REASON_PRESENT_WHEN_READY",
    } & codes(result)


def test_faithful_blocked_payload_passes_fidelity_but_is_not_builder_ready():
    values = transaction_inputs(distinct_ids=True)
    interrogation = values["constructability_review"]["reviewed_nodes"][0][
        "interrogation_result"
    ]
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = False
    values["constructability_review"]["blocking_dependencies"] = [
        "CE-RU-001:R05_OVERLAY_STRATEGY_MUST_BE_PROVEN:overlay"
    ]
    values["implementation_strategy_map"] = None
    values["builder_executable_package"] = None
    first = evaluate(values)
    values["final_payload"] = faithful_nonready_payload(values, first, "blocked")
    result = evaluate(values)
    assert result["fidelity_passed"] is True
    assert result["builder_ready"] is False
    assert result["transaction_status"] == "blocked"


def test_faithful_insufficient_payload_passes_fidelity_but_is_not_builder_ready():
    values = transaction_inputs(distinct_ids=True)
    interrogation = values["constructability_review"]["reviewed_nodes"][0][
        "interrogation_result"
    ]
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False
    values["constructability_review"]["blocking_dependencies"] = []
    values["implementation_strategy_map"] = None
    values["builder_executable_package"] = None
    first = evaluate(values)
    values["final_payload"] = faithful_nonready_payload(
        values,
        first,
        "insufficient_evidence",
    )
    result = evaluate(values)
    assert result["fidelity_passed"] is True
    assert result["builder_ready"] is False
    assert result["transaction_status"] == "insufficient_evidence"
