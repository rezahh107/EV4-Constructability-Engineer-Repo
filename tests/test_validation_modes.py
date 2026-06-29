from pathlib import Path

from validator.engine import validate_file

ROOT = Path(__file__).resolve().parents[1]


def test_report_mode_accepts_non_executable_review_without_package() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/report/v01_needs_user_evidence_geometry.yaml",
        repo_root=ROOT,
        mode="report",
    )

    assert result["passed"] is True
    assert result["mode"] == "report"
    assert result["rules_violated"] == []


def test_package_mode_requires_builder_package() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/report/v01_needs_user_evidence_geometry.yaml",
        repo_root=ROOT,
        mode="package",
    )

    assert result["passed"] is False
    assert "R18_PACKAGE_MODE_REQUIRES_BUILDER_PACKAGE" in result["rules_violated"]


def test_package_mode_accepts_executable_builder_package() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/v01_pure_structure.yaml",
        repo_root=ROOT,
        mode="package",
    )

    assert result["passed"] is True
    assert result["mode"] == "package"


def test_non_executable_review_cannot_emit_package_in_full_mode() -> None:
    result = validate_file(
        ROOT / "fixtures/invalid/i09_blocked_review_with_builder_package.yaml",
        repo_root=ROOT,
        mode="full",
    )

    assert result["passed"] is False
    assert "R19_NON_EXECUTABLE_REVIEW_MUST_NOT_EMIT_BUILDER_PACKAGE" in result["rules_violated"]


def test_report_mode_rejects_builder_package_output() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/v01_pure_structure.yaml",
        repo_root=ROOT,
        mode="report",
    )

    assert result["passed"] is False
    assert "R17_REPORT_MODE_MUST_NOT_EMIT_BUILDER_PACKAGE" in result["rules_violated"]
