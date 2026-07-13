from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "planning" / "decision-escape-routes.schema.json"
STATE = ROOT / "planning" / "DECISION_ESCAPE_ROUTES.yml"


def load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def load_state() -> dict:
    return yaml.safe_load(STATE.read_text(encoding="utf-8"))


def schema_errors(payload: dict):
    validator = Draft202012Validator(load_schema())
    return sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            list(error.absolute_path),
            error.validator,
            list(error.absolute_schema_path),
        ),
    )


def test_decision_escape_routes_state_file_validates_against_schema() -> None:
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    assert schema_errors(load_state()) == []


def test_authority_provenance_requires_exact_sha() -> None:
    payload = copy.deepcopy(load_state())
    payload["authority_provenance"]["inspected_base_sha"] = "not-a-sha"
    assert schema_errors(payload)


def test_session_scope_uses_per_artifact_not_single_turn() -> None:
    payload = copy.deepcopy(load_state())
    payload["records"][1]["session_scope"] = "single_turn"
    assert schema_errors(payload)

    payload["records"][1]["session_scope"] = "per_artifact"
    assert schema_errors(payload) == []


def test_decision_escape_routes_schema_rejects_authored_derived_fields() -> None:
    for field in ["resolved", "production_ready"]:
        payload = copy.deepcopy(load_state())
        payload["records"][0][field] = False
        assert schema_errors(payload), field


def test_decision_escape_routes_schema_rejects_legacy_routes_array() -> None:
    payload = copy.deepcopy(load_state())
    payload["routes"] = []
    assert schema_errors(payload)


def test_mapped_record_requires_decision_family_and_pattern() -> None:
    for field in ["decision_family", "required_decision_card_ref_pattern"]:
        payload = copy.deepcopy(load_state())
        payload["records"][0][field] = None
        assert schema_errors(payload), field


def test_not_applicable_mapping_requires_reason_and_null_mapping_fields() -> None:
    payload = copy.deepcopy(load_state())
    record = payload["records"][0]
    record["mapping_status"] = "not_applicable_with_reason"
    record["decision_family"] = None
    record["required_decision_card_ref_pattern"] = None
    record["not_applicable_reason"] = "No Kernel-governed decision family applies."
    assert schema_errors(payload) == []

    record["decision_family"] = "layout_structure"
    assert schema_errors(payload)


def test_schema_backed_requires_schema_carrier() -> None:
    payload = copy.deepcopy(load_state())
    record = payload["records"][1]
    record["status"]["enforcement_status"] = "schema_backed"
    record["carriers"]["schema_carrier"] = None
    assert schema_errors(payload)


def test_validator_backed_requires_validator_carriers() -> None:
    for carrier in ["validator_rule", "validator_diagnostic"]:
        payload = copy.deepcopy(load_state())
        record = payload["records"][1]
        record["status"]["enforcement_status"] = "validator_backed"
        record["carriers"][carrier] = None
        assert schema_errors(payload), carrier


def test_fixture_tested_requires_positive_and_negative_fixtures() -> None:
    for carrier in ["test_command", "positive_fixture", "negative_fixture", "validator_rule", "validator_diagnostic"]:
        payload = copy.deepcopy(load_state())
        record = payload["records"][1]
        record["status"]["enforcement_status"] = "fixture_tested"
        record["carriers"][carrier] = None
        assert schema_errors(payload), carrier


def test_ci_enforced_requires_ci_and_fixture_carriers() -> None:
    for carrier in ["CI_step", "test_command", "positive_fixture", "negative_fixture", "validator_rule", "validator_diagnostic"]:
        payload = copy.deepcopy(load_state())
        record = payload["records"][1]
        record["status"]["enforcement_status"] = "ci_enforced"
        record["carriers"][carrier] = None
        assert schema_errors(payload), carrier


def test_sequence_ci_enforced_requires_sequence_carriers() -> None:
    for carrier in ["sequence_CI_step", "test_command", "positive_fixture", "negative_fixture", "validator_rule", "validator_diagnostic"]:
        payload = copy.deepcopy(load_state())
        record = payload["records"][0]
        record["status"]["enforcement_status"] = "sequence_ci_enforced"
        record["carriers"][carrier] = None
        assert schema_errors(payload), carrier


def test_extended_ladder_requires_matching_carrier() -> None:
    cases = [
        ("advisory_ci_observed", "CI_step"),
        ("runtime_monitor_enforced", "runtime_monitor"),
        ("os_harness_enforced", "os_harness_policy"),
        ("downstream_contract_enforced", "downstream_contract"),
    ]
    for status, carrier in cases:
        payload = copy.deepcopy(load_state())
        record = payload["records"][1]
        record["status"]["enforcement_status"] = status
        record["carriers"][carrier] = None
        assert schema_errors(payload), (status, carrier)
