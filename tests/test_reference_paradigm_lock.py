from pathlib import Path
import subprocess
import sys

import pytest

from validator.engine import validate_file
from validator.reference_paradigm_lock import validate_path

ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/valid/center_anchored_symmetric_pill_cards.json"
INVALID = sorted((ROOT / "tests/invalid").glob("*.json"))


@pytest.mark.parametrize("path", [VALID])
def test_valid_reference_paradigm_lock_passes(path: Path) -> None:
    result = validate_path(path, repo_root=ROOT)
    assert result["passed"] is True


@pytest.mark.parametrize("path", INVALID)
def test_invalid_reference_paradigm_lock_fails(path: Path) -> None:
    result = validate_path(path, repo_root=ROOT)
    assert result["passed"] is False


def test_engine_schema_validates_reference_paradigm_lock() -> None:
    result = validate_file(VALID, repo_root=ROOT)
    assert result["passed"] is True


def test_builder_ready_unknown_layout_is_blocked_by_engine() -> None:
    result = validate_file(ROOT / "tests/invalid/unknown_layout_paradigm_marked_builder_ready.json", repo_root=ROOT)
    assert result["passed"] is False
    assert "R30_REFERENCE_PARADIGM_UNKNOWN_BLOCKS_BUILDER_READY" in result["rules_violated"]


def test_node_wrapper_validates_reference_paradigm_lock() -> None:
    result = subprocess.run(
        ["node", "scripts/validate-reference-paradigm-lock.mjs", str(VALID), "--repo-root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_python_module_cli_rejects_invalid_directory() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "validator.reference_paradigm_lock",
            "tests/invalid",
            "--repo-root",
            ".",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
