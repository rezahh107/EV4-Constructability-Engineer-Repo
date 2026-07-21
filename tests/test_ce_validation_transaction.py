from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import validator.ce_validation_transaction as transaction_module
import validator.project_gate_exporter as exporter_module
from validator.ce_validation_transaction import (
    _synchronize_intake_stage_status,
    validate_transaction_artifact,
)
from validator.project_gate_export import load_json
from validator.project_gate_exporter import ExportDiagnostic, ExporterError, export_file
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json

SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from ce_bootstrap_test_support import route, valid_pair  # noqa: E402


@pytest.fixture(autouse=True)
def live_provenance_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): _provenance(),
    )


def _cleanup(path: Path) -> None:
    path.unlink(missing_ok=True)
    parent = path.parent
    if parent.name == ".tmp-test-output" and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def test_bootstrap_exact_byte_snapshot_change_blocks_first_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake_path, source_path = valid_pair(tmp_path)
    original_read_bytes = Path.read_bytes
    target = source_path.resolve()
    reads = 0

    def changed_second_read(path: Path) -> bytes:
        nonlocal reads
        data = original_read_bytes(path)
        if path.resolve() == target:
            reads += 1
            if reads == 2:
                return data + b"\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", changed_second_read)
    result = route("شروع", [intake_path, source_path])

    assert result["route"] == "blocked_source_binding_invalid"
    assert result["pipeline_execution"] == "forbidden"
    assert result["source_provenance_verification"] == "failed"
    assert result["diagnostics"][0]["code"] == (
        "CE_BOOTSTRAP_INPUT_CHANGED_DURING_ROUTING"
    )


def test_bootstrap_positive_control_reports_exact_snapshot_evidence(tmp_path: Path) -> None:
    intake_path, source_path = valid_pair(tmp_path)
    result = route("شروع", [intake_path, source_path])

    assert result["route"] == "architect_intake_validation"
    assert result["source_binding_verified"] is True
    assert result["input_snapshot_evidence"]["second_read_equality"] is True
    assert len(result["input_snapshot_evidence"]["ce_input_file_sha256"]) == 64
    assert len(result["input_snapshot_evidence"]["source_bundle_file_sha256"]) == 64


def test_payload_mutation_after_snapshot_fails_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "payload-mutated.json"
    _cleanup(output_path)
    original_validate = transaction_module.validate_payload_and_ce_semantics

    def validate_then_mutate(repo_root: Path, payload: dict) -> dict:
        result = original_validate(repo_root, payload)
        mutated = json.loads(payload_path.read_text(encoding="utf-8"))
        mutated["payload_identity"]["run_id"] = "mutated-after-snapshot"
        _write_json(payload_path, mutated)
        return result

    monkeypatch.setattr(
        transaction_module,
        "validate_payload_and_ce_semantics",
        validate_then_mutate,
    )
    try:
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
        assert result.diagnostics[0].code == "CE_EXPORT_PAYLOAD_CHANGED_DURING_EXPORT"
        assert not output_path.exists()
    finally:
        _cleanup(output_path)


def test_output_path_cannot_alias_transaction_input(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    protected_dir = ROOT / ".tmp-test-output"
    protected_dir.mkdir(exist_ok=True)
    payload_path = _write_json(
        protected_dir / "aliased-payload.json",
        _payload(intake, intake_path),
    )
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=payload_path,
            overwrite=True,
        )
        assert result.status == "invalid"
        assert result.diagnostics[0].code == "CE_EXPORT_OUTPUT_ALIASES_INPUT"
    finally:
        _cleanup(payload_path)


def test_overwrite_refuses_unowned_existing_target(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "unowned.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text('{"unrelated":true}\n', encoding="utf-8")
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            overwrite=True,
        )
        assert result.status == "invalid"
        assert result.output_written is False
        assert result.diagnostics[0].code == "CE_EXPORT_OUTPUT_NOT_OWNED"
        assert output_path.read_text(encoding="utf-8") == '{"unrelated":true}\n'
    finally:
        _cleanup(output_path)


def test_failed_overwrite_restores_prior_valid_owned_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "preserve-prior.json"
    _cleanup(output_path)
    try:
        first = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert first.status == "successful", first.as_dict()
        prior_bytes = output_path.read_bytes()

        def reject_post_write(repo_root: Path, bundle: dict) -> None:
            raise ExporterError(
                ExportDiagnostic(
                    "CE_TRX_TEST_POST_WRITE_REJECTION",
                    "post_write_validation",
                    "Injected transaction post-write rejection.",
                )
            )

        monkeypatch.setattr(exporter_module, "validate_stage_bundle_schema", reject_post_write)
        second = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            overwrite=True,
        )
        assert second.status == "invalid"
        assert second.output_written is False
        assert second.summary["artifact_state"] == "prior_valid_artifact_restored"
        assert second.summary["prior_artifact_preserved"] is True
        assert output_path.read_bytes() == prior_bytes
        assert load_json(output_path)["handoff"]["allowed"] is True
    finally:
        _cleanup(output_path)


def test_caller_authored_allowed_handoff_is_rejected_by_recomputation(
    tmp_path: Path,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "forged-handoff.json"
    _cleanup(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        forged = load_json(output_path)
        forged["final_stage_bundle"]["payload"]["data"]["unresolved_evidence"] = [
            {"unresolved_id": "forged-blocker"}
        ]
        forged["handoff"]["allowed"] = True
        forged["handoff"]["status"] = "successful"
        forged["handoff"]["failure_reasons"] = []
        forged["handoff"]["blocking_diagnostics"] = []
        forged["handoff"]["unresolved_evidence"] = []

        diagnostics = validate_transaction_artifact(ROOT, forged)
        assert "CE_TRX_UNRESOLVED_EVIDENCE" in {item.code for item in diagnostics}
    finally:
        _cleanup(output_path)


def test_integrity_valid_blocked_artifact_is_not_promoted_to_authorized(
    tmp_path: Path,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path, synthetic=True),
    )
    output_path = ROOT / ".tmp-test-output" / "blocked-integrity.json"
    _cleanup(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "blocked"
        assert result.summary["artifact_integrity_status"] == "valid"
        assert result.summary["semantic_validation_status"] == "valid"
        assert result.summary["authorization_valid"] is False
        assert result.handoff_allowed is False
    finally:
        _cleanup(output_path)


def test_insufficient_intake_cannot_be_reported_as_complete_stage() -> None:
    manifest = [
        {
            "stage_id": "architect_intake_validation",
            "mandatory": True,
            "status": "complete",
            "blockers": [],
            "unknowns": [],
        }
    ]
    intake = {
        "missing_evidence": [
            {
                "missing_id": "missing-source",
                "current_evidence_owner": "architect",
            }
        ]
    }
    _synchronize_intake_stage_status(
        manifest,
        {"status": "insufficient_evidence"},
        intake,
    )
    assert manifest[0]["status"] == "insufficient_evidence"
    assert manifest[0]["blockers"] == [
        {"code": "CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE"}
    ]
    assert manifest[0]["unknowns"] == intake["missing_evidence"]
