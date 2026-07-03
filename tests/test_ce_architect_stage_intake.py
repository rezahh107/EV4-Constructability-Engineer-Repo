from __future__ import annotations
import copy, importlib.util, json, subprocess, sys
from pathlib import Path
import pytest

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

def mutate(path: str, value):
    payload = load_payload(); cur = payload; parts = path.split(".")
    for p in parts[:-1]:
        cur = cur[int(p)] if p.isdigit() else cur[p]
    if parts[-1].isdigit():
        cur[int(parts[-1])] = value
    else:
        cur[parts[-1]] = value
    return payload

def test_fixture_suite_passes():
    failures, reports = mod.validate_fixture_suite(ROOT)
    assert failures == 0
    assert len(reports) == 24

def test_direct_copies_preserve_exact_values():
    payload = load_payload()
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "valid"
    assert payload["source_contract"]["schema_id"] == "ev4-architect-stage-payload@1.0.0"
    assert payload["selected_architecture"]["selected_candidate_id"] == "ARCH-FAM-C"
    assert payload["negative_boundary_assertions"]["builder_ready"] is False

def test_structural_projection_does_not_add_ce_actions():
    payload = load_payload()
    assert "ce_review_units" not in payload
    assert "action_proposed" not in json.dumps(payload)
    assert all("source_node_id" in n for n in payload["structure_projection"]["nodes"])

def test_invalid_legacy_source_schema_rejected():
    _, reports = mod.validate_fixture_suite(ROOT)
    case = next(r for r in reports if r["fixture"].endswith("#legacy-source-schema-used-as-canonical-source"))
    assert case["actual"] == "invalid"
    assert "SCHEMA_VALIDATION_FAILED" in case["diagnostic_codes"]

def test_unresolved_evidence_remains_unresolved():
    payload = load_payload()
    assert {u["state"] for u in payload["unresolved_evidence"]} == {"insufficient_evidence"}

def test_insufficient_evidence_is_distinct():
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_file(ROOT/"fixtures/architect-stage-intake/insufficient-evidence/missing-real-architect-stage-bundle.v1.json")
    assert result["status"] == "insufficient_evidence"
    assert result["diagnostics"] == []

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

@pytest.mark.parametrize(("path","value"), [
    ("source_contract", None),
    ("selected_architecture.selected_candidate_id", {"not":"string"}),
    ("structure_projection", None),
    ("selected_architecture.decision_source_refs", {"not":"array"}),
    ("unresolved_evidence", 7),
    ("negative_boundary_assertions", []),
    ("source_repository_ref", None),
])
def test_schema_invalid_nested_types_fail_before_semantic(path, value):
    validator = mod.CEArchitectStageIntakeValidator(ROOT)
    payload = mutate(path, value)
    first = validator.validate_value(payload)
    second = validator.validate_value(copy.deepcopy(payload))
    assert first == second
    assert first["status"] == "invalid"
    codes = [d["code"] for d in first["diagnostics"]]
    assert "SCHEMA_VALIDATION_FAILED" in codes
    assert all(code == "SCHEMA_VALIDATION_FAILED" for code in codes)
    assert all("rule_id" not in d for d in first["diagnostics"])

def test_cli_schema_invalid_nested_type_exit_1_no_traceback(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(mutate("source_contract", None)), encoding="utf-8")
    first = run_cli("--file", str(path), "--format", "json")
    second = run_cli("--file", str(path), "--format", "json")
    assert first.returncode == 1
    assert second.returncode == 1
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["diagnostics"][0]["code"] == "SCHEMA_VALIDATION_FAILED"

def test_cli_insufficient_evidence_exit_2():
    completed = run_cli("--file","fixtures/architect-stage-intake/insufficient-evidence/missing-real-architect-stage-bundle.v1.json","--format","json")
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "insufficient_evidence"

def test_duplicate_mapping_trace_rejected():
    payload = load_payload()
    payload["mapping_trace"][1]["source_path"] = "$.schema_id"
    payload["mapping_trace"][1]["target_path"] = "$.source_contract.schema_id"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert any(d["code"] == "CE_I10_DUPLICATE_MAPPING_TRACE" for d in result["diagnostics"])

def test_structural_projection_requires_deterministic_order():
    payload = load_payload()
    payload["mapping_trace"][2]["ordering_rule"] = "preserve_source_order"
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(payload)
    assert result["status"] == "invalid"
    assert any(d["code"] == "CE_I10_MAPPING_ORDER_NOT_DETERMINISTIC" for d in result["diagnostics"])
