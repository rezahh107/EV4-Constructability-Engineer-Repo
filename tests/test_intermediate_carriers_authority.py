from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

import validator.intermediate_carriers as public_module
from validator.intermediate_carriers import (
    canonical_json_bytes,
    evaluate_ce_intermediate_validation,
)
from validator.intermediate_carriers_fidelity import (
    _diagnose_ce_payload_against_serialized_carriers,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/intermediate-carriers/valid/minimal-complete"
RUN_ID = "ce-intermediate-fixture-001"


def load(name: str):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


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


def codes(result):
    return {item["code"] for item in result["diagnostics"]}


def test_authoritative_api_accepts_raw_inputs_only():
    signature = inspect.signature(evaluate_ce_intermediate_validation)
    assert set(signature.parameters) == {
        "run_id",
        "intake",
        "source_bundle",
        "constructability_review",
        "implementation_strategy_map",
        "builder_executable_package",
        "final_payload",
        "repo_root",
    }
    assert "identity_carrier" not in signature.parameters


def test_public_module_exposes_no_serialized_carrier_success_validator():
    assert not hasattr(public_module, "validate_ce_payload_against_intermediate_carriers")
    assert "validate_ce_payload_against_intermediate_carriers" not in public_module.__all__


def test_authoritative_evaluator_derives_four_carriers_deterministically():
    first = evaluate_ce_intermediate_validation(**transaction_inputs())
    second = evaluate_ce_intermediate_validation(**transaction_inputs())
    assert first["fidelity_passed"] is True
    assert first["builder_ready"] is True
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert set(first["carriers"]) == {
        "architecture_identity_preservation_result",
        "ce_review_units_and_interrogation_results",
        "dependency_classification",
        "implementation_strategy_coverage_result",
    }


def test_forged_serialized_carriers_cannot_authorize_public_result():
    forged = {
        "schema_id": "ev4-ce-intermediate-validation-carrier@1.0.0",
        "schema_version": "1.0.0",
        "status": "complete",
        "diagnostics": [],
        "source_identities": [{"sha256": "0" * 64}],
        "derived_data": {},
    }
    with pytest.raises(TypeError):
        evaluate_ce_intermediate_validation(
            **transaction_inputs(),
            identity_carrier=forged,
            review_carrier=forged,
            dependency_carrier=forged,
            strategy_carrier=forged,
        )


def test_private_diagnostic_api_cannot_return_authority_shaped_success():
    result = evaluate_ce_intermediate_validation(**transaction_inputs())
    carriers = result["carriers"]
    diagnostic = _diagnose_ce_payload_against_serialized_carriers(
        payload=transaction_inputs()["final_payload"],
        identity_carrier=carriers["architecture_identity_preservation_result"],
        review_carrier=carriers["ce_review_units_and_interrogation_results"],
        dependency_carrier=carriers["dependency_classification"],
        strategy_carrier=carriers["implementation_strategy_coverage_result"],
    )
    assert diagnostic == {
        "diagnostic_match": True,
        "authoritative": False,
        "diagnostics": [],
        "carrier_statuses": result["carrier_statuses"],
    }
    assert not {"passed", "fidelity_passed", "builder_ready"} & set(diagnostic)


def test_schema_invalid_payload_stops_before_carrier_authority():
    values = transaction_inputs()
    values["final_payload"]["payload_status"] = "blocked"
    result = evaluate_ce_intermediate_validation(**values)
    assert result["transaction_status"] == "invalid"
    assert result["fidelity_passed"] is False
    assert result["builder_ready"] is False
    assert result["carriers"] == {}
    assert "CE_INTERMEDIATE_PAYLOAD_SCHEMA_INVALID" in codes(result)


def test_semantic_violation_outside_carrier_projection_is_rejected():
    values = transaction_inputs()
    values["final_payload"]["constructability_review"]["constructability_status"] = "blocked"
    result = evaluate_ce_intermediate_validation(**values)
    assert result["transaction_status"] == "invalid"
    assert result["fidelity_passed"] is False
    assert "CE_INTERMEDIATE_PAYLOAD_SEMANTIC_INVALID" in codes(result)


@pytest.mark.parametrize(
    "mutation",
    [
        "package_id",
        "review_ref",
        "selected_candidate_locked",
        "approved_class_names_unchanged",
        "architect_contract",
        "confirmed_action_ids",
        "batch_id",
        "action",
        "action_type",
        "target_node",
        "parameters",
    ],
)
def test_same_invalid_package_in_raw_and_payload_is_not_builder_ready(mutation):
    values = transaction_inputs()
    package = values["builder_executable_package"]
    if mutation in {"package_id", "review_ref", "batch_id"}:
        if mutation == "batch_id":
            package["first_safe_builder_batch"].pop("batch_id")
        else:
            package.pop(mutation)
    elif mutation in {"selected_candidate_locked", "approved_class_names_unchanged"}:
        package[mutation] = False
    elif mutation == "architect_contract":
        package["architect_contract"] = []
    elif mutation == "confirmed_action_ids":
        package["confirmation_request"]["confirmed_action_ids"] = []
    elif mutation == "action":
        package["first_safe_builder_batch"]["actions"] = [None]
    elif mutation == "action_type":
        package["first_safe_builder_batch"]["actions"][0].pop("action_type")
    elif mutation == "target_node":
        package["first_safe_builder_batch"]["actions"][0].pop("target_node")
    else:
        package["first_safe_builder_batch"]["actions"][0]["parameters"] = []
    values["final_payload"]["builder_executable_package"] = copy.deepcopy(package)
    result = evaluate_ce_intermediate_validation(**values)
    assert result["builder_ready"] is False
    assert "CE_STRATEGY_COVERAGE_PACKAGE_SCHEMA_VALIDATION_FAILED" in codes(result)


def test_repo_root_omission_is_a_call_error_not_a_validation_bypass():
    values = transaction_inputs()
    values.pop("repo_root")
    with pytest.raises(TypeError):
        evaluate_ce_intermediate_validation(**values)
