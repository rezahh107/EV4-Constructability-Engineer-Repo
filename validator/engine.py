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
DOCUMENT_SCHEMA_BY_ID = {
    "ev4-ce-stage-payload@1.0.0": "schemas/ce_stage_payload.v1.schema.json",
}
REFERENCE_PARADIGM_SCHEMA = "schemas/reference-paradigm-lock.schema.json"
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


def _collect_schema_errors(schema: dict[str, Any], document: dict[str, Any], prefix: str) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.path) or prefix
        errors.append(f"{path}: {error.message}")
    return errors


def schema_validate(document: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path.cwd()
    errors: list[str] = []

    document_schema_path = DOCUMENT_SCHEMA_BY_ID.get(document.get("schema_id"))
    if document_schema_path:
        schema = load_json(root / document_schema_path)
        errors.extend(_collect_schema_errors(schema, document, "document"))

    for key, schema_path in SCHEMA_BY_KIND.items():
        if key not in document or document[key] is None:
            continue
        schema = load_json(root / schema_path)
        errors.extend(_collect_schema_errors(schema, document[key], key))

    if "reference_paradigm_lock" in document or "paradigm_to_structure_map" in document:
        schema = load_json(root / REFERENCE_PARADIGM_SCHEMA)
        errors.extend(_collect_schema_errors(schema, document, "reference_paradigm_lock"))

    return errors


def validate_schemas(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path.cwd()
    errors: list[str] = []
    checked: list[str] = []

    for schema_path in sorted((root / "schemas").glob("*.schema.json")):
        checked.append(str(schema_path.relative_to(root)))
        try:
            Draft202012Validator.check_schema(load_json(schema_path))
        except Exception as exc:  # pragma: no cover - exact jsonschema exception varies
            errors.append(f"{schema_path.relative_to(root)}: {exc}")

    return {"passed": not errors, "checked": checked, "schema_errors": errors}


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


def _visual_parity_requested(document: dict[str, Any]) -> bool:
    package = document.get("builder_executable_package")
    return bool(
        document.get("visual_parity_build") is True
        or document.get("builder_ready") is True
        or (isinstance(package, dict) and package.get("visual_parity_build") is True)
    )


def _package_requires_reference_carriers(document: dict[str, Any]) -> bool:
    package = document.get("builder_executable_package")
    return isinstance(package, dict) and _visual_parity_requested(document)


def _reference_carriers(document: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if _package_requires_reference_carriers(document):
        package = document["builder_executable_package"]
        lock = package.get("reference_paradigm_lock")
        structure_map = package.get("paradigm_to_structure_map")
        return (lock if isinstance(lock, dict) else None, structure_map if isinstance(structure_map, dict) else None)
    lock = document.get("reference_paradigm_lock")
    structure_map = document.get("paradigm_to_structure_map")
    return (lock if isinstance(lock, dict) else None, structure_map if isinstance(structure_map, dict) else None)


def _package_carrier_violations(document: dict[str, Any]) -> list[ConstructabilityViolation]:
    if not _package_requires_reference_carriers(document):
        return []

    package = document.get("builder_executable_package") or {}
    violations: list[ConstructabilityViolation] = []
    package_lock = package.get("reference_paradigm_lock")
    package_map = package.get("paradigm_to_structure_map")

    if not isinstance(package_lock, dict) or package_lock.get("paradigm_locked") is not True:
        violations.append(
            ConstructabilityViolation(
                rule_id="R35_REFERENCE_PARADIGM_LOCK_MUST_BE_CARRIED_IN_PACKAGE",
                status="blocked",
                message="visual-parity Builder package must carry locked reference_paradigm_lock inside builder_executable_package.",
                location="builder_executable_package.reference_paradigm_lock",
            )
        )
    if not isinstance(package_map, dict):
        violations.append(
            ConstructabilityViolation(
                rule_id="R36_REFERENCE_PARADIGM_STRUCTURE_MAP_MUST_BE_CARRIED_IN_PACKAGE",
                status="blocked",
                message="visual-parity Builder package must carry paradigm_to_structure_map inside builder_executable_package.",
                location="builder_executable_package.paradigm_to_structure_map",
            )
        )

    return violations


def _reference_paradigm_preflight_violations(document: dict[str, Any]) -> list[ConstructabilityViolation]:
    if not _visual_parity_requested(document):
        return []

    violations: list[ConstructabilityViolation] = []
    violations.extend(_package_carrier_violations(document))
    if violations:
        return violations

    lock, structure_map = _reference_carriers(document)

    if not isinstance(lock, dict) or lock.get("paradigm_locked") is not True:
        violations.append(
            ConstructabilityViolation(
                rule_id="R29_REFERENCE_PARADIGM_LOCK_REQUIRED",
                status="blocked",
                message="visual-parity Builder-ready output requires locked reference_paradigm_lock.",
                location="reference_paradigm_lock",
            )
        )
        return violations

    if lock.get("layout_paradigm") == "unknown":
        violations.append(
            ConstructabilityViolation(
                rule_id="R30_REFERENCE_PARADIGM_UNKNOWN_BLOCKS_BUILDER_READY",
                status="blocked",
                message="layout_paradigm unknown blocks Builder-ready visual-parity output.",
                location="reference_paradigm_lock.layout_paradigm",
            )
        )

    if not isinstance(structure_map, dict):
        violations.append(
            ConstructabilityViolation(
                rule_id="R31_REFERENCE_PARADIGM_STRUCTURE_MAP_REQUIRED",
                status="blocked",
                message="visual-parity Builder-ready output requires paradigm_to_structure_map.",
                location="paradigm_to_structure_map",
            )
        )
    elif not isinstance(structure_map.get("first_batch_requirements"), list) or not structure_map.get("first_batch_requirements"):
        violations.append(
            ConstructabilityViolation(
                rule_id="R32_REFERENCE_PARADIGM_FIRST_BATCH_REQUIREMENTS_REQUIRED",
                status="blocked",
                message="visual-parity Builder-ready output requires first_batch_requirements.",
                location="paradigm_to_structure_map.first_batch_requirements",
            )
        )

    return violations


def validate_document(document: dict[str, Any], *, repo_root: Path | None = None, mode: ValidationMode = "full") -> dict[str, Any]:
    if mode not in VALIDATION_MODES:
        raise ValueError(f"Unsupported validation mode: {mode}")

    schema_errors = schema_validate(document, repo_root=repo_root)
    rule_violations = _mode_preflight_violations(document, mode)
    rule_violations.extend(_reference_paradigm_preflight_violations(document))
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


def validate_file(path: str | Path, *, repo_root: Path | None = None, mode: ValidationMode = "full", strict: bool = False) -> dict[str, Any]:
    document = load_yaml(path)
    result = validate_document(document, repo_root=repo_root, mode=mode)
    if strict and not result["passed"]:
        violations = [ConstructabilityViolation(**violation) for violation in result.get("violations", [])]
        raise ConstructabilityException(violations)
    return result


def _fixture_paths(directory: Path) -> list[Path]:
    return sorted([*directory.rglob("*.json"), *directory.rglob("*.yaml"), *directory.rglob("*.yml")])


def validate_path(path: str | Path, *, repo_root: Path | None = None, mode: ValidationMode = "full") -> dict[str, Any]:
    target = Path(path)
    if target.is_file():
        result = validate_file(target, repo_root=repo_root, mode=mode)
        result["path"] = str(target)
        return result

    if not target.is_dir():
        raise FileNotFoundError(target)

    results = []
    for fixture_path in _fixture_paths(target):
        result = validate_file(fixture_path, repo_root=repo_root, mode=mode)
        result["path"] = str(fixture_path)
        results.append(result)

    return {"passed": all(item["passed"] for item in results), "mode": mode, "path": str(target), "count": len(results), "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate EV4 constructability fixtures/packages.")
    parser.add_argument("path", nargs="?", help="YAML fixture, package path, or directory")
    parser.add_argument("--repo-root", default=".", help="Repository root containing schemas/")
    parser.add_argument("--mode", choices=sorted(VALIDATION_MODES), default="full", help="Validation contract to apply.")
    parser.add_argument("--schema-self-check", action="store_true", help="Validate repository JSON schemas themselves")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args(argv)

    if args.schema_self_check:
        result = validate_schemas(repo_root=Path(args.repo_root))
    else:
        if not args.path:
            parser.error("path is required unless --schema-self-check is used")
        result = validate_path(args.path, repo_root=Path(args.repo_root), mode=args.mode)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        label = "PASS" if result["passed"] else "FAIL-CLOSED"
        print(f"{label} mode={result.get('mode', 'schemas')}")
        for error in result.get("schema_errors", []):
            print(f"- {error}")
        for rule_id in result.get("rules_violated", []):
            print(f"- {rule_id}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
