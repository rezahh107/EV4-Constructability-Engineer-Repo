from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

import validator.project_gate_exporter as exporter_module
from validator.project_gate_export import load_json
from validator.project_gate_exporter import ExportDiagnostic, ExporterError, export_file
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
    payload_path = _write_json(tmp_path / "ce-stage-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / name
    output_path.unlink(missing_ok=True)
    return payload_path, intake_path, source_path, output_path


def _deny_target_unlink(
    monkeypatch: pytest.MonkeyPatch,
    output_path: Path,
) -> Callable[..., None]:
    original_unlink = Path.unlink
    target = output_path.resolve()

    def deny_unlink(path: Path, missing_ok: bool = False) -> None:
        if path.resolve() == target:
            raise PermissionError("injected cleanup denial")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", deny_unlink)
    return original_unlink


def _reject_schema(repo_root: Path, bundle: dict) -> None:
    raise ExporterError(
        ExportDiagnostic(
            "CE_EXPORT_TEST_POST_WRITE_REJECTION",
            "post_write_validation",
            "Injected post-write schema revalidation failure.",
        )
    )


@pytest.mark.parametrize(
    ("failure_mode", "expected_original_code"),
    [
        ("schema", "CE_EXPORT_TEST_POST_WRITE_REJECTION"),
        ("identity", "CE_EXPORT_POST_WRITE_IDENTITY_INVALID"),
    ],
)
def test_cleanup_failure_reports_persisted_invalid_artifact_truthfully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
    expected_original_code: str,
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path, f"cleanup-failure-{failure_mode}.json"
    )
    if failure_mode == "schema":
        monkeypatch.setattr(exporter_module, "validate_stage_bundle_schema", _reject_schema)
    else:
        monkeypatch.setattr(exporter_module, "verify_export_identity", lambda export: False)
    original_unlink = _deny_target_unlink(monkeypatch, output_path)

    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        report = result.as_dict()

        assert result.status == "invalid"
        assert result.handoff_allowed is False
        assert result.output_written is True
        assert report["output_valid"] is False
        assert report["output_cleanup_failed"] is True
        assert report["artifact_state"] == "invalid_artifact_persisted"
        assert report["artifact_must_not_be_consumed"] is True
        assert [item["code"] for item in report["diagnostics"]] == [
            expected_original_code,
            "CE_EXPORT_POST_WRITE_CLEANUP_FAILED",
        ]
        assert output_path.exists()
        assert load_json(output_path)["handoff"]["allowed"] is True
        assert report["handoff_allowed"] is False
        assert report["handoff_prohibited"] is True
    finally:
        original_unlink(output_path, missing_ok=True)
        if output_path.parent.exists():
            output_path.parent.rmdir()


def test_cli_cleanup_failure_returns_structured_invalid_artifact_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload_path, intake_path, source_path, output_path = _prepare_export(
        tmp_path, "cli-cleanup-failure.json"
    )
    monkeypatch.setattr(exporter_module, "validate_stage_bundle_schema", _reject_schema)
    original_unlink = _deny_target_unlink(monkeypatch, output_path)

    try:
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
        assert report["handoff_allowed"] is False
        assert report["output_written"] is True
        assert report["output_valid"] is False
        assert report["output_cleanup_failed"] is True
        assert report["artifact_state"] == "invalid_artifact_persisted"
        assert report["artifact_must_not_be_consumed"] is True
        assert report["diagnostics"][1]["code"] == "CE_EXPORT_POST_WRITE_CLEANUP_FAILED"
        assert output_path.exists()
    finally:
        original_unlink(output_path, missing_ok=True)
        if output_path.parent.exists():
            output_path.parent.rmdir()


def test_historical_v1_1_status_fields_remain_in_their_original_block() -> None:
    text = (ROOT / "STATUS.md").read_text(encoding="utf-8")
    start = text.index("CE_ARCHITECT_STAGE_INTAKE_V1_1:")
    end = text.index("```", start)
    block = text[start:end]

    assert "  builder_authorization_at_intake: false\n" in block
    assert "  real_cross_repository_validation: not_available\n" in block
    assert "  fixture_classification: synthetic\n" in block
