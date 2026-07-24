from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
import validator.project_gate_exporter_core as core_module
import validator.project_gate_exporter_orchestration as orchestration_module
from validator.project_gate_export import load_json
from validator.project_gate_exporter import (
    EXPECTED_STAGE_BUNDLE_SHA256,
    ExportDiagnostic,
    ExporterError,
    _safe_output_path,
    export_file,
    validate_stage_bundle_lock,
    verify_export_identity,
)
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json


@pytest.fixture(autouse=True)
def live_provenance_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = _provenance()
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): observed,
    )


def _cleanup_output(output_path: Path) -> None:
    output_path.unlink(missing_ok=True)
    if output_path.parent.exists():
        output_path.parent.rmdir()


def _fail_second_intake_read(
    monkeypatch: pytest.MonkeyPatch,
    intake_path: Path,
    error: OSError,
) -> None:
    original_read_bytes = Path.read_bytes
    target = intake_path.resolve()
    call_count = 0

    def flaky_read_bytes(path: Path) -> bytes:
        nonlocal call_count
        if path.resolve() == target:
            call_count += 1
            if call_count == 2:
                raise error
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)


def test_stage_bundle_contract_bytes_and_lock_are_pinned() -> None:
    path = ROOT / "contracts/project-gate/stage-bundle.v1.schema.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_STAGE_BUNDLE_SHA256
    validate_stage_bundle_lock(ROOT)


def test_export_file_api_rejects_caller_supplied_provenance(tmp_path: Path) -> None:
    assert "provenance" not in inspect.signature(export_file).parameters
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "forged-provenance.json"
    _cleanup_output(output_path)
    with pytest.raises(TypeError):
        export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
            provenance=_provenance(dirty=False),  # type: ignore[call-arg]
        )
    assert not output_path.exists()


def test_valid_real_payload_produces_allowed_gate_ready_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = core_module.GitProvenance(
        repository="rezahh107/EV4-Constructability-Engineer-Repo",
        ref="feature/ce-project-gate-exporter",
        commit_sha="1234567890abcdef1234567890abcdef12345678",
        dirty=False,
        dirty_paths=(),
    )
    calls: list[tuple[Path, tuple[Path, ...]]] = []

    def inspect_boundary(repo_root: Path, ignored_paths=()) -> core_module.GitProvenance:
        calls.append((repo_root, tuple(ignored_paths)))
        return observed

    monkeypatch.setattr(exporter_module, "inspect_git_provenance", inspect_boundary)
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert len(calls) == 1
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
        assert export["producer"] == {
            "stage": "ce",
            "repository": observed.repository,
            "ref": observed.ref,
            "commit_sha": observed.commit_sha,
        }
        assert result.summary["producer_commit"] == observed.commit_sha
        assert result.summary["producer_ref"] == observed.ref
        assert verify_export_identity(export)
        assert "builder_context_package" not in json.dumps(export).lower()
    finally:
        _cleanup_output(output_path)


def test_repeated_export_of_same_run_is_deterministic(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        first = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        first_bytes = output_path.read_bytes()
        second = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
            overwrite=True,
        )
        assert first.status == second.status == "successful"
        assert output_path.read_bytes() == first_bytes
        assert first.summary["export_hash"] == second.summary["export_hash"]
    finally:
        _cleanup_output(output_path)


def test_synthetic_payload_writes_blocked_export_without_false_acceptance(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path, synthetic=True),
    )
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
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
        _cleanup_output(output_path)


def test_dirty_live_checkout_is_metadata_only_and_allows_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = _provenance(dirty=True)
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): observed,
    )
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        assert result.output_written is True
        assert result.handoff_allowed is True
        assert result.summary["authorization_valid"] is True
        assert result.summary["repository_dirty"] is True
        assert result.summary["dirty_paths"] == list(observed.dirty_paths)
        export = load_json(output_path)
        assert export["handoff"]["allowed"] is True
        assert "CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF" not in {
            item["code"] for item in export["handoff"]["blocking_diagnostics"]
        }
    finally:
        _cleanup_output(output_path)



def test_source_intake_hash_mismatch_produces_no_output(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload = _payload(intake, intake_path)
    payload["source_architect_intake"]["artifact_hash"]["value"] = "0" * 64
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", payload)
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert result.status == "invalid"
        assert result.output_written is False
        assert result.diagnostics[0].code == "CE_EXPORT_SOURCE_INTAKE_HASH_MISMATCH"
        assert not output_path.exists()
    finally:
        _cleanup_output(output_path)


def test_file_bytes_source_intake_hash_uses_stable_snapshot(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload = _payload(intake, intake_path)
    payload["source_architect_intake"]["artifact_hash"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(intake_path.read_bytes()).hexdigest(),
        "scope": "file_bytes",
    }
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", payload)
    output_path = ROOT / ".tmp-test-output" / "file-bytes.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        assert result.summary["source_intake_hash_scope"] == "file_bytes"
    finally:
        _cleanup_output(output_path)


@pytest.mark.parametrize(
    "error_type",
    [PermissionError, FileNotFoundError, OSError],
    ids=["permission", "disappeared", "generic-oserror"],
)
def test_source_intake_second_read_failure_is_structured_and_writes_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[OSError],
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / f"read-failure-{error_type.__name__}.json"
    _cleanup_output(output_path)
    _fail_second_intake_read(monkeypatch, intake_path, error_type("injected read failure"))
    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
        output_path=output_path,
    )
    assert result.status == "invalid"
    assert result.output_written is False
    assert result.handoff_allowed is False
    assert not output_path.exists()
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "CE_EXPORT_SOURCE_INTAKE_READ_FAILED"
    assert diagnostic.stage == "source_binding"
    assert diagnostic.path == str(intake_path)
    assert diagnostic.repair_owner == "repository_owner"
    assert diagnostic.blocking is True


def test_source_intake_change_between_validation_stages_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "changed-intake.json"
    _cleanup_output(output_path)
    original_read_bytes = Path.read_bytes
    target = intake_path.resolve()
    call_count = 0

    def changed_read_bytes(path: Path) -> bytes:
        nonlocal call_count
        data = original_read_bytes(path)
        if path.resolve() == target:
            call_count += 1
            if call_count == 2:
                return data + b"\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", changed_read_bytes)
    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
        output_path=output_path,
    )
    assert result.status == "invalid"
    assert result.output_written is False
    assert result.diagnostics[0].code == "CE_EXPORT_SOURCE_INTAKE_CHANGED_DURING_EXPORT"
    assert not output_path.exists()


def test_cli_source_intake_read_failure_returns_json_and_exit_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "cli-read-failure.json"
    _cleanup_output(output_path)
    _fail_second_intake_read(monkeypatch, intake_path, PermissionError("injected permission failure"))
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
        ]
    )
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 1
    assert captured.err == ""
    assert report["status"] == "invalid"
    assert report["output_written"] is False
    assert report["diagnostics"][0]["code"] == "CE_EXPORT_SOURCE_INTAKE_READ_FAILED"
    assert "Traceback" not in captured.out
    assert not output_path.exists()


def test_tampered_export_identity_is_rejected(tmp_path: Path) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert result.output_written
        export = load_json(output_path)
        export["handoff"]["target"] = "responsive"
        assert verify_export_identity(export) is False
    finally:
        _cleanup_output(output_path)


def test_output_path_must_remain_inside_repository(tmp_path: Path) -> None:
    with pytest.raises(Exception) as exc_info:
        _safe_output_path(ROOT, tmp_path / "outside.json", overwrite=False)
    assert getattr(exc_info.value, "diagnostic").code == "CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY"


def test_malformed_manifest_identity_fails_closed() -> None:
    assert verify_export_identity({"export_id": "tampered"}) is False
    assert verify_export_identity({"export_id": "tampered", "stage_manifest": []}) is False
    assert verify_export_identity({"export_id": "tampered", "stage_manifest": [None]}) is False
    assert verify_export_identity(
        {"export_id": "tampered", "stage_manifest": [{"output": "invalid"}]}
    ) is False


def test_missing_stage_bundle_lock_has_stable_diagnostic(tmp_path: Path) -> None:
    with pytest.raises(ExporterError) as exc_info:
        validate_stage_bundle_lock(tmp_path)
    assert exc_info.value.diagnostic.code == "CE_EXPORT_STAGE_BUNDLE_LOCK_MISSING"


def test_subprocess_oserror_has_stable_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_oserror(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("command unavailable")

    monkeypatch.setattr(core_module.subprocess, "run", raise_oserror)
    with pytest.raises(ExporterError) as exc_info:
        core_module._run(["git", "status"], tmp_path)
    assert exc_info.value.diagnostic.code == "CE_EXPORT_COMMAND_EXECUTION_FAILED"


def test_non_object_intake_validator_output_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed = subprocess.CompletedProcess(
        args=["validator"], returncode=0, stdout="[]", stderr=""
    )
    monkeypatch.setattr(core_module, "_run", lambda command, cwd: completed)
    with pytest.raises(ExporterError) as exc_info:
        core_module.run_official_intake_validation(
            tmp_path, tmp_path / "intake.json", tmp_path / "bundle.json"
        )
    assert exc_info.value.diagnostic.code == "CE_EXPORT_INTAKE_VALIDATOR_OUTPUT_INVALID"


def test_atomic_write_oserror_has_stable_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_permission(*args: object, **kwargs: object) -> tuple[int, str]:
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(orchestration_module.tempfile, "mkstemp", raise_permission)
    with pytest.raises(ExporterError) as exc_info:
        orchestration_module._atomic_write(tmp_path / "output.json", b"{}\n")
    assert exc_info.value.diagnostic.code == "CE_EXPORT_WRITE_FAILED"


def test_post_write_validation_failure_removes_invalid_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)

    def reject_post_write(repo_root: Path, bundle: dict) -> None:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_TEST_POST_WRITE_REJECTION",
                "post_write_validation",
                "Injected post-write validation failure.",
            )
        )

    monkeypatch.setattr(exporter_module, "validate_stage_bundle_schema", reject_post_write)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            intermediate_inputs_path=Path(intake_path).with_name("ce-intermediate-export-inputs.json"),
            output_path=output_path,
        )
        assert result.status == "invalid"
        assert result.output_written is False
        assert result.diagnostics[0].code == "CE_EXPORT_TEST_POST_WRITE_REJECTION"
        assert not output_path.exists()
    finally:
        _cleanup_output(output_path)
