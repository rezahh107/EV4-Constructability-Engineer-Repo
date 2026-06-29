from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

HEADERS = [
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
RISKS = {"Critical", "High", "Medium", "Low"}
STATUSES = {
    "prose_only",
    "schema_backed",
    "validator_backed",
    "fixture_tested",
    "ci_enforced",
    "downstream_contract_enforced",
}
WEAK = {"prose_only", "schema_backed"}


def clean(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1].strip()
    return value


def split_row(line: str) -> list[str]:
    parts = line.strip().split("|")
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [clean(part) for part in parts]


def separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", cell.strip()) for cell in cells)


def parse(content: str) -> list[dict[str, str]]:
    lines = content.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().startswith("| rule_id |"):
            headers = split_row(line)
            if headers != HEADERS:
                raise ValueError(f"bad headers at line {index + 1}")
            if index + 1 >= len(lines) or not separator(split_row(lines[index + 1])):
                raise ValueError(f"bad separator at line {index + 2}")
            start = index + 2
            break
    if start is None:
        raise ValueError("coverage table not found")

    rows = []
    for line_number, line in enumerate(lines[start:], start=start + 1):
        if not line.strip().startswith("|"):
            break
        cells = split_row(line)
        if len(cells) != len(HEADERS):
            raise ValueError(f"bad cell count at line {line_number}")
        row = dict(zip(HEADERS, cells, strict=True))
        row["line"] = str(line_number)
        rows.append(row)
    if not rows:
        raise ValueError("coverage table has no rows")
    return rows


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
    errors = []
    seen = set()
    for row in rows:
        rule_id = row.get("rule_id", "")
        risk = row.get("risk", "")
        status = row.get("status", "")
        line = row.get("line", "?")
        if not rule_id:
            errors.append(f"line {line}: missing rule_id")
            continue
        if rule_id in seen:
            errors.append(f"line {line}: duplicate rule_id {rule_id}")
        seen.add(rule_id)
        if risk not in RISKS:
            errors.append(f"line {line}: invalid risk {risk}")
        if status not in STATUSES:
            errors.append(f"line {line}: invalid status {status}")
        if risk == "Critical" and status in WEAK:
            errors.append(f"line {line}: weak critical rule {rule_id}")
    return errors


def validate_coverage_file(path: str | Path) -> dict[str, Any]:
    rows = parse(Path(path).read_text(encoding="utf-8"))
    errors = validate_rows(rows)
    return {
        "passed": not errors,
        "count": len(rows),
        "critical_count": sum(row.get("risk") == "Critical" for row in rows),
        "high_count": sum(row.get("risk") == "High" for row in rows),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="docs/BEHAVIORAL_RULE_COVERAGE.md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate_coverage_file(args.path)
    except Exception as exc:
        result = {"passed": False, "errors": [str(exc)]}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("PASS" if result["passed"] else "FAIL-CLOSED")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
