from pathlib import Path

from validator.engine import validate_file

ROOT = Path(__file__).resolve().parents[1]


def test_valid_package_has_no_rule_violations() -> None:
    result = validate_file(ROOT / "fixtures/valid/v01_pure_structure.yaml", repo_root=ROOT)
    assert result["passed"] is True
    assert result["rules_violated"] == []
