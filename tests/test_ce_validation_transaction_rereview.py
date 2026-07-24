from __future__ import annotations

import json
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
from validator.ce_validation_transaction import validate_transaction_artifact
from validator.project_gate_export import (
    load_json,
    validate_producer_gate_export,
)
from validator.project_gate_exporter import (
    ExportDiagnostic,
    ExporterError,
    export_file,
)
from validator.project_gate_exporter_validation import (
    _export_identity_hash,
    verify_export_identity,
)
from exporter_test_support import (
    INTERMEDIATE_INPUTS_FILENAME,
    ROOT,
    _payload,
    _provenance,
    _real_source_pair,
    _write_json,
)


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


def _reject_post_write(repo_root: Path, bundle: dict) -> None:
    raise ExporterError(
        ExportDiagnostic(
            "CE_TRX_TEST_POST_WRITE_REJECTION",
            "post_write_validation",
            "Injected post-write rejection for restoration mutation coverage.",
        )
    )


def test_restoration_write_failure_reports_persisted_candidate_truthfully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    output_path = ROOT / ".tmp-test-output" / "restore-write-failure.json"
    _cleanup(output_path)
    try:
        first = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert first.status == "successful", first.as_dict()
        prior_bytes = output_path.read_bytes()

        changed_payload = load_json(payload_path)
        changed_run_id = "ce-run-test-restoration-failure"
        changed_payload["payload_identity"]["run_id"] = changed_run_id
        _write_json(payload_path, changed_payload)
        sidecar_path = intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)
        sidecar = load_json(sidecar_path)
        sidecar["run_id"] = changed_run_id
        _write_json(sidecar_path, sidecar)

        monkeypatch.setattr(
            exporter_module,
            "validate_stage_bundle_schema",
            _reject_post_write,
        )
        original_atomic_write = exporter_module._atomic_write
        writes = 0

        def fail_only_restoration(path: Path, data: bytes) -> None:
            nonlocal writes
            writes += 1
            if writes == 2:
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_WRITE_FAILED",
                        "atomic_write",
                        "Injected restoration write failure.",
                        str(path),
                        "repository_owner",
                    )
                )
            original_atomic_write(path, data)

        monkeypatch.setattr(exporter_module, "_atomic_write", fail_only_restoration)
        exit_code = exporter_module.main(
            [
                "--repo-root",
                str(ROOT),
                "--payload",
                str(payload_path),
                "--source-intake",
                str(intake_path),
                "--source-bundle",
                str(source_path),
                "--intermediate-inputs",
                str(Path(intake_path).with_name("ce-intermediate-export-inputs.json")),
                "--output",
                str(output_path),
                "--overwrite",
            ]
        )
        captured = capsys.readouterr()
        report = json.loads(captured.out)

        assert exit_code == 1
        assert captured.err == ""
        assert "Traceback" not in captured.out
        assert [item["code"] for item in report["diagnostics"]] == [
            "CE_TRX_TEST_POST_WRITE_REJECTION",
            "CE_EXPORT_POST_WRITE_CLEANUP_FAILED",
        ]
        assert report["output_cleanup_failed"] is True
        assert report["output_written"] is True
        assert report["artifact_state"] == "invalid_artifact_persisted"
        assert report["artifact_must_not_be_consumed"] is True
        assert report["prior_artifact_existed"] is True
        assert report["prior_artifact_replaced"] is True
        assert report["prior_artifact_restored"] is False
        assert report["prior_artifact_preserved"] is False
        assert output_path.exists()
        assert output_path.read_bytes() != prior_bytes
    finally:
        _cleanup(output_path)


def test_nested_synthetic_marker_cannot_be_cleared_by_declared_flag_mutation(
    tmp_path: Path,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path, synthetic=True),
    )
    output_path = ROOT / ".tmp-test-output" / "synthetic-declaration-forgery.json"
    _cleanup(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert result.status == "blocked", result.as_dict()
        forged = load_json(output_path)
        assert forged["final_stage_bundle"]["payload"]["data"]["payload_identity"][
            "synthetic"
        ] is True

        forged["final_stage_bundle"]["synthetic"] = False
        forged["handoff"]["allowed"] = True
        forged["handoff"]["status"] = "successful"
        forged["handoff"]["failure_reasons"] = []
        forged["handoff"]["blocking_diagnostics"] = []
        forged["handoff"]["unresolved_evidence"] = []
        identity_hash = _export_identity_hash(forged)
        forged["export_id"] = f"ce-project-gate-export-{identity_hash}"
        forged["stage_manifest"][-1]["output"]["artifact_hash"]["value"] = identity_hash
        assert verify_export_identity(forged) is True

        producer_codes = {
            item.code for item in validate_producer_gate_export(ROOT, forged)
        }
        transaction_codes = {
            item.code for item in validate_transaction_artifact(ROOT, forged)
        }
        assert "CE_STAGE_BUNDLE_SYNTHETIC_STATE_MISMATCH" in producer_codes
        assert "CE_PG_SYNTHETIC_EVIDENCE_BLOCKS_HANDOFF" in producer_codes
        assert "CE_TRX_SYNTHETIC_STATE_MISMATCH" in transaction_codes
        assert "CE_TRX_SYNTHETIC_EVIDENCE_BLOCKED" in transaction_codes
    finally:
        _cleanup(output_path)


def test_successful_overwrite_reports_replacement_not_preservation(
    tmp_path: Path,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    output_path = ROOT / ".tmp-test-output" / "successful-replacement.json"
    _cleanup(output_path)
    try:
        first = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert first.status == "successful", first.as_dict()
        prior_bytes = output_path.read_bytes()

        changed_payload = load_json(payload_path)
        changed_run_id = "ce-run-test-replacement"
        changed_payload["payload_identity"]["run_id"] = changed_run_id
        _write_json(payload_path, changed_payload)
        sidecar_path = intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)
        sidecar = load_json(sidecar_path)
        sidecar["run_id"] = changed_run_id
        _write_json(sidecar_path, sidecar)
        second = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
            overwrite=True,
        )

        assert second.status == "successful", second.as_dict()
        assert output_path.read_bytes() != prior_bytes
        assert second.summary["prior_artifact_existed"] is True
        assert second.summary["prior_artifact_replaced"] is True
        assert second.summary["prior_artifact_restored"] is False
        assert second.summary["prior_artifact_preserved"] is False
    finally:
        _cleanup(output_path)
