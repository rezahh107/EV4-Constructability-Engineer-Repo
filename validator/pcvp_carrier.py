from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

Severity = Literal["error", "warning", "info", "insufficient_evidence"]
_SEVERITY_ORDER = {
    "error": 0,
    "insufficient_evidence": 1,
    "warning": 2,
    "info": 3,
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    path: str = "$"
    details: dict[str, Any] = field(default_factory=dict)

    def sort_key(self) -> tuple[Any, ...]:
        return (
            self.path,
            _SEVERITY_ORDER[self.severity],
            self.code,
            self.message,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
        }
        if self.details:
            result["details"] = self.details
        return result


def diagnostic(
    code: str,
    severity: Severity,
    message: str,
    path: str = "$",
    **details: Any,
) -> Diagnostic:
    return Diagnostic(code, severity, message, path, details)


def sort_diagnostics(items: list[Diagnostic]) -> list[Diagnostic]:
    return sorted(items, key=lambda item: item.sort_key())


def load_json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

POLICY_ID = "EV4-PCVP"
POLICY_VERSION = "1.0.0"
ARCHITECTURE_LOCK_ID = "EV4-PCVP-ROLL-LOCK-20260727-R1"
CANONICAL_REPOSITORY = "rezahh107/EV4-Decision-Kernel"
CANONICAL_COMMIT = "069a50fa243b01fa578a7c1bcb8864d9e796d34b"
LOCK_PATH = "contracts/pcvp/pcvp-v1.lock.json"
LOCK_SCHEMA_VERSION = "ev4-pcvp-contract-lock.v1"
VENDORED_ROOT = "contracts/pcvp/vendor/decision-kernel/v1.0.0"
PROFILE_PATH = "contracts/pcvp/constructability.profile.yaml"
PROFILE_SHA256 = "00b5e3a1b3490f9b81ef8e81fc1b51b8899f2dd6ba5ba416b38a47a270488461"
EXPECTED_SOURCE_STAGE = "ARCHITECT"
EXPECTED_CONSUMER_STAGE = "CONSTRUCTABILITY_ENGINEER"
SCHEMA_NAMES = (
    "authorization.schema.json",
    "claim.schema.json",
    "effect.schema.json",
    "handoff.schema.json",
)


def inspect_optional_pcvp_carrier(
    artifact: Any,
    repository_root: str | Path = ".",
) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Validate an optional canonical PCVP carrier without activating emission.

    Legacy Architect intake documents remain valid when the carrier is absent.
    When present, the exact carrier is surfaced losslessly only after the pinned
    canonical schemas and mechanically checkable cross-record predicates pass.
    """

    if not isinstance(artifact, dict) or "continuation_assurance" not in artifact:
        return _projection("legacy_absent"), []

    carrier_document = {
        "continuation_assurance": copy.deepcopy(
            artifact.get("continuation_assurance")
        )
    }
    schemas, diagnostics = _load_pinned_schemas(Path(repository_root))
    if schemas is not None:
        runtime_schema = copy.deepcopy(schemas["handoff.schema.json"])
        properties = runtime_schema["properties"]["continuation_assurance"][
            "properties"
        ]
        properties["claims"]["items"] = schemas["claim.schema.json"]
        properties["effects"]["items"] = schemas["effect.schema.json"]
        properties["authorizations"]["items"] = schemas[
            "authorization.schema.json"
        ]
        for error in sorted(
            Draft202012Validator(runtime_schema).iter_errors(carrier_document),
            key=lambda item: (_path(list(item.absolute_path)), item.message),
        ):
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_CARRIER_SCHEMA_INVALID",
                    "error",
                    error.message,
                    _path(list(error.absolute_path)),
                    validator_layer="JSON_SCHEMA",
                )
            )

    if not any(item.severity == "error" for item in diagnostics):
        diagnostics.extend(_mechanical_diagnostics(carrier_document, artifact))

    ordered = sort_diagnostics(_deduplicate(diagnostics))
    if any(item.severity == "error" for item in ordered):
        return _projection("invalid"), ordered

    continuation = carrier_document["continuation_assurance"]
    return (
        _projection(
            "validated",
            policy_id=continuation["policy_id"],
            policy_version=continuation["policy_version"],
            source_stage=continuation["source_stage"],
            canonical_hash=canonical_sha256(carrier_document),
            carrier=carrier_document,
        ),
        ordered,
    )


def _load_pinned_schemas(
    repository_root: Path,
) -> tuple[dict[str, dict[str, Any]] | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    lock_file = repository_root / LOCK_PATH
    try:
        lock = load_json_file(lock_file)
    except (OSError, ValueError, TypeError) as exc:
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_UNAVAILABLE",
                "error",
                "The pinned PCVP contract lock could not be loaded.",
                "$.continuation_assurance",
                error_type=type(exc).__name__,
            )
        )
        return None, diagnostics

    if not isinstance(lock, dict):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_INVALID",
                "error",
                "The PCVP contract lock must be an object.",
                "$.continuation_assurance",
            )
        )
        return None, diagnostics

    expected_identity = {
        "schema_version": LOCK_SCHEMA_VERSION,
        "architecture_lock_id": ARCHITECTURE_LOCK_ID,
    }
    for key, expected in expected_identity.items():
        if lock.get(key) != expected:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_LOCK_IDENTITY_MISMATCH",
                    "error",
                    "The PCVP contract lock identity does not match the frozen rollout.",
                    f"$.{key}",
                    expected=expected,
                    actual=lock.get(key),
                )
            )

    policy = lock.get("policy") if isinstance(lock.get("policy"), dict) else {}
    expected_policy = {
        "id": POLICY_ID,
        "version": POLICY_VERSION,
        "adoption_status": "not_yet_adopted",
        "activation": "NONE",
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_LOCK_IDENTITY_MISMATCH",
                    "error",
                    "The PCVP policy lock identity or dormant state drifted.",
                    f"$.policy.{key}",
                    expected=expected,
                    actual=policy.get(key),
                )
            )

    canonical = (
        lock.get("canonical")
        if isinstance(lock.get("canonical"), dict)
        else {}
    )
    if canonical.get("repository") != CANONICAL_REPOSITORY:
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_IDENTITY_MISMATCH",
                "error",
                "The PCVP canonical owner must remain Decision Kernel.",
                "$.canonical.repository",
                expected=CANONICAL_REPOSITORY,
                actual=canonical.get("repository"),
            )
        )
    if canonical.get("commit_sha") != CANONICAL_COMMIT:
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_IDENTITY_MISMATCH",
                "error",
                "The PCVP contract must remain pinned to the verified immutable commit.",
                "$.canonical.commit_sha",
                expected=CANONICAL_COMMIT,
                actual=canonical.get("commit_sha"),
            )
        )

    profile = lock.get("profile") if isinstance(lock.get("profile"), dict) else {}
    expected_profile = {
        "profile_id": "EV4-PCVP-PROFILE-CONSTRUCTABILITY",
        "profile_version": "1.0.0",
        "repository": "rezahh107/EV4-Constructability-Engineer-Repo",
        "stage_id": EXPECTED_CONSUMER_STAGE,
        "consumes_from": [EXPECTED_SOURCE_STAGE],
        "path": PROFILE_PATH,
        "sha256": PROFILE_SHA256,
        "local_copy_authoritative": False,
    }
    if profile != expected_profile:
        diagnostics.append(
            diagnostic(
                "CE_PCVP_PROFILE_IDENTITY_MISMATCH",
                "error",
                "The repository-correct PCVP profile identity or dormant copy drifted.",
                "$.profile",
                expected=expected_profile,
                actual=profile,
            )
        )
    else:
        profile_file = repository_root / PROFILE_PATH
        try:
            observed_profile_hash = hashlib.sha256(profile_file.read_bytes()).hexdigest()
        except OSError as exc:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_PROFILE_UNAVAILABLE",
                    "error",
                    "The pinned Constructability profile could not be read.",
                    "$.profile.path",
                    error_type=type(exc).__name__,
                )
            )
        else:
            if observed_profile_hash != PROFILE_SHA256:
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_PROFILE_HASH_MISMATCH",
                        "error",
                        "The Constructability profile bytes do not match the immutable lock.",
                        "$.profile.sha256",
                        expected=PROFILE_SHA256,
                        actual=observed_profile_hash,
                    )
                )

    vendored = (
        lock.get("vendored")
        if isinstance(lock.get("vendored"), dict)
        else {}
    )
    if (
        vendored.get("root") != VENDORED_ROOT
        or vendored.get("local_copy_authoritative") is not False
    ):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_IDENTITY_MISMATCH",
                "error",
                "The vendored schema set must remain non-authoritative at the locked path.",
                "$.vendored",
            )
        )

    verification = (
        lock.get("verification")
        if isinstance(lock.get("verification"), dict)
        else {}
    )
    if (
        verification.get("byte_equality_required") is not True
        or verification.get("compare_against_moving_default_branch") is not False
    ):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_IDENTITY_MISMATCH",
                "error",
                "The PCVP lock must require exact bytes at an immutable commit.",
                "$.verification",
            )
        )

    entries = lock.get("files") if isinstance(lock.get("files"), list) else []
    by_name = {
        entry.get("name"): entry
        for entry in entries
        if isinstance(entry, dict)
        and isinstance(entry.get("name"), str)
    }
    if set(by_name) != set(SCHEMA_NAMES) or len(entries) != len(SCHEMA_NAMES):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_LOCK_FILE_SET_INVALID",
                "error",
                "The PCVP lock must cover exactly the four canonical carrier schemas.",
                "$.files",
                expected=list(SCHEMA_NAMES),
                actual=sorted(str(item) for item in by_name),
            )
        )

    schemas: dict[str, dict[str, Any]] = {}
    for name in SCHEMA_NAMES:
        entry = by_name.get(name)
        if not isinstance(entry, dict):
            continue
        expected_hash = entry.get("sha256")
        path = repository_root / VENDORED_ROOT / name
        try:
            content = path.read_bytes()
        except OSError as exc:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_VENDORED_SCHEMA_UNAVAILABLE",
                    "error",
                    "A pinned PCVP schema could not be read.",
                    f"$.files.{name}",
                    error_type=type(exc).__name__,
                )
            )
            continue
        observed_hash = hashlib.sha256(content).hexdigest()
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or observed_hash != expected_hash
        ):
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_VENDORED_SCHEMA_HASH_MISMATCH",
                    "error",
                    "Vendored PCVP schema bytes do not match the immutable lock.",
                    f"$.files.{name}.sha256",
                    expected=expected_hash,
                    actual=observed_hash,
                )
            )
            continue
        try:
            parsed = load_json_file(path)
        except (ValueError, TypeError) as exc:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_VENDORED_SCHEMA_INVALID",
                    "error",
                    "A pinned PCVP schema is not strict UTF-8 JSON.",
                    f"$.files.{name}",
                    error_type=type(exc).__name__,
                )
            )
            continue
        if not isinstance(parsed, dict):
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_VENDORED_SCHEMA_INVALID",
                    "error",
                    "A pinned PCVP schema must be an object.",
                    f"$.files.{name}",
                )
            )
            continue
        schemas[name] = parsed

    if diagnostics or set(schemas) != set(SCHEMA_NAMES):
        return None, diagnostics
    return schemas, diagnostics


def _mechanical_diagnostics(
    document: dict[str, Any],
    artifact: dict[str, Any],
) -> list[Diagnostic]:
    carrier = document["continuation_assurance"]
    claims = carrier["claims"]
    effects = carrier["effects"]
    authorizations = carrier["authorizations"]
    summary = carrier["stage_summary"]
    diagnostics: list[Diagnostic] = []

    if carrier["source_stage"] != EXPECTED_SOURCE_STAGE:
        diagnostics.append(
            diagnostic(
                "CE_PCVP_SOURCE_STAGE_MISMATCH",
                "error",
                "PCVP source_stage does not match the Constructability incoming profile.",
                "$.continuation_assurance.source_stage",
                expected=EXPECTED_SOURCE_STAGE,
                actual=carrier["source_stage"],
                validator_layer="INTEGRATION",
            )
        )

    claim_by_id = {item["claim_id"]: item for item in claims}
    effect_by_id = {item["effect_id"]: item for item in effects}
    auth_by_id = {item["authorization_id"]: item for item in authorizations}
    all_ids = [
        *[item["claim_id"] for item in claims],
        *[item["effect_id"] for item in effects],
        *[item["authorization_id"] for item in authorizations],
    ]
    if len(set(all_ids)) != len(all_ids):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_ID_NOT_GLOBALLY_UNIQUE",
                "error",
                "Claim, Effect and Authorization IDs must be globally unique.",
                "$.continuation_assurance",
                validator_layer="CROSS_RECORD",
            )
        )

    for claim_index, claim in enumerate(claims):
        for dependency_id in claim["dependency_refs"]:
            if dependency_id not in claim_by_id:
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_CLAIM_DEPENDENCY_UNRESOLVED",
                        "error",
                        "Claim dependency does not resolve to another Claim.",
                        f"$.continuation_assurance.claims[{claim_index}].dependency_refs",
                        claim_id=claim["claim_id"],
                        dependency_id=dependency_id,
                        validator_layer="CROSS_RECORD",
                    )
                )

    for effect_index, effect in enumerate(effects):
        effect_path = f"$.continuation_assurance.effects[{effect_index}]"
        for claim_id in effect["depends_on_claim_ids"]:
            if claim_id not in claim_by_id:
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_EFFECT_CLAIM_REF_UNRESOLVED",
                        "error",
                        "Effect dependency does not resolve to a Claim.",
                        f"{effect_path}.depends_on_claim_ids",
                        effect_id=effect["effect_id"],
                        claim_id=claim_id,
                        validator_layer="CROSS_RECORD",
                    )
                )

        auth_ref = effect["authorization_ref"]
        authorization = auth_by_id.get(auth_ref) if auth_ref is not None else None
        if auth_ref is not None and authorization is None:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_EFFECT_AUTH_REF_UNRESOLVED",
                    "error",
                    "Effect Authorization reference does not resolve.",
                    f"{effect_path}.authorization_ref",
                    effect_id=effect["effect_id"],
                    authorization_id=auth_ref,
                    validator_layer="CROSS_RECORD",
                )
            )
        if authorization is not None:
            stage_scope = authorization["stage_scope"]
            if (
                stage_scope["from"] != EXPECTED_SOURCE_STAGE
                or stage_scope["through"] != EXPECTED_CONSUMER_STAGE
            ):
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_EFFECT_AUTH_STAGE_SCOPE_MISMATCH",
                        "error",
                        "Referenced Authorization does not cover the "
                        "Architect-to-Constructability edge.",
                        f"{effect_path}.authorization_ref",
                        effect_id=effect["effect_id"],
                        authorization_id=auth_ref,
                        expected_from=EXPECTED_SOURCE_STAGE,
                        expected_through=EXPECTED_CONSUMER_STAGE,
                        actual=stage_scope,
                        validator_layer="INTEGRATION",
                    )
                )
            if authorization["status"] != "ACTIVE":
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_EFFECT_AUTH_NOT_ACTIVE",
                        "error",
                        "Referenced Authorization is not active.",
                        f"{effect_path}.authorization_ref",
                        effect_id=effect["effect_id"],
                        authorization_id=auth_ref,
                        status=authorization["status"],
                        validator_layer="CROSS_RECORD",
                    )
                )
            covered = (
                effect["effect_id"] in authorization["allowed_effect_ids"]
                or effect["effect_class"]
                in authorization["allowed_effect_classes"]
            )
            if not covered:
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_EFFECT_AUTH_NOT_COVERING",
                        "error",
                        "Referenced Authorization does not cover the Effect.",
                        f"{effect_path}.authorization_ref",
                        effect_id=effect["effect_id"],
                        authorization_id=auth_ref,
                        validator_layer="CROSS_RECORD",
                    )
                )
            if authorization["permitted_scope"] != effect["permitted_scope"]:
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_EFFECT_AUTH_SCOPE_MISMATCH",
                        "error",
                        "Effect scope differs from its referenced Authorization.",
                        f"{effect_path}.permitted_scope",
                        effect_id=effect["effect_id"],
                        authorization_id=auth_ref,
                        validator_layer="CROSS_RECORD",
                    )
                )
            if (
                authorization["basis"] == "SAFE_REVERSIBLE_DEFAULT"
                and effect["effect_class"]
                in {
                    "EXTERNAL_MUTATION",
                    "IRREVERSIBLE_OR_AUTHORITY_BEARING",
                }
            ):
                diagnostics.append(
                    diagnostic(
                        "CE_PCVP_SAFE_DEFAULT_FORBIDDEN_EFFECT",
                        "error",
                        "Safe reversible default cannot authorize this Effect class.",
                        effect_path,
                        effect_id=effect["effect_id"],
                        effect_class=effect["effect_class"],
                        validator_layer="SEMANTIC_POLICY",
                    )
                )

        dependent_claims = [
            claim_by_id[claim_id]
            for claim_id in effect["depends_on_claim_ids"]
            if claim_id in claim_by_id
        ]
        contradicted_critical = any(
            claim["criticality"] == "CRITICAL"
            and claim["applicability_state"] == "APPLICABLE"
            and claim["verification_state"] == "CONTRADICTED"
            for claim in dependent_claims
        )
        if (
            contradicted_critical
            and effect["continuation_state"] != "BLOCKED"
        ):
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_CONTRADICTED_CRITICAL_EFFECT_NOT_BLOCKED",
                    "error",
                    "A critical contradicted dependency must block the Effect.",
                    f"{effect_path}.continuation_state",
                    effect_id=effect["effect_id"],
                    validator_layer="SEMANTIC_POLICY",
                )
            )

    current_effect = effect_by_id.get(summary["current_effect_id"])
    if current_effect is None:
        diagnostics.append(
            diagnostic(
                "CE_PCVP_SUMMARY_EFFECT_REF_UNRESOLVED",
                "error",
                "Stage Summary current_effect_id does not resolve.",
                "$.continuation_assurance.stage_summary.current_effect_id",
                validator_layer="CROSS_RECORD",
            )
        )
        return diagnostics

    current_dependencies = set(current_effect["depends_on_claim_ids"])
    for claim_id in summary["derived_from_claim_ids"]:
        if claim_id not in claim_by_id:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_SUMMARY_CLAIM_REF_UNRESOLVED",
                    "error",
                    "Stage Summary Claim reference does not resolve.",
                    "$.continuation_assurance.stage_summary.derived_from_claim_ids",
                    claim_id=claim_id,
                    validator_layer="CROSS_RECORD",
                )
            )
        elif claim_id not in current_dependencies:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_SUMMARY_CLAIM_NOT_EFFECT_DEPENDENCY",
                    "error",
                    "Stage Summary derives from a Claim outside the current Effect.",
                    "$.continuation_assurance.stage_summary.derived_from_claim_ids",
                    claim_id=claim_id,
                    validator_layer="CROSS_RECORD",
                )
            )

    dependent_claims = [
        claim_by_id[claim_id]
        for claim_id in current_effect["depends_on_claim_ids"]
        if claim_id in claim_by_id
    ]
    critical_contradicted = any(
        claim["criticality"] == "CRITICAL"
        and claim["applicability_state"] == "APPLICABLE"
        and claim["verification_state"] == "CONTRADICTED"
        for claim in dependent_claims
    )
    any_contradicted = any(
        claim["verification_state"] == "CONTRADICTED"
        for claim in dependent_claims
    )
    critical_applicable_not_verified = any(
        claim["criticality"] == "CRITICAL"
        and claim["applicability_state"] == "APPLICABLE"
        and claim["verification_state"] != "VERIFIED"
        for claim in dependent_claims
    )
    material_applicability_undetermined = any(
        claim["criticality"] in {"CRITICAL", "MATERIAL"}
        and claim["applicability_state"] == "UNDETERMINED"
        for claim in dependent_claims
    )
    applicable_unverified = any(
        claim["applicability_state"] == "APPLICABLE"
        and claim["verification_state"] == "UNVERIFIED"
        for claim in dependent_claims
    )
    projection = summary["owner_projection"]

    if projection == "GREEN" and (
        current_effect["continuation_state"] != "CONTINUE"
        or critical_applicable_not_verified
        or any_contradicted
        or material_applicability_undetermined
    ):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_GREEN_PROJECTION_INVALID",
                "error",
                "GREEN is not derivable from the current Effect dependencies.",
                "$.continuation_assurance.stage_summary.owner_projection",
                validator_layer="SEMANTIC_POLICY",
            )
        )

    if projection == "YELLOW":
        expected_substate = (
            "CONTINUATION_AVAILABLE"
            if current_effect["continuation_state"] == "CONTINUE"
            else (
                "OWNER_CHOICE_REQUIRED"
                if current_effect["continuation_state"]
                == "AUTHORIZATION_REQUIRED"
                else None
            )
        )
        if (
            expected_substate is None
            or summary["yellow_substate"] != expected_substate
            or (
                not applicable_unverified
                and current_effect["continuation_state"]
                != "AUTHORIZATION_REQUIRED"
            )
            or critical_contradicted
        ):
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_YELLOW_PROJECTION_INVALID",
                    "error",
                    "YELLOW projection or substate is not derivable.",
                    "$.continuation_assurance.stage_summary",
                    validator_layer="SEMANTIC_POLICY",
                )
            )

    if (
        projection == "RED"
        and current_effect["continuation_state"] != "BLOCKED"
    ):
        diagnostics.append(
            diagnostic(
                "CE_PCVP_RED_WITH_NON_BLOCKED_EFFECT",
                "error",
                "RED requires a BLOCKED current Effect.",
                "$.continuation_assurance.stage_summary.owner_projection",
                validator_layer="SEMANTIC_POLICY",
            )
        )

    if (
        current_effect["continuation_state"] == "BLOCKED"
        or critical_contradicted
    ) and projection != "RED":
        diagnostics.append(
            diagnostic(
                "CE_PCVP_REQUIRED_RED_PROJECTION_MISSING",
                "error",
                "A blocked or critically contradicted current Effect requires RED.",
                "$.continuation_assurance.stage_summary.owner_projection",
                validator_layer="SEMANTIC_POLICY",
            )
        )
    return diagnostics


def _projection(
    status: str,
    *,
    policy_id: str | None = None,
    policy_version: str | None = None,
    source_stage: str | None = None,
    canonical_hash: str | None = None,
    carrier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "compatibility_mode": "DUAL_READ",
        "canonical_owner": CANONICAL_REPOSITORY,
        "canonical_commit": CANONICAL_COMMIT,
        "architecture_lock_id": ARCHITECTURE_LOCK_ID,
        "adoption_status": "not_yet_adopted",
        "activation_effect": "NONE",
    }
    if status == "validated":
        result.update(
            {
                "policy_id": policy_id,
                "policy_version": policy_version,
                "source_stage": source_stage,
                "canonical_sha256": canonical_hash,
                "carrier": copy.deepcopy(carrier),
            }
        )
    return result


def _path(parts: list[Any]) -> str:
    value = "$"
    for part in parts:
        value += f"[{part}]" if isinstance(part, int) else f".{part}"
    return value


def _deduplicate(items: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[tuple[str, str, str]] = set()
    result: list[Diagnostic] = []
    for item in items:
        key = (item.code, item.path, item.message)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


__all__ = [
    "ARCHITECTURE_LOCK_ID",
    "CANONICAL_COMMIT",
    "CANONICAL_REPOSITORY",
    "POLICY_ID",
    "POLICY_VERSION",
    "inspect_optional_pcvp_carrier",
]
