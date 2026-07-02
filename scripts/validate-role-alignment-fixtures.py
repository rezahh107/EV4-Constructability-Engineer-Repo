from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from validator.rules import evaluate_document

ROOT = Path(__file__).resolve().parents[1]
VALID_DIR = ROOT / "tests" / "role-alignment" / "valid"
INVALID_DIR = ROOT / "tests" / "role-alignment" / "invalid"
PREREQUISITES_SCHEMA = ROOT / "schemas" / "ce-builder-executable-prerequisites.schema.json"
SUPPORTED_BUILDER_EXECUTABLE_PACKAGE_SCHEMA = "ev4-builder-executable-package@1.0.0"

VISUAL_PREREQUISITES = (
    "golden_reference_contract",
    "reference_paradigm_lock",
    "paradigm_to_structure_map",
    "build_intent_brief",
    "spatial_lexicon_version_used",
    "visual_tolerance_policy",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package(doc: dict) -> dict | None:
    value = doc.get("builder_executable_package")
    return value if isinstance(value, dict) else None


def review(doc: dict) -> dict:
    value = doc.get("constructability_review")
    return value if isinstance(value, dict) else doc


def gate_document(doc: dict) -> dict:
    rev = review(doc)
    pkg = package(doc)
    gate = {
        "constructability_status": rev.get("constructability_status"),
        "allowed_output_now": rev.get("allowed_output_now"),
        "blocked_output_now": rev.get("blocked_output_now"),
    }
    if isinstance(pkg, dict):
        gate["builder_package_gate_check"] = {
            "schema": pkg.get("schema"),
            "builder_decisions_required": pkg.get("builder_decisions_required"),
            "blocking_dependencies": pkg.get("blocking_dependencies"),
            "selected_candidate_locked": pkg.get("selected_candidate_locked"),
            "selected_candidate_id_unchanged": pkg.get("selected_candidate_id_unchanged"),
            "approved_class_names_unchanged": pkg.get("approved_class_names_unchanged"),
            "confirmation_request_present": isinstance(pkg.get("confirmation_request"), dict),
            "first_safe_builder_batch_present": isinstance(pkg.get("first_safe_builder_batch"), dict),
        }
        if pkg.get("visual_parity_build") is True:
            gate["visual_reference_prerequisites"] = {
                "visual_parity_build": True,
                "golden_reference_contract": pkg.get("golden_reference_contract"),
                "reference_paradigm_lock": pkg.get("reference_paradigm_lock"),
                "paradigm_to_structure_map": pkg.get("paradigm_to_structure_map"),
                "build_intent_brief": pkg.get("build_intent_brief"),
                "spatial_lexicon_version_used": pkg.get("spatial_lexicon_version_used"),
                "visual_tolerance_policy": pkg.get("visual_tolerance_policy"),
            }
    return gate


def assert_prerequisite_schema(doc: dict, path: Path, validator: Draft202012Validator) -> None:
    errors = list(validator.iter_errors(gate_document(doc)))
    if errors:
        details = "; ".join(str(error.message) for error in errors)
        raise ValueError(f"{path}: prerequisite schema validation failed: {details}")


def assert_role_alignment(doc: dict, path: Path) -> None:
    rev = review(doc)
    pkg = package(doc)
    status = rev.get("constructability_status")
    allowed = rev.get("allowed_output_now")
    blocked = rev.get("blocked_output_now")

    if status != "executable_ready":
        if pkg is not None:
            raise ValueError(f"{path}: non-executable review must not emit builder_executable_package")
        if allowed != "Constructability Review" or blocked != "Builder Executable Package":
            raise ValueError(f"{path}: blocked review must expose Constructability Review only")
        return

    if pkg is None:
        raise ValueError(f"{path}: executable_ready requires builder_executable_package")
    if pkg.get("schema") != SUPPORTED_BUILDER_EXECUTABLE_PACKAGE_SCHEMA:
        raise ValueError(f"{path}: builder_executable_package.schema must be {SUPPORTED_BUILDER_EXECUTABLE_PACKAGE_SCHEMA}")
    if allowed != "Builder Executable Package" or blocked != "none":
        raise ValueError(f"{path}: executable_ready must expose Builder Executable Package only")
    if pkg.get("builder_package_status") != "executable_ready":
        raise ValueError(f"{path}: builder_package_status must be executable_ready")
    if pkg.get("builder_decisions_required") != 0:
        raise ValueError(f"{path}: builder_decisions_required must be 0")
    if pkg.get("blocking_dependencies") != []:
        raise ValueError(f"{path}: blocking_dependencies must be []")
    for field in ("selected_candidate_locked", "selected_candidate_id_unchanged", "approved_class_names_unchanged"):
        if pkg.get(field) is not True:
            raise ValueError(f"{path}: {field} must be true")
    if not isinstance(pkg.get("confirmation_request"), dict):
        raise ValueError(f"{path}: confirmation_request is required")
    if not isinstance(pkg.get("first_safe_builder_batch"), dict):
        raise ValueError(f"{path}: first_safe_builder_batch is required")

    if pkg.get("visual_parity_build") is True:
        missing = [field for field in VISUAL_PREREQUISITES if field not in pkg or pkg.get(field) in (None, "", [], {})]
        if missing:
            raise ValueError(f"{path}: visual parity package missing CE-carried prerequisites: {', '.join(missing)}")


def validate_valid_fixtures(validator: Draft202012Validator) -> None:
    paths = sorted(VALID_DIR.glob("*.json"))
    if not paths:
        raise ValueError("No valid role-alignment fixtures found")
    for path in paths:
        doc = load_json(path)
        assert_prerequisite_schema(doc, path, validator)
        violations = evaluate_document(doc)
        if violations:
            raise ValueError(f"{path}: validator violations: {[v.rule_id for v in violations]}")
        assert_role_alignment(doc, path)
        print(f"valid role-alignment fixture passed: {path.relative_to(ROOT)}")


def validate_invalid_fixtures(validator: Draft202012Validator) -> None:
    paths = sorted(INVALID_DIR.glob("*.json"))
    if not paths:
        raise ValueError("No invalid role-alignment fixtures found")
    for path in paths:
        doc = load_json(path)
        failed = bool(evaluate_document(doc))
        if not failed:
            try:
                assert_prerequisite_schema(doc, path, validator)
                assert_role_alignment(doc, path)
            except ValueError:
                failed = True
        if not failed:
            raise ValueError(f"invalid role-alignment fixture unexpectedly passed: {path.relative_to(ROOT)}")
        print(f"invalid role-alignment fixture correctly failed: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    schema = load_json(PREREQUISITES_SCHEMA)
    Draft202012Validator.check_schema(schema)
    schema_validator = Draft202012Validator(schema)
    validate_valid_fixtures(schema_validator)
    validate_invalid_fixtures(schema_validator)
