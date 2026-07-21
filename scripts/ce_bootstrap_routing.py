from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from ce_bootstrap_spec import *
from ce_bootstrap_validation import *
from ce_bootstrap_snapshot import (
    assert_snapshot_unchanged,
    strict_load_json_snapshot,
)


def load_official_module(root: Path) -> Any:
    name = "ce_bootstrap_official_intake_validator"
    if name in sys.modules:
        return sys.modules[name]
    path = root / INTAKE_VALIDATOR_REL
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "official validator load failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _unwrap_source_bundle(value: dict[str, Any]) -> dict[str, Any] | None:
    nested = value.get("source_bundle")
    if isinstance(nested, dict) and isinstance(nested.get("bundle_id"), str):
        return nested
    if isinstance(value.get("bundle_id"), str) and isinstance(value.get("payload"), dict):
        return value
    return None


def attachment_kind(value: dict[str, Any]) -> str:
    schema_id = value.get("schema_id")
    if schema_id == CANONICAL_SCHEMA_ID:
        return "canonical"
    if schema_id in LEGACY_SCHEMA_IDS:
        return "legacy"
    if value.get("schema_version") == RECEIPT_SCHEMA_ID:
        return "receipt_like"
    if _unwrap_source_bundle(value) is not None:
        return "source_bundle"
    if schema_id in WRONG_STAGE_SCHEMA_IDS or {"result", "final_stage_bundle", "transition"} & set(value):
        return "wrong"
    return "invalid"


def _base_route(case_id: str) -> dict[str, Any]:
    expected = EXPECTED_ROUTING_CASES[case_id]
    return {key: expected[key] for key in DECISION_FIELDS}


def _receipt_record(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    transition = value.get("transition")
    if not isinstance(transition, dict):
        issues.append("missing_transition")
    else:
        if transition.get("id") not in {"ev4-architect-to-ce-transition", SOURCE_TRANSITION_ID}:
            issues.append("wrong_transition")
        if transition.get("version") != SOURCE_TRANSITION_VERSION:
            issues.append("wrong_transition_version")
    if value.get("handoff_allowed") is not True:
        issues.append("handoff_not_allowed")
    return {
        "path": str(path),
        "receipt_like_attachment": True,
        "receipt_validation_status": "unverified",
        "receipt_role": "diagnostic_untrusted",
        "observed_issues": issues,
    }


def _architect_payload_from_source_bundle(source: dict[str, Any]) -> dict[str, Any]:
    payload = source.get("payload")
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _source_provenance_diagnostics(intake: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    transition = intake.get("project_gate_transition") if isinstance(intake.get("project_gate_transition"), dict) else {}
    expected_transition = {
        "executed": True,
        "transition_id": SOURCE_TRANSITION_ID,
        "transition_version": SOURCE_TRANSITION_VERSION,
        "producer_repository": PROJECT_GATE_PRODUCER,
    }
    for field, expected in expected_transition.items():
        if transition.get(field) != expected:
            diagnostics.append({"code": "CE_BOOTSTRAP_TRANSITION_IDENTITY_MISMATCH", "field": field, "expected": expected, "observed": transition.get(field)})
    source_ref = intake.get("source_repository_ref") if isinstance(intake.get("source_repository_ref"), dict) else {}
    source_contract = intake.get("source_contract") if isinstance(intake.get("source_contract"), dict) else {}
    produced_by = source.get("produced_by") if isinstance(source.get("produced_by"), dict) else {}
    payload = _architect_payload_from_source_bundle(source)
    expected_repo = source_ref.get("repository")
    if produced_by.get("repository") != expected_repo:
        diagnostics.append({"code": "CE_BOOTSTRAP_SOURCE_PRODUCER_MISMATCH", "expected": expected_repo, "observed": produced_by.get("repository")})
    if payload.get("owner_repository") != source_contract.get("owner_repository"):
        diagnostics.append({"code": "CE_BOOTSTRAP_SOURCE_OWNER_MISMATCH", "expected": source_contract.get("owner_repository"), "observed": payload.get("owner_repository")})
    expected_commit = source_ref.get("commit_sha")
    if expected_commit and produced_by.get("commit_sha") != expected_commit:
        diagnostics.append({"code": "CE_BOOTSTRAP_SOURCE_COMMIT_MISMATCH", "expected": expected_commit, "observed": produced_by.get("commit_sha")})
    return diagnostics


def _snapshot_changed_result(exc: ValidationError) -> dict[str, Any]:
    result = _base_route("CE-BOOT-ROUTE-SOURCE-BINDING-INVALID")
    result["diagnostics"] = [
        {
            "code": "CE_BOOTSTRAP_INPUT_CHANGED_DURING_ROUTING",
            "severity": "error",
            "message": str(exc),
            "path": "$attachments",
        }
    ]
    result["source_provenance_verification"] = "failed"
    return result


def _route_authorized_attachments(root: Path, attachments: Iterable[Path]) -> dict[str, Any]:
    root = root.resolve()
    module = load_official_module(root)
    official = module.CEArchitectStageIntakeValidator(root)
    buckets: dict[str, list[dict[str, Any]]] = {key: [] for key in ("valid", "insufficient", "invalid", "receipt_like", "legacy", "wrong", "source_bundle")}
    for supplied in attachments:
        path = supplied if supplied.is_absolute() else root / supplied
        try:
            snapshot = strict_load_json_snapshot(path)
        except ValidationError as exc:
            buckets["invalid"].append({"path": str(path), "reason": str(exc)})
            continue
        value = snapshot.value
        kind = attachment_kind(value)
        if kind == "canonical":
            validation = official.validate_value(value)
            record = {
                "path": str(path),
                "value": value,
                "snapshot": snapshot,
                "validation_status": validation["status"],
                "diagnostics": validation["diagnostics"],
            }
            target = "valid" if validation["status"] == "valid" else "insufficient" if validation["status"] == "insufficient_evidence" else "invalid"
            buckets[target].append(record)
        elif kind == "receipt_like":
            buckets[kind].append(_receipt_record(path, value))
        elif kind == "source_bundle":
            buckets[kind].append({"path": str(path), "value": _unwrap_source_bundle(value), "snapshot": snapshot})
        else:
            buckets[kind].append({"path": str(path), "value": value})

    if len(buckets["valid"]) > 1:
        result = _base_route("CE-BOOT-ROUTE-AMBIGUOUS-INPUT")
        result["candidate_paths"] = [item["path"] for item in buckets["valid"]]
        return result

    if len(buckets["valid"]) == 1:
        conflicts = buckets["insufficient"] + buckets["invalid"] + buckets["receipt_like"] + buckets["legacy"] + buckets["wrong"]
        if conflicts or len(buckets["source_bundle"]) > 1:
            result = _base_route("CE-BOOT-ROUTE-CONFLICTING-ATTACHMENTS")
            result["conflicting_paths"] = [item["path"] for item in conflicts + buckets["source_bundle"]]
            result["receipt_evidence"] = buckets["receipt_like"]
            return result
        if not buckets["source_bundle"]:
            result = _base_route("CE-BOOT-ROUTE-SOURCE-BINDING-MISSING")
            result["ce_input_path"] = buckets["valid"][0]["path"]
            result["source_provenance_verification"] = "unavailable_missing_source_bundle_bytes"
            return result
        intake_record = buckets["valid"][0]
        source_record = buckets["source_bundle"][0]
        intake = intake_record["value"]
        source = source_record["value"]
        official_diags = module.validate_source_bundle_binding(intake, source)
        diagnostics = [diag.to_dict() if hasattr(diag, "to_dict") else dict(diag) for diag in official_diags]
        diagnostics.extend(_source_provenance_diagnostics(intake, source))
        if diagnostics:
            result = _base_route("CE-BOOT-ROUTE-SOURCE-BINDING-INVALID")
            result["diagnostics"] = diagnostics
            result["source_provenance_verification"] = "failed"
            return result
        try:
            assert_snapshot_unchanged(intake_record["snapshot"])
            assert_snapshot_unchanged(source_record["snapshot"])
        except ValidationError as exc:
            return _snapshot_changed_result(exc)
        result = _base_route("CE-BOOT-ROUTE-VALID-BOUND-INPUT")
        result.update({
            "ce_input_path": intake_record["path"],
            "source_bundle_path": source_record["path"],
            "source_binding_verified": True,
            "source_provenance_verification": "verified",
            "input_snapshot_evidence": {
                "ce_input_file_sha256": intake_record["snapshot"].sha256,
                "source_bundle_file_sha256": source_record["snapshot"].sha256,
                "second_read_equality": True,
            },
            "source_binding_evidence": {
                "bundle_id_match": True,
                "canonical_sha256_match": True,
                "transition_identity_match": True,
                "project_gate_producer_match": True,
                "upstream_producer_match": True,
            },
        })
        return result

    if len(buckets["receipt_like"]) > 1:
        result = _base_route("CE-BOOT-ROUTE-CONFLICTING-ATTACHMENTS")
        result["receipt_evidence"] = buckets["receipt_like"]
        result["conflicting_paths"] = [item["path"] for item in buckets["receipt_like"]]
        return result
    if buckets["insufficient"]:
        result = _base_route("CE-BOOT-ROUTE-INSUFFICIENT-EVIDENCE")
        result["diagnostics"] = buckets["insufficient"][0]["diagnostics"]
        return result
    if buckets["invalid"]:
        result = _base_route("CE-BOOT-ROUTE-INVALID-INPUT")
        result["diagnostics"] = buckets["invalid"]
        return result
    if buckets["legacy"]:
        return _base_route("CE-BOOT-ROUTE-LEGACY-INPUT")
    if buckets["wrong"]:
        return _base_route("CE-BOOT-ROUTE-WRONG-ARTIFACT")
    if buckets["receipt_like"]:
        result = _base_route("CE-BOOT-ROUTE-RECEIPT-ONLY")
        result["receipt_evidence"] = buckets["receipt_like"]
        return result
    result = _base_route("CE-BOOT-ROUTE-BARE-START")
    if buckets["source_bundle"]:
        result["source_bundle_present_without_ce_input"] = True
    return result


@dataclass(frozen=True)
class RoutingRequest:
    message: str
    operating_mode: str
    active_ce_run: bool
    attachments: tuple[Path, ...]

    @classmethod
    def from_value(cls, value: dict[str, Any]) -> "RoutingRequest":
        require(isinstance(value, dict), "routing request must be an object")
        for field in ("message", "operating_mode", "active_ce_run", "attachments"):
            require(field in value, f"routing request missing field: {field}")
        require(isinstance(value["message"], str), "routing request message must be a string")
        require(value["operating_mode"] in OPERATING_MODES, "routing request operating_mode is invalid")
        require(isinstance(value["active_ce_run"], bool), "routing request active_ce_run must be boolean")
        require(isinstance(value["attachments"], list) and all(isinstance(item, str) for item in value["attachments"]), "routing request attachments must be string paths")
        return cls(value["message"], value["operating_mode"], value["active_ce_run"], tuple(Path(item) for item in value["attachments"]))


def _authorization_result(authorized: bool, operating_mode: str, reason: str) -> dict[str, Any]:
    return {
        "activation_authorized": authorized,
        "operating_mode": operating_mode,
        "authorization_reason": reason,
    }


def route_request(root: Path, request: RoutingRequest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, dict):
        request = RoutingRequest.from_value(request)
    root = root.resolve()
    maintenance = request.operating_mode == "repository_maintenance" or has_repository_maintenance_intent(request.message)
    if maintenance:
        result = _base_route("CE-BOOT-ROUTE-REPOSITORY-MAINTENANCE")
        return {**_authorization_result(False, "repository_maintenance", "repository_maintenance_precedence"), **result}
    if is_bare_start(request.message):
        authorized = _authorization_result(True, "user_facing_new_ce_run", "exact_normalized_start")
    elif request.active_ce_run and request.operating_mode in {"auto", "active_ce_run", "user_facing_new_ce_run"}:
        authorized = _authorization_result(True, "active_ce_run", "authorized_active_ce_run")
    else:
        result = _base_route("CE-BOOT-ROUTE-UNAUTHORIZED")
        return {**_authorization_result(False, "no_authorized_ce_context", "no_exact_start_or_active_ce_run"), **result}
    if not request.attachments:
        return {**authorized, **_base_route("CE-BOOT-ROUTE-BARE-START")}
    return {**authorized, **_route_authorized_attachments(root, request.attachments)}
