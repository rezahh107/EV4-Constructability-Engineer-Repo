from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from .action_contract_registry import ACTION_CONTRACTS
from .action_ir import ActionIRValidationError, normalize_action


class ActionEffectError(ValueError):
    """Raised when canonical Architect/action inputs cannot be evaluated."""


def _reviewed_by_id(review_draft: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["node_id"]): dict(item)
        for item in review_draft.get("reviewed_nodes") or []
        if isinstance(item, Mapping) and isinstance(item.get("node_id"), str)
    }


def _structure_nodes(source_bundle: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    payload = source_bundle.get("payload")
    model = payload.get("approved_structure_model") if isinstance(payload, Mapping) else None
    nodes = model.get("structure_nodes") if isinstance(model, Mapping) else None
    if not isinstance(nodes, list):
        raise ActionEffectError("Accepted Architect Build Tree is missing")
    result: dict[str, dict[str, Any]] = {}
    for raw in nodes:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("node_id"), str):
            raise ActionEffectError("Accepted Architect Build Tree contains an invalid node")
        node_id = str(raw["node_id"])
        if node_id in result:
            raise ActionEffectError(f"Duplicate accepted Build Tree node: {node_id}")
        result[node_id] = dict(raw)
    return result


def _approved_classes(architect_intake: Mapping[str, Any]) -> set[str]:
    intent = architect_intake.get("architect_intent_preserved")
    class_intent = intent.get("class_intent") if isinstance(intent, Mapping) else None
    values = (
        class_intent.get("approved_class_names")
        if isinstance(class_intent, Mapping)
        else []
    )
    return {str(item) for item in values or [] if isinstance(item, str)}


def _permissions(
    architect_intake: Mapping[str, Any], source_bundle: Mapping[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    bundle_payload = source_bundle.get("payload")
    for intent in (
        architect_intake.get("architect_intent_preserved"),
        bundle_payload.get("architect_intent")
        if isinstance(bundle_payload, Mapping)
        else None,
    ):
        if not isinstance(intent, Mapping):
            continue
        raw = intent.get("extension_permissions")
        if isinstance(raw, list):
            result.extend(dict(item) for item in raw if isinstance(item, Mapping))
    return result


def _permission_matches(
    permission: Mapping[str, Any],
    *,
    candidate_id: str | None,
    subject_ref: str,
    action_type: str,
    effect_kind: str,
    class_names: set[str],
    node_ids: set[str],
) -> bool:
    if permission.get("status") not in {"approved", "explicitly_approved", True}:
        return False
    if permission.get("selected_candidate_id") not in {None, candidate_id}:
        return False
    if permission.get("subject_ref") not in {None, subject_ref}:
        return False
    if permission.get("effect_kind") not in {None, effect_kind, "class_and_structure"}:
        return False
    allowed_actions = permission.get("allowed_action_types")
    if isinstance(allowed_actions, list) and action_type not in allowed_actions:
        return False
    allowed_classes = permission.get("allowed_class_names")
    if class_names and (
        not isinstance(allowed_classes, list)
        or not class_names.issubset({str(item) for item in allowed_classes})
    ):
        return False
    allowed_nodes = permission.get("allowed_node_ids")
    if node_ids and (
        not isinstance(allowed_nodes, list)
        or not node_ids.issubset({str(item) for item in allowed_nodes})
    ):
        return False
    return True


def _permission_granted(
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    *,
    subject_ref: str,
    action_type: str,
    effect_kind: str,
    class_names: set[str] | None = None,
    node_ids: set[str] | None = None,
) -> bool:
    selected = architect_intake.get("selected_architecture")
    candidate_id = (
        str(selected.get("selected_candidate_id"))
        if isinstance(selected, Mapping)
        and selected.get("selected_candidate_id") is not None
        else None
    )
    return any(
        _permission_matches(
            item,
            candidate_id=candidate_id,
            subject_ref=subject_ref,
            action_type=action_type,
            effect_kind=effect_kind,
            class_names=class_names or set(),
            node_ids=node_ids or set(),
        )
        for item in _permissions(architect_intake, source_bundle)
    )


def _class_effect(
    action_ir: Mapping[str, Any],
    approved: set[str],
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    parameters = dict(action_ir.get("normalized_parameters") or {})
    additions = {str(value) for value in parameters.get("class_names") or []}
    removals = {str(value) for value in parameters.get("remove_classes") or []}
    replacements = [
        {"from": str(item["from"]), "to": str(item["to"])}
        for item in parameters.get("replace_classes") or []
        if isinstance(item, Mapping)
    ]
    introduced = (additions - approved) | {
        item["to"] for item in replacements if item["to"] not in approved
    }
    removed_approved = (removals & approved) | {
        item["from"] for item in replacements if item["from"] in approved
    }
    class_set_changed = bool(introduced or removed_approved or replacements)
    permission_granted = (not class_set_changed) or _permission_granted(
        architect_intake,
        source_bundle,
        subject_ref=str(action_ir["target_node"]),
        action_type=str(action_ir["action_type"]),
        effect_kind="class",
        class_names=introduced | removed_approved,
    )
    diagnostics: list[dict[str, Any]] = []
    if introduced and not permission_granted:
        diagnostics.append(
            {
                "code": "CE_ACTION_EFFECT_UNAPPROVED_CLASS",
                "class_names": sorted(introduced),
            }
        )
    if removed_approved and not permission_granted:
        diagnostics.append(
            {
                "code": "CE_ACTION_EFFECT_APPROVED_CLASS_REMOVED_OR_REPLACED",
                "class_names": sorted(removed_approved),
            }
        )
    return {
        "kind": "class_effect",
        "applied_class_names": sorted(additions),
        "introduced_class_names": sorted(introduced),
        "removed_approved_class_names": sorted(removed_approved),
        "replacements": replacements,
        "changes_approved_class_set": class_set_changed,
        "permission_required": class_set_changed,
        "permission_granted": permission_granted,
        "preserves_approved_class_set": not class_set_changed,
        "diagnostics": diagnostics,
    }


def _structure_effect(
    action_ir: Mapping[str, Any],
    tree: Mapping[str, Mapping[str, Any]],
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    action_type = str(action_ir["action_type"])
    target = str(action_ir["target_node"])
    parameters = dict(action_ir.get("normalized_parameters") or {})
    diagnostics: list[dict[str, Any]] = []
    produced: set[str] = set()
    removed: set[str] = set()
    parent_changes: list[dict[str, Any]] = []
    identity_changes: list[dict[str, Any]] = []
    if target not in tree:
        diagnostics.append({"code": "CE_ACTION_EFFECT_TARGET_OUTSIDE_BUILD_TREE"})
    if action_type == "create_element":
        new_node = str(parameters["produced_node_id"])
        parent = str(parameters["parent_node_id"])
        produced.add(new_node)
        if new_node in tree:
            diagnostics.append({"code": "CE_ACTION_EFFECT_PRODUCED_NODE_ALREADY_EXISTS"})
        if parent not in tree:
            diagnostics.append({"code": "CE_ACTION_EFFECT_PARENT_OUTSIDE_BUILD_TREE"})
        else:
            parent_changes.append(
                {"node_id": new_node, "from_parent": None, "to_parent": parent}
            )
    elif action_type in {"remove_element", "delete_element"}:
        removed.add(target)
    elif action_type in {"reparent_element", "move_element"}:
        new_parent = str(parameters["new_parent_node_id"])
        old_parent = tree.get(target, {}).get("parent_node_id")
        if new_parent not in tree:
            diagnostics.append({"code": "CE_ACTION_EFFECT_NEW_PARENT_OUTSIDE_BUILD_TREE"})
        else:
            parent_changes.append(
                {
                    "node_id": target,
                    "from_parent": old_parent,
                    "to_parent": new_parent,
                }
            )
    elif action_type == "replace_element":
        replacement = str(parameters["replacement_node_id"])
        removed.add(target)
        produced.add(replacement)
        identity_changes.append({"from": target, "to": replacement})
    elif action_type == "rename_node":
        identity_changes.append({"from": target, "to": str(parameters["new_node_id"])})
    changed_nodes = (
        produced
        | removed
        | {str(item["node_id"]) for item in parent_changes}
        | {str(item["from"]) for item in identity_changes}
        | {str(item["to"]) for item in identity_changes}
    )
    permission_granted = _permission_granted(
        architect_intake,
        source_bundle,
        subject_ref=target,
        action_type=action_type,
        effect_kind="structure",
        node_ids=changed_nodes,
    )
    if not permission_granted:
        diagnostics.append(
            {
                "code": "CE_ACTION_EFFECT_STRUCTURE_PERMISSION_REQUIRED",
                "node_ids": sorted(changed_nodes),
            }
        )
    return {
        "kind": "structure_effect",
        "produced_node_ids": sorted(produced),
        "removed_node_ids": sorted(removed),
        "parent_changes": parent_changes,
        "identity_changes": identity_changes,
        "changes_build_tree": True,
        "permission_required": True,
        "permission_granted": permission_granted,
        "preserves_build_tree": False,
        "diagnostics": diagnostics,
    }


def _forbidden_conflicts(
    action_type: str,
    *,
    class_changed: bool,
    structure_changed: bool,
    forbidden_work: Sequence[str],
) -> list[str]:
    conflicts: list[str] = []
    for item in forbidden_work:
        normalized = str(item).casefold()
        conflict = False
        if class_changed and ("class" in normalized or "redesign" in normalized):
            conflict = True
        if structure_changed and any(
            token in normalized
            for token in (
                "structure",
                "build_tree",
                "build tree",
                "redesign",
                "identity",
            )
        ):
            conflict = True
        if (
            structure_changed
            and action_type == "create_element"
            and "invent_geometry" in normalized
        ):
            conflict = True
        if action_type == "attach_asset" and "asset" in normalized:
            conflict = True
        if action_type == "set_responsive" and "breakpoint" in normalized:
            conflict = True
        if action_type == "bind_dynamic_loop" and "dynamic" in normalized:
            conflict = True
        if conflict:
            conflicts.append(str(item))
    return sorted(set(conflicts))


def derive_action_effects(
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
) -> dict[str, Any]:
    tree = _structure_nodes(source_bundle)
    approved = _approved_classes(architect_intake)
    reviewed = _reviewed_by_id(review_draft)
    forbidden_work = [str(item) for item in architect_intake.get("forbidden_work") or []]
    actions = review_draft.get("builder_action_proposals")
    actions = actions if isinstance(actions, list) else []
    records: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for index, raw in enumerate(actions):
        if not isinstance(raw, Mapping):
            diagnostics.append({"code": "CE_ACTION_EFFECT_ACTION_INVALID"})
            continue
        try:
            action_ir = normalize_action(raw, index)
        except ActionIRValidationError as exc:
            action_id = str(raw.get("action_id") or f"action-{index + 1}")
            diagnostic = {
                "code": "CE_ACTION_EFFECT_PARAMETERS_INVALID",
                "message": str(exc),
                "action_id": action_id,
                "action_type": str(raw.get("action_type") or "unknown"),
                "target_node": str(raw.get("target_node") or "unknown"),
            }
            diagnostics.append(diagnostic)
            records.append(
                {
                    "action_id": action_id,
                    "action_type": diagnostic["action_type"],
                    "target_node": diagnostic["target_node"],
                    "action_ir": None,
                    "class_effect": None,
                    "structure_effect": None,
                    "forbidden_work_conflicts": [],
                    "diagnostics": [diagnostic],
                    "changes_class_assignment": False,
                    "changes_approved_class_set": False,
                    "changes_structure": False,
                    "preserves_approved_class_set": False,
                    "preserves_build_tree": False,
                    "blocked": True,
                }
            )
            continue
        action_id = action_ir["action_id"]
        action_type = action_ir["action_type"]
        target = action_ir["target_node"]
        contract = ACTION_CONTRACTS[action_type]
        record: dict[str, Any] = {
            "action_id": action_id,
            "action_type": action_type,
            "target_node": target,
            "action_ir": action_ir,
            "draft_disclosure": {
                "requires_class_change": bool(
                    reviewed.get(target, {}).get("requires_class_change", False)
                ),
                "requires_structure_change": bool(
                    reviewed.get(target, {}).get("requires_structure_change", False)
                ),
                "architect_decomposition_permission": bool(
                    reviewed.get(target, {}).get(
                        "architect_decomposition_permission", False
                    )
                ),
            },
            "class_effect": None,
            "structure_effect": None,
            "forbidden_work_conflicts": [],
            "diagnostics": [],
        }
        if contract["derived_class_effects"]:
            record["class_effect"] = _class_effect(
                action_ir, approved, architect_intake, source_bundle
            )
        if contract["derived_structure_effects"]:
            record["structure_effect"] = _structure_effect(
                action_ir, tree, architect_intake, source_bundle
            )
        if action_ir["decision_state"] != "resolved":
            record["diagnostics"].append(
                {
                    "code": "CE_ACTION_EFFECT_HIDDEN_BUILDER_DECISION",
                    "paths": list(action_ir.get("hidden_decision_paths") or []),
                }
            )
        class_effect = record.get("class_effect") or {}
        structure_effect = record.get("structure_effect") or {}
        class_changed = bool(class_effect.get("changes_approved_class_set"))
        structure_changed = bool(structure_effect.get("changes_build_tree"))
        conflicts = _forbidden_conflicts(
            action_type,
            class_changed=class_changed,
            structure_changed=structure_changed,
            forbidden_work=forbidden_work,
        )
        record["forbidden_work_conflicts"] = conflicts
        if conflicts:
            record["diagnostics"].append(
                {
                    "code": "CE_ACTION_EFFECT_FORBIDDEN_WORK_CONFLICT",
                    "forbidden_work": conflicts,
                }
            )
        for effect in (class_effect, structure_effect):
            for diagnostic in effect.get("diagnostics") or []:
                record["diagnostics"].append(dict(diagnostic))
        record["changes_class_assignment"] = bool(record.get("class_effect"))
        record["changes_approved_class_set"] = class_changed
        record["changes_structure"] = structure_changed
        record["preserves_approved_class_set"] = not class_changed
        record["preserves_build_tree"] = not structure_changed
        record["blocked"] = bool(record["diagnostics"])
        records.append(record)
        for diagnostic in record["diagnostics"]:
            diagnostics.append(
                {
                    **dict(diagnostic),
                    "action_id": action_id,
                    "action_type": action_type,
                    "target_node": target,
                }
            )
    records.sort(key=lambda item: str(item["action_id"]))
    diagnostics.sort(
        key=lambda item: (str(item.get("action_id")), str(item.get("code")))
    )
    return {
        "result_kind": "builder_action_effects",
        "records": records,
        "diagnostics": diagnostics,
        "complete": not diagnostics,
    }


__all__ = ["ActionEffectError", "derive_action_effects"]
