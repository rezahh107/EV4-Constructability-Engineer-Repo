import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "validator.engine", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_report_mode_outputs_json_success() -> None:
    result = _run_cli(
        "fixtures/valid/report/v01_needs_user_evidence_geometry.yaml",
        "--mode",
        "report",
        "--repo-root",
        ".",
        "--json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["mode"] == "report"


def test_cli_package_mode_fails_invalid_package() -> None:
    result = _run_cli(
        "fixtures/regression/r01_unflagged_connector_geometry_dependency.yaml",
        "--mode",
        "package",
        "--repo-root",
        ".",
        "--json",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert "R03_GEOMETRY_MUST_BE_PROVEN" in payload["rules_violated"]


def test_cli_schema_self_check_outputs_json_success() -> None:
    result = _run_cli("--schema-self-check", "--repo-root", ".", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert "schemas/constructability_review.schema.json" in payload["checked"]


def test_cli_directory_mode_outputs_aggregate_json() -> None:
    result = _run_cli("fixtures/valid/report", "--mode", "report", "--repo-root", ".", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["count"] >= 1
    assert payload["results"][0]["mode"] == "report"
