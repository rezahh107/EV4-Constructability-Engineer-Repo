from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
import validator.project_gate_exporter_core as core_module
from validator.ce_validation_transaction import secure_build_export
from validator.project_gate_exporter import ExportResult, export_file
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


def _fixture_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    intermediate_path = intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME)
    return payload_path, intake_path, source_path, intermediate_path


def _cleanup(path: Path) -> None:
    path.unlink(missing_ok=True)
    parent = path.parent
    if parent.name in {".tmp-test-output", ".tmp-test-input"} and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def test_public_python_signatures_require_explicit_intermediate_input() -> None:
    export_signature = inspect.signature(export_file)
    secure_signature = inspect.signature(secure_build_export)
    assert export_signature.parameters["intermediate_inputs_path"].default is inspect.Parameter.empty
    assert secure_signature.parameters["intermediate_inputs_path"].default is inspect.Parameter.empty
    assert list(export_signature.parameters) == [
        "repo_root",
        "payload_path",
        "source_intake_path",
        "source_bundle_path",
        "intermediate_inputs_path",
        "output_path",
        "overwrite",
    ]


def test_cli_requires_intermediate_inputs() -> None:
    with pytest.raises(SystemExit) as exc_info:
        exporter_module.main(
  [
      "--payload",
      "payload.json",
      "--source-intake",
      "intake.json",
      "--source-bundle",
      "bundle.json",
  ]
        )
    assert exc_info.value.code == 2


def test_cli_passes_supplied_intermediate_path_without_pre_resolution(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: dict[str, object] = {}

    def fake_export_file(**kwargs: object) -> ExportResult:
        observed.update(kwargs)
        return ExportResult(
  status="successful",
  output_path="ce-project-gate.json",
  output_written=True,
  handoff_allowed=True,
  diagnostics=(),
  summary={"authorization_valid": True},
        )

    monkeypatch.setattr(exporter_module, "export_file", fake_export_file)
    supplied = Path("relative/runtime/custom-intermediate.json")
    exit_code = exporter_module.main(
        [
  "--payload",
  "payload.json",
  "--source-intake",
  "intake.json",
  "--source-bundle",
  "bundle.json",
  "--intermediate-inputs",
  str(supplied),
  "--output",
  "ce-project-gate.json",
        ]
    )
    assert exit_code == 0
    assert observed["intermediate_inputs_path"] == supplied
    assert json.loads(capsys.readouterr().out)["status"] == "successful"


def test_custom_intermediate_filename_and_directory_succeeds_without_sibling_discovery(
    tmp_path: Path,
) -> None:
    payload_path, intake_path, source_path, hidden_path = _fixture_paths(tmp_path)
    custom_path = tmp_path / "operator-selected" / "current-ce-runtime-inputs.json"
    custom_path.parent.mkdir(parents=True)
    hidden_path.replace(custom_path)
    assert not hidden_path.exists()
    output_path = ROOT / ".tmp-test-output" / "custom-intermediate-path.json"
    _cleanup(output_path)
    try:
        result = export_file(
  repo_root=ROOT,
  payload_path=payload_path,
  source_intake_path=intake_path,
  source_bundle_path=source_path,
  intermediate_inputs_path=custom_path,
  output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        assert result.handoff_allowed is True
        assert result.summary["authorization_valid"] is True
    finally:
        _cleanup(output_path)


def test_missing_supplied_intermediate_input_returns_structured_failure(tmp_path: Path) -> None:
    payload_path, intake_path, source_path, _ = _fixture_paths(tmp_path)
    missing_path = tmp_path / "operator-selected" / "missing.json"
    output_path = ROOT / ".tmp-test-output" / "missing-explicit-intermediate.json"
    _cleanup(output_path)
    result = export_file(
        repo_root=ROOT,
        payload_path=payload_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        intermediate_inputs_path=missing_path,
        output_path=output_path,
    )
    assert result.status == "invalid"
    assert result.output_written is False
    assert result.handoff_allowed is False
    assert result.diagnostics[0].code == "CE_EXPORT_INTERMEDIATE_INPUTS_READ_FAILED"
    assert not output_path.exists()


def test_output_cannot_alias_explicit_intermediate_input(tmp_path: Path) -> None:
    payload_path, intake_path, source_path, hidden_path = _fixture_paths(tmp_path)
    protected_path = ROOT / ".tmp-test-input" / "explicit-intermediate.json"
    _cleanup(protected_path)
    protected_path.parent.mkdir(parents=True, exist_ok=True)
    protected_path.write_bytes(hidden_path.read_bytes())
    try:
        result = export_file(
  repo_root=ROOT,
  payload_path=payload_path,
  source_intake_path=intake_path,
  source_bundle_path=source_path,
  intermediate_inputs_path=protected_path,
  output_path=protected_path,
  overwrite=True,
        )
        assert result.status == "invalid"
        assert result.output_written is False
        assert result.handoff_allowed is False
        assert result.diagnostics[0].code == "CE_EXPORT_OUTPUT_ALIASES_INPUT"
    finally:
        _cleanup(protected_path)


def test_realistic_dirty_git_metadata_is_diagnostic_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path, intake_path, source_path, intermediate_path = _fixture_paths(tmp_path)
    output_path = ROOT / ".tmp-test-output" / "realistic-dirty-metadata.json"
    _cleanup(output_path)

    def fake_git(repo_root: Path, *args: str) -> str:
        commands = {
  ("rev-parse", "--show-toplevel"): str(ROOT),
  ("remote", "get-url", "origin"): "https://github.com/rezahh107/EV4-Constructability-Engineer-Repo.git",
  ("rev-parse", "HEAD"): "1234567890abcdef1234567890abcdef12345678",
  ("status", "--porcelain=v1", "--untracked-files=all"): " M docs/unrelated.md\n?? scratch/unrelated.txt",
        }
        return commands[args]

    original_run = core_module._run

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if command == ["git", "symbolic-ref", "--quiet", "--short", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, "feature/explicit-inputs\n", "")
        return original_run(command, cwd)

    monkeypatch.setattr(core_module, "_git", fake_git)
    monkeypatch.setattr(core_module, "_run", fake_run)
    monkeypatch.setattr(exporter_module, "inspect_git_provenance", core_module.inspect_git_provenance)
    try:
        result = export_file(
  repo_root=ROOT,
  payload_path=payload_path,
  source_intake_path=intake_path,
  source_bundle_path=source_path,
  intermediate_inputs_path=intermediate_path,
  output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        assert result.handoff_allowed is True
        assert result.summary["authorization_valid"] is True
        assert result.summary["repository_dirty"] is True
        assert result.summary["dirty_paths"] == ["docs/unrelated.md", "scratch/unrelated.txt"]
        assert "CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF" not in {
  diagnostic.code for diagnostic in result.diagnostics
        }
    finally:
        _cleanup(output_path)


def test_documented_commands_expose_explicit_intermediate_input() -> None:
    document = (ROOT / "docs/CE_PROJECT_GATE_EXPORTER.md").read_text(encoding="utf-8")
    assert document.count("--intermediate-inputs") >= 2
    assert "dirty checkout is reported as metadata and does not affect functional authorization" in document
