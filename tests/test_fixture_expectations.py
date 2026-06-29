from pathlib import Path

import pytest

from validator.engine import load_yaml, validate_file

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "path",
    [ROOT / "fixtures/valid/v01_pure_structure.yaml"],
)
def test_selected_valid_fixtures_pass(path: Path) -> None:
    result = validate_file(path, repo_root=ROOT)
    assert result["passed"] is True


@pytest.mark.parametrize(
    "path",
    sorted((ROOT / "fixtures/invalid").glob("*.yaml"))
    + sorted((ROOT / "fixtures/regression").glob("*.yaml")),
)
def test_invalid_fixtures_include_expected_rules(path: Path) -> None:
    fixture = load_yaml(path)
    expected_rules = set(fixture.get("expected", {}).get("rules_violated", []))
    result = validate_file(path, repo_root=ROOT)
    assert result["passed"] is False
    assert expected_rules.issubset(set(result["rules_violated"]))
