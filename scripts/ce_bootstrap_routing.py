from __future__ import annotations

import importlib.util
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from ce_bootstrap_spec import *
from ce_bootstrap_validation import *
from ce_bootstrap_snapshot import (
    AttachmentSnapshot,
    assert_snapshot_unchanged,
    strict_load_json_snapshot,
)


VerificationStatus = Literal["verified", "evidence_required", "conflict"]


@dataclass(frozen=True)
class SourceVerificationResult:
    status: VerificationStatus
    diagnostics: tuple[dict[str, Any], ...]
    checks: dict[str, bool]


@dataclass(frozen=True)
class RuntimeAttachments:
    buckets: dict[str, list[dict[str, Any]]]

    @property
    def valid(self) -> list[dict[str, Any]]:
        return self.buckets["valid"]


@dataclass(frozen=True)
class RoutingRequest:
    message: str
    operating_mode: str
    active_ce_run: bool
    attachments: tuple[Path, ...]

    @classmethod
    def from_value(cls, value: dict[str, Any]) -> "RoutingRequest":
        require(isinstance(value, dict), "routing request must be an object")
        for field in ("message", "operating_mode", "attachments"):
            require(field in value, f"routing request missing field: {field}")
        require(isinstance(value["message"], str), "routing request message must be a string")
        require(
            value["operating_mode"] in OPERATING_MODES,
            "routing request operating_mode is invalid",
        )
        active_ce_run = value.get("active_ce_run", False)
        require(isinstance(active_ce_run, bool), "routing request active_ce_run must be boolean")
        require(
            isinstance(value["attachments"], list)
            and all(isinstance(item, str) for item in value["attachments"]),
            "routing request attachments must be string paths",
        )
        return cls(
            value["message"],
            value["operating_mode"],
            active_ce_run,
            tuple(Path(item) for item in value["attachments"]),
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
    if isinstance(schema_id, str) and schema_id.startswith("ev4-ce-architect-stage-intake@"):
        return "canonical"
    if value.get("schema_version") == RECEIPT_SCHEMA_ID:
        return "receipt_like"
    if _unwrap_source_bundle(value) is not None:
        return "source_bundle"
    if schema_id in WRONG_STAGE_SCHEMA_IDS or {"result", "final_stage_bundle", "transition"} & set(value):
        return "wrong"
    return "irrelevant"


def _base_route(case_id: str) -> dict[str, Any]:
    expected = EXPECTED_ROUTING_CASES[case_id]
    return {key: expected[key] for key in DECISION_FIELDS}


def _authorization_result(
    authorized: bool,
    operating_mode: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "activation_authorized": authorized,
        "operating_mode": operating_mode,
        "authorization_reason": reason,
    }


def _maintenance_result(reason: str) -> dict[str, Any]:
    return {
        **_authorization_result(False, "repository_maintenance", reason),
        **_base_route("CE-RUNTIME-REPOSITORY-MAINTENANCE"),
    }


def _normalized_message(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def _has_explicit_repository_maintenance_operation(value: str) -> bool:
    """Recognize bounded action-plus-repository-object requests."""
    text = _normalized_message(value)
    if not text:
        return False

    english_action = re.search(
        r"\b(review|inspect|audit|repair|fix|modify|update|edit|change|debug|refactor|validate)\b",
        text,
    )
    english_object = re.search(
        r"\b(repository|repo|pull request|issue|workflow|ci|github actions?|branch|commit)\b"
        r"|\bpr\s*(?:#\s*)?\d+\b"
        r"|(?:^|\s)(?:scripts|tests|schemas|docs|validator|manifests|contracts|\.github)/[^\s]+",
        text,
    )
    if english_action and english_object:
        return True

    persian_actions = (
        "بررسی",
        "بازبینی",
        "ممیزی",
        "اصلاح",
        "تعمیر",
        "تغییر",
        "ویرایش",
        "به‌روزرسانی",
        "دیباگ",
    )
    persian_objects = (
        "ریپو",
        "مخزن",
        "پول ریکوئست",
        "ورک‌فلو",
        "ci",
        "گیت‌هاب اکشن",
        "برنچ",
        "کامیت",
    )
    has_persian_action = any(action in text for action in persian_actions)
    has_persian_object = any(obj in text for obj in persian_objects)
    has_pr_number = re.search(r"\bpr\s*(?:#|شماره)?\s*\d+\b", text) is not None
    return has_persian_action and (has_persian_object or has_pr_number)


def _warning(code: str, path: str, message: str, *, kind: str) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "warning",
        "path": path,
        "attachment_kind": kind,
        "message": message,
    }


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
        "receipt_role": "diagnostic_nonsemantic",
        "observed_issues": issues,
    }


def _architect_payload_from_source_bundle(source: dict[str, Any]) -> dict[str, Any]:
    payload = source.get("payload")
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _diag(
    code: str,
    message: str,
    path: str,
    *,
    severity: str = "error",
    expected: Any = None,
    observed: Any = None,
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "path": path,
    }
    if expected is not None or observed is not None:
        diagnostic["details"] = {"expected": expected, "observed": observed}
    return diagnostic


def _verify_selected_source_bundle(
    module: Any,
    intake: dict[str, Any],
    source: dict[str, Any],
) -> SourceVerificationResult:
    diagnostics = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in module.validate_source_bundle_binding(intake, source)
    ]
    checks = {
        "bundle_id_match": not any(item.get("code") == "CE_I21_SOURCE_BUNDLE_ID_MISMATCH" for item in diagnostics),
        "canonical_sha256_match": not any(item.get("code") == "CE_I21_SOURCE_BUNDLE_HASH_MISMATCH" for item in diagnostics),
        "transition_identity_match": True,
        "project_gate_producer_match": True,
        "upstream_producer_match": True,
    }

    transition = intake.get("project_gate_transition") if isinstance(intake.get("project_gate_transition"), dict) else {}
    expected_transition = {
        "executed": True,
        "transition_id": SOURCE_TRANSITION_ID,
        "transition_version": SOURCE_TRANSITION_VERSION,
    }
    for field, expected in expected_transition.items():
        observed = transition.get(field)
        if observed != expected:
            checks["transition_identity_match"] = False
            diagnostics.append(
                _diag(
                    "CE_RUNTIME_TRANSITION_IDENTITY_MISMATCH",
                    "Project Gate transition identity must match the canonical CE transition.",
                    f"$.project_gate_transition.{field}",
                    expected=expected,
                    observed=observed,
                )
            )

    observed_project_gate = transition.get("producer_repository")
    if observed_project_gate != PROJECT_GATE_PRODUCER:
        checks["project_gate_producer_match"] = False
        diagnostics.append(
            _diag(
                "CE_RUNTIME_PROJECT_GATE_PRODUCER_MISMATCH",
                "Project Gate producer identity must match the canonical transition producer.",
                "$.project_gate_transition.producer_repository",
                expected=PROJECT_GATE_PRODUCER,
                observed=observed_project_gate,
            )
        )

    source_ref = intake.get("source_repository_ref") if isinstance(intake.get("source_repository_ref"), dict) else {}
    source_contract = intake.get("source_contract") if isinstance(intake.get("source_contract"), dict) else {}
    produced_by = source.get("produced_by") if isinstance(source.get("produced_by"), dict) else {}
    payload_schema = source.get("payload_schema") if isinstance(source.get("payload_schema"), dict) else {}
    payload = _architect_payload_from_source_bundle(source)

    expected_repository = source_contract.get("owner_repository")
    repository_observations = {
        "$.source_repository_ref.repository": source_ref.get("repository"),
        "$.source_bundle.produced_by.repository": produced_by.get("repository"),
        "$.source_bundle.payload.owner_repository": payload.get("owner_repository"),
        "$.source_bundle.payload_schema.owner_repository": payload_schema.get("owner_repository"),
    }
    for path, observed in repository_observations.items():
        if not expected_repository or observed != expected_repository:
            checks["upstream_producer_match"] = False
            diagnostics.append(
                _diag(
                    "CE_RUNTIME_ARCHITECT_REPOSITORY_IDENTITY_MISMATCH",
                    "Architect repository identity must agree across intake and source bundle.",
                    path,
                    expected=expected_repository,
                    observed=observed,
                )
            )

    expected_schema_id = source_contract.get("schema_id")
    expected_schema_version = source_contract.get("schema_version")
    contract_observations = {
        "$.source_bundle.payload.schema_id": (payload.get("schema_id"), expected_schema_id),
        "$.source_bundle.payload.schema_version": (payload.get("schema_version"), expected_schema_version),
        "$.source_bundle.payload_schema.id": (payload_schema.get("id"), expected_schema_id),
        "$.source_bundle.payload_schema.version": (payload_schema.get("version"), expected_schema_version),
    }
    for path, (observed, expected) in contract_observations.items():
        if not expected or observed != expected:
            checks["upstream_producer_match"] = False
            diagnostics.append(
                _diag(
                    "CE_RUNTIME_SOURCE_PAYLOAD_CONTRACT_MISMATCH",
                    "Source payload contract identity must match the intake source contract.",
                    path,
                    expected=expected,
                    observed=observed,
                )
            )

    if source.get("stage") != "architect":
        checks["upstream_producer_match"] = False
        diagnostics.append(
            _diag(
                "CE_RUNTIME_SOURCE_STAGE_MISMATCH",
                "Relied-upon source evidence must be an Architect-stage bundle.",
                "$.source_bundle.stage",
                expected="architect",
                observed=source.get("stage"),
            )
        )

    commit_identities = {
        "$.source_repository_ref.commit_sha": source_ref.get("commit_sha"),
        "$.source_contract.accepted_main_merge_commit": source_contract.get("accepted_main_merge_commit"),
        "$.source_bundle.produced_by.commit_sha": produced_by.get("commit_sha"),
    }
    missing_commit_paths = [
        path
        for path, value in commit_identities.items()
        if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{40}", value) is None
    ]
    if missing_commit_paths:
        checks["upstream_producer_match"] = False
        for path in missing_commit_paths:
            diagnostics.append(
                _diag(
                    "CE_RUNTIME_SOURCE_COMMIT_IDENTITY_REQUIRED",
                    "Complete Architect commit identity is required before supplied source provenance can be verified.",
                    path,
                    severity="insufficient_evidence",
                    observed=commit_identities[path],
                )
            )
    elif len(set(commit_identities.values())) != 1:
        checks["upstream_producer_match"] = False
        diagnostics.append(
            _diag(
                "CE_RUNTIME_SOURCE_COMMIT_MISMATCH",
                "Architect commit identity must agree across intake contract, intake reference, and source producer.",
                "$.source_repository_ref.commit_sha",
                expected=source_contract.get("accepted_main_merge_commit"),
                observed={
                    "source_repository_ref": source_ref.get("commit_sha"),
                    "source_bundle_produced_by": produced_by.get("commit_sha"),
                },
            )
        )

    if source_ref.get("bundle_id") != transition.get("source_bundle_id"):
        checks["upstream_producer_match"] = False
        diagnostics.append(
            _diag(
                "CE_RUNTIME_SOURCE_REFERENCE_BUNDLE_ID_MISMATCH",
                "Intake source_repository_ref.bundle_id must identify the selected source bundle.",
                "$.source_repository_ref.bundle_id",
                expected=transition.get("source_bundle_id"),
                observed=source_ref.get("bundle_id"),
            )
        )

    has_error = any(item.get("severity", "error") == "error" for item in diagnostics)
    has_missing_identity = any(item.get("severity") == "insufficient_evidence" for item in diagnostics)
    status: VerificationStatus
    if has_error:
        status = "conflict"
    elif has_missing_identity:
        status = "evidence_required"
    else:
        status = "verified"
    return SourceVerificationResult(status, tuple(diagnostics), checks)


def _source_bundle_required(diagnostics: list[dict[str, Any]]) -> bool:
    serialized = json.dumps(diagnostics, ensure_ascii=False).upper()
    return "SOURCE_BUNDLE" in serialized or "SOURCE BUNDLE" in serialized


def _warnings_for_buckets(buckets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    mapping = {
        "insufficient": (
            "CE_RUNTIME_EXTRA_INSUFFICIENT_INPUT_IGNORED",
            "An additional insufficient CE candidate was ignored because one valid CE input was selected.",
        ),
        "invalid": (
            "CE_RUNTIME_EXTRA_INVALID_INPUT_IGNORED",
            "An additional invalid CE candidate was ignored because one valid CE input was selected.",
        ),
        "unreadable": (
            "CE_RUNTIME_EXTRA_UNREADABLE_FILE_IGNORED",
            "An unreadable or malformed extra file was ignored.",
        ),
        "receipt_like": (
            "CE_RUNTIME_EXTRA_RECEIPT_IGNORED",
            "Receipt-like evidence is diagnostic only and was not used as semantic input.",
        ),
        "legacy": (
            "CE_RUNTIME_EXTRA_LEGACY_INPUT_IGNORED",
            "A legacy CE artifact was ignored because one valid canonical input was selected.",
        ),
        "wrong": (
            "CE_RUNTIME_EXTRA_WRONG_STAGE_ARTIFACT_IGNORED",
            "A wrong-stage artifact was ignored because one valid canonical input was selected.",
        ),
        "irrelevant": (
            "CE_RUNTIME_EXTRA_IRRELEVANT_FILE_IGNORED",
            "An unrelated extra file was ignored.",
        ),
    }
    for kind, (code, message) in mapping.items():
        for item in buckets[kind]:
            warnings.append(_warning(code, item["path"], message, kind=kind))
    return warnings


def _inspect_runtime_attachments(root: Path, attachments: Iterable[Path]) -> RuntimeAttachments:
    module = load_official_module(root)
    official = module.CEArchitectStageIntakeValidator(root)
    buckets: dict[str, list[dict[str, Any]]] = {
        key: []
        for key in (
            "valid",
            "insufficient",
            "invalid",
            "unreadable",
            "receipt_like",
            "legacy",
            "wrong",
            "source_bundle",
            "irrelevant",
        )
    }

    for supplied in attachments:
        path = supplied if supplied.is_absolute() else root / supplied
        try:
            snapshot = strict_load_json_snapshot(path)
        except ValidationError as exc:
            buckets["unreadable"].append({"path": str(path), "reason": str(exc)})
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
            target = (
                "valid"
                if validation["status"] == "valid"
                else "insufficient"
                if validation["status"] == "insufficient_evidence"
                else "invalid"
            )
            buckets[target].append(record)
        elif kind == "receipt_like":
            buckets[kind].append(_receipt_record(path, value))
        elif kind == "source_bundle":
            buckets[kind].append(
                {
                    "path": str(path),
                    "value": _unwrap_source_bundle(value),
                    "snapshot": snapshot,
                }
            )
        else:
            buckets[kind].append({"path": str(path), "value": value})

    return RuntimeAttachments(buckets)


def _snapshot_changed_result(exc: ValidationError, warnings: list[dict[str, Any]]) -> dict[str, Any]:
    result = _base_route("CE-RUNTIME-SOURCE-EVIDENCE-CONFLICT")
    result.update(
        {
            "diagnostics": [
                {
                    "code": "CE_BOOTSTRAP_INPUT_CHANGED_DURING_ROUTING",
                    "severity": "error",
                    "message": str(exc),
                    "path": "$attachments",
                }
            ],
            "source_provenance_verification": "failed",
            "source_binding_verified": False,
            "source_bundle_required": True,
            "warnings": warnings,
        }
    )
    return result


def _route_one_valid_input(root: Path, inspected: RuntimeAttachments) -> dict[str, Any]:
    buckets = inspected.buckets
    module = load_official_module(root)
    intake_record = buckets["valid"][0]
    intake = intake_record["value"]
    warnings = _warnings_for_buckets(buckets)
    source_record: dict[str, Any] | None = None
    verification: SourceVerificationResult | None = None

    if len(buckets["source_bundle"]) == 1:
        source_record = buckets["source_bundle"][0]
        verification = _verify_selected_source_bundle(module, intake, source_record["value"])
        try:
            assert_snapshot_unchanged(intake_record["snapshot"])
            assert_snapshot_unchanged(source_record["snapshot"])
        except ValidationError as exc:
            return _snapshot_changed_result(exc, warnings)

        if verification.status == "conflict":
            result = _base_route("CE-RUNTIME-SOURCE-EVIDENCE-CONFLICT")
            result.update(
                {
                    "diagnostics": list(verification.diagnostics),
                    "source_provenance_verification": "failed",
                    "source_binding_verified": False,
                    "source_bundle_required": True,
                    "warnings": warnings,
                }
            )
            return result
        if verification.status == "evidence_required":
            result = _base_route("CE-RUNTIME-EVIDENCE-REQUIRED")
            result.update(
                {
                    "diagnostics": list(verification.diagnostics),
                    "requested_evidence": list(verification.diagnostics),
                    "ce_input_path": intake_record["path"],
                    "source_bundle_path": source_record["path"],
                    "source_provenance_verification": "incomplete_required_identity",
                    "source_binding_verified": False,
                    "source_bundle_required": True,
                    "warnings": warnings,
                }
            )
            return result
    elif len(buckets["source_bundle"]) > 1:
        for item in buckets["source_bundle"]:
            warnings.append(
                _warning(
                    "CE_RUNTIME_MULTIPLE_OPTIONAL_SOURCE_BUNDLES_IGNORED",
                    item["path"],
                    "Multiple optional source bundles were supplied; none was selected automatically.",
                    kind="source_bundle",
                )
            )

    try:
        assert_snapshot_unchanged(intake_record["snapshot"])
    except ValidationError as exc:
        result = _base_route("CE-RUNTIME-INVALID-INPUT")
        result.update(
            {
                "diagnostics": [
                    {
                        "code": "CE_BOOTSTRAP_INPUT_CHANGED_DURING_ROUTING",
                        "severity": "error",
                        "message": str(exc),
                        "path": intake_record["path"],
                    }
                ],
                "source_bundle_required": False,
                "source_binding_verified": False,
                "warnings": warnings,
            }
        )
        return result

    result_case = "CE-RUNTIME-VALID-BOUND-INPUT" if source_record is not None else "CE-RUNTIME-VALID-INPUT"
    result = _base_route(result_case)
    result.update(
        {
            "ce_input_path": intake_record["path"],
            "source_bundle_required": False,
            "warnings": warnings,
            "ignored_attachment_paths": [
                item["path"]
                for kind in (
                    "insufficient",
                    "invalid",
                    "unreadable",
                    "receipt_like",
                    "legacy",
                    "wrong",
                    "irrelevant",
                )
                for item in buckets[kind]
            ],
            "receipt_evidence": buckets["receipt_like"],
            "input_snapshot_evidence": {
                "ce_input_file_sha256": intake_record["snapshot"].sha256,
                "second_read_equality": True,
            },
        }
    )

    if source_record is None:
        result.update(
            {
                "source_binding_verified": False,
                "source_provenance_verification": "not_required_for_complete_input",
            }
        )
    else:
        require(verification is not None and verification.status == "verified", "positive source verification state drifted")
        result.update(
            {
                "source_bundle_path": source_record["path"],
                "source_binding_verified": True,
                "source_provenance_verification": "verified",
                "input_snapshot_evidence": {
                    **result["input_snapshot_evidence"],
                    "source_bundle_file_sha256": source_record["snapshot"].sha256,
                },
                "source_binding_evidence": verification.checks,
            }
        )
    return result


def _route_without_valid_input(inspected: RuntimeAttachments) -> dict[str, Any]:
    buckets = inspected.buckets
    if buckets["insufficient"]:
        result = _base_route("CE-RUNTIME-EVIDENCE-REQUIRED")
        diagnostics = buckets["insufficient"][0]["diagnostics"]
        result.update(
            {
                "diagnostics": diagnostics,
                "ce_input_path": buckets["insufficient"][0]["path"],
                "source_bundle_required": _source_bundle_required(diagnostics),
                "requested_evidence": diagnostics,
                "warnings": _warnings_for_buckets(buckets),
            }
        )
        return result
    if buckets["invalid"] or buckets["unreadable"]:
        result = _base_route("CE-RUNTIME-INVALID-INPUT")
        result.update(
            {
                "diagnostics": [
                    *[
                        {"path": item["path"], "diagnostics": item.get("diagnostics", [])}
                        for item in buckets["invalid"]
                    ],
                    *buckets["unreadable"],
                ],
                "source_bundle_required": False,
            }
        )
        return result
    if buckets["legacy"]:
        result = _base_route("CE-RUNTIME-LEGACY-INPUT")
        result.update(
            {
                "candidate_paths": [item["path"] for item in buckets["legacy"]],
                "source_bundle_required": False,
            }
        )
        return result
    if buckets["wrong"]:
        result = _base_route("CE-RUNTIME-WRONG-ARTIFACT")
        result.update(
            {
                "candidate_paths": [item["path"] for item in buckets["wrong"]],
                "source_bundle_required": False,
            }
        )
        return result

    result = _base_route("CE-RUNTIME-WAITING-FOR-INPUT")
    result.update(
        {
            "warnings": _warnings_for_buckets(buckets),
            "receipt_evidence": buckets["receipt_like"],
            "source_bundle_present_without_ce_input": bool(buckets["source_bundle"]),
            "source_bundle_required": False,
        }
    )
    return result


def route_request(
    root: Path,
    request: RoutingRequest | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(request, dict):
        request = RoutingRequest.from_value(request)
    root = root.resolve()

    if request.operating_mode == "repository_maintenance":
        return _maintenance_result("explicit_repository_maintenance_mode")

    inspected = _inspect_runtime_attachments(root, request.attachments)

    if len(inspected.valid) > 1:
        result = _base_route("CE-RUNTIME-AMBIGUOUS-INPUT")
        result.update(
            {
                "candidate_paths": [item["path"] for item in inspected.valid],
                "warnings": _warnings_for_buckets(inspected.buckets),
                "source_bundle_required": False,
            }
        )
        return {
            **_authorization_result(True, "ce_runtime", "content_driven_runtime_intake"),
            **result,
        }

    explicit_maintenance = _has_explicit_repository_maintenance_operation(request.message)
    if len(inspected.valid) == 1:
        if explicit_maintenance:
            return _maintenance_result("explicit_repository_maintenance_operation")
        result = _route_one_valid_input(root, inspected)
        return {
            **_authorization_result(True, "ce_runtime", "content_driven_runtime_intake"),
            **result,
        }

    if explicit_maintenance:
        return _maintenance_result("explicit_repository_maintenance_operation")

    result = _route_without_valid_input(inspected)
    return {
        **_authorization_result(True, "ce_runtime", "content_driven_runtime_intake"),
        **result,
    }
