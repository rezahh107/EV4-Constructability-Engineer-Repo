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


def test_decision_escape_routes_schema_rejects_authored_resolved_record_field() -> None:
    payload = copy.deepcopy(load_state())
    record = copy.deepcopy(payload["records"][0])
    record["resolved"] = False
    payload["records"] = [record]

    errors = schema_errors(payload)

    assert errors
    assert any(error.validator in {"not", "additionalProperties"} for error in errors)


def test_decision_escape_routes_schema_rejects_authored_production_ready_record_field() -> None:
    payload = copy.deepcopy(load_state())
    record = copy.deepcopy(payload["records"][0])
    record["production_ready"] = False
    payload["records"] = [record]

    errors = schema_errors(payload)

    assert errors
    assert any(error.validator in {"not", "additionalProperties"} for error in errors)


def test_decision_escape_routes_schema_rejects_legacy_routes_array() -> None:
    payload = copy.deepcopy(load_state())
    payload["routes"] = []

    errors = schema_errors(payload)

    assert errors
    assert any(error.validator == "additionalProperties" for error in errors)
    assert any(error.validator == "not" and list(error.absolute_path) == [] for error in errors)


def test_decision_escape_routes_record_requires_sequence_carriers() -> None:
    payload = copy.deepcopy(load_state())
    del payload["records"][0]["carriers"]["sequence_CI_step"]

    errors = schema_errors(payload)

    assert errors
    assert any(error.validator == "required" for error in errors)
