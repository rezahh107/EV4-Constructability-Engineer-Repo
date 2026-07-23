from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

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
REQUIRED_REVIEW_UNIT_FIELDS = (
    "node_id", "node_type", "action_proposed", "node_status", "interrogation_result",
)
REQUIRED_INTERROGATION_FIELDS = (
    "geometry_required", "asset_required", "overlay_strategy_required",
    "responsive_behavior", "interaction_implied", "dynamic_loop_implied",
    "accessibility_claimed", "exact_ui_control_path_used",
    "requires_class_change", "requires_structure_change",
)
DEPENDENCY_DIMENSIONS = (
    "geometry", "asset", "overlay", "responsive", "interaction",
    "dynamic_loop", "accessibility", "exact_ui_control_path",
    "class_change", "structure_change",
)
UNRESOLVED_DECISION_KEYS = {
    "architect_decision_required", "builder_decision_required", "choose_between",
    "decision_to_make", "open_question", "requires_architect_amendment",
    "requires_builder_decision", "requires_user_choice", "tbd", "todo",
    "unknown_control", "unresolved_decision", "user_decision_required",
}
UNRESOLVED_DECISION_VALUES = {
    "architect_choice_required", "builder_decision_required", "choose_in_builder",
    "tbd", "todo", "unknown", "unresolved", "user_choice_required",
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
        result: dict[str, Any] = {
            "code": self.code,
            "carrier_kind": self.carrier_kind,
            "severity_or_status": self.severity_or_status,
            "message": self.message,
            "path_or_source_ref": self.path_or_source_ref,
            "repair_owner": self.repair_owner,
            "related_ids": list(self.related_ids),
        }
        return result

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

def _sorted_unique_strings(values: Iterable[Any]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})

def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []

def _diag(
    code: str,
    kind: str,
    severity: str,
    message: str,
    path: str = "$",
    owner: str = "ce",
    related_ids: Iterable[str] = (),
) -> CarrierDiagnostic:
    return CarrierDiagnostic(
        code=code,
        carrier_kind=kind,
        severity_or_status=severity,
        message=message,
        path_or_source_ref=path,
        repair_owner=owner,
        related_ids=tuple(sorted(set(related_ids))),
    )

def _diagnostic_sort_key(item: CarrierDiagnostic | dict[str, Any]) -> tuple[str, ...]:
    if isinstance(item, CarrierDiagnostic):
        return (
            item.path_or_source_ref,
            item.code,
            item.severity_or_status,
            ",".join(item.related_ids),
        )
    return (
        str(item.get("path_or_source_ref", "$")),
        str(item.get("code", "")),
        str(item.get("severity_or_status", "")),
        ",".join(str(value) for value in item.get("related_ids", [])),
    )

def _status_from_diagnostics(diagnostics: list[CarrierDiagnostic]) -> str:
    severities = {item.severity_or_status for item in diagnostics}
    if "invalid" in severities:
        return "invalid"
    if "blocked" in severities:
        return "blocked"
    if "insufficient_evidence" in severities:
        return "insufficient_evidence"
    return "complete"

def _source_identity(source_kind: str, value: Any, identity: str | None = None) -> dict[str, str]:
    return {
        "source_kind": source_kind,
        "identity": identity or source_kind,
        "sha256": canonical_sha256(value),
    }

def _carrier(
    kind: str,
    run_id: str,
    diagnostics: list[CarrierDiagnostic],
    source_identities: list[dict[str, str]],
    derived_data: dict[str, Any],
) -> dict[str, Any]:
    ordered = sorted(diagnostics, key=_diagnostic_sort_key)
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "carrier_kind": kind,
        "owner_repository": OWNER_REPOSITORY,
        "run_id": run_id,
        "status": _status_from_diagnostics(ordered),
        "diagnostics": [item.as_dict() for item in ordered],
        "source_identities": sorted(
            source_identities,
            key=lambda item: (item["source_kind"], item["identity"], item["sha256"]),
        ),
        "derived_data": derived_data,
    }

def _source_bundle_payload(source_bundle: dict[str, Any]) -> dict[str, Any]:
    outer = _as_dict(source_bundle.get("source_bundle"))
    return _as_dict(outer.get("payload"))

def _intake_nodes(intake: dict[str, Any]) -> list[dict[str, Any]]:
    projection = _as_dict(intake.get("structure_projection"))
    return sorted(
        [copy.deepcopy(item) for item in _as_list(projection.get("nodes")) if isinstance(item, dict)],
        key=lambda item: str(item.get("source_node_id", "")),
    )

def _source_nodes(source_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _source_bundle_payload(source_bundle)
    model = _as_dict(payload.get("approved_structure_model"))
    return sorted(
        [copy.deepcopy(item) for item in _as_list(model.get("structure_nodes")) if isinstance(item, dict)],
        key=lambda item: str(item.get("node_id", "")),
    )

def _node_ids(nodes: Iterable[dict[str, Any]], field: str) -> list[str]:
    return _sorted_unique_strings(item.get(field) for item in nodes)

def _review_unit_id(node: dict[str, Any]) -> str | None:
    value = node.get("review_unit_id") or node.get("node_id")
    return value if isinstance(value, str) and value else None

def _review_source_ref(node: dict[str, Any]) -> str | None:
    value = node.get("architect_node_ref") or node.get("node_id")
    return value if isinstance(value, str) and value else None

def _unknown_ids(values: Any) -> list[str]:
    result = []
    for item in _as_list(values):
        if not isinstance(item, dict):
            continue
        value = item.get("unresolved_id") or item.get("id")
        if isinstance(value, str) and value:
            result.append(value)
    return sorted(set(result))
