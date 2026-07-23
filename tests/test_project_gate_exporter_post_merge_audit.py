from __future__ import annotations

import json
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
import validator.project_gate_exporter_orchestration as orchestration_module
from validator.project_gate_exporter import (
    ExportDiagnostic,
    ExporterError,
    _safe_output_path,
    export_file,
)
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
    if output_path.parent.exists() and not any(output_path.parent.iterdir()):
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
        mutated = json.loads(source_path.read_text(encoding="utf-8"))
        mutated["bundle_id"] = f"{mutated['bundle_id']}-changed-after-validation"
        _write_json(source_path, mutated)
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


def test_source_bundle_aba_change_uses_private_snapshot_without_authorizing_legacy_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        "source-bundle-aba.json",
    )
    original_validate = orchestration_module.run_official_intake_validation
    original_bytes = source_path.read_bytes()
    mutated = json.loads(original_bytes.decode("utf-8"))
    mutated["bundle_id"] = f"{mutated['bundle_id']}-aba-mutated"
    mutated_bytes = json.dumps(
        mutated,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    observed: dict[str, object] = {}

    def validate_private_snapshot_during_aba(
        repo_root: Path,
        observed_intake_path: Path,
        observed_source_path: Path,
    ) -> dict:
        observed["source_path"] = observed_source_path
        observed["source_bytes"] = observed_source_path.read_bytes()
        observed["snapshot_directory"] = observed_source_path.parent
        source_path.write_bytes(mutated_bytes)
        try:
            assert source_path.read_bytes() == mutated_bytes
            return original_validate(
                repo_root,
                observed_intake_path,
                observed_source_path,
            )
        finally:
            source_path.write_bytes(original_bytes)

    monkeypatch.setattr(
        orchestration_module,
        "run_official_intake_validation",
        validate_private_snapshot_during_aba,
    )
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "blocked", result.as_dict()
        assert result.output_written is True
        assert result.handoff_allowed is False
        assert observed["source_path"] != source_path
        assert observed["source_bytes"] == original_bytes
        assert observed["source_bytes"] != mutated_bytes
        snapshot_directory = observed["snapshot_directory"]
        assert isinstance(snapshot_directory, Path)
        assert snapshot_directory != output_path.parent
        assert not snapshot_directory.exists()
        expected_source_bundle = json.loads(original_bytes.decode("utf-8"))
        assert result.summary["source_bundle_hash"] == orchestration_module._json_hash(
            expected_source_bundle
        )
        assert result.summary["official_builder_authorization"] is False
    finally:
        source_path.write_bytes(original_bytes)
        _cleanup_output(output_path)


def test_source_intake_aba_change_uses_private_snapshot_without_authorizing_legacy_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        "source-intake-aba.json",
    )
    original_validate = orchestration_module.run_official_intake_validation
    original_bytes = intake_path.read_bytes()
    mutated_bytes = b'{"schema_id":"aba-mutated-intake"}\n'
    observed: dict[str, object] = {}

    def validate_private_snapshot_during_aba(
        repo_root: Path,
        observed_intake_path: Path,
        observed_source_path: Path,
    ) -> dict:
        observed["intake_path"] = observed_intake_path
        observed["intake_bytes"] = observed_intake_path.read_bytes()
        observed["snapshot_directory"] = observed_intake_path.parent
        intake_path.write_bytes(mutated_bytes)
        try:
            assert intake_path.read_bytes() == mutated_bytes
            return original_validate(
                repo_root,
                observed_intake_path,
                observed_source_path,
            )
        finally:
            intake_path.write_bytes(original_bytes)

    monkeypatch.setattr(
        orchestration_module,
        "run_official_intake_validation",
        validate_private_snapshot_during_aba,
    )
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "blocked", result.as_dict()
        assert result.output_written is True
        assert result.handoff_allowed is False
        assert observed["intake_path"] != intake_path
        assert observed["intake_bytes"] == original_bytes
        assert observed["intake_bytes"] != mutated_bytes
        snapshot_directory = observed["snapshot_directory"]
        assert isinstance(snapshot_directory, Path)
        assert snapshot_directory != output_path.parent
        assert not snapshot_directory.exists()
        assert result.summary["official_builder_authorization"] is False
    finally:
        intake_path.write_bytes(original_bytes)
        _cleanup_output(output_path)


def test_private_validation_snapshots_are_removed_when_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        "validation-failure-cleanup.json",
    )
    observed: dict[str, Path] = {}

    def reject_private_snapshot(
        repo_root: Path,
        observed_intake_path: Path,
        observed_source_path: Path,
    ) -> dict:
        observed["directory"] = observed_intake_path.parent
        assert observed_source_path.parent == observed_intake_path.parent
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_TEST_VALIDATOR_REJECTION",
                "source_intake_validation",
                "Injected official validator rejection.",
            )
        )

    monkeypatch.setattr(
        orchestration_module,
        "run_official_intake_validation",
        reject_private_snapshot,
    )
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
    assert result.diagnostics[0].code == "CE_EXPORT_TEST_VALIDATOR_REJECTION"
    assert not observed["directory"].exists()
    assert not output_path.exists()


def test_private_validation_snapshot_cleanup_failure_is_structured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        "validation-cleanup-failure.json",
    )
    original_rmtree = orchestration_module.shutil.rmtree
    observed_directories: list[Path] = []

    def fail_cleanup(path: str | Path, *args: object, **kwargs: object) -> None:
        observed_directories.append(Path(path))
        raise PermissionError("injected private snapshot cleanup failure")

    monkeypatch.setattr(orchestration_module.shutil, "rmtree", fail_cleanup)
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
            "CE_EXPORT_VALIDATION_SNAPSHOT_CLEANUP_FAILED"
        )
        assert result.diagnostics[0].repair_owner == "repository_owner"
        assert not output_path.exists()
    finally:
        for directory in observed_directories:
            original_rmtree(directory, ignore_errors=True)
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
        assert report["handoff_allowed"] is False
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


def test_cli_rejects_output_directory_even_with_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = ROOT / ".tmp-test-output" / "directory-output"
    output_path.mkdir(parents=True, exist_ok=True)
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
                "--overwrite",
            ]
        )
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert exit_code == 1
        assert captured.err == ""
        assert "Traceback" not in captured.out
        assert report["status"] == "invalid"
        assert report["output_written"] is False
        assert report["handoff_allowed"] is False
        assert report["diagnostics"][0]["code"] == "CE_EXPORT_OUTPUT_IS_DIRECTORY"
        assert output_path.is_dir()
    finally:
        output_path.rmdir()
        if output_path.parent.exists():
            output_path.parent.rmdir()


@pytest.mark.parametrize(
    ("failing_target", "expected_code"),
    [
        ("repo_root", "CE_EXPORT_REPOSITORY_PATH_INSPECTION_FAILED"),
        ("payload", "CE_EXPORT_INPUT_PATH_INSPECTION_FAILED"),
        ("source_intake", "CE_EXPORT_INPUT_PATH_INSPECTION_FAILED"),
        ("source_bundle", "CE_EXPORT_INPUT_PATH_INSPECTION_FAILED"),
        ("output", "CE_EXPORT_OUTPUT_PATH_INSPECTION_FAILED"),
    ],
)
def test_cli_path_resolution_failures_are_structured_and_write_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failing_target: str,
    expected_code: str,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path,
        f"{failing_target}-resolution-failure.json",
    )
    paths = {
        "repo_root": ROOT,
        "payload": payload_path,
        "source_intake": intake_path,
        "source_bundle": source_path,
        "output": output_path,
    }
    target = paths[failing_target]
    original_resolve = Path.resolve

    def fail_selected_resolve(path: Path, strict: bool = False) -> Path:
        if path == target:
            raise RuntimeError(f"injected {failing_target} resolution failure")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_selected_resolve)
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
    assert report["handoff_allowed"] is False
    assert report["diagnostics"][0]["code"] == expected_code
    assert report["diagnostics"][0]["path"] == str(target)
    assert report["diagnostics"][0]["repair_owner"] == "repository_owner"
    assert not output_path.exists()


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
