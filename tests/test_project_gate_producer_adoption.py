from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from validator.project_gate_export import (
    EXPECTED_PRODUCER_EXPORT_SHA256,
    canonical_bytes,
    load_json,
    sha256_file,
    validate_pipeline_manifest,
    validate_producer_gate_export,
    validate_project_gate_lock,
    validate_repository,
)

ROOT = Path(__file__).resolve().parents[1]


def test_vendored_project_gate_contract_exact_bytes() -> None:
    vendored = ROOT / "contracts/project-gate/producer-gate-export.v1.schema.json"
    assert sha256_file(vendored) == EXPECTED_PRODUCER_EXPORT_SHA256
    assert validate_project_gate_lock(ROOT) == []


def test_pipeline_manifest_is_canonical_and_final_export_stage() -> None:
    diagnostics = validate_pipeline_manifest(ROOT)
    assert diagnostics == []
    manifest = load_json(ROOT / "manifests/ce_pipeline_manifest.v1.json")
    stages = manifest["project_execution_stages"]
    assert [stage["ordinal"] for stage in stages] == list(range(1, len(stages) + 1))
    assert stages[-1]["stage_id"] == "project_gate_export"
    assert stages[-1]["mandatory"] is True


def test_valid_blocked_export_is_machine_valid_but_not_builder_authorization() -> None:
    fixture = load_json(ROOT / "fixtures/project_gate_export/valid_blocked_ce_producer_gate_export.json")
    export = fixture["document"]
    diagnostics = validate_producer_gate_export(ROOT, export)
    assert diagnostics == []
    assert export["handoff"]["allowed"] is False
    assert export["final_stage_bundle"]["payload"]["data"]["builder_package_emitted"] is False


def test_silent_fallback_is_rejected() -> None:
    fixture = load_json(ROOT / "fixtures/project_gate_export/invalid_silent_fallback_true.json")
    diagnostics = validate_producer_gate_export(ROOT, fixture["document"])
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "CE_PG_SILENT_FALLBACK_FORBIDDEN" in codes


def test_repository_project_gate_adoption_fixtures_match_expectations() -> None:
    result = validate_repository(ROOT)
    assert result["passed"], result["diagnostics"]


def test_deterministic_canonical_serialization_rejects_nan() -> None:
    with pytest.raises(ValueError):
        canonical_bytes({"value": math.nan})


def test_json_loader_rejects_non_standard_infinity(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"value": Infinity}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_json(path)


def test_canonical_serialization_is_stable() -> None:
    left = {"b": [2, 1], "a": {"z": 1}}
    right = json.loads('{"a":{"z":1},"b":[2,1]}')
    assert canonical_bytes(left) == canonical_bytes(right)
