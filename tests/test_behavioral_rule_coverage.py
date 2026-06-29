from pathlib import Path
import subprocess
import sys

from validator.behavioral_rule_coverage import parse_coverage_markdown, validate_coverage_file, validate_rows

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "docs/BEHAVIORAL_RULE_COVERAGE.md"


def _row(rule_id: str, risk: str, status: str) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "concept": "test rule",
        "risk": risk,
        "prose_source": "docs/test.md",
        "schema_carrier": "field",
        "validator_rule": "R_TEST",
        "valid_fixture": "tests/valid/test.json",
        "invalid_fixture": "tests/invalid/test.json",
        "CI_step": "pytest -q",
        "downstream_contract": "consumer rejects invalid package",
        "status": status,
        "line": "1",
    }


def test_current_behavioral_rule_coverage_passes() -> None:
    result = validate_coverage_file(COVERAGE)

    assert result["passed"] is True
    assert result["critical_count"] >= 1
    assert result["high_count"] >= 1


def test_parse_coverage_markdown_extracts_matrix_rows() -> None:
    rows = parse_coverage_markdown(COVERAGE.read_text(encoding="utf-8"))

    rule_ids = {row["rule_id"] for row in rows}
    assert "R-CE-PAR-01" in rule_ids
    assert "R-CE-BATCH-01" in rule_ids


def test_parse_coverage_markdown_allows_leading_whitespace_and_one_dash_separator() -> None:
    doc = "\n".join(
        [
            "# Coverage",
            "",
            "   | rule_id | concept | risk | prose_source | schema_carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | status |",
            "   |-|-|-:|-|-|-|-|-|-|-|-|",
            "   | `R-TEST-SPACE` | Test | High | `docs/test.md` | `field` | `R_TEST` | `tests/valid/test.json` | `tests/invalid/test.json` | `pytest -q` | consumer | `validator_backed` |",
        ]
    )

    rows = parse_coverage_markdown(doc)

    assert rows[0]["rule_id"] == "R-TEST-SPACE"


def test_critical_schema_backed_rule_fails_closed() -> None:
    errors = validate_rows([_row("R-TEST-CRITICAL", "Critical", "schema_backed")])

    assert errors
    assert "R-TEST-CRITICAL" in errors[0]


def test_critical_prose_only_rule_fails_closed() -> None:
    errors = validate_rows([_row("R-TEST-PROSE", "Critical", "prose_only")])

    assert errors
    assert "R-TEST-PROSE" in errors[0]


def test_high_schema_backed_rule_is_allowed_temporarily() -> None:
    errors = validate_rows([_row("R-TEST-HIGH", "High", "schema_backed")])

    assert errors == []


def test_duplicate_rule_id_fails() -> None:
    errors = validate_rows([
        _row("R-TEST-DUP", "High", "validator_backed"),
        _row("R-TEST-DUP", "High", "validator_backed"),
    ])

    assert any("duplicate rule_id R-TEST-DUP" in error for error in errors)


def test_cli_rejects_invalid_critical_gap(tmp_path: Path) -> None:
    invalid_doc = tmp_path / "coverage.md"
    invalid_doc.write_text(
        "\n".join(
            [
                "# Coverage",
                "",
                "| rule_id | concept | risk | prose_source | schema_carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | status |",
                "|---|---|---:|---|---|---|---|---|---|---|---|",
                "| `R-TEST-001` | Test | Critical | `docs/test.md` | `field` | `None` | `None` | `None` | `None` | `None` | `schema_backed` |",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "scripts/validate-behavioral-rule-coverage.py", str(invalid_doc)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "FAIL-CLOSED" in result.stdout


def test_cli_reports_malformed_file_without_traceback(tmp_path: Path) -> None:
    malformed = tmp_path / "coverage.md"
    malformed.write_text("# Missing table\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate-behavioral-rule-coverage.py", str(malformed)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "FAIL-CLOSED" in result.stdout
    assert "Traceback" not in result.stderr
