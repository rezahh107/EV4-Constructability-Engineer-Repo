from pathlib import Path

import pytest

from validator.engine import load_yaml, validate_file

ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = sorted((ROOT / "fixtures/valid").glob("*.yaml"))
INVALID_FIXTURES = sorted((ROOT / "fixtures/invalid").glob("*.yaml"))
REGRESSION_FIXTURES = sorted((ROOT / "fixtures/regression").glob("*.yaml"))


@pytest.mark.parametrize("path", VALID_FIXTURES)
def test_valid_fixtures_pass(path: Path) -> None:
    result = validate_file(path, repo_root=ROOT)
    assert result["passed"] is True


@pytest.mark.parametrize("path", INVALID_FIXTURES + REGRESSION_FIXTURES)
def test_invalid_fixtures_have_expected_rules(path: Path) -> None:
    fixture = load_yaml(path)
    expected_rules = set(fixture.get("expected", {}).get("rules_violated", []))
    result = validate_file(path, repo_root=ROOT)
    assert result["passed"] is False
    assert expected_rules.issubset(set(result["rules_violated"]))
