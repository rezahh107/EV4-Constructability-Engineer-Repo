from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ALLOWED_RISKS = {"Critical", "High", "Medium", "Low"}
ALLOWED_STATUSES = {
    "prose_only",
    "schema_backed",
    "validator_backed",
    "fixture_tested",
    "ci_enforced",
    "downstream_contract_enforced",
}
CRITICAL_WEAK_STATUSES = {"prose_only", "schema_backed"}
REQUIRED_HEADERS = [
    "rule_id",
    "concept",
    "risk",
    "prose_source",
    "schema_carrier",
    "validator_rule",
    "valid_fixture",
    "invalid_fixture",
    "CI_step",
    "downstream_contract",
    "status",
]


def _clean_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def _split_row(line: str) -> list[str]:
    parts = line.strip().split("|")
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [_clean_cell(cell) for cell in parts]


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", cell.strip()) for cell in cells)


def _find_coverage_table(lines: list[str]) -> tuple[int, list[str]]:
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = _split_row(line)
        if not headers or headers[0] != "rule_id":
            continue
        if headers != REQUIRED_HEADERS:
            raise ValueError(f"Unexpected coverage table headers at line {index + 1}: {headers}")
        if index + 1 >= len(lines):
            raise ValueError("Coverage table is missing separator row.")
        separator = _split_row(lines[index + 1])
        if len(separator) != len(headers) or not _is_separator_row(separator):
            raise ValueError(f"Coverage table separator is invalid at line {index + 2}.")
        return index + 2, headers
    raise ValueError("Coverage table with rule_id header was not found.")


def parse_coverage_markdown(content: str) -> list[dict[str, str]]:
    lines = content.splitlines()
    start_index, headers = _find_coverage_table(lines)
    rows: list[dict[str, str]] = []

    for line_number, line in enumerate(lines[start_index:], start=start_index + 1):
        if not line.strip().startswith("|"):
            break
        cells = _split_row(line)
        if len(cells) != len(headers):
            raise ValueError(f"Coverage table row at line {line_number} has {len(cells)} cells, expected {len(headers)}.")
        row = dict(zip(headers, cells, strict=True))
        row["line"] = str(line_number)
        rows.append(row)

    if not rows:
        raise ValueError("Coverage table contains no rule rows.")
    return rows


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()

    for row in rows:
        rule_id = row.get("rule_id", "")
        line = row.get("line", "?")
        risk = row.get("risk", "")
        status = row.get("status", "")

        if not rule_id:
            errors.append(f"line {line}: rule_id is required")
            continue
        if rule_id in seen:
            errors.append(f"line {line}: duplicate rule_id {rule_id}")
        seen.add(rule_id)

        if risk not in ALLOWED_RISKS:
            errors.append(f"line {line}: {rule_id} has invalid risk {risk}")
        if status not in ALLOWED_STATUSES:
            errors.append(f"line {line}: {rule_id} has invalid status {status}")

        if risk == "Critical" and status in CRITICAL_WEAK_STATUSES:
            errors.append(
                f"line {line}: {rule_id} is Critical but only {status}; add validator, invalid fixture, and CI coverage or lower the risk honestly"
            )

    return errors


def validate_coverage_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    rows = parse_coverage_markdown(target.read_text(encoding="utf-8"))
    errors = validate_rows(rows)
    return {
        "passed": not errors,
        "path": str(target),
        "count": len(rows),
        "errors": errors,
        "critical_count": sum(1 for row in rows if row.get("risk") == "Critical"),
        "high_count": sum(1 for row in rows if row.get("risk") == "High"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate behavioral rule coverage matrix.")
    parser.add_argument("path", nargs="?", default="docs/BEHAVIORAL_RULE_COVERAGE.md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = validate_coverage_file(args.path)
    except Exception as exc:
        if args.json:
            print(json.dumps({"passed": False, "errors": [str(exc)]}, indent=2, ensure_ascii=False))
        else:
            print("FAIL-CLOSED")
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("PASS" if result["passed"] else "FAIL-CLOSED")
        print(f"rules={result['count']} critical={result['critical_count']} high={result['high_count']}")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
