from __future__ import annotations

import json
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
import validator.project_gate_exporter_orchestration as orchestration_module
from validator.project_gate_exporter import ExporterError, _safe_output_path, export_file
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json


@pytest.fixture(autouse=True)
def live_provenance_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): _provenance(),
    )


def _prepare_export(tmp_path: Path, name: str) -> tuple[Path, Path, Path, Path]:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    output_path = ROOT / ".tmp-test-output" / name
    output_path.unlink(missing_ok=True)
    return payload_path, intake_path, source_path, output_path


def _cleanup_output(output_path: Path) -> None:
    output_path.unlink(missing_ok=True)
    if output_path.parent.exists():
        output_path.parent.rmdir()


def test_source_bundle_change_after_official_validation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        "source-bundle-changed.json",
    )
    original_validate = orchestration_module.run_official_intake_validation

    def validate_then_mutate(
        repo_root: Path,
        observed_intake_path: Path,
        observed_source_path: Path,
    ) -> dict:
        report = original_validate(
            repo_root,
            observed_intake_path,
            observed_source_path,
        )
        mutated = json.loads(observed_source_path.read_text(encoding="utf-8"))
        mutated["bundle_id"] = f"{mutated['bundle_id']}-changed-after-validation"
        _write_json(observed_source_path, mutated)
        return report

    monkeypatch.setattr(
        orchestration_module,
        "run_official_intake_validation",
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
        assert result.diagnostics[0].code == (
            "CE_EXPORT_SOURCE_BUNDLE_CHANGED_DURING_EXPORT"
        )
        assert not output_path.exists()
    finally:
        _cleanup_output(output_path)


def test_source_bundle_second_read_failure_is_structured_and_writes_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        "source-bundle-read-failure.json",
    )
    original_read_bytes = Path.read_bytes
    target = source_path.resolve()
    call_count = 0

    def flaky_read_bytes(path: Path) -> bytes:
        nonlocal call_count
        if path.resolve() == target:
            call_count += 1
            if call_count == 2:
                raise PermissionError("injected source-bundle read failure")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)
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
        assert result.diagnostics[0].code == "CE_EXPORT_SOURCE_BUNDLE_READ_FAILED"
        assert result.diagnostics[0].repair_owner == "repository_owner"
        assert not output_path.exists()
    finally:
        _cleanup_output(output_path)


def test_cli_refuses_existing_leaf_symlink_with_structured_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = ROOT / ".tmp-test-output"
    output_dir.mkdir(exist_ok=True)
    target = output_dir / "symlink-target.json"
    output_path = output_dir / "symlink-output.json"
    target.unlink(missing_ok=True)
    output_path.unlink(missing_ok=True)
    output_path.symlink_to(target.name)
    try:
        exit_code = exporter_module.main(
            [
                "--repo-root",
                str(ROOT),
                "--payload",
                str(tmp_path / "unused-payload.json"),
                "--source-intake",
                str(tmp_path / "unused-intake.json"),
                "--source-bundle",
                str(tmp_path / "unused-bundle.json"),
                "--output",
                str(output_path),
            ]
        )
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert exit_code == 1
        assert captured.err == ""
        assert "Traceback" not in captured.out
        assert report["status"] == "invalid"
        assert report["output_written"] is False
        assert report["diagnostics"][0]["code"] == (
            "CE_EXPORT_OUTPUT_SYMLINK_FORBIDDEN"
        )
        assert output_path.is_symlink()
        assert not target.exists()
    finally:
        output_path.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        if output_dir.exists():
            output_dir.rmdir()


def test_output_path_resolution_failure_has_stable_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    resolved_root = repo_root.resolve()
    candidate = resolved_root / "loop.json"
    original_resolve = Path.resolve

    def fail_candidate_resolve(path: Path, strict: bool = False) -> Path:
        if path == candidate:
            raise RuntimeError("injected symlink loop")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_candidate_resolve)
    with pytest.raises(ExporterError) as exc_info:
        _safe_output_path(repo_root, Path("loop.json"), overwrite=False)
    assert exc_info.value.diagnostic.code == (
        "CE_EXPORT_OUTPUT_PATH_INSPECTION_FAILED"
    )
    assert exc_info.value.diagnostic.repair_owner == "repository_owner"
