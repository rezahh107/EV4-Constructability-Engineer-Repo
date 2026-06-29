from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator

from .exceptions import ConstructabilityException, ConstructabilityViolation
from .rules import evaluate_document

ValidationMode = Literal["report", "package", "full"]

SCHEMA_BY_KIND = {
    "constructability_review": "schemas/constructability_review.schema.json",
    "implementation_strategy_map": "schemas/implementation_strategy_map.schema.json",
    "builder_executable_package": "schemas/builder_executable_package.schema.json",
}
VALIDATION_MODES = {"report", "package", "full"}


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"Expected mapping document in {path}")
    return data


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return data


def schema_validate(document: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path.cwd()
    errors: list[str] = []

    for key, schema_path in SCHEMA_BY_KIND.items():
        if key not in document:
            continue
        schema = load_json(root / schema_path)
        validator = Draft202012Validator(schema)
        schema_errors = sorted(
            validator.iter_errors(document[key]),
            key=lambda item: list(item.path),
        )
        for error in schema_errors:
            path = ".".join(str(part) for part in error.path) or key
            errors.append(f"{key}.{path}: {error.message}")

    return errors


def _mode_preflight_violations(document: dict[str, Any], mode: ValidationMode) -> list[ConstructabilityViolation]:
    review = document.get("constructability_review") or document
    if mode == "report" and review.get("constructability_status") == "executable_ready":
        return [
            ConstructabilityViolation(
                rule_id="R21_REPORT_MODE_MUST_BE_NON_EXECUTABLE",
                status="blocked",
                message="report mode validates non-executable reviews only; status must not be executable_ready.",
                location="constructability_review.constructability_status",
            )
        ]
    return []


def validate_document(
    document: dict[str, Any],
    *,
    repo_root: Path | None = None,
    mode: ValidationMode = "full",
) -> dict[str, Any]:
    if mode not in VALIDATION_MODES:
        raise ValueError(f"Unsupported validation mode: {mode}")

    schema_errors = schema_validate(document, repo_root=repo_root)
    rule_violations = _mode_preflight_violations(document, mode)
    rule_violations.extend(evaluate_document(document, mode=mode))
    expected = document.get("expected") or {}
    expected_pass = expected.get("validation_pass")
    passed = not schema_errors and not rule_violations
    result = {
        "passed": passed,
        "mode": mode,
        "schema_errors": schema_errors,
        "violations": [violation.__dict__ for violation in rule_violations],
        "rules_violated": [violation.rule_id for violation in rule_violations],
        "expected_pass": expected_pass,
    }

    if expected_pass is not None:
        result["matches_expected"] = passed is bool(expected_pass)
        expected_rules = set(expected.get("rules_violated") or [])
        if expected_rules:
            actual_rules = set(result["rules_violated"])
            result["expected_rules_present"] = sorted(expected_rules.intersection(actual_rules))
            result["expected_rules_missing"] = sorted(expected_rules.difference(actual_rules))

    return result


def validate_file(
    path: str | Path,
    *,
    repo_root: Path | None = None,
    mode: ValidationMode = "full",
    strict: bool = False,
) -> dict[str, Any]:
    document = load_yaml(path)
    result = validate_document(document, repo_root=repo_root, mode=mode)
    if strict and not result["passed"]:
        violations = [
            ConstructabilityViolation(**violation)
            for violation in result.get("violations", [])
        ]
        raise ConstructabilityException(violations)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate EV4 constructability fixtures/packages.")
    parser.add_argument("path", help="YAML fixture or package path")
    parser.add_argument("--repo-root", default=".", help="Repository root containing schemas/")
    parser.add_argument(
        "--mode",
        choices=sorted(VALIDATION_MODES),
        default="full",
        help="Validation contract to apply.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args(argv)

    result = validate_file(args.path, repo_root=Path(args.repo_root), mode=args.mode)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        label = "PASS" if result["passed"] else "FAIL-CLOSED"
        print(f"{label} mode={result['mode']}")
        if result["schema_errors"]:
            print("schema_errors:")
            for error in result["schema_errors"]:
                print(f"- {error}")
        if result["rules_violated"]:
            print("rules_violated:")
            for rule_id in result["rules_violated"]:
                print(f"- {rule_id}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
