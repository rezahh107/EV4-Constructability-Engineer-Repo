#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from validator.kernel_decision_receipts import validate_receipt_document


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def iter_fixture_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            out.extend(
                sorted(p for p in path.rglob("*") if p.suffix.lower() in {".json", ".yaml", ".yml"})
            )
        else:
            out.append(path)
    return out


def validate_file(path: Path) -> dict[str, Any]:
    value = _load(path)
    diagnostics = validate_receipt_document(value)
    expected = value.get("expected", {}) if isinstance(value, dict) else {}
    passed = not diagnostics
    return {
        "path": str(path),
        "passed": passed,
        "expected_pass": expected.get("validation_pass"),
        "matches_expected": expected.get("validation_pass") is None
        or passed is bool(expected.get("validation_pass")),
        "diagnostics": [diagnostic.to_dict() for diagnostic in diagnostics],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate UX-safe CE Kernel decision receipt fixtures."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("fixtures/kernel-decision-receipts")],
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = [validate_file(path) for path in iter_fixture_paths(args.paths)]
    failed = [result for result in results if not result["matches_expected"]]

    if args.json:
        print(json.dumps({"passed": not failed, "results": results}, indent=2, ensure_ascii=False))
    else:
        print("PASS" if not failed else "FAIL-CLOSED")
        for result in results:
            print(
                f"{result['path']}: passed={result['passed']} "
                f"expected={result['expected_pass']} matches={result['matches_expected']}"
            )
            for diagnostic in result["diagnostics"]:
                print(f"  - {diagnostic['code']} at {diagnostic['path']}: {diagnostic['message']}")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
