from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from validator.project_gate_export import (
    load_json,
    validate_pipeline_manifest,
    validate_producer_gate_export,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_manifest_repo(tmp_path: Path, manifest: dict) -> Path:
    repo = tmp_path / "repo"
    (repo / "schemas").mkdir(parents=True)
    (repo / "manifests").mkdir(parents=True)
    schema = (ROOT / "schemas/ce_pipeline_manifest.v1.schema.json").read_text(encoding="utf-8")
    (repo / "schemas/ce_pipeline_manifest.v1.schema.json").write_text(schema, encoding="utf-8")
    (repo / "manifests/ce_pipeline_manifest.v1.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    return repo


def test_malformed_manifest_non_integer_ordinal_fails_closed(tmp_path: Path) -> None:
    manifest = load_json(ROOT / "manifests/ce_pipeline_manifest.v1.json")
    manifest["project_execution_stages"][1]["ordinal"] = "2"
    repo = _write_manifest_repo(tmp_path, manifest)

    diagnostics = validate_pipeline_manifest(repo)

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "CE_PIPELINE_ORDINAL_TYPE_INVALID" in codes
    assert "CE_PG_SCHEMA_INVALID" in codes


def test_malformed_manifest_stage_entry_object_fails_closed(tmp_path: Path) -> None:
    manifest = load_json(ROOT / "manifests/ce_pipeline_manifest.v1.json")
    manifest["project_execution_stages"][-1] = "malformed-stage"
    repo = _write_manifest_repo(tmp_path, manifest)

    diagnostics = validate_pipeline_manifest(repo)

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "CE_PIPELINE_STAGE_OBJECT_REQUIRED" in codes
    assert "CE_PIPELINE_EXPORT_NOT_FINAL" in codes


def test_malformed_export_final_stage_entry_fails_closed() -> None:
    fixture = load_json(ROOT / "fixtures/project_gate_export/valid_blocked_ce_producer_gate_export.json")
    export = deepcopy(fixture["document"])
    export["stage_manifest"][-1] = "malformed-stage"

    diagnostics = validate_producer_gate_export(ROOT, export)

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "CE_PG_STAGE_OBJECT_REQUIRED" in codes
    assert "CE_PG_EXPORT_STAGE_NOT_FINAL" in codes


def test_schema_error_sorting_handles_mixed_path_components() -> None:
    fixture = load_json(ROOT / "fixtures/project_gate_export/valid_blocked_ce_producer_gate_export.json")
    export = deepcopy(fixture["document"])
    export["stage_manifest"][0]["output"]["present"] = "yes"
    export["stage_manifest"][1] = "malformed-stage"

    diagnostics = validate_producer_gate_export(ROOT, export)

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "CE_PG_SCHEMA_INVALID" in codes
    assert "CE_PG_STAGE_OBJECT_REQUIRED" in codes
