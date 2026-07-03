from __future__ import annotations
import copy, importlib.util, json, subprocess, sys
from pathlib import Path
import pytest
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-ce-architect-stage-intake.py"
spec = importlib.util.spec_from_file_location("ce_intake_validator", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["ce_intake_validator"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

def run_cli(*args: str):
    return subprocess.run([sys.executable, str(SCRIPT), "--repo-root", str(ROOT), *args], cwd=ROOT, text=True, capture_output=True, check=False, timeout=30)

def load_payload():
    return json.loads((ROOT/"fixtures/architect-stage-intake/valid/minimal-canonical-intake.v1.json").read_text(encoding="utf-8"))

def load_v11_payload():
    return json.loads((ROOT/"fixtures/architect-stage-intake-v1-1/valid/project-gate-transition-complete.v1_1.json").read_text(encoding="utf-8"))

def mutate(path: str, value, payload=None):
    payload = copy.deepcopy(payload or load_payload()); cur = payload; parts = path.split(".")
    for p in parts[:-1]:
        cur = cur[int(p)] if p.isdigit() else cur[p]
    if parts[-1].isdigit():
        cur[int(parts[-1])] = value
    else:
        cur[parts[-1]] = value
    return payload

def delete(path: str, payload=None):
    payload = copy.deepcopy(payload or load_payload()); cur = payload; parts = path.split(".")
    for p in parts[:-1]:
        cur = cur[int(p)] if p.isdigit() else cur[p]
    if parts[-1].isdigit():
        del cur[int(parts[-1])]
    else:
        del cur[parts[-1]]
    return payload

def test_fixture_suite_passes():
    failures, reports = mod.validate_fixture_suite(ROOT)
    assert failures == 0
    assert len(reports) == 36

def test_schema_meta_validation_rejects_invalid_bundled_schema(tmp_path: Path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "ce_architect_stage_intake.v1.schema.json").write_text(
        json.dumps({"$schema":"https://json-schema.org/draft/2020-12/schema","type": 1}),
        encoding="utf-8",
    )
    with pytest.raises(SchemaError):
        mod.CEArchitectStageIntakeValidator(tmp_path)

def test_v1_0_remains_valid_for_compatibility():
    payload = load_payload()
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "valid"
    assert payload["schema_id"] == "ev4-ce-architect-stage-intake@1.0.0"
    assert payload["ce_processing_prerequisites"]["project_gate_transition_implemented"] is False
    assert "project_gate_transition" not in payload

def test_v1_1_accepts_truthful_transition_execution_metadata():
    payload = load_v11_payload()
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "valid"
    assert payload["schema_id"] == "ev4-ce-architect-stage-intake@1.1.0"
    assert payload["project_gate_transition"]["executed"] is True
    assert payload["project_gate_transition"]["transition_id"] == "ev4-architect-to-ce-transition@1.0.0"
    assert payload["project_gate_transition"]["producer_repository"] == "rezahh107/EV4-Project-Gate"
    assert payload["ce_processing_prerequisites"]["intake_contains_ce_conclusions"] is False
    assert payload["ce_processing_prerequisites"]["intake_contains_builder_authorization"] is False

def test_structural_projection_does_not_add_ce_actions():
    payload = load_v11_payload()
    serialized = json.dumps(payload)
    assert "ce_review_units" not in payload
    assert "action_proposed" not in serialized
    assert "builder_executable_package" not in serialized
    assert all("source_node_id" in n for n in payload["structure_projection"]["nodes"])

def test_unresolved_evidence_remains_unresolved():
    payload = load_v11_payload()
    assert {u["state"] for u in payload["unresolved_evidence"]} == {"insufficient_evidence"}

def test_insufficient_evidence_v1_1_is_distinct():
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_file(ROOT/"fixtures/architect-stage-intake-v1-1/insufficient-evidence/project-gate-transition-insufficient.v1_1.json")
    assert result["status"] == "insufficient_evidence"
    assert result["diagnostics"] == []

def test_complete_v1_1_without_optional_missing_evidence_is_valid():
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(load_v11_payload())
    assert result["status"] == "valid"
    assert result["diagnostics"] == []

def test_transition_execution_record_missing_is_invalid():
    payload = delete("project_gate_transition", load_v11_payload())
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == "CE_I13_TRANSITION_RECORD_REQUIRED"
    assert result["diagnostics"][0]["rule_id"] == "CE-I13"

def test_executed_false_for_project_gate_intake_is_invalid():
    payload = mutate("project_gate_transition.executed", False, load_v11_payload())
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == "CE_I14_TRANSITION_IDENTITY_INVALID"

@pytest.mark.parametrize(("path","value"), [
    ("project_gate_transition.transition_id", "ev4-wrong-transition@1.0.0"),
    ("project_gate_transition.producer_repository", "rezahh107/EV4-Architect-Repo"),
])
def test_wrong_transition_identity_is_invalid(path, value):
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(mutate(path, value, load_v11_payload()))
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["rule_id"] == "CE-I14"

@pytest.mark.parametrize("path", ["project_gate_transition.source_bundle_id", "project_gate_transition.source_bundle_hash"])
def test_missing_source_bundle_traceability_is_invalid(path):
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(delete(path, load_v11_payload()))
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["rule_id"] == "CE-I15"

@pytest.mark.parametrize("path", ["project_gate_transition.transition_id", "project_gate_transition.transition_version", "project_gate_transition.producer_repository"])
def test_missing_transition_identity_is_invalid(path):
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(delete(path, load_v11_payload()))
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["rule_id"] == "CE-I14"

def test_source_bundle_id_mismatch_is_invalid_semantic():
    payload = mutate("project_gate_transition.source_bundle_id", "different-bundle", load_v11_payload())
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == "CE_I15_SOURCE_BUNDLE_TRACE_MISMATCH"

@pytest.mark.parametrize(("path","rule"), [
    ("ce_processing_prerequisites.intake_contains_ce_conclusions","CE-I16"),
    ("ce_processing_prerequisites.intake_contains_builder_authorization","CE-I17"),
    ("ce_processing_prerequisites.real_cross_repository_validation_available","CE-I18"),
    ("negative_boundary_assertions.ce_approved","CE-I06"),
    ("negative_boundary_assertions.builder_ready","CE-I07"),
])
def test_positive_or_contradictory_claims_are_invalid(path, rule):
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(mutate(path, True, load_v11_payload()))
    assert result["status"] == "invalid"
    assert any(d.get("rule_id") == rule for d in result["diagnostics"])

def test_missing_file_is_structured_invalid():
    completed = run_cli("--file","fixtures/architect-stage-intake/invalid/missing-file.json","--format","json")
    assert completed.returncode == 1
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == "FILE_READ_ERROR"

@pytest.mark.parametrize("bad", [[], "x", 1])
def test_top_level_non_object_inputs_are_invalid(tmp_path: Path, bad):
    path = tmp_path / "bad.json"; path.write_text(json.dumps(bad), encoding="utf-8")
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_file(path)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == "INPUT_NOT_OBJECT"

@pytest.mark.parametrize(( "path","value" ), [
    ("source_contract", None),
    ("selected_architecture.selected_candidate_id", {"not":"string"}),
    ("structure_projection", None),
    ("selected_architecture.decision_source_refs", {"not":"array"}),
    ("unresolved_evidence", 7),
    ("negative_boundary_assertions", []),
    ("source_repository_ref", None),
    ("project_gate_transition", None),
])
def test_schema_invalid_nested_types_fail_before_semantic(path, value):
    validator = mod.CEArchitectStageIntakeValidator(ROOT)
    payload = mutate(path, value, load_v11_payload())
    first = validator.validate_value(payload)
    second = validator.validate_value(copy.deepcopy(payload))
    assert first == second
    assert first["status"] == "invalid"
    assert all(d["severity"] == "error" for d in first["diagnostics"])

def test_cli_valid_text_output():
    completed = run_cli("--file","fixtures/architect-stage-intake-v1-1/valid/project-gate-transition-complete.v1_1.json")
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout == "status: valid\n"

def test_cli_invalid_text_output_includes_diagnostics():
    completed = run_cli("--file","fixtures/architect-stage-intake/invalid/missing-file.json")
    assert completed.returncode == 1
    assert completed.stderr == ""
    assert "Traceback" not in completed.stdout
    assert completed.stdout.startswith("status: invalid\n[ERROR] FILE_READ_ERROR at $: File could not be read.\n")

def test_cli_insufficient_evidence_text_output():
    completed = run_cli("--file","fixtures/architect-stage-intake-v1-1/insufficient-evidence/project-gate-transition-insufficient.v1_1.json")
    assert completed.returncode == 2
    assert completed.stderr == ""
    assert completed.stdout == "status: insufficient_evidence\n"

def test_cli_json_mode_remains_compact_and_deterministic():
    first = run_cli("--file","fixtures/architect-stage-intake-v1-1/valid/project-gate-transition-complete.v1_1.json","--format","json")
    second = run_cli("--file","fixtures/architect-stage-intake-v1-1/valid/project-gate-transition-complete.v1_1.json","--format","json")
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    assert first.stdout.startswith('{"diagnostics"')
    assert json.loads(first.stdout)["status"] == "valid"

def test_cli_schema_invalid_nested_type_exit_1_no_traceback(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(mutate("project_gate_transition", None, load_v11_payload())), encoding="utf-8")
    first = run_cli("--file", str(path), "--format", "json")
    second = run_cli("--file", str(path), "--format", "json")
    assert first.returncode == 1
    assert second.returncode == 1
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    assert "Traceback" not in first.stdout

def test_cli_insufficient_evidence_exit_2():
    completed = run_cli("--file","fixtures/architect-stage-intake-v1-1/insufficient-evidence/project-gate-transition-insufficient.v1_1.json","--format","json")
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "insufficient_evidence"

def test_ce_i11_missing_missing_evidence_uses_rule_specific_schema_diagnostic():
    payload = load_v11_payload()
    payload["intake_status"] = "insufficient_evidence"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert result["diagnostics"][0]["code"] == "CE_I11_MISSING_EVIDENCE_REQUIRED"
    assert result["diagnostics"][0]["rule_id"] == "CE-I11"

def test_unrelated_schema_failure_remains_generic_schema_diagnostic():
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(mutate("source_contract", None, load_v11_payload()))
    assert result["status"] == "invalid"
    assert any(d["code"] == "SCHEMA_VALIDATION_FAILED" for d in result["diagnostics"])

def test_semantic_validation_is_not_executed_for_schema_invalid_input():
    payload = mutate("project_gate_transition", None, load_v11_payload())
    payload["source_repository_ref"]["ref"] = "/builder-feed-export"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    codes = [d["code"] for d in result["diagnostics"]]
    assert "CE_I12_LEGACY_SOURCE_STAGE_FORBIDDEN" not in codes

def test_duplicate_mapping_trace_rejected():
    payload = load_v11_payload()
    payload["mapping_trace"][1]["source_path"] = "$.bundle_id"
    payload["mapping_trace"][1]["target_path"] = "$.project_gate_transition.source_bundle_id"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert any(d["code"] == "CE_I10_DUPLICATE_MAPPING_TRACE" for d in result["diagnostics"])

def test_structural_projection_requires_deterministic_order():
    payload = load_v11_payload()
    payload["mapping_trace"][2]["ordering_rule"] = "preserve_source_order"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert any(d["code"] == "CE_I10_MAPPING_ORDER_NOT_DETERMINISTIC" for d in result["diagnostics"])

def test_status_history_preserved():
    status = (ROOT/"STATUS.md").read_text(encoding="utf-8")
    assert "CE_ARCHITECT_STAGE_INTAKE_V1:" in status
    assert "CE_ARCHITECT_STAGE_INTAKE_V1_1:" in status
