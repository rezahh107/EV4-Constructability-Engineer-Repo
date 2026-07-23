from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

OWNER_REPOSITORY = "rezahh107/EV4-Constructability-Engineer-Repo"
SCHEMA_ID = "ev4-ce-intermediate-validation-carrier@1.0.0"
SCHEMA_VERSION = "1.0.0"
LEGAL_STATUSES = {"complete", "insufficient_evidence", "blocked", "invalid"}
CARRIER_KINDS = {
    "architecture_identity_preservation_result",
    "ce_review_units_and_interrogation_results",
    "dependency_classification",
    "implementation_strategy_coverage_result",
}
DEPENDENCY_RULES = {
    "geometry": "R03_GEOMETRY_MUST_BE_PROVEN",
    "asset": "R04_ASSET_SOURCE_OR_PLACEHOLDER",
    "overlay": "R05_OVERLAY_STRATEGY_MUST_BE_PROVEN",
    "responsive": "R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK",
    "interaction": "R07_INTERACTION_REQUIRES_APPROVAL",
    "dynamic_loop": "R08_DYNAMIC_LOOP_REQUIRES_APPROVAL",
    "accessibility": "R16_ACCESSIBILITY_CLAIM_REQUIRES_EVIDENCE",
    "exact_ui_control_path": "R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE",
    "class_change": "R09_STRUCTURE_OR_CLASS_CHANGE_REQUIRES_PERMISSION",
    "structure_change": "R09_STRUCTURE_OR_CLASS_CHANGE_REQUIRES_PERMISSION",
}
REQUIRED_INTERROGATION_FIELDS = {
    "geometry_required",
    "asset_required",
    "overlay_strategy_required",
    "responsive_behavior",
    "interaction_implied",
    "dynamic_loop_implied",
    "accessibility_claimed",
    "exact_ui_control_path_used",
    "requires_class_change",
    "requires_structure_change",
}
UNRESOLVED_DECISION_KEYS = {
    "architect_decision_required",
    "builder_decision_required",
    "choose_between",
    "decision_to_make",
    "open_question",
    "requires_architect_amendment",
    "requires_builder_decision",
    "requires_user_choice",
    "tbd",
    "todo",
    "unknown_control",
    "unresolved_decision",
    "user_decision_required",
}
UNRESOLVED_DECISION_VALUES = {
    "architect_choice_required",
    "builder_decision_required",
    "choose_in_builder",
    "tbd",
    "todo",
    "unknown",
    "unresolved",
    "user_choice_required",
}


@dataclass(frozen=True)
class CarrierDiagnostic:
    code: str
    carrier_kind: str
    severity_or_status: str
    message: str
    path_or_source_ref: str = "$"
    repair_owner: str = "ce"
    related_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "carrier_kind": self.carrier_kind,
            "severity_or_status": self.severity_or_status,
            "message": self.message,
            "path_or_source_ref": self.path_or_source_ref,
            "repair_owner": self.repair_owner,
            "related_ids": list(self.related_ids),
        }


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(values: Iterable[Any]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _diag(
    code: str,
    carrier_kind: str,
    severity_or_status: str,
    message: str,
    path_or_source_ref: str = "$",
    repair_owner: str = "ce",
    related_ids: Iterable[str] = (),
) -> CarrierDiagnostic:
    return CarrierDiagnostic(
        code=code,
        carrier_kind=carrier_kind,
        severity_or_status=severity_or_status,
        message=message,
        path_or_source_ref=path_or_source_ref,
        repair_owner=repair_owner,
        related_ids=tuple(sorted(set(related_ids))),
    )


def _diagnostic_key(value: CarrierDiagnostic | dict[str, Any]) -> tuple[str, str, str, str]:
    if isinstance(value, CarrierDiagnostic):
        return (
            value.path_or_source_ref,
            value.code,
            value.severity_or_status,
            ",".join(value.related_ids),
        )
    return (
        str(value.get("path_or_source_ref", "$")),
        str(value.get("code", "")),
        str(value.get("severity_or_status", "")),
        ",".join(str(item) for item in _as_list(value.get("related_ids"))),
    )


def _status(diagnostics: Iterable[CarrierDiagnostic]) -> str:
    severities = {item.severity_or_status for item in diagnostics}
    if "invalid" in severities:
        return "invalid"
    if "blocked" in severities:
        return "blocked"
    if "insufficient_evidence" in severities:
        return "insufficient_evidence"
    return "complete"


def _source_identity(source_kind: str, identity: str, value: Any) -> dict[str, str]:
    return {
        "source_kind": source_kind,
        "identity": identity,
        "sha256": canonical_sha256(value),
    }


def _carrier(
    carrier_kind: str,
    run_id: str,
    diagnostics: list[CarrierDiagnostic],
    source_identities: list[dict[str, str]],
    derived_data: dict[str, Any],
) -> dict[str, Any]:
    ordered = sorted(diagnostics, key=_diagnostic_key)
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "carrier_kind": carrier_kind,
        "owner_repository": OWNER_REPOSITORY,
        "run_id": run_id,
        "status": _status(ordered),
        "diagnostics": [item.as_dict() for item in ordered],
        "source_identities": sorted(
            source_identities,
            key=lambda item: (item["source_kind"], item["identity"], item["sha256"]),
        ),
        "derived_data": derived_data,
    }


def _bundle_object(source_bundle: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(source_bundle.get("source_bundle"))


def _bundle_payload(source_bundle: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(_bundle_object(source_bundle).get("payload"))


def _intake_nodes(intake: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = _as_list(_as_dict(intake.get("structure_projection")).get("nodes"))
    return sorted(
        [copy.deepcopy(item) for item in nodes if isinstance(item, dict)],
        key=lambda item: str(item.get("source_node_id", "")),
    )


def _source_nodes(source_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = _as_list(
        _as_dict(_bundle_payload(source_bundle).get("approved_structure_model")).get(
            "structure_nodes"
        )
    )
    return sorted(
        [copy.deepcopy(item) for item in nodes if isinstance(item, dict)],
        key=lambda item: str(item.get("node_id", "")),
    )


def _unknown_ids(values: Any) -> list[str]:
    result: list[str] = []
    for item in _as_list(values):
        if isinstance(item, dict):
            value = item.get("unresolved_id") or item.get("id")
            if isinstance(value, str) and value:
                result.append(value)
    return sorted(set(result))


def _review_unit_id(item: dict[str, Any]) -> str | None:
    value = item.get("review_unit_id") or item.get("node_id")
    return value if isinstance(value, str) and value else None


def _review_source_ref(item: dict[str, Any]) -> str | None:
    value = item.get("architect_node_ref") or item.get("node_id")
    return value if isinstance(value, str) and value else None


def _normalized_review_nodes(review: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [item for item in _as_list(review.get("reviewed_nodes")) if isinstance(item, dict)]
    normalized: list[dict[str, Any]] = []
    for item in nodes:
        value = copy.deepcopy(item)
        unit_id = _review_unit_id(value)
        source_ref = _review_source_ref(value)
        if unit_id:
            value["review_unit_id"] = unit_id
        if source_ref:
            value["architect_node_ref"] = source_ref
        value["architect_evidence_refs"] = _strings(value.get("architect_evidence_refs") or [])
        normalized.append(value)
    return sorted(
        normalized,
        key=lambda item: (
            str(item.get("architect_node_ref", "")),
            str(item.get("review_unit_id", "")),
        ),
    )


def _contains_unresolved_decision(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).strip().lower() in UNRESOLVED_DECISION_KEYS
            or _contains_unresolved_decision(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_unresolved_decision(item) for item in value)
    if isinstance(value, str):
        return value.strip().lower() in UNRESOLVED_DECISION_VALUES
    return False

__all__ = [
    "CarrierDiagnostic",
    "OWNER_REPOSITORY",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "LEGAL_STATUSES",
    "CARRIER_KINDS",
    "DEPENDENCY_RULES",
    "REQUIRED_INTERROGATION_FIELDS",
    "UNRESOLVED_DECISION_KEYS",
    "UNRESOLVED_DECISION_VALUES",
    "canonical_json_bytes",
    "canonical_sha256",
    "_as_dict",
    "_as_list",
    "_strings",
    "_diag",
    "_diagnostic_key",
    "_status",
    "_source_identity",
    "_carrier",
    "_bundle_object",
    "_bundle_payload",
    "_intake_nodes",
    "_source_nodes",
    "_unknown_ids",
    "_review_unit_id",
    "_review_source_ref",
    "_normalized_review_nodes",
    "_contains_unresolved_decision",
]
