from __future__ import annotations

from typing import Any

from .exceptions import ConstructabilityViolation

BLOCKING_NODE_STATUSES = {"blocked", "needs_user_evidence", "needs_architect_amendment"}
RESPONSIVE_ALLOWED = {"blocked", "evidence_backed", "not_applicable"}


def _is_true(value: Any) -> bool:
    return value is True


def _rule(rule_id: str, status: str, message: str, location: str = "document") -> ConstructabilityViolation:
    return ConstructabilityViolation(rule_id=rule_id, status=status, message=message, location=location)


def _review(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("constructability_review") or doc


def _package(doc: dict[str, Any]) -> dict[str, Any] | None:
    return doc.get("builder_executable_package")


def _nodes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return list((_review(doc).get("reviewed_nodes") or []))


def _status(doc: dict[str, Any]) -> str | None:
    pkg = _package(doc)
    if pkg:
        return pkg.get("builder_package_status")
    return _review(doc).get("constructability_status")


def _blocking_dependencies(doc: dict[str, Any]) -> list[Any]:
    pkg = _package(doc)
    if pkg is not None:
        return list(pkg.get("blocking_dependencies") or [])
    return list(_review(doc).get("blocking_dependencies") or [])


def evaluate_document(doc: dict[str, Any]) -> list[ConstructabilityViolation]:
    """Return fail-closed violations for a constructability fixture or package.

    The engine intentionally uses redundant gates. A package must satisfy schema-level
    structure and rule-level execution proof. Architect silence is never treated as proof.
    """

    violations: list[ConstructabilityViolation] = []
    review = _review(doc)
    pkg = _package(doc)
    status = _status(doc)
    executable = status == "executable_ready"

    builder_decisions_required = (
        pkg.get("builder_decisions_required") if pkg is not None else review.get("builder_decisions_required")
    )
    if executable and builder_decisions_required != 0:
        violations.append(
            _rule(
                "R01_BUILDER_DECISIONS_ZERO",
                "blocked",
                "executable_ready requires builder_decisions_required == 0.",
            )
        )

    if executable and _blocking_dependencies(doc):
        violations.append(
            _rule(
                "R02_BLOCKING_DEPENDENCIES_EMPTY",
                "blocked",
                "executable_ready requires blocking_dependencies == [].",
            )
        )

    for index, node in enumerate(_nodes(doc)):
        location = f"reviewed_nodes[{index}]"
        interrogation = node.get("interrogation_result") or {}

        if _is_true(interrogation.get("geometry_required")) and not _is_true(
            interrogation.get("geometry_proven")
        ):
            violations.append(
                _rule(
                    "R03_GEOMETRY_MUST_BE_PROVEN",
                    "needs_user_evidence",
                    "Geometry-dependent action lacks proven anchors, coordinates, or strategy.",
                    location,
                )
            )

        if _is_true(interrogation.get("asset_required")):
            has_asset = _is_true(interrogation.get("asset_source_present"))
            has_placeholder = _is_true(interrogation.get("placeholder_policy_present"))
            if not (has_asset or has_placeholder):
                violations.append(
                    _rule(
                        "R04_ASSET_SOURCE_OR_PLACEHOLDER",
                        "needs_user_evidence",
                        "Asset action requires an asset source or explicit placeholder policy.",
                        location,
                    )
                )

        if _is_true(interrogation.get("overlay_strategy_required")) and not _is_true(
            interrogation.get("overlay_strategy_proven")
        ):
            violations.append(
                _rule(
                    "R05_OVERLAY_STRATEGY_MUST_BE_PROVEN",
                    "blocked",
                    "Overlay action requires containment, positioning, and z-index strategy.",
                    location,
                )
            )

        if _is_true(interrogation.get("action_targets_responsive")):
            responsive_behavior = interrogation.get("responsive_behavior", "unknown")
            if responsive_behavior not in RESPONSIVE_ALLOWED:
                violations.append(
                    _rule(
                        "R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK",
                        "needs_user_evidence",
                        "Responsive action requires evidence-backed strategy or explicit block.",
                        location,
                    )
                )

        if _is_true(interrogation.get("interaction_implied")) and not _is_true(
            interrogation.get("interaction_approved")
        ):
            violations.append(
                _rule(
                    "R07_INTERACTION_REQUIRES_APPROVAL",
                    "needs_architect_amendment",
                    "Interaction is implied but not approved by architecture.",
                    location,
                )
            )

        if _is_true(interrogation.get("dynamic_loop_implied")) and not _is_true(
            interrogation.get("dynamic_loop_approved")
        ):
            violations.append(
                _rule(
                    "R08_DYNAMIC_LOOP_REQUIRES_APPROVAL",
                    "needs_architect_amendment",
                    "Dynamic Loop or data binding is implied but not approved.",
                    location,
                )
            )

        needs_structure_or_class_change = _is_true(
            interrogation.get("requires_structure_change")
        ) or _is_true(interrogation.get("requires_class_change"))
        if needs_structure_or_class_change and not _is_true(
            interrogation.get("architect_decomposition_permission")
        ):
            violations.append(
                _rule(
                    "R09_STRUCTURE_OR_CLASS_CHANGE_REQUIRES_PERMISSION",
                    "needs_architect_amendment",
                    "Structure or approved class names would change without Architect permission.",
                    location,
                )
            )

        if _is_true(interrogation.get("exact_ui_control_path_used")) and not _is_true(
            interrogation.get("ui_control_evidence_present")
        ):
            violations.append(
                _rule(
                    "R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE",
                    "needs_user_evidence",
                    "Exact Elementor UI path requires current UI, user, version, or official-doc evidence.",
                    location,
                )
            )

        node_status = node.get("node_status")
        if executable and node_status in BLOCKING_NODE_STATUSES:
            violations.append(
                _rule(
                    "R14_BLOCKED_NODE_BLOCKS_EXECUTABLE_READY",
                    node_status,
                    "A blocked/evidence/amendment node prevents executable_ready.",
                    location,
                )
            )

    if executable:
        confirmation = (pkg or {}).get("confirmation_request")
        first_batch = (pkg or {}).get("first_safe_builder_batch")
        if not isinstance(confirmation, dict) or not first_batch:
            violations.append(
                _rule(
                    "R11_EXECUTABLE_REQUIRES_CONFIRMATION_AND_BATCH",
                    "blocked",
                    "executable_ready requires structured confirmation_request and first_safe_builder_batch.",
                )
            )
        elif not all(
            key in confirmation
            for key in ("confirmation_id", "confirmed_action_ids", "expected_user_token")
        ):
            violations.append(
                _rule(
                    "R11_EXECUTABLE_REQUIRES_STRUCTURED_CONFIRMATION",
                    "blocked",
                    "confirmation_request must include confirmation_id, confirmed_action_ids, expected_user_token.",
                )
            )

        for field in (
            "selected_candidate_locked",
            "selected_candidate_id_unchanged",
            "approved_class_names_unchanged",
        ):
            if not _is_true((pkg or review).get(field)):
                violations.append(
                    _rule(
                        "R15_SELECTED_CANDIDATE_AND_CLASSES_LOCKED",
                        "blocked",
                        f"executable_ready requires {field}: true.",
                    )
                )

    qa = doc.get("qa_status") or review.get("qa_status") or (pkg or {}).get("qa_status") or {}
    if qa.get("production_ready") is True and not _is_true(qa.get("full_qa_evidence_present")):
        violations.append(
            _rule(
                "R12_PRODUCTION_READY_REQUIRES_QA_EVIDENCE",
                "blocked",
                "production_ready true requires separate frontend/responsive/accessibility/browser/export QA evidence.",
            )
        )

    if status == "executable_with_logged_assumption":
        assumptions = review.get("logged_assumptions") or (pkg or {}).get("logged_assumptions") or []
        if not assumptions:
            violations.append(
                _rule(
                    "R13_LOGGED_ASSUMPTION_GATE",
                    "blocked",
                    "executable_with_logged_assumption requires at least one logged assumption.",
                )
            )
        for index, assumption in enumerate(assumptions):
            location = f"logged_assumptions[{index}]"
            if assumption.get("risk_level") != "low" or not _is_true(
                assumption.get("reversible")
            ) or not _is_true(assumption.get("visible_in_output")) or _is_true(
                assumption.get("crosses_architecture_boundary")
            ):
                violations.append(
                    _rule(
                        "R13_LOGGED_ASSUMPTION_GATE",
                        "blocked",
                        "Logged assumption must be low-risk, reversible, visible, and boundary-safe.",
                        location,
                    )
                )

    return violations
