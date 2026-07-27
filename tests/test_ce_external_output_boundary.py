from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import validator._verified_project_gate_exporter_impl as verified_impl
import validator.project_gate_exporter_core as exporter_core
import validator.verified_project_gate_exporter as public_exporter
from exporter_test_support import ROOT, _provenance, _real_source_pair, _write_json
from validator.ce_validation_transaction import safe_output_path
from validator.payload_assembler import sha256_json
from validator.project_gate_exporter_core import ExportDiagnostic, ExporterError
from verified_exporter_test_support import _geometry_draft


def _patch_provenance(monkeypatch: pytest.MonkeyPatch, *, dirty: bool = False) -> None:
    monkeypatch.setattr(
        verified_impl,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): _provenance(dirty=dirty),
    )


def _write_inputs(tmp_path: Path, *, authorized: bool) -> tuple[Path, Path, Path]:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    if authorized:
        intake["unresolved_evidence"] = []
        source["payload"]["unresolved_evidence"] = []
        intake["project_gate_transition"]["source_bundle_hash"]["value"] = sha256_json(source)
        _write_json(intake_path, intake)
        _write_json(source_path, source)
    review_path = _write_json(tmp_path / "ce-review-draft.json", _geometry_draft(intake_path))
    return review_path, intake_path, source_path


def _run_public_cli(
    capsys: pytest.CaptureFixture[str],
    *,
    review_path: Path,
    intake_path: Path,
    source_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> tuple[int, dict]:
    argv = [
        "--review-draft",
        str(review_path),
        "--source-intake",
        str(intake_path),
        "--source-bundle",
        str(source_path),
        "--output",
        str(output_path),
        "--repo-root",
        str(ROOT),
    ]
    if overwrite:
        argv.append("--overwrite")
    exit_code = public_exporter.main(argv)
    report = json.loads(capsys.readouterr().out)
    return exit_code, report


def test_public_identity_and_cli_surface_are_stable() -> None:
    assert public_exporter.VERIFIED_EXPORTER_ID == "ev4-producer-gate-export-validator"
    assert public_exporter.VERIFIED_EXPORTER_VERSION == "1.1.0"
    assert public_exporter.OFFICIAL_CLI_OPTIONS == (
        "--review-draft",
        "--source-intake",
        "--source-bundle",
        "--output",
        "--repo-root",
        "--overwrite",
    )


def test_absolute_external_output_is_published_directly_with_exit_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_provenance(monkeypatch)
    review_path, intake_path, source_path = _write_inputs(tmp_path / "inputs", authorized=True)
    output_path = (tmp_path / "workbench-attempt" / "generated-artifacts" / "ce-project-gate.json").resolve()
    output_path.parent.mkdir(parents=True)

    exit_code, report = _run_public_cli(
        capsys,
        review_path=review_path,
        intake_path=intake_path,
        source_path=source_path,
        output_path=output_path,
    )

    assert exit_code == 0, report
    assert report["status"] == "successful"
    assert report["handoff_allowed"] is True
    assert report["authorization_valid"] is True
    assert report["output_written"] is True
    assert report["output_valid"] is True
    assert Path(report["output_path"]).resolve() == output_path
    assert output_path.is_file()


def test_valid_blocked_external_output_preserves_exit_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_provenance(monkeypatch)
    review_path, intake_path, source_path = _write_inputs(tmp_path / "inputs", authorized=False)
    output_path = (tmp_path / "external" / "ce-project-gate.json").resolve()
    output_path.parent.mkdir(parents=True)

    exit_code, report = _run_public_cli(
        capsys,
        review_path=review_path,
        intake_path=intake_path,
        source_path=source_path,
        output_path=output_path,
    )

    assert exit_code == 2, report
    assert report["status"] in {"blocked", "insufficient_evidence"}
    assert report["handoff_allowed"] is False
    assert report["authorization_valid"] is False
    assert report["output_written"] is True
    assert report["output_valid"] is True
    assert output_path.is_file()


def test_invalid_external_export_preserves_exit_one_and_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_provenance(monkeypatch)
    review_path, intake_path, source_path = _write_inputs(tmp_path / "inputs", authorized=True)
    draft = json.loads(review_path.read_text(encoding="utf-8"))
    draft.pop("schema_id")
    _write_json(review_path, draft)
    output_path = (tmp_path / "external" / "ce-project-gate.json").resolve()
    output_path.parent.mkdir(parents=True)

    exit_code, report = _run_public_cli(
        capsys,
        review_path=review_path,
        intake_path=intake_path,
        source_path=source_path,
        output_path=output_path,
    )

    assert exit_code == 1, report
    assert report["status"] == "invalid"
    assert report["handoff_allowed"] is False
    assert report["authorization_valid"] is False
    assert report["output_written"] is False
    assert report["output_valid"] is False
    assert not output_path.exists()


def test_relative_outputs_remain_ce_root_relative(tmp_path: Path) -> None:
    relative = Path(".tmp-test-output/external-boundary-relative.json")
    observed = safe_output_path(ROOT, relative, False)
    assert observed == (ROOT / relative).resolve(strict=False)

    absolute = (tmp_path / "external-output.json").resolve()
    assert safe_output_path(ROOT, absolute, False) == absolute


def test_external_output_safety_controls_remain_active(tmp_path: Path) -> None:
    external = (tmp_path / "external.json").resolve()

    with pytest.raises(ExporterError) as alias_error:
        safe_output_path(ROOT, external, False, protected_inputs=(external,))
    assert alias_error.value.diagnostic.code == "CE_EXPORT_OUTPUT_ALIASES_INPUT"

    directory = tmp_path / "directory-target"
    directory.mkdir()
    with pytest.raises(ExporterError) as directory_error:
        safe_output_path(ROOT, directory.resolve(), False)
    assert directory_error.value.diagnostic.code == "CE_EXPORT_OUTPUT_IS_DIRECTORY"

    external.write_text('{"foreign":true}\n', encoding="utf-8")
    with pytest.raises(ExporterError) as ownership_error:
        safe_output_path(ROOT, external, True)
    assert ownership_error.value.diagnostic.code == "CE_EXPORT_OUTPUT_NOT_OWNED"


def test_external_output_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "output-link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink fixture unavailable: {exc}")

    with pytest.raises(ExporterError) as symlink_error:
        safe_output_path(ROOT, link, True)
    assert symlink_error.value.diagnostic.code == "CE_EXPORT_OUTPUT_SYMLINK_FORBIDDEN"


def test_external_owned_overwrite_restores_prior_bytes_after_post_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provenance(monkeypatch)
    review_path, intake_path, source_path = _write_inputs(tmp_path / "inputs", authorized=True)
    output_path = (tmp_path / "external" / "ce-project-gate.json").resolve()
    output_path.parent.mkdir(parents=True)

    first = verified_impl.export_verified_review_file(
        repo_root=ROOT,
        review_draft_path=review_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        output_path=output_path,
    )
    assert first.status == "successful", first.as_dict()
    prior_bytes = output_path.read_bytes()

    original_validate = verified_impl.validate_stage_bundle_schema
    calls = 0

    def fail_post_write(repo_root: Path, bundle: dict) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ExporterError(
                ExportDiagnostic(
                    "CE_EXPORT_TEST_POST_WRITE_REJECTION",
                    "post_write_validation",
                    "Injected post-write rejection for rollback proof.",
                    str(output_path),
                )
            )
        original_validate(repo_root, bundle)

    monkeypatch.setattr(verified_impl, "validate_stage_bundle_schema", fail_post_write)
    second = verified_impl.export_verified_review_file(
        repo_root=ROOT,
        review_draft_path=review_path,
        source_intake_path=intake_path,
        source_bundle_path=source_path,
        output_path=output_path,
        overwrite=True,
    )

    assert second.status == "invalid"
    assert second.output_written is False
    assert second.handoff_allowed is False
    assert output_path.read_bytes() == prior_bytes


def test_git_provenance_ignores_external_paths_without_comparison_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external = (tmp_path / "outside" / "ce-project-gate.json").resolve()

    def fake_git(root: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo_root)
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/rezahh107/EV4-Constructability-Engineer-Repo.git"
        if args == ("rev-parse", "HEAD"):
            return "a" * 40
        if args == ("status", "--porcelain=v1", "--untracked-files=all"):
            return "?? local-untracked.txt"
        raise AssertionError(args)

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        assert command == ["git", "symbolic-ref", "--quiet", "--short", "HEAD"]
        assert cwd == repo_root.resolve()
        return subprocess.CompletedProcess(command, 0, "fix/ce-external-output-boundary\n", "")

    monkeypatch.setattr(exporter_core, "_git", fake_git)
    monkeypatch.setattr(exporter_core, "_run", fake_run)

    provenance = exporter_core.inspect_git_provenance(repo_root, ignored_paths=(external,))
    assert provenance.dirty is True
    assert provenance.dirty_paths == ("local-untracked.txt",)
    assert str(external) not in provenance.dirty_paths
