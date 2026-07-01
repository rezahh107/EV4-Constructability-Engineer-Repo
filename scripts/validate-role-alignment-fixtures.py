from __future__ import annotations

import json
from pathlib import Path

from validator.rules import evaluate_document

ROOT = Path(__file__).resolve().parents[1]
VALID_DIR = ROOT / "tests" / "role-alignment" / "valid"
INVALID_DIR = ROOT / "tests" / "role-alignment" / "invalid"

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


def validate_valid_fixtures() -> None:
    paths = sorted(VALID_DIR.glob("*.json"))
    if not paths:
        raise ValueError("No valid role-alignment fixtures found")
    for path in paths:
        doc = load_json(path)
        violations = evaluate_document(doc)
        if violations:
            raise ValueError(f"{path}: validator violations: {[v.rule_id for v in violations]}")
        assert_role_alignment(doc, path)
        print(f"valid role-alignment fixture passed: {path.relative_to(ROOT)}")


def validate_invalid_fixtures() -> None:
    paths = sorted(INVALID_DIR.glob("*.json"))
    if not paths:
        raise ValueError("No invalid role-alignment fixtures found")
    for path in paths:
        doc = load_json(path)
        failed = bool(evaluate_document(doc))
        if not failed:
            try:
                assert_role_alignment(doc, path)
            except ValueError:
                failed = True
        if not failed:
            raise ValueError(f"invalid role-alignment fixture unexpectedly passed: {path.relative_to(ROOT)}")
        print(f"invalid role-alignment fixture correctly failed: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    validate_valid_fixtures()
    validate_invalid_fixtures()
