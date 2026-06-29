from __future__ import annotations

from typing import Any, Literal

from .exceptions import ConstructabilityViolation

ValidationMode = Literal["report", "package", "full"]

BLOCKING_NODE_STATUSES = {"blocked", "needs_user_evidence", "needs_architect_amendment"}
NON_EXECUTABLE_REVIEW_STATUSES = {"blocked", "needs_user_evidence", "needs_architect_amendment"}
RESPONSIVE_ALLOWED = {"blocked", "evidence_backed", "not_applicable"}
VALIDATION_MODES = {"report", "package", "full"}


def _is_true(value: Any) -> bool:
    return value is True


def _has_object(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def _rule(rule_id: str, status: str, message: str, location: str = "document") -> ConstructabilityViolation:
    return ConstructabilityViolation(rule_id=rule_id, status=status, message=message, location=location)


def _review(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("constructability_review") or doc


def _package(doc: dict[str, Any]) -> dict[str, Any] | None:
    return doc.get("builder_executable_package")


def _nodes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return list((_review(doc).get("reviewed_nodes") or []))


def _review_status(doc: dict[str, Any]) -> str | None:
    return _review(doc).get("constructability_status")


def _package_status(doc: dict[str, Any]) -> str | None:
    pkg = _package(doc)
    if pkg is None:
        return None
    return pkg.get("builder_package_status")


def _status(doc: dict[str, Any]) -> str | None:
    return _package_status(doc) or _review_status(doc)


def _blocking_dependencies(doc: dict[str, Any]) -> list[Any]:
    pkg = _package(doc)
    deps = list(_review(doc).get("blocking_dependencies") or [])
    if pkg is not None:
        deps.extend(pkg.get("blocking_dependencies") or [])
    return deps


def _builder_decisions_required(doc: dict[str, Any]) -> int | None:
    values: list[int] = []
    review_value = _review(doc).get("builder_decisions_required")
    if isinstance(review_value, int):
        values.append(review_value)
    pkg = _package(doc)
    if pkg is not None:
        package_value = pkg.get("builder_decisions_required")
        if isinstance(package_value, int):
            values.append(package_value)
    return max(values) if values else None


def _class_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _same_class_contract(actual: Any, expected: Any) -> bool:
    actual_classes = _class_names(actual)
    expected_classes = _class_names(expected)
    return len(actual_classes) == len(expected_classes) and set(actual_classes) == set(expected_classes)


def _evaluate_architect_contract(doc: dict[str, Any]) -> list[ConstructabilityViolation]:
    violations: list[ConstructabilityViolation] = []
    pkg = _package(doc)
    if pkg is None:
        return violations

    contract = pkg.get("architect_contract")
    if not isinstance(contract, dict):
        return [
            _rule(
                "R22_ARCHITECT_CONTRACT_REQUIRED",
                "blocked",
                "Builder package requires architect_contract with canonical selected_candidate_id and approved_class_names.",
                "builder_executable_package.architect_contract",
            )
        ]

    review_candidate = _review(doc).get("selected_candidate_id")
    package_candidate = pkg.get("selected_candidate_id")
    contract_candidate = contract.get("selected_candidate_id")
    if package_candidate != contract_candidate or review_candidate != contract_candidate:
        violations.append(_rule("R23_ARCHITECT_CONTRACT_MISMATCH", "blocked", "selected_candidate_id must match architect_contract in review and package.", "builder_executable_package.selected_candidate_id"))

    if not _same_class_contract(pkg.get("approved_class_names"), contract.get("approved_class_names")):
        violations.append(_rule("R23_ARCHITECT_CONTRACT_MISMATCH", "blocked", "approved_class_names must match architect_contract exactly; Builder may not add or remove classes.", "builder_executable_package.approved_class_names"))

    return violations


def _evaluate_mode_contract(doc: dict[str, Any], mode: ValidationMode) -> list[ConstructabilityViolation]:
    violations: list[ConstructabilityViolation] = []
    review_status = _review_status(doc)
    package_present = _package(doc) is not None

    if mode not in VALIDATION_MODES:
        violations.append(_rule("R00_INVALID_VALIDATION_MODE", "blocked", f"Unsupported mode: {mode}."))
        return violations
    if mode == "report" and package_present:
        violations.append(_rule("R17_REPORT_MODE_MUST_NOT_EMIT_BUILDER_PACKAGE", "blocked", "report mode validates review output only; package must be absent."))
    if mode == "package" and not package_present:
        violations.append(_rule("R18_PACKAGE_MODE_REQUIRES_BUILDER_PACKAGE", "blocked", "package mode requires builder_executable_package."))
    if package_present and review_status in NON_EXECUTABLE_REVIEW_STATUSES:
        violations.append(_rule("R19_NON_EXECUTABLE_REVIEW_MUST_NOT_EMIT_BUILDER_PACKAGE", "blocked", "A non-executable review must not include a Builder package."))
    if mode == "package" and review_status != "executable_ready":
        violations.append(_rule("R20_PACKAGE_MODE_REQUIRES_EXECUTABLE_REVIEW", "blocked", "package mode requires constructability_status == executable_ready."))
    return violations


def evaluate_document(doc: dict[str, Any], *, mode: ValidationMode = "full") -> list[ConstructabilityViolation]:
    violations: list[ConstructabilityViolation] = []
    review = _review(doc)
    pkg = _package(doc)
    status = _status(doc)
    review_status = _review_status(doc)
    executable = status == "executable_ready"

    violations.extend(_evaluate_mode_contract(doc, mode))
    violations.extend(_evaluate_architect_contract(doc))

    builder_decisions_required = _builder_decisions_required(doc)
    if executable and builder_decisions_required != 0:
        violations.append(_rule("R01_BUILDER_DECISIONS_ZERO", "blocked", "executable_ready requires builder_decisions_required == 0."))
    if executable and _blocking_dependencies(doc):
        violations.append(_rule("R02_BLOCKING_DEPENDENCIES_EMPTY", "blocked", "executable_ready requires blocking_dependencies == []."))

    for index, node in enumerate(_nodes(doc)):
        location = f"reviewed_nodes[{index}]"
        node_status = node.get("node_status")
        node_claims_executable = executable or node_status == "executable_ready"
        interrogation = node.get("interrogation_result") or {}

        if node_claims_executable and _is_true(interrogation.get("geometry_required")) and not _is_true(interrogation.get("geometry_proven")):
            violations.append(_rule("R03_GEOMETRY_MUST_BE_PROVEN", "needs_user_evidence", "Geometry-dependent action lacks proven anchors, coordinates, or strategy.", location))
        if node_claims_executable and _is_true(interrogation.get("geometry_proven")) and not _has_object(interrogation.get("geometry_proof")):
            violations.append(_rule("R24_GEOMETRY_PROOF_OBJECT_REQUIRED", "blocked", "geometry_proven true requires geometry_proof object.", location))

        if node_claims_executable and _is_true(interrogation.get("asset_required")):
            has_asset = _is_true(interrogation.get("asset_source_present"))
            has_placeholder = _is_true(interrogation.get("placeholder_policy_present"))
            if not (has_asset or has_placeholder):
                violations.append(_rule("R04_ASSET_SOURCE_OR_PLACEHOLDER", "needs_user_evidence", "Asset action requires an asset source or explicit placeholder policy.", location))

        if node_claims_executable and _is_true(interrogation.get("overlay_strategy_required")) and not _is_true(interrogation.get("overlay_strategy_proven")):
            violations.append(_rule("R05_OVERLAY_STRATEGY_MUST_BE_PROVEN", "blocked", "Overlay action requires containment, positioning, and z-index strategy.", location))
        if node_claims_executable and _is_true(interrogation.get("overlay_strategy_proven")) and not _has_object(interrogation.get("overlay_strategy")):
            violations.append(_rule("R25_OVERLAY_STRATEGY_OBJECT_REQUIRED", "blocked", "overlay_strategy_proven true requires overlay_strategy object.", location))

        if node_claims_executable and _is_true(interrogation.get("action_targets_responsive")):
            responsive_behavior = interrogation.get("responsive_behavior", "unknown")
            if responsive_behavior not in RESPONSIVE_ALLOWED:
                violations.append(_rule("R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK", "needs_user_evidence", "Responsive action requires evidence-backed strategy or explicit block.", location))

        if node_claims_executable and _is_true(interrogation.get("interaction_implied")) and not _is_true(interrogation.get("interaction_approved")):
            violations.append(_rule("R07_INTERACTION_REQUIRES_APPROVAL", "needs_architect_amendment", "Interaction is implied but not approved by architecture.", location))

        if node_claims_executable and _is_true(interrogation.get("dynamic_loop_implied")) and not _is_true(interrogation.get("dynamic_loop_approved")):
            violations.append(_rule("R08_DYNAMIC_LOOP_REQUIRES_APPROVAL", "needs_architect_amendment", "Dynamic Loop or data binding is implied but not approved.", location))
        if node_claims_executable and _is_true(interrogation.get("dynamic_loop_approved")) and not _has_object(interrogation.get("dynamic_loop_binding_map")):
            violations.append(_rule("R26_DYNAMIC_LOOP_BINDING_MAP_REQUIRED", "blocked", "dynamic_loop_approved true requires dynamic_loop_binding_map object.", location))

        needs_structure_or_class_change = _is_true(interrogation.get("requires_structure_change")) or _is_true(interrogation.get("requires_class_change"))
        if node_claims_executable and needs_structure_or_class_change and not _is_true(interrogation.get("architect_decomposition_permission")):
            violations.append(_rule("R09_STRUCTURE_OR_CLASS_CHANGE_REQUIRES_PERMISSION", "needs_architect_amendment", "Structure or approved class names would change without Architect permission.", location))

        if node_claims_executable and _is_true(interrogation.get("exact_ui_control_path_used")) and not _is_true(interrogation.get("ui_control_evidence_present")):
            violations.append(_rule("R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE", "needs_user_evidence", "Exact Elementor UI path requires current UI or official-doc evidence.", location))
        if node_claims_executable and _is_true(interrogation.get("ui_control_evidence_present")) and not _has_object(interrogation.get("ui_control_evidence")):
            violations.append(_rule("R27_UI_CONTROL_EVIDENCE_OBJECT_REQUIRED", "blocked", "ui_control_evidence_present true requires ui_control_evidence object.", location))

        if node_claims_executable and _is_true(interrogation.get("accessibility_claimed")) and not _is_true(interrogation.get("accessibility_evidenced")):
            violations.append(_rule("R16_ACCESSIBILITY_CLAIM_REQUIRES_EVIDENCE", "blocked", "Accessibility claims require supporting evidence.", location))

        if executable and node_status in BLOCKING_NODE_STATUSES:
            violations.append(_rule("R14_BLOCKED_NODE_BLOCKS_EXECUTABLE_READY", node_status, "A blocked/evidence/amendment node prevents executable_ready.", location))

    if executable:
        confirmation = (pkg or {}).get("confirmation_request")
        first_batch = (pkg or {}).get("first_safe_builder_batch")
        if not isinstance(confirmation, dict) or not first_batch:
            violations.append(_rule("R11_EXECUTABLE_REQUIRES_CONFIRMATION_AND_BATCH", "blocked", "executable_ready requires confirmation_request and first_safe_builder_batch."))
        elif not all(key in confirmation for key in ("confirmation_id", "confirmed_action_ids", "expected_user_token")):
            violations.append(_rule("R11_EXECUTABLE_REQUIRES_STRUCTURED_CONFIRMATION", "blocked", "confirmation_request is missing required structured fields."))

        for field in ("selected_candidate_locked", "selected_candidate_id_unchanged", "approved_class_names_unchanged"):
            if not _is_true((pkg or review).get(field)):
                violations.append(_rule("R15_SELECTED_CANDIDATE_AND_CLASSES_LOCKED", "blocked", f"executable_ready requires {field}: true."))

    for qa_source in (doc, review, pkg or {}):
        qa_block = qa_source.get("qa_status")
        if not isinstance(qa_block, dict):
            continue
        if qa_block.get("production_ready") is True and not _is_true(qa_block.get("full_qa_evidence_present")):
            violations.append(_rule("R12_PRODUCTION_READY_REQUIRES_QA_EVIDENCE", "blocked", "production_ready true requires separate QA evidence."))
            break
        if qa_block.get("production_ready") is True and not _has_object(qa_block.get("qa_matrix")):
            violations.append(_rule("R28_QA_MATRIX_REQUIRED", "blocked", "production_ready true requires qa_matrix object."))
            break

    if review_status == "executable_with_logged_assumption":
        assumptions = review.get("logged_assumptions") or (pkg or {}).get("logged_assumptions") or []
        if not assumptions:
            violations.append(_rule("R13_LOGGED_ASSUMPTION_GATE", "blocked", "executable_with_logged_assumption requires at least one logged assumption."))
        for index, assumption in enumerate(assumptions):
            location = f"logged_assumptions[{index}]"
            invalid_assumption = (
                assumption.get("risk_level") != "low"
                or not _is_true(assumption.get("reversible"))
                or not _is_true(assumption.get("visible_in_output"))
                or _is_true(assumption.get("crosses_architecture_boundary"))
            )
            if invalid_assumption:
                violations.append(_rule("R13_LOGGED_ASSUMPTION_GATE", "blocked", "Logged assumption must be low-risk, reversible, visible, and boundary-safe.", location))

    return violations
