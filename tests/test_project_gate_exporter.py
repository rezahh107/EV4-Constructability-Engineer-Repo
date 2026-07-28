from __future__ import annotations

import json
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json
from project_gate_exporter_legacy_suite import *  # noqa: F401,F403
from project_gate_exporter_legacy_suite import _cleanup_output
from validator.project_gate_export import load_json
from validator.project_gate_exporter import _safe_output_path, export_file
from validator.project_gate_exporter_core import ExporterError


def test_dirty_live_checkout_cannot_authorize_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dirty state is metadata only; the legacy boundary remains the sole blocker."""
    observed = _provenance(dirty=True)
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): observed,
    )
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(
        tmp_path / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    output_path = ROOT / ".tmp-test-output" / "ce-project-gate.json"
    _cleanup_output(output_path)
    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "blocked"
        assert result.output_written is True
        assert result.handoff_allowed is False
        assert result.summary["repository_dirty"] is True
        assert result.summary["dirty_paths"] == list(observed.dirty_paths)
        export = load_json(output_path)
        diagnostic_codes = {
            item["code"] for item in export["handoff"]["blocking_diagnostics"]
        }
        assert "CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF" not in diagnostic_codes
        assert "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN" in diagnostic_codes
    finally:
        _cleanup_output(output_path)


def test_output_path_default_remains_inside_repository(tmp_path: Path) -> None:
    absolute_external = (tmp_path / "outside.json").resolve()
    with pytest.raises(ExporterError) as external_error:
        _safe_output_path(ROOT, absolute_external, overwrite=False)
    assert external_error.value.diagnostic.code == "CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY"

    relative = Path(".tmp-test-output/relative-output-contract.json")
    assert _safe_output_path(ROOT, relative, overwrite=False) == (ROOT / relative).resolve()


def test_legacy_external_output_is_rejected_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = _provenance(dirty=False)
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): observed,
    )
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    intake, _, intake_path, source_path = _real_source_pair(inputs_dir)
    payload_path = _write_json(
        inputs_dir / "ce-stage-payload.json",
        _payload(intake, intake_path),
    )
    output_path = (tmp_path / "external" / "legacy-project-gate.json").resolve()

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
    assert [item.code for item in result.diagnostics] == [
        "CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY"
    ]
    assert not output_path.exists()

    exit_code = exporter_module.main(
        [
            "--payload",
            str(payload_path),
            "--source-intake",
            str(intake_path),
            "--source-bundle",
            str(source_path),
            "--output",
            str(output_path),
            "--repo-root",
            str(ROOT),
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["status"] == "invalid"
    assert report["output_written"] is False
    assert [item["code"] for item in report["diagnostics"]] == [
        "CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY"
    ]
    assert not output_path.exists()
