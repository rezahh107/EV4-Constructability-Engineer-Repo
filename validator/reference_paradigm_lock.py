from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .engine import load_json, load_yaml

SCHEMA_PATH = "schemas/reference-paradigm-lock.schema.json"
VALID_LAYOUTS = {
    "center-anchored-symmetric",
    "vertical-list",
    "grid",
    "split-hero",
    "radial-diagram",
    "unknown",
}


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_items(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def _load_document(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        return load_json(path)
    return load_yaml(path)


def _schema_errors(document: dict[str, Any], repo_root: Path) -> list[str]:
    schema = load_json(repo_root / SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "document"
        errors.append(f"{location}: {error.message}")
    return errors


def _builder_ready_requested(document: dict[str, Any]) -> bool:
    package = document.get("builder_executable_package")
    return bool(
        document.get("visual_parity_build") is True
        or document.get("builder_ready") is True
        or (isinstance(package, dict) and package.get("visual_parity_build") is True)
    )


def _rule_errors(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lock = document.get("reference_paradigm_lock")
    structure_map = document.get("paradigm_to_structure_map")
    builder_ready = _builder_ready_requested(document)

    if not isinstance(lock, dict):
        return ["reference_paradigm_lock is required"]

    if lock.get("schema") != "ev4-reference-paradigm-lock@1.0.0":
        errors.append("schema must be ev4-reference-paradigm-lock@1.0.0")
    if not _has_text(lock.get("source_reference_id")):
        errors.append("source_reference_id is required")
    if lock.get("extracted_by") != "constructability_engineer":
        errors.append("extracted_by must equal constructability_engineer")
    if lock.get("paradigm_locked") is not True:
        errors.append("paradigm_locked must be true")
    if not _has_text(lock.get("layout_paradigm")):
        errors.append("layout_paradigm is required")
    elif lock.get("layout_paradigm") not in VALID_LAYOUTS:
        errors.append("layout_paradigm is not recognized")
    if builder_ready and lock.get("layout_paradigm") == "unknown":
        errors.append("layout_paradigm cannot be unknown for builder-ready output")
    if not _has_text(lock.get("primary_anchor")):
        errors.append("primary_anchor is required")
    if not _has_text(lock.get("distribution_model")):
        errors.append("distribution_model is required")
    if not _has_text(lock.get("repeated_unit_form")):
        errors.append("repeated_unit_form is required")
    if not _has_text(lock.get("connector_model")):
        errors.append("connector_model is required")
    if not _has_text(lock.get("spatial_symmetry")):
        errors.append("spatial_symmetry is required")
    if not _has_items(lock.get("completion_signature")):
        errors.append("completion_signature must be a non-empty array")

    if not isinstance(structure_map, dict):
        return [*errors, "paradigm_to_structure_map is required"]

    if not isinstance(structure_map.get("primary_anchor"), dict):
        errors.append("paradigm_to_structure_map.primary_anchor is required")
    if not _has_items(structure_map.get("regions")):
        errors.append("paradigm_to_structure_map.regions must be non-empty")
    if not isinstance(structure_map.get("repeated_units"), dict):
        errors.append("paradigm_to_structure_map.repeated_units is required")
    if not isinstance(structure_map.get("connector_layer"), dict):
        errors.append("paradigm_to_structure_map.connector_layer is required")
    if not _has_items(structure_map.get("first_batch_requirements")):
        errors.append("first_batch_requirements are required for visual-parity builds")

    return errors


def validate_reference_paradigm_lock(
    document: dict[str, Any], *, repo_root: Path | None = None
) -> dict[str, Any]:
    root = repo_root or Path.cwd()
    schema_errors = _schema_errors(document, root)
    rule_errors = _rule_errors(document)
    return {
        "passed": not schema_errors and not rule_errors,
        "schema_errors": schema_errors,
        "rule_errors": rule_errors,
    }


def _paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted([*path.rglob("*.json"), *path.rglob("*.yaml"), *path.rglob("*.yml")])


def validate_path(path: str | Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    results = []
    for fixture_path in _paths(target):
        result = validate_reference_paradigm_lock(_load_document(fixture_path), repo_root=repo_root)
        result["path"] = str(fixture_path)
        results.append(result)
    return {"passed": all(item["passed"] for item in results), "count": len(results), "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate EV4 reference paradigm lock fixtures.")
    parser.add_argument("paths", nargs="+", help="JSON/YAML fixture files or directories")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = [validate_path(path, repo_root=Path(args.repo_root)) for path in args.paths]
    passed = all(result["passed"] for result in results)
    payload = {"passed": passed, "results": results}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("PASS" if passed else "FAIL-CLOSED")
        for group in results:
            for item in group["results"]:
                if not item["passed"]:
                    print(item["path"])
                    for error in item["schema_errors"] + item["rule_errors"]:
                        print(f"- {error}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
