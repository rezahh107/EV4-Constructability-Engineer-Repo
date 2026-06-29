from pathlib import Path

from validator.engine import validate_file

ROOT = Path(__file__).resolve().parents[1]


def test_connector_geometry_case_is_rejected() -> None:
    result = validate_file(
        ROOT / "fixtures/regression/r01_unflagged_connector_geometry_dependency.yaml",
        repo_root=ROOT,
    )
    assert result["passed"] is False
    assert "R03_GEOMETRY_MUST_BE_PROVEN" in result["rules_violated"]
    assert "R05_OVERLAY_STRATEGY_MUST_BE_PROVEN" in result["rules_violated"]
