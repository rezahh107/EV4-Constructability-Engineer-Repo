from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from deterministic_runtime_support import (  # noqa: E402
    canonical_bundle,
    canonical_draft,
    canonical_intake,
)
from validator.payload_assembler import canonical_bytes  # noqa: E402


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


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


def main() -> int:
    executable = shutil.which("ev4-ce-project-gate-export")
    if executable is None:
        raise AssertionError("Installed official CLI entry point was not found")

    workspace = ROOT / ".tmp-ce-cli-validation"
    review = workspace / "custom-review-location" / "review-any-name.json"
    intake = workspace / "architect-intake.json"
    bundle_path = workspace / "architect-source-bundle.json"
    output = workspace / "verified-project-gate-export.json"
    dirty_probe = ROOT / "docs" / ".ce-cli-dirty-metadata-probe.tmp"

    shutil.rmtree(workspace, ignore_errors=True)
    dirty_probe.unlink(missing_ok=True)
    bundle = canonical_bundle()
    _write(review, canonical_draft())
    _write(intake, canonical_intake(bundle=bundle))
    _write(bundle_path, bundle)

    try:
        clean = _run_cli(
            executable,
            review=review,
            intake=intake,
            bundle=bundle_path,
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
            bundle=bundle_path,
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
