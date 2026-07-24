from __future__ import annotations

import copy
import json
from typing import Any, Mapping, Sequence

from .action_contract_registry import ACTION_CONTRACTS, effect_parameter_keys


class ActionIRValidationError(ValueError):
    """Raised when a Builder proposal cannot be normalized without ambiguity."""


_DECISION_TOKENS = {
    "tbd",
    "todo",
    "choose",
    "select",
    "decide",
    "unknown",
    "either",
    "or",
}


def _canonical(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


def _hidden_decisions(value: Any, path: str) -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            lowered = str(key).casefold()
            if lowered in {"requires_decision", "decision_required"} and child is True:
                findings.append(child_path)
            if lowered.endswith("_options") and isinstance(child, list) and len(child) > 1:
                findings.append(child_path)
            findings.extend(_hidden_decisions(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_hidden_decisions(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        normalized = value.casefold().strip()
        if (
            normalized in _DECISION_TOKENS
            or normalized.startswith("choose ")
            or " tbd" in f" {normalized}"
        ):
            findings.append(path)
    return findings


def _list_of_strings(value: Any, key: str) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result = [str(item) for item in value if isinstance(item, str) and item]
        if len(result) != len(value):
            raise ActionIRValidationError(f"{key} must contain only non-empty strings")
        return sorted(set(result))
    raise ActionIRValidationError(f"{key} must be a non-empty string or string array")


def _replacement_list(value: Any) -> list[dict[str, str]]:
    raw_items = value if isinstance(value, list) else [value]
    result: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, Mapping):
            raise ActionIRValidationError("class replacement must be an object or object array")
        old = item.get("from") or item.get("old")
        new = item.get("to") or item.get("new")
        if not all(isinstance(part, str) and part for part in (old, new)):
            raise ActionIRValidationError("class replacement requires non-empty from/to values")
        result.append({"from": str(old), "to": str(new)})
    return sorted(result, key=lambda item: (item["from"], item["to"]))


def _normalize_value(action_type: str, key: str, value: Any) -> Any:
    if key in {"class_names", "remove_classes"}:
        return _list_of_strings(value, key)
    if key == "replace_classes":
        return _replacement_list(value)
    if key in {"properties", "binding_map"}:
        if not isinstance(value, Mapping) or not value:
            raise ActionIRValidationError(f"{key} must be a non-empty object")
        return _canonical(dict(value))
    if key == "viewports":
        return _list_of_strings(value, key)
    if isinstance(value, (Mapping, list)):
        return _canonical(value)
    if value is None or value == "":
        raise ActionIRValidationError(f"{key} must not be empty")
    return value


def _normalized_parameters(action_type: str, parameters: Mapping[str, Any]) -> dict[str, Any]:
    contract = ACTION_CONTRACTS[action_type]
    aliases = dict(contract["aliases"])
    allowed = set(contract["required_parameter_keys"]) | set(contract["optional_parameter_keys"])
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in parameters.items():
        key = str(raw_key)
        canonical_key = aliases.get(key, key)
        if key in aliases and canonical_key in parameters:
            raise ActionIRValidationError(
                f"Ambiguous parameter alias: both {key!r} and {canonical_key!r} are present"
            )
        if (
            key in {"requires_decision", "decision_required"}
            or key.casefold().endswith("_options")
        ):
            continue
        if canonical_key not in allowed:
            if key in effect_parameter_keys():
                raise ActionIRValidationError(
                    f"Effect-bearing parameter {key!r} is forbidden for {action_type}"
                )
            raise ActionIRValidationError(f"Unknown parameter {key!r} for {action_type}")
        if canonical_key in normalized:
            raise ActionIRValidationError(f"Conflicting parameter aliases for {canonical_key}")
        normalized[canonical_key] = _normalize_value(action_type, canonical_key, raw_value)

    missing = [key for key in contract["required_parameter_keys"] if key not in normalized]
    if missing:
        raise ActionIRValidationError(
            f"Action {action_type} is missing required parameters: {', '.join(missing)}"
        )
    if action_type == "apply_class" and not normalized:
        raise ActionIRValidationError(
            "apply_class requires a class assignment or class-set mutation"
        )
    if action_type == "apply_class" and "replace_classes" in normalized:
        sources = [item["from"] for item in normalized["replace_classes"]]
        targets = [item["to"] for item in normalized["replace_classes"]]
        if len(sources) != len(set(sources)) or len(targets) != len(set(targets)):
            raise ActionIRValidationError("Conflicting class replacement combination")
    return _canonical(normalized)


def normalize_action(action: Mapping[str, Any], index: int = 0) -> dict[str, Any]:
    if not isinstance(action, Mapping):
        raise ActionIRValidationError("Builder action must be an object")

    is_ir = "normalized_parameters" in action and "parameters" not in action
    allowed_top = {
        "action_id",
        "action_type",
        "target_node",
        "normalized_parameters" if is_ir else "parameters",
        "derived_effects",
        "required_claims",
        "required_permissions",
        "decision_state",
        "hidden_decision_paths",
        "source_draft_path",
    }
    unknown_top = sorted(str(key) for key in action if key not in allowed_top)
    if unknown_top:
        raise ActionIRValidationError("Unknown action fields: " + ", ".join(unknown_top))

    action_id = action.get("action_id")
    action_type = action.get("action_type")
    target_node = action.get("target_node")
    if not all(
        isinstance(value, str) and value
        for value in (action_id, action_type, target_node)
    ):
        raise ActionIRValidationError("Action identity is incomplete")
    if action_type not in ACTION_CONTRACTS:
        raise ActionIRValidationError(f"Unknown action type: {action_type}")

    raw_parameters = action.get("normalized_parameters" if is_ir else "parameters", {})
    if not isinstance(raw_parameters, Mapping):
        raise ActionIRValidationError("Action parameters must be an object")
    parameters = _normalized_parameters(str(action_type), raw_parameters)
    hidden = _hidden_decisions(
        raw_parameters, f"$.builder_action_proposals[{index}].parameters"
    )

    contract = ACTION_CONTRACTS[str(action_type)]
    ir = {
        "action_id": str(action_id),
        "action_type": str(action_type),
        "target_node": str(target_node),
        "normalized_parameters": parameters,
        "derived_effects": {
            "class": list(contract["derived_class_effects"]),
            "structure": list(contract["derived_structure_effects"]),
            "decision": list(contract["derived_decision_effects"]),
        },
        "required_claims": list(contract["required_claims"]),
        "required_permissions": list(contract["required_permissions"]),
        "decision_state": "unresolved" if hidden else "resolved",
        "hidden_decision_paths": sorted(hidden),
        "source_draft_path": str(
            action.get("source_draft_path") or f"$.builder_action_proposals[{index}]"
        ),
    }
    return _canonical(ir)


def normalize_actions(actions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, action in enumerate(actions):
        ir = normalize_action(action, index)
        if ir["action_id"] in seen_ids:
            raise ActionIRValidationError(f"Duplicate Builder action: {ir['action_id']}")
        seen_ids.add(ir["action_id"])
        result.append(ir)
    if not result:
        raise ActionIRValidationError("At least one Builder action is required")
    return _canonical(result)


def normalized_review_draft(
    review_draft: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    draft = copy.deepcopy(dict(review_draft))
    raw_actions = draft.get("builder_action_proposals")
    if not isinstance(raw_actions, list):
        raise ActionIRValidationError("builder_action_proposals must be an array")
    action_ir = normalize_actions(raw_actions)
    draft["builder_action_proposals"] = [
        {
            "action_id": item["action_id"],
            "action_type": item["action_type"],
            "target_node": item["target_node"],
            "parameters": copy.deepcopy(item["normalized_parameters"]),
        }
        for item in action_ir
    ]
    return _canonical(draft), action_ir


__all__ = [
    "ActionIRValidationError",
    "normalize_action",
    "normalize_actions",
    "normalized_review_draft",
]
