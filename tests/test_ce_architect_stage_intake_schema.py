from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-ce-architect-stage-intake.py"
SCHEMA_V1_1 = ROOT / "schemas" / "ce_architect_stage_intake.v1_1.schema.json"
FIXTURE = ROOT / "fixtures" / "architect-stage-intake-v1-1" / "valid" / "project-gate-transition-complete.v1_1.json"

spec = importlib.util.spec_from_file_location("ce_intake_validator_for_schema_tests", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["ce_intake_validator_for_schema_tests"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


def load_schema() -> dict:
    return json.loads(SCHEMA_V1_1.read_text(encoding="utf-8"))


def load_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def schema_errors(payload: dict):
    validator = Draft202012Validator(load_schema())
    return sorted(validator.iter_errors(payload), key=lambda e: (list(e.absolute_path), e.validator, list(e.absolute_schema_path)))


def add_derivation_rule_to_trace(index: int, classification: str) -> dict:
    payload = load_payload()
    payload["mapping_trace"][index]["classification"] = classification
    payload["mapping_trace"][index]["derivation_rule"] = {"id": "CE-MAP-A2C-01", "version": "1.0.0"}
    return payload


NON_DERIVED_CASES = [
    ("direct_evidence_copy", 0),
    ("deterministic_structural_projection", 7),
    ("allowed_representation_conversion", 14),
    ("unsupported", 0),
]


def test_direct_schema_rejects_non_derived_rows_with_derivation_rule():
    for classification, index in NON_DERIVED_CASES:
        payload = add_derivation_rule_to_trace(index, classification)
        errors = schema_errors(payload)
        assert errors, classification
        assert any(list(error.absolute_path)[:2] == ["mapping_trace", index] for error in errors)


def test_direct_schema_rejects_derived_metadata_without_derivation_rule():
    payload = load_payload()
    del payload["mapping_trace"][15]["derivation_rule"]
    errors = schema_errors(payload)
    assert errors
    assert any(list(error.absolute_path)[:2] == ["mapping_trace", 15] and error.validator == "required" for error in errors)


def test_direct_schema_accepts_derived_metadata_with_exact_derivation_rule():
    payload = load_payload()
    errors = schema_errors(payload)
    assert errors == []


def test_schema_rejection_occurs_before_semantic_validation():
    payload = add_derivation_rule_to_trace(0, "direct_evidence_copy")
    payload["source_repository_ref"]["ref"] = "/builder-feed-export"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    codes = [diagnostic["code"] for diagnostic in result["diagnostics"]]
    assert "CE_I21_UNDOCUMENTED_DERIVATION_RULE" in codes
    assert "CE_I12_LEGACY_SOURCE_STAGE_FORBIDDEN" not in codes


def test_schema_file_contains_inverse_draft_2020_12_conditional():
    mapping_trace_item = load_schema()["$defs"]["mappingTraceItem"]
    rule = mapping_trace_item["allOf"][0]
    assert rule["if"]["properties"]["classification"]["const"] == "deterministic_derived_metadata"
    assert rule["then"] == {"required": ["derivation_rule"]}
    assert rule["else"] == {"not": {"required": ["derivation_rule"]}}
    assert mapping_trace_item["additionalProperties"] is False
