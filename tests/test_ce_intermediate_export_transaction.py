from __future__ import annotations

import copy
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
from exporter_test_support import (
    INTERMEDIATE_INPUTS_FILENAME,
    ROOT,
    _payload,
    _provenance,
    _real_source_pair,
    _write_json,
)
from validator.project_gate_export import load_json
from validator.project_gate_exporter import export_file


@pytest.fixture(autouse=True)
def live_provenance_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): _provenance(),
    )


def _export(tmp_path: Path, *, payload: dict | None = None):
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    final_payload = payload or _payload(intake, intake_path)
    if payload is not None and not intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME).exists():
        _payload(intake, intake_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", final_payload)
    output_path = ROOT / ".tmp-test-output" / f"intermediate-{tmp_path.name}.json"
    output_path.unlink(missing_ok=True)
    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        output_path=output_path,
    )
    return result, output_path, intake_path


def test_authoritative_export_requires_independent_intermediate_input_artifact(
    tmp_path: Path,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    sidecar = intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)
    sidecar.unlink()
    output_path = ROOT / ".tmp-test-output" / "missing-intermediate.json"
    output_path.unlink(missing_ok=True)

    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        output_path=output_path,
    )

    assert result.status == "invalid"
    assert result.output_written is False
    assert result.handoff_allowed is False
    assert result.diagnostics[0].code == "CE_EXPORT_INTERMEDIATE_INPUTS_READ_FAILED"
    assert not output_path.exists()


def test_final_payload_cannot_override_independent_review(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload = _payload(intake, intake_path)
    sidecar_path = intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)
    sidecar = load_json(sidecar_path)
    sidecar["constructability_review"]["reviewed_nodes"][0][
        "action_proposed"
    ] = "independent-drift"
    _write_json(sidecar_path, sidecar)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", payload)
    output_path = ROOT / ".tmp-test-output" / "independent-review-drift.json"
    output_path.unlink(missing_ok=True)

    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        output_path=output_path,
    )

    assert result.status == "invalid"
    assert result.output_written is False
    assert result.handoff_allowed is False
    assert "CE_INTERMEDIATE_FIDELITY_REVIEWED_NODES_MISMATCH" in {
        item.code for item in result.diagnostics
    }
    assert not output_path.exists()


def test_stage_manifest_uses_internally_derived_carrier_outputs(tmp_path: Path) -> None:
    result, output_path, _ = _export(tmp_path)
    try:
        assert result.status == "successful", result.as_dict()
        export = load_json(output_path)
        by_id = {item["stage_id"]: item for item in export["stage_manifest"]}
        for stage_id in (
            "identity_lock_validation",
            "node_action_interrogation",
            "hidden_dependency_classification",
            "constructability_review",
            "implementation_strategy_determination",
            "builder_package_gate",
        ):
            stage = by_id[stage_id]
            assert stage["status"] == "complete"
            assert stage["output"]["artifact_ref"].startswith(
                "ce-intermediate-transaction:"
            )
            assert len(stage["output"]["artifact_hash"]["value"]) == 64
    finally:
        output_path.unlink(missing_ok=True)


def test_identical_invalid_builder_packages_cannot_authorize_export(
    tmp_path: Path,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload = _payload(intake, intake_path)
    sidecar_path = intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)
    sidecar = load_json(sidecar_path)
    del sidecar["builder_executable_package"]["package_id"]
    payload["builder_executable_package"] = copy.deepcopy(
        sidecar["builder_executable_package"]
    )
    _write_json(sidecar_path, sidecar)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", payload)
    output_path = ROOT / ".tmp-test-output" / "invalid-equal-package.json"
    output_path.unlink(missing_ok=True)

    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        output_path=output_path,
    )

    assert result.status == "invalid"
    assert result.output_written is False
    assert result.handoff_allowed is False
    assert "CE_STRATEGY_COVERAGE_PACKAGE_SCHEMA_VALIDATION_FAILED" in {
        item.code for item in result.diagnostics
    }
    assert not output_path.exists()
