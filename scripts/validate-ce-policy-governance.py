#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "ce_policy_decision_context.v1.schema.json"
FIXTURE_ROOT = ROOT / "fixtures" / "ce-policy-governance"

DIAG_SCHEMA = "CE_POLICY_CONTEXT_SCHEMA_INVALID"
DIAG_LINEAGE = "CE_POLICY_KERNEL_LINEAGE_REQUIRED"
DIAG_OPTION = "CE_POLICY_KERNEL_SELECTED_OPTION_MISMATCH"
DIAG_DOMAIN = "CE_POLICY_DOMAIN_ADVISORY_CANNOT_AUTHORIZE"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_context(value: Any) -> list[Diagnostic]:
    schema = load_json(SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        return [
            Diagnostic(
                DIAG_SCHEMA,
                "$" + "".join(f"[{part!r}]" for part in error.absolute_path),
                error.message,
            )
            for error in errors
        ]

    diagnostics: list[Diagnostic] = []

    if value["decision_scope"] == "kernel_governed_choice":
        matching = [
            entry
            for entry in value["upstream_decision_lineage"]
            if entry["decision_family"] == value["decision_family"]
        ]
        if not matching:
            diagnostics.append(
                Diagnostic(
                    DIAG_LINEAGE,
                    "$.upstream_decision_lineage",
                    "Kernel-governed choices require complete matching machine-readable decision lineage.",
                )
            )
        elif all(
            entry["selected_option"] != value["requested_option"]
            for entry in matching
        ):
            diagnostics.append(
                Diagnostic(
                    DIAG_OPTION,
                    "$.requested_option",
                    "Requested option must equal the upstream Kernel selected_option.",
                )
            )

    for index, artifact in enumerate(value["external_domain_artifacts"]):
        if (
            artifact["trust_class"] == "unverified_advisory"
            and artifact["changed_decision_outcome"]
        ):
            diagnostics.append(
                Diagnostic(
                    DIAG_DOMAIN,
                    f"$.external_domain_artifacts[{index}]",
                    "An unverified advisory Domain artifact cannot authorize or change a decision outcome.",
                )
            )

    return diagnostics


def fixture_paths(paths: list[Path]) -> list[Path]:
    output: list[Path] = []
    for path in paths:
        if path.is_dir():
            output.extend(sorted(path.rglob("*.json")))
        else:
            output.append(path)
    return output


def validate_file(path: Path) -> dict[str, Any]:
    value = load_json(path)
    diagnostics = validate_context(value)
    passed = not diagnostics
    expected = value.get("expected", {}).get("validation_pass")
    return {
        "path": str(path),
        "passed": passed,
        "expected_pass": expected,
        "matches_expected": expected is None or passed is expected,
        "diagnostics": [diagnostic.as_dict() for diagnostic in diagnostics],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=[FIXTURE_ROOT])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = [validate_file(path) for path in fixture_paths(args.paths)]
    failed = [result for result in results if not result["matches_expected"]]

    if args.json:
        print(
            json.dumps(
                {"passed": not failed, "results": results},
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print("PASS" if not failed else "FAIL-CLOSED")
        for result in results:
            print(
                f"{result['path']}: passed={result['passed']} "
                f"expected={result['expected_pass']} "
                f"matches={result['matches_expected']}"
            )
            for diagnostic in result["diagnostics"]:
                print(
                    f"  - {diagnostic['code']} at {diagnostic['path']}: "
                    f"{diagnostic['message']}"
                )

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
