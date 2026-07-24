from __future__ import annotations

from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json
from project_gate_exporter_legacy_suite import *  # noqa: F401,F403
from project_gate_exporter_legacy_suite import _cleanup_output
from validator.project_gate_export import load_json
from validator.project_gate_exporter import export_file


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
