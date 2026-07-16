from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from validator.project_gate_export import load_json
from validator.project_gate_exporter import (
    EXPECTED_STAGE_BUNDLE_SHA256,
    _safe_output_path,
    export_file,
    validate_stage_bundle_lock,
    verify_export_identity,
)
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json


def test_stage_bundle_contract_bytes_and_lock_are_pinned() -> None:
    path = ROOT / "contracts/project-gate/stage-bundle.v1.schema.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_STAGE_BUNDLE_SHA256
    validate_stage_bundle_lock(ROOT)


def test_valid_real_payload_produces_allowed_gate_ready_export(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    output_path.unlink(missing_ok=True)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            provenance=_provenance(),
        )
        assert result.status == "successful", result.as_dict()
        assert result.output_written is True
        assert result.handoff_allowed is True
        export = load_json(output_path)
        assert export["schema_version"] == "producer-gate-export.v1"
        assert export["final_stage_bundle"]["schema_version"] == "stage-evidence-bundle.v1"
        assert export["handoff"] == {
            "target": "builder",
            "status": "successful",
            "allowed": True,
            "failure_reasons": [],
            "blocking_diagnostics": [],
            "unresolved_evidence": [],
        }
        assert export["producer"]["commit_sha"] == _provenance().commit_sha
        assert verify_export_identity(export)
        assert "builder_context_package" not in json.dumps(export).lower()
    finally:
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()


def test_repeated_export_of_same_run_is_deterministic(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    output_path.unlink(missing_ok=True)
    try:
        first = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            provenance=_provenance(),
        )
        first_bytes = output_path.read_bytes()
        second = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            overwrite=True,
            provenance=_provenance(),
        )
        assert first.status == second.status == "successful"
        assert output_path.read_bytes() == first_bytes
        assert first.summary["export_hash"] == second.summary["export_hash"]
    finally:
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()


def test_synthetic_payload_writes_blocked_export_without_false_acceptance(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path, synthetic=True),
    )
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    output_path.unlink(missing_ok=True)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            provenance=_provenance(),
        )
        assert result.status == "blocked"
        assert result.output_written is True
        assert result.handoff_allowed is False
        export = load_json(output_path)
        assert export["handoff"]["allowed"] is False
        assert "CE_EXPORT_SYNTHETIC_EVIDENCE_BLOCKED" in {
            item["code"] for item in export["handoff"]["blocking_diagnostics"]
        }
    finally:
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()


def test_dirty_checkout_writes_blocked_export(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    output_path.unlink(missing_ok=True)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            provenance=_provenance(dirty=True),
        )
        assert result.status == "blocked"
        assert result.output_written is True
        assert result.handoff_allowed is False
        assert result.summary["repository_dirty"] is True
    finally:
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()


def test_source_intake_hash_mismatch_produces_no_output(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload = _payload(intake, intake_path)
    payload["source_architect_intake"]["artifact_hash"]["value"] = "0" * 64
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", payload)
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    output_path.unlink(missing_ok=True)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            provenance=_provenance(),
        )
        assert result.status == "invalid"
        assert result.output_written is False
        assert result.diagnostics[0].code == "CE_EXPORT_SOURCE_INTAKE_HASH_MISMATCH"
        assert not output_path.exists()
    finally:
        if output_path.parent.exists():
            output_path.parent.rmdir()


def test_tampered_export_identity_is_rejected(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    output_path.unlink(missing_ok=True)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            provenance=_provenance(),
        )
        assert result.output_written
        export = load_json(output_path)
        export["handoff"]["target"] = "responsive"
        assert verify_export_identity(export) is False
    finally:
        output_path.unlink(missing_ok=True)
        output_path.parent.rmdir()


def test_output_path_must_remain_inside_repository(tmp_path: Path) -> None:
    with pytest.raises(Exception) as exc_info:
        _safe_output_path(ROOT, tmp_path / "outside.json", overwrite=False)
    assert getattr(exc_info.value, "diagnostic").code == "CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY"
