from __future__ import annotations

import copy
from collections import Counter, defaultdict
from typing import Any, Mapping

from .action_effects import ActionEffectError, derive_action_effects
from .claim_policy_registry import (
    CLAIM_POLICIES,
    PROPOSED_ACTION_HINTS,
    derive_action_claims,
)


class ObligationDerivationError(ValueError):
    """Raised when canonical inputs cannot produce a complete obligation matrix."""


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _structure_nodes(
    intake: Mapping[str, Any], source_bundle: Mapping[str, Any]
) -> list[dict[str, Any]]:
    intake_projection = _as_dict(intake.get("structure_projection"))
    intake_nodes = intake_projection.get("nodes")
    bundle_payload = _as_dict(source_bundle.get("payload"))
    approved = _as_dict(bundle_payload.get("approved_structure_model"))
    bundle_nodes = approved.get("structure_nodes")
    if not isinstance(intake_nodes, list) or not isinstance(bundle_nodes, list):
        raise ObligationDerivationError("Canonical Architect structure nodes are missing")

    normalized_intake: dict[str, dict[str, Any]] = {}
    for item in intake_nodes:
        if not isinstance(item, Mapping):
            raise ObligationDerivationError(
                "Architect intake contains an invalid structure node"
            )
        node_id = item.get("source_node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ObligationDerivationError(
                "Architect intake structure node has no source_node_id"
            )
        if node_id in normalized_intake:
            raise ObligationDerivationError(
                f"Duplicate Architect intake node: {node_id}"
            )
        normalized_intake[node_id] = dict(item)

    normalized_bundle: dict[str, dict[str, Any]] = {}
    for item in bundle_nodes:
        if not isinstance(item, Mapping):
            raise ObligationDerivationError(
                "Architect source bundle contains an invalid structure node"
            )
        node_id = item.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ObligationDerivationError(
                "Architect source bundle structure node has no node_id"
            )
        if node_id in normalized_bundle:
            raise ObligationDerivationError(
                f"Duplicate Architect source node: {node_id}"
            )
        normalized_bundle[node_id] = dict(item)

    if set(normalized_intake) != set(normalized_bundle):
        raise ObligationDerivationError(
            "Architect intake and source bundle structure identities differ"
        )

    result: list[dict[str, Any]] = []
    for node_id in sorted(normalized_intake):
        intake_node = normalized_intake[node_id]
        source_node = normalized_bundle[node_id]
        if (
            intake_node.get("parent_node_id") != source_node.get("parent_node_id")
            or list(intake_node.get("children") or [])
            != list(source_node.get("children") or [])
            or intake_node.get("node_kind") != source_node.get("node_kind")
        ):
            raise ObligationDerivationError(
                f"Architect node identity differs for {node_id}"
            )
        result.append(
            {
                "node_id": node_id,
                "node_kind": str(
                    source_node.get("node_kind") or "implementation_node"
                ),
                "parent_node_id": source_node.get("parent_node_id"),
                "children": list(source_node.get("children") or []),
                "evidence_refs": sorted(
                    str(value) for value in source_node.get("evidence_refs") or []
                ),
            }
        )
    return result


def _requested_claims(node: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    raw = node.get("requested_claims")
    if not isinstance(raw, list):
        return result
    for item in raw:
        if isinstance(item, str):
            result.add(item)
        elif isinstance(item, Mapping) and isinstance(item.get("claim_id"), str):
            result.add(str(item["claim_id"]))
    unknown = sorted(result - set(CLAIM_POLICIES))
    if unknown:
        raise ObligationDerivationError(
            f"Unknown requested claims: {', '.join(unknown)}"
        )
    return result


def _hint_claims(proposed_action: str) -> set[str]:
    lowered = proposed_action.casefold()
    claims: set[str] = set()
    for token, token_claims in PROPOSED_ACTION_HINTS:
        if token in lowered:
            claims.update(token_claims)
    return claims


def _action_map(draft: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actions = draft.get("builder_action_proposals")
    if not isinstance(actions, list):
        return result
    action_ids: set[str] = set()
    for item in actions:
        if not isinstance(item, Mapping):
            raise ObligationDerivationError("Builder action must be an object")
        action_id = item.get("action_id")
        action_type = item.get("action_type")
        target = item.get("target_node")
        if not all(
            isinstance(value, str) and value
            for value in (action_id, action_type, target)
        ):
            raise ObligationDerivationError("Builder action identity is incomplete")
        if action_id in action_ids:
            raise ObligationDerivationError(f"Duplicate Builder action: {action_id}")
        action_ids.add(action_id)
        result[target].append(copy.deepcopy(dict(item)))
    return result


def derive_review_obligations(
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    claim_policy_registry: Mapping[str, Mapping[str, Any]] = CLAIM_POLICIES,
) -> dict[str, Any]:
    """Derive complete review obligations and Builder-action effects."""
    required_nodes = _structure_nodes(architect_intake, source_bundle)
    required_ids = [item["node_id"] for item in required_nodes]
    required_set = set(required_ids)

    raw_reviewed = review_draft.get("reviewed_nodes")
    if not isinstance(raw_reviewed, list):
        raw_reviewed = []
    reviewed = [dict(item) for item in raw_reviewed if isinstance(item, Mapping)]
    reviewed_ids = [
        str(item.get("node_id"))
        for item in reviewed
        if isinstance(item.get("node_id"), str)
    ]
    counts = Counter(reviewed_ids)
    duplicate_nodes = sorted(
        node_id for node_id, count in counts.items() if count > 1
    )
    missing_nodes = sorted(required_set - set(reviewed_ids))
    orphan_nodes = sorted(set(reviewed_ids) - required_set)

    actions_by_node = _action_map(review_draft)
    unknown_action_targets = sorted(set(actions_by_node) - required_set)
    diagnostics: list[dict[str, Any]] = []
    for node_id in missing_nodes:
        diagnostics.append(
            {"code": "CE_OBLIGATION_REQUIRED_NODE_MISSING", "node_id": node_id}
        )
    for node_id in orphan_nodes:
        diagnostics.append(
            {"code": "CE_OBLIGATION_ORPHAN_DRAFT_NODE", "node_id": node_id}
        )
    for node_id in duplicate_nodes:
        diagnostics.append(
            {"code": "CE_OBLIGATION_DUPLICATE_REVIEW_UNIT", "node_id": node_id}
        )
    for node_id in unknown_action_targets:
        diagnostics.append(
            {"code": "CE_OBLIGATION_UNKNOWN_ACTION_TARGET", "node_id": node_id}
        )

    try:
        action_effects = derive_action_effects(
            architect_intake, source_bundle, review_draft
        )
    except ActionEffectError as exc:
        action_effects = {
            "result_kind": "builder_action_effects",
            "records": [],
            "diagnostics": [
                {
                    "code": "CE_ACTION_EFFECT_DERIVATION_FAILED",
                    "message": str(exc),
                }
            ],
            "complete": False,
        }
    diagnostics.extend(copy.deepcopy(action_effects["diagnostics"]))
    effects_by_action = {
        str(item.get("action_id")): item
        for item in action_effects.get("records") or []
        if isinstance(item, Mapping)
    }

    reviewed_by_id = {
        str(item.get("node_id")): item
        for item in reviewed
        if isinstance(item.get("node_id"), str)
    }
    required_claims_by_node: dict[str, list[str]] = {}
    requested_claims_by_node: dict[str, list[str]] = {}
    applicable_rules_by_node: dict[str, list[str]] = {}
    action_types_by_node: dict[str, list[str]] = {}
    explicit_no_claim_nodes: list[str] = []

    for node in required_nodes:
        node_id = node["node_id"]
        draft_node = reviewed_by_id.get(node_id, {})
        mandatory: set[str] = set()
        action_types: list[str] = []
        actions = actions_by_node.get(node_id, [])
        for action in actions:
            action_type = str(action["action_type"])
            action_types.append(action_type)
            derived = derive_action_claims(action_type)
            if derived is None:
                diagnostics.append(
                    {
                        "code": "CE_OBLIGATION_UNKNOWN_ACTION_TYPE",
                        "node_id": node_id,
                        "action_type": action_type,
                    }
                )
                continue
            mandatory.update(derived)
            effect = effects_by_action.get(str(action["action_id"]), {})
            if effect.get("changes_class_assignment") or effect.get(
                "changes_structure"
            ):
                mandatory.add("geometry")
        proposed_action = str(draft_node.get("proposed_action") or "")
        mandatory.update(_hint_claims(proposed_action))
        # Draft flags are additive disclosures only; they cannot suppress action-derived effects.
        if (
            draft_node.get("requires_class_change") is True
            or draft_node.get("requires_structure_change") is True
        ):
            mandatory.add("geometry")
        requested = _requested_claims(draft_node)
        all_claims = mandatory | requested

        explicit_no_claim = bool(actions) and all(
            derive_action_claims(str(action["action_type"])) == ()
            and not effects_by_action.get(str(action["action_id"]), {}).get(
                "changes_class_assignment"
            )
            and not effects_by_action.get(str(action["action_id"]), {}).get(
                "changes_structure"
            )
            for action in actions
        )
        if not actions:
            diagnostics.append(
                {"code": "CE_OBLIGATION_NODE_HAS_NO_BUILDER_ACTION", "node_id": node_id}
            )
        elif not all_claims and explicit_no_claim:
            explicit_no_claim_nodes.append(node_id)
        elif not all_claims:
            diagnostics.append(
                {"code": "CE_OBLIGATION_EMPTY_CLAIM_SET_UNPROVEN", "node_id": node_id}
            )

        omitted = sorted(mandatory - requested)
        if omitted:
            diagnostics.append(
                {
                    "code": "CE_OBLIGATION_DRAFT_OMITTED_MANDATORY_CLAIMS",
                    "node_id": node_id,
                    "claims": omitted,
                    "blocking": False,
                }
            )
        required_claims_by_node[node_id] = sorted(all_claims)
        requested_claims_by_node[node_id] = sorted(requested)
        applicable_rules_by_node[node_id] = sorted(
            str(claim_policy_registry[claim]["applicable_rule"])
            for claim in all_claims
        )
        action_types_by_node[node_id] = sorted(action_types)

    blocking_codes = {
        "CE_OBLIGATION_REQUIRED_NODE_MISSING",
        "CE_OBLIGATION_ORPHAN_DRAFT_NODE",
        "CE_OBLIGATION_DUPLICATE_REVIEW_UNIT",
        "CE_OBLIGATION_UNKNOWN_ACTION_TARGET",
        "CE_OBLIGATION_UNKNOWN_ACTION_TYPE",
        "CE_OBLIGATION_NODE_HAS_NO_BUILDER_ACTION",
        "CE_OBLIGATION_EMPTY_CLAIM_SET_UNPROVEN",
        "CE_ACTION_EFFECT_DERIVATION_FAILED",
        "CE_ACTION_EFFECT_ACTION_INVALID",
        "CE_ACTION_EFFECT_ACTION_IDENTITY_INCOMPLETE",
        "CE_ACTION_EFFECT_UNAPPROVED_CLASS",
        "CE_ACTION_EFFECT_APPROVED_CLASS_REMOVED_OR_REPLACED",
        "CE_ACTION_EFFECT_CLASS_PARAMETERS_MISSING",
        "CE_ACTION_EFFECT_STRUCTURE_PERMISSION_REQUIRED",
        "CE_ACTION_EFFECT_PRODUCED_NODE_ID_REQUIRED",
        "CE_ACTION_EFFECT_PRODUCED_NODE_ALREADY_EXISTS",
        "CE_ACTION_EFFECT_PARENT_OUTSIDE_BUILD_TREE",
        "CE_ACTION_EFFECT_NEW_PARENT_OUTSIDE_BUILD_TREE",
        "CE_ACTION_EFFECT_REPLACEMENT_NODE_ID_REQUIRED",
        "CE_ACTION_EFFECT_NEW_NODE_ID_REQUIRED",
        "CE_ACTION_EFFECT_TARGET_OUTSIDE_BUILD_TREE",
        "CE_ACTION_EFFECT_FORBIDDEN_WORK_CONFLICT",
        "CE_ACTION_EFFECT_PARAMETERS_INVALID",
    }
    complete = not any(item.get("code") in blocking_codes for item in diagnostics)
    required_permissions = sorted(
        str(item.get("action_id"))
        for item in action_effects.get("records") or []
        if isinstance(item, Mapping)
        and any(
            isinstance(effect, Mapping)
            and effect.get("permission_required") is True
            and effect.get("permission_granted") is not True
            for effect in (item.get("class_effect"), item.get("structure_effect"))
        )
    )
    return {
        "required_architect_nodes": required_nodes,
        "required_review_units": [f"ce-unit-{node_id}" for node_id in required_ids],
        "required_claims_by_node": required_claims_by_node,
        "requested_claims_by_node": requested_claims_by_node,
        "applicable_rules_by_node": applicable_rules_by_node,
        "action_types_by_node": action_types_by_node,
        "action_effects": copy.deepcopy(action_effects),
        "required_strategy_coverage": required_ids,
        "required_builder_decision_checks": sorted(
            str(action["action_id"])
            for actions in actions_by_node.values()
            for action in actions
        ),
        "required_architect_permissions": required_permissions,
        "explicit_no_claim_nodes": sorted(explicit_no_claim_nodes),
        "missing_nodes": missing_nodes,
        "orphan_nodes": orphan_nodes,
        "duplicate_nodes": duplicate_nodes,
        "unknown_action_targets": unknown_action_targets,
        "diagnostics": diagnostics,
        "complete": complete,
    }
