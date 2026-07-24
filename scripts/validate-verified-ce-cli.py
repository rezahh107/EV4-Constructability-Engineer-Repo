from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from exporter_test_support import _real_source_pair, _write_json  # noqa: E402
from verified_exporter_test_support import _geometry_draft  # noqa: E402
from validator.payload_assembler import sha256_json  # noqa: E402


def _run_cli(
    executable: str,
    *,
    review: Path,
    intake: Path,
    bundle: Path,
    output: Path,
    overwrite: bool,
) -> dict[str, Any]:
    command = [
        executable,
        "--review-draft",
        str(review),
        "--source-intake",
        str(intake),
        "--source-bundle",
        str(bundle),
        "--output",
        str(output),
        "--repo-root",
        str(ROOT),
    ]
    if overwrite:
        command.append("--overwrite")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Official CLI did not return JSON. exit={completed.returncode}; "
            f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        ) from exc
    if completed.returncode != 0:
        raise AssertionError(
            f"Official CLI failed. exit={completed.returncode}; report={report}; "
            f"stderr={completed.stderr!r}"
        )
    return report


def _assert_authorized(report: dict[str, Any]) -> None:
    assert report["status"] == "successful", report
    assert report["handoff_allowed"] is True, report
    assert report["authorization_valid"] is True, report
    assert report["output_valid"] is True, report


def _write_real_authorized_inputs(workspace: Path, review: Path) -> tuple[Path, Path]:
    intake, source, intake_path, bundle_path = _real_source_pair(workspace)

    # Retain canonical responsive risk seeds: they are Architect-owned scope hints,
    # not executed runtime evidence and do not block an unrelated geometry-only Draft.
    intake["unresolved_evidence"] = []
    source["payload"]["unresolved_evidence"] = []
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = sha256_json(source)

    _write_json(intake_path, intake)
    _write_json(bundle_path, source)
    review.parent.mkdir(parents=True, exist_ok=True)
    _write_json(review, _geometry_draft(intake_path))
    return intake_path, bundle_path


def main() -> int:
    executable = shutil.which("ev4-ce-project-gate-export")
    if executable is None:
        raise AssertionError("Installed official CLI entry point was not found")

    workspace = ROOT / ".tmp-ce-cli-validation"
    review = workspace / "custom-review-location" / "review-any-name.json"
    output = workspace / "verified-project-gate-export.json"
    dirty_probe = ROOT / "docs" / ".ce-cli-dirty-metadata-probe.tmp"

    shutil.rmtree(workspace, ignore_errors=True)
    dirty_probe.unlink(missing_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    intake, bundle = _write_real_authorized_inputs(workspace, review)

    try:
        clean = _run_cli(
            executable,
            review=review,
            intake=intake,
            bundle=bundle,
            output=output,
            overwrite=False,
        )
        _assert_authorized(clean)
        assert clean["repository_dirty"] is False, clean
        assert clean["dirty_paths"] == [], clean

        dirty_probe.write_text("functional metadata probe\n", encoding="utf-8")
        dirty = _run_cli(
            executable,
            review=review,
            intake=intake,
            bundle=bundle,
            output=output,
            overwrite=True,
        )
        _assert_authorized(dirty)
        assert dirty["repository_dirty"] is True, dirty
        assert "docs/.ce-cli-dirty-metadata-probe.tmp" in dirty["dirty_paths"], dirty
        assert (
            clean["status"],
            clean["handoff_allowed"],
            clean["authorization_valid"],
        ) == (
            dirty["status"],
            dirty["handoff_allowed"],
            dirty["authorization_valid"],
        )

        print(
            json.dumps(
                {
                    "status": clean["status"],
                    "handoff_allowed": clean["handoff_allowed"],
                    "authorization_valid": clean["authorization_valid"],
                    "clean_repository_dirty": clean["repository_dirty"],
                    "dirty_repository_dirty": dirty["repository_dirty"],
                    "dirty_paths": dirty["dirty_paths"],
                },
                sort_keys=True,
            )
        )
        return 0
    finally:
        dirty_probe.unlink(missing_ok=True)
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
