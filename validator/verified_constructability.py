from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator

from .project_gate_export import CE_REPOSITORY, canonical_bytes

REVIEW_DRAFT_SCHEMA_ID: Final = "ev4-ce-review-draft@1.0.0"
VERIFIED_PAYLOAD_SCHEMA_ID: Final = "ev4-ce-stage-payload@1.1.0"
VERIFIED_PAYLOAD_SCHEMA_VERSION: Final = "1.1.0"
BUILDER_PACKAGE_SCHEMA_ID: Final = "ev4-builder-executable-package@1.0.0"
RESOLVER_ID: Final = "ev4-ce-proof-resolver"
RESOLVER_VERSION: Final = "1.0.0"

RESOLVED_STATES: Final = {
    "VERIFIED",
    "ATTRIBUTED_SUPPORTED",
    "UNVERIFIED",
    "INSUFFICIENT_EVIDENCE",
    "ARCHITECT_DECISION_REQUIRED",
    "DOWNSTREAM_VALIDATION_REQUIRED",
    "REJECTED_PROVENANCE_MISMATCH",
    "NOT_APPLICABLE",
}

PROHIBITED_DRAFT_KEYS: Final = {
    "geometry_proven",
    "overlay_strategy_proven",
    "responsive_behavior",
    "accessibility_evidenced",
    "ui_control_evidence_present",
    "interaction_approved",
    "dynamic_loop_approved",
    "constructability_status",
    "builder_package_status",
    "builder_package_emitted",
    "handoff",
    "payload_status",
    "verification_status",
    "state",
    "source_sha256",
    "run_id",
}


CLAIM_POLICIES: Final[dict[str, dict[str, Any]]] = {
    "geometry": {
        "semantic_class": "COMPUTED_FACT",
        "authority_owner": "CE",
        "subject_binding_required": True,
        "admissible_evidence_modes": (
            "VERIFIED_ARTIFACT",
            "ATTRIBUTED_ENGINEERING_JUDGMENT",
        ),
        "required_semantics": (
            "subject_ref",
            "anchor_model",
            "coordinate_or_layout_model",
            "derivation_method",
        ),
        "derivation_rule": "verified_or_attributed_supported",
        "unavailable_evidence_behavior": "INSUFFICIENT_EVIDENCE",
        "may_authorize_builder_handoff": True,
    },
    "overlay_strategy": {
        "semantic_class": "COMPUTED_FACT",
        "authority_owner": "CE",
        "subject_binding_required": True,
        "admissible_evidence_modes": (
            "VERIFIED_ARTIFACT",
            "ATTRIBUTED_ENGINEERING_JUDGMENT",
        ),
        "required_semantics": (
            "subject_ref",
            "containment_model",
            "positioning_model",
            "stacking_model",
            "derivation_method",
        ),
        "derivation_rule": "verified_or_attributed_supported",
        "unavailable_evidence_behavior": "INSUFFICIENT_EVIDENCE",
        "may_authorize_builder_handoff": True,
    },
    "responsive_behavior": {
        "semantic_class": "TOOL_EXECUTION",
        "authority_owner": "downstream_runtime_validation",
        "subject_binding_required": True,
        "admissible_evidence_modes": (
            "VERIFIED_TOOL_EXECUTION",
            "VERIFIED_ARTIFACT",
        ),
        "required_semantics": ("subject_ref", "target_identity", "result_digest"),
        "derivation_rule": "runtime_evidence_only",
        "unavailable_evidence_behavior": "DOWNSTREAM_VALIDATION_REQUIRED",
        "may_authorize_builder_handoff": False,
    },
    "ui_control_path": {
        "semantic_class": "OBSERVED_FACT",
        "authority_owner": "CE",
        "subject_binding_required": True,
        "admissible_evidence_modes": ("VERIFIED_ARTIFACT",),
        "required_semantics": ("subject_ref", "source_identity", "source_bytes_sha256"),
        "derivation_rule": "verified_artifact_only",
        "unavailable_evidence_behavior": "INSUFFICIENT_EVIDENCE",
        "may_authorize_builder_handoff": True,
    },
    "accessibility": {
        "semantic_class": "TOOL_EXECUTION",
        "authority_owner": "downstream_runtime_validation",
        "subject_binding_required": True,
        "admissible_evidence_modes": (
            "VERIFIED_TOOL_EXECUTION",
            "VERIFIED_ARTIFACT",
        ),
        "required_semantics": ("subject_ref", "target_identity", "result_digest"),
        "derivation_rule": "compatible_runtime_evidence_only",
        "unavailable_evidence_behavior": "DOWNSTREAM_VALIDATION_REQUIRED",
        "may_authorize_builder_handoff": False,
    },
    "dynamic_loop_approval": {
        "semantic_class": "ARCHITECT_DECISION",
        "authority_owner": "Architect",
        "subject_binding_required": True,
        "admissible_evidence_modes": ("VERIFIED_ARCHITECT_DECISION",),
        "required_semantics": (
            "subject_ref",
            "decision_ref",
            "selected_candidate_id",
            "source_digest",
        ),
        "derivation_rule": "architect_decision_only",
        "unavailable_evidence_behavior": "ARCHITECT_DECISION_REQUIRED",
        "may_authorize_builder_handoff": True,
    },
    "interaction_approval": {
        "semantic_class": "ARCHITECT_DECISION",
        "authority_owner": "Architect",
        "subject_binding_required": True,
        "admissible_evidence_modes": ("VERIFIED_ARCHITECT_DECISION",),
        "required_semantics": (
            "subject_ref",
            "decision_ref",
            "selected_candidate_id",
            "source_digest",
        ),
        "derivation_rule": "architect_decision_only",
        "unavailable_evidence_behavior": "ARCHITECT_DECISION_REQUIRED",
        "may_authorize_builder_handoff": True,
    },
    "asset_source": {
        "semantic_class": "OBSERVED_FACT",
        "authority_owner": "CE",
        "subject_binding_required": True,
        "admissible_evidence_modes": ("VERIFIED_ARTIFACT",),
        "required_semantics": ("subject_ref", "source_identity", "source_bytes_sha256"),
        "derivation_rule": "verified_artifact_only",
        "unavailable_evidence_behavior": "INSUFFICIENT_EVIDENCE",
        "may_authorize_builder_handoff": True,
    },
    "placeholder_policy": {
        "semantic_class": "ATTRIBUTED_ENGINEERING_JUDGMENT",
        "authority_owner": "CE",
        "subject_binding_required": True,
        "admissible_evidence_modes": ("ATTRIBUTED_ENGINEERING_JUDGMENT",),
        "required_semantics": ("subject_ref", "premises", "derivation_method"),
        "derivation_rule": "attributed_supported_only",
        "unavailable_evidence_behavior": "INSUFFICIENT_EVIDENCE",
        "may_authorize_builder_handoff": True,
    },
    "QA": {
        "semantic_class": "TOOL_EXECUTION",
        "authority_owner": "downstream_runtime_validation",
        "subject_binding_required": True,
        "admissible_evidence_modes": ("VERIFIED_TOOL_EXECUTION",),
        "required_semantics": ("subject_ref", "target_identity", "result_digest"),
        "derivation_rule": "verified_tool_execution_only",
        "unavailable_evidence_behavior": "DOWNSTREAM_VALIDATION_REQUIRED",
        "may_authorize_builder_handoff": False,
    },
    "constructability_status": {
        "semantic_class": "COMPUTED_FACT",
        "authority_owner": "CE runtime",
        "subject_binding_required": False,
        "admissible_evidence_modes": (),
        "required_semantics": (),
        "derivation_rule": "derive_from_claim_resolution",
        "unavailable_evidence_behavior": "blocked",
        "may_authorize_builder_handoff": True,
    },
    "builder_eligibility": {
        "semantic_class": "COMPUTED_FACT",
        "authority_owner": "CE runtime",
        "subject_binding_required": False,
        "admissible_evidence_modes": (),
        "required_semantics": (),
        "derivation_rule": "derive_from_constructability_and_package",
        "unavailable_evidence_behavior": "blocked",
        "may_authorize_builder_handoff": True,
    },
}


class CapabilityError(TypeError):
    """Raised when a caller attempts to forge or misuse an opaque capability."""


class DraftValidationError(ValueError):
    """Raised when a CE Review Draft violates the non-authoritative input contract."""


class EvidenceVerificationError(ValueError):
    """Raised when source identity, digest, or subject binding cannot be verified."""


class _OpaqueCapability:
    __slots__ = ("_record_bytes", "_fingerprint", "_production")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __copy__(self) -> object:
        raise CapabilityError("Opaque capabilities cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise CapabilityError("Opaque capabilities cannot be deep-copied")


class VerifiedArtifactEvidence(_OpaqueCapability):
    __slots__ = ()


class VerifiedToolExecutionEvidence(_OpaqueCapability):
    __slots__ = ()


class VerifiedArchitectDecision(_OpaqueCapability):
    __slots__ = ()


class AttributedEngineeringJudgment(_OpaqueCapability):
    __slots__ = ()


class DownstreamTestObligation(_OpaqueCapability):
    __slots__ = ()


class VerifiedConstructabilityProof(_OpaqueCapability):
    __slots__ = ()


class VerifiedArchitectIntake(_OpaqueCapability):
    __slots__ = ()


class VerifiedSourceBundle(_OpaqueCapability):
    __slots__ = ()


class VerifiedCEStagePayload(_OpaqueCapability):
    __slots__ = ()


_CAPABILITY_REGISTRY: dict[int, tuple[object, type[_OpaqueCapability], str, bool]] = {}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_record_bytes(record: Mapping[str, Any]) -> bytes:
    return canonical_bytes(record)


def _mint(
    capability_type: type[_OpaqueCapability],
    record: Mapping[str, Any],
    *,
    production: bool = True,
) -> _OpaqueCapability:
    record_bytes = _canonical_record_bytes(record)
    fingerprint = _sha256(capability_type.__name__.encode("utf-8") + b"\0" + record_bytes)
    capability = object.__new__(capability_type)
    object.__setattr__(capability, "_record_bytes", record_bytes)
    object.__setattr__(capability, "_fingerprint", fingerprint)
    object.__setattr__(capability, "_production", production)
    _CAPABILITY_REGISTRY[id(capability)] = (
        capability,
        capability_type,
        fingerprint,
        production,
    )
    return capability


def _capability_record(
    value: object,
    expected_type: type[_OpaqueCapability],
    *,
    require_production: bool = True,
) -> dict[str, Any]:
    if type(value) is not expected_type:
        raise CapabilityError(f"Expected exact {expected_type.__name__} capability")
    registered = _CAPABILITY_REGISTRY.get(id(value))
    if registered is None or registered[0] is not value or registered[1] is not expected_type:
        raise CapabilityError("Capability was not minted by the official CE runtime")
    fingerprint = _sha256(
        expected_type.__name__.encode("utf-8") + b"\0" + value._record_bytes  # type: ignore[attr-defined]
    )
    if registered[2] != fingerprint or value._fingerprint != fingerprint:  # type: ignore[attr-defined]
        raise CapabilityError("Capability fingerprint mismatch")
    if require_production and (not registered[3] or value._production is not True):  # type: ignore[attr-defined]
        raise CapabilityError("Test-only capability cannot authorize production")
    decoded = json.loads(value._record_bytes)  # type: ignore[attr-defined]
    if not isinstance(decoded, dict):
        raise CapabilityError("Capability record is invalid")
    return decoded


def capability_record(value: object) -> dict[str, Any]:
    """Return a defensive copy of an official capability record for diagnostics."""
    if not isinstance(value, _OpaqueCapability):
        raise CapabilityError("Value is not an opaque CE capability")
    return copy.deepcopy(_capability_record(value, type(value)))


def _json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise EvidenceVerificationError("Architect decision_ref must be a JSON Pointer")
    current = document
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise EvidenceVerificationError(f"Architect decision path not found: {pointer}") from exc
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise EvidenceVerificationError(f"Architect decision path not found: {pointer}")
    return current


def _walk_for_prohibited_keys(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in PROHIBITED_DRAFT_KEYS or key.endswith("_proven"):
                found.append(child_path)
            found.extend(_walk_for_prohibited_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_for_prohibited_keys(child, f"{path}[{index}]"))
    return found


def validate_review_draft(
    draft: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    schema_path = repo_root / "schemas/ce_review_draft.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(draft),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        raise DraftValidationError(f"{path}: {error.message}")
    prohibited = _walk_for_prohibited_keys(draft)
    if prohibited:
        raise DraftValidationError(
            "CE Review Draft contains authority-bearing caller fields: " + ", ".join(prohibited)
        )
    return copy.deepcopy(dict(draft))


def verify_architect_intake(
    *,
    intake: Mapping[str, Any],
    intake_bytes: bytes,
    source_ref: str,
) -> VerifiedArchitectIntake:
    if intake.get("schema_id") != "ev4-ce-architect-stage-intake@1.1.0":
        raise EvidenceVerificationError("Unsupported Architect intake schema")
    selected = intake.get("selected_architecture")
    preserved = intake.get("architect_intent_preserved")
    transition = intake.get("project_gate_transition")
    if not isinstance(selected, dict) or not isinstance(preserved, dict) or not isinstance(transition, dict):
        raise EvidenceVerificationError("Architect intake identity surfaces are incomplete")
    class_intent = preserved.get("class_intent")
    if not isinstance(class_intent, dict):
        raise EvidenceVerificationError("Architect class intent is missing")
    candidate = selected.get("selected_candidate_id")
    classes = class_intent.get("approved_class_names")
    if not isinstance(candidate, str) or not candidate or not isinstance(classes, list):
        raise EvidenceVerificationError("Architect candidate or class identity is invalid")
    record = {
        "assurance_kind": "VERIFIED_ARTIFACT",
        "source_ref": source_ref,
        "schema_id": str(intake.get("schema_id")),
        "schema_version": str(intake.get("schema_version")),
        "selected_candidate_id": candidate,
        "approved_class_names": classes,
        "source_canonical_sha256": _sha256(canonical_bytes(intake)),
        "source_bytes_sha256": _sha256(intake_bytes),
        "source_bundle_id": transition.get("source_bundle_id"),
        "source_bundle_hash": transition.get("source_bundle_hash"),
        "intake": dict(intake),
        "producer": {
            "kind": "CE_VERIFIED_ADAPTER",
            "tool_or_method": "verify_architect_intake",
        },
    }
    return _mint(VerifiedArchitectIntake, record)  # type: ignore[return-value]


def verify_source_bundle(
    *,
    source_bundle: Mapping[str, Any],
    source_bundle_bytes: bytes,
    verified_intake: VerifiedArchitectIntake,
    source_ref: str,
) -> VerifiedSourceBundle:
    intake_record = _capability_record(verified_intake, VerifiedArchitectIntake)
    expected_hash_record = intake_record.get("source_bundle_hash")
    if not isinstance(expected_hash_record, dict):
        raise EvidenceVerificationError("Architect intake does not retain source bundle hash")
    expected_hash = expected_hash_record.get("value")
    observed_hash = _sha256(canonical_bytes(source_bundle))
    if expected_hash != observed_hash:
        raise EvidenceVerificationError("Source bundle canonical digest does not match intake")
    expected_id = intake_record.get("source_bundle_id")
    observed_id = source_bundle.get("bundle_id")
    if expected_id != observed_id:
        raise EvidenceVerificationError("Source bundle identity does not match intake")
    record = {
        "assurance_kind": "VERIFIED_ARTIFACT",
        "source_ref": source_ref,
        "source_identity": observed_id,
        "source_canonical_sha256": observed_hash,
        "source_bytes_sha256": _sha256(source_bundle_bytes),
        "selected_candidate_id": intake_record["selected_candidate_id"],
        "intake_canonical_sha256": intake_record["source_canonical_sha256"],
        "source_bundle": dict(source_bundle),
        "producer": {
            "kind": "CE_VERIFIED_ADAPTER",
            "tool_or_method": "verify_source_bundle",
        },
    }
    return _mint(VerifiedSourceBundle, record)  # type: ignore[return-value]


def verify_repo_artifact(
    *,
    repo_root: Path,
    source_ref: str,
    claim_id: str,
    payload_id: str,
    subject_ref: str,
    source_identity: str | None = None,
) -> VerifiedArtifactEvidence:
    if claim_id not in CLAIM_POLICIES:
        raise EvidenceVerificationError(f"Unknown claim policy: {claim_id}")
    root = repo_root.resolve(strict=True)
    candidate = Path(source_ref)
    path = candidate if candidate.is_absolute() else root / candidate
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceVerificationError("Verified repository artifact must remain inside repo root") from exc
    if not resolved.is_file():
        raise EvidenceVerificationError(f"Verified artifact is not a file: {source_ref}")
    raw = resolved.read_bytes()
    record = {
        "mode": "VERIFIED_ARTIFACT",
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "payload_id": payload_id,
        "source_ref": relative,
        "source_identity": source_identity or relative,
        "source_bytes_sha256": _sha256(raw),
        "target_binding": {"payload_id": payload_id, "subject_ref": subject_ref},
        "producer": {
            "kind": "CE_VERIFIED_ADAPTER",
            "repository": CE_REPOSITORY,
            "tool_or_method": "verify_repo_artifact",
        },
        "verification": {"method": "exact_file_bytes_sha256", "status": "VERIFIED"},
    }
    return _mint(VerifiedArtifactEvidence, record)  # type: ignore[return-value]


def record_tool_execution(
    *,
    claim_id: str,
    payload_id: str,
    subject_ref: str,
    tool_identity: str,
    tool_version_or_commit: str,
    method_or_command: str,
    target_identity: str,
    started_at: str,
    completed_at: str,
    exit_code: int,
    result: Mapping[str, Any],
) -> VerifiedToolExecutionEvidence:
    if claim_id not in CLAIM_POLICIES:
        raise EvidenceVerificationError(f"Unknown claim policy: {claim_id}")
    if exit_code != 0:
        raise EvidenceVerificationError("Failed tool execution cannot mint verified evidence")
    record = {
        "mode": "VERIFIED_TOOL_EXECUTION",
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "payload_id": payload_id,
        "tool_identity": tool_identity,
        "tool_version_or_commit": tool_version_or_commit,
        "method_or_command": method_or_command,
        "target_identity": target_identity,
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "result_digest": _sha256(canonical_bytes(result)),
        "target_binding": {"payload_id": payload_id, "subject_ref": subject_ref},
        "producer": {
            "kind": "CE_TOOL_EXECUTION_ADAPTER",
            "repository": CE_REPOSITORY,
            "tool_or_method": "record_tool_execution",
        },
        "verification": {"method": "runtime_captured_execution", "status": "VERIFIED"},
    }
    return _mint(VerifiedToolExecutionEvidence, record)  # type: ignore[return-value]


def verify_architect_decision(
    *,
    verified_intake: VerifiedArchitectIntake,
    claim_id: str,
    payload_id: str,
    subject_ref: str,
    decision_ref: str,
) -> VerifiedArchitectDecision:
    if claim_id not in {"dynamic_loop_approval", "interaction_approval"}:
        raise EvidenceVerificationError("Claim is not Architect-owned")
    intake_record = _capability_record(verified_intake, VerifiedArchitectIntake)
    decision = _json_pointer(intake_record["intake"], decision_ref)
    if decision is not True:
        raise EvidenceVerificationError("Architect decision is not an explicit approved=true fact")
    record = {
        "mode": "VERIFIED_ARCHITECT_DECISION",
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "payload_id": payload_id,
        "source_intake_identity": intake_record["source_ref"],
        "decision_ref": decision_ref,
        "selected_candidate_id": intake_record["selected_candidate_id"],
        "source_digest": intake_record["source_canonical_sha256"],
        "target_binding": {"payload_id": payload_id, "subject_ref": subject_ref},
        "producer": {
            "kind": "CE_VERIFIED_ADAPTER",
            "tool_or_method": "verify_architect_decision",
        },
        "verification": {"method": "intake_json_pointer_and_digest", "status": "VERIFIED"},
    }
    return _mint(VerifiedArchitectDecision, record)  # type: ignore[return-value]


def attribute_engineering_judgment(
    *,
    claim_id: str,
    payload_id: str,
    subject_ref: str,
    reviewer_identity: str,
    premises: Sequence[str],
    derivation_method: str,
    limitations: Sequence[str],
    semantic_details: Mapping[str, Any],
) -> AttributedEngineeringJudgment:
    policy = CLAIM_POLICIES.get(claim_id)
    if policy is None or "ATTRIBUTED_ENGINEERING_JUDGMENT" not in policy["admissible_evidence_modes"]:
        raise EvidenceVerificationError(f"Claim policy does not admit CE judgment: {claim_id}")
    if not reviewer_identity or not premises or not derivation_method:
        raise EvidenceVerificationError("Attributed judgment requires reviewer, premises, and method")
    record = {
        "mode": "ATTRIBUTED_ENGINEERING_JUDGMENT",
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "payload_id": payload_id,
        "reviewer_identity": reviewer_identity,
        "premises": list(premises),
        "derivation_method": derivation_method,
        "limitations": list(limitations),
        "semantic_details": dict(semantic_details),
        "target_binding": {"payload_id": payload_id, "subject_ref": subject_ref},
        "producer": {
            "kind": "CE_ATTRIBUTION_ADAPTER",
            "tool_or_method": "attribute_engineering_judgment",
        },
        "verification": {"method": "attribution_not_external_verification", "status": "ATTRIBUTED"},
    }
    return _mint(AttributedEngineeringJudgment, record)  # type: ignore[return-value]


def create_downstream_test_obligation(
    *,
    claim_id: str,
    payload_id: str,
    subject_ref: str,
    consumer_stage: str,
    required_test: str,
    blocking_behavior: str,
    completion_criteria: str,
) -> DownstreamTestObligation:
    if claim_id not in CLAIM_POLICIES:
        raise EvidenceVerificationError(f"Unknown claim policy: {claim_id}")
    record = {
        "mode": "DOWNSTREAM_TEST_OBLIGATION",
        "claim_id": claim_id,
        "claim_ref": f"{subject_ref}:{claim_id}",
        "subject_ref": subject_ref,
        "payload_id": payload_id,
        "consumer_stage": consumer_stage,
        "required_test": required_test,
        "blocking_behavior": blocking_behavior,
        "completion_criteria": completion_criteria,
        "target_binding": {"payload_id": payload_id, "subject_ref": subject_ref},
        "producer": {
            "kind": "CE_OBLIGATION_ADAPTER",
            "tool_or_method": "create_downstream_test_obligation",
        },
        "verification": {"method": "obligation_record", "status": "UNPROVEN"},
    }
    return _mint(DownstreamTestObligation, record)  # type: ignore[return-value]


def _proof_from_evidence(
    evidence: object,
    *,
    payload_id: str,
    subject_ref: str,
    claim_id: str,
) -> VerifiedConstructabilityProof:
    allowed_types: dict[type[_OpaqueCapability], str] = {
        VerifiedArtifactEvidence: "VERIFIED_ARTIFACT",
        VerifiedToolExecutionEvidence: "VERIFIED_TOOL_EXECUTION",
        VerifiedArchitectDecision: "VERIFIED_ARCHITECT_DECISION",
        AttributedEngineeringJudgment: "ATTRIBUTED_ENGINEERING_JUDGMENT",
    }
    evidence_type = type(evidence)
    mode = allowed_types.get(evidence_type)
    if mode is None:
        raise CapabilityError("Unsupported evidence capability type")
    record = _capability_record(evidence, evidence_type)
    if record.get("payload_id") != payload_id or record.get("subject_ref") != subject_ref:
        raise EvidenceVerificationError("Evidence target binding mismatch")
    if record.get("claim_id") != claim_id:
        raise EvidenceVerificationError("Evidence claim binding mismatch")
    policy = CLAIM_POLICIES[claim_id]
    if mode not in policy["admissible_evidence_modes"]:
        raise EvidenceVerificationError("Evidence mode is incompatible with claim policy")
    proof_record = {
        "mode": mode,
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "payload_id": payload_id,
        "evidence_digest": _sha256(canonical_bytes(record)),
        "evidence": record,
        "policy": {
            "authority_owner": policy["authority_owner"],
            "derivation_rule": policy["derivation_rule"],
            "may_authorize_builder_handoff": policy["may_authorize_builder_handoff"],
        },
    }
    return _mint(VerifiedConstructabilityProof, proof_record)  # type: ignore[return-value]


def _resolution_state(mode: str) -> str:
    if mode == "ATTRIBUTED_ENGINEERING_JUDGMENT":
        return "ATTRIBUTED_SUPPORTED"
    return "VERIFIED"


def _runtime_evidence_entry(record: Mapping[str, Any], index: int) -> dict[str, Any]:
    mode = str(record.get("mode"))
    source: dict[str, Any]
    if mode == "VERIFIED_ARTIFACT":
        source = {
            "type": "repo_path",
            "reference": record["source_ref"],
            "bytes_sha256": record["source_bytes_sha256"],
        }
    elif mode == "VERIFIED_ARCHITECT_DECISION":
        source = {
            "type": "architect_intake",
            "reference": record["decision_ref"],
            "bytes_sha256": record["source_digest"],
        }
    elif mode == "VERIFIED_TOOL_EXECUTION":
        source = {
            "type": "tool_execution",
            "reference": record["target_identity"],
            "bytes_sha256": record["result_digest"],
        }
    elif mode == "ATTRIBUTED_ENGINEERING_JUDGMENT":
        source = {
            "type": "attributed_judgment",
            "reference": record["reviewer_identity"],
        }
    else:
        source = {
            "type": "downstream_obligation",
            "reference": record.get("claim_ref", record.get("claim_id", "unknown")),
        }
    return {
        "evidence_id": f"ce-runtime-evidence-{index + 1}",
        "claim_refs": [f"{record['subject_ref']}:{record['claim_id']}"],
        "subject_ref": record["subject_ref"],
        "assurance_kind": mode,
        "source": source,
        "producer": record.get("producer", {}),
        "target_binding": record["target_binding"],
        "verification": record.get("verification", {}),
        "limitations": list(record.get("limitations") or []),
    }


def _claim_request_map(node: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    requests = node.get("requested_claims")
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(requests, list):
        return result
    for item in requests:
        if isinstance(item, str):
            result[item] = {"claim_id": item, "required": True}
        elif isinstance(item, dict) and isinstance(item.get("claim_id"), str):
            result[item["claim_id"]] = dict(item)
    return result


def _candidate_sources(node: Mapping[str, Any], claim_id: str) -> list[dict[str, Any]]:
    refs = node.get("candidate_source_refs")
    if not isinstance(refs, list):
        return []
    return [
        dict(item)
        for item in refs
        if isinstance(item, dict) and item.get("claim_id") == claim_id
    ]


def _judgment_semantics(node: Mapping[str, Any], claim_id: str) -> dict[str, Any]:
    details = node.get("claim_semantics")
    if isinstance(details, dict) and isinstance(details.get(claim_id), dict):
        return dict(details[claim_id])
    return {}


def _derive_builder_actions(draft: Mapping[str, Any]) -> list[dict[str, Any]]:
    proposals = draft.get("builder_action_proposals")
    if not isinstance(proposals, list):
        return []
    actions: list[dict[str, Any]] = []
    for item in proposals:
        if not isinstance(item, dict):
            continue
        actions.append(
            {
                "action_id": item["action_id"],
                "action_type": item["action_type"],
                "target_node": item["target_node"],
                "parameters": copy.deepcopy(item.get("parameters") or {}),
                "requires_decision": False,
            }
        )
    return actions


def assemble_verified_ce_stage_payload(
    *,
    draft: Mapping[str, Any],
    verified_intake: VerifiedArchitectIntake,
    verified_source_bundle: VerifiedSourceBundle,
    repo_root: Path,
    proofs: Sequence[object] = (),
    tool_evidence: Sequence[VerifiedToolExecutionEvidence] = (),
) -> VerifiedCEStagePayload:
    clean_draft = validate_review_draft(draft, repo_root=repo_root)
    intake_record = _capability_record(verified_intake, VerifiedArchitectIntake)
    bundle_record = _capability_record(verified_source_bundle, VerifiedSourceBundle)
    if bundle_record.get("intake_canonical_sha256") != intake_record.get("source_canonical_sha256"):
        raise EvidenceVerificationError("Verified source bundle is stale or bound to another intake")
    if bundle_record.get("selected_candidate_id") != intake_record.get("selected_candidate_id"):
        raise EvidenceVerificationError("Verified source bundle candidate binding mismatch")

    review_id = str(clean_draft["review_id"])
    payload_seed = {
        "review_id": review_id,
        "intake": intake_record["source_canonical_sha256"],
        "source_bundle": bundle_record["source_canonical_sha256"],
    }
    payload_id = f"ce-verified-{_sha256(canonical_bytes(payload_seed))}"
    run_id = f"ce-run-{_sha256(canonical_bytes({'payload_id': payload_id}))[:24]}"

    supplied_capabilities = list(proofs) + list(tool_evidence)
    supplied_by_key: dict[tuple[str, str], list[object]] = {}
    for item in supplied_capabilities:
        item_type = type(item)
        if item_type not in {
            VerifiedArtifactEvidence,
            VerifiedToolExecutionEvidence,
            VerifiedArchitectDecision,
            AttributedEngineeringJudgment,
            VerifiedConstructabilityProof,
        }:
            raise CapabilityError("Plain dictionaries and lookalike proofs are forbidden")
        if item_type is VerifiedConstructabilityProof:
            proof_record = _capability_record(item, VerifiedConstructabilityProof)
            if proof_record.get("payload_id") != payload_id:
                raise EvidenceVerificationError("Proof is bound to another Payload")
            key = (str(proof_record["subject_ref"]), str(proof_record["claim_id"]))
        else:
            evidence_record = _capability_record(item, item_type)
            if evidence_record.get("payload_id") != payload_id:
                raise EvidenceVerificationError("Evidence is bound to another Payload")
            key = (str(evidence_record["subject_ref"]), str(evidence_record["claim_id"]))
        supplied_by_key.setdefault(key, []).append(item)

    reviewed_nodes: list[dict[str, Any]] = []
    authority_resolution: list[dict[str, Any]] = []
    runtime_records: list[dict[str, Any]] = []
    unresolved_evidence: list[dict[str, Any]] = []
    generated_obligations: list[DownstreamTestObligation] = []
    blocking_dependencies: list[str] = []

    for node in clean_draft["reviewed_nodes"]:
        node_id = str(node["node_id"])
        requests = _claim_request_map(node)
        node_resolutions: dict[str, str] = {}
        node_evidence_ids: dict[str, list[str]] = {}
        for claim_id, request in requests.items():
            policy = CLAIM_POLICIES.get(claim_id)
            if policy is None or claim_id in {"constructability_status", "builder_eligibility"}:
                raise DraftValidationError(f"Unknown or runtime-derived requested claim: {claim_id}")
            candidates: list[object] = list(supplied_by_key.get((node_id, claim_id), []))

            for source in _candidate_sources(node, claim_id):
                mode = source.get("mode")
                try:
                    if mode == "VERIFIED_ARTIFACT":
                        candidates.append(
                            verify_repo_artifact(
                                repo_root=repo_root,
                                source_ref=str(source["source_ref"]),
                                claim_id=claim_id,
                                payload_id=payload_id,
                                subject_ref=node_id,
                                source_identity=str(source.get("source_identity") or source["source_ref"]),
                            )
                        )
                    elif mode == "VERIFIED_ARCHITECT_DECISION":
                        candidates.append(
                            verify_architect_decision(
                                verified_intake=verified_intake,
                                claim_id=claim_id,
                                payload_id=payload_id,
                                subject_ref=node_id,
                                decision_ref=str(source["decision_ref"]),
                            )
                        )
                except (CapabilityError, EvidenceVerificationError, KeyError) as exc:
                    authority_resolution.append(
                        {
                            "claim_ref": f"{node_id}:{claim_id}",
                            "claim_id": claim_id,
                            "subject_ref": node_id,
                            "policy": policy,
                            "submitted_judgment": None,
                            "verified_evidence": [],
                            "resolved_state": "REJECTED_PROVENANCE_MISMATCH",
                            "limitations": [str(exc)],
                            "downstream_obligation": None,
                        }
                    )

            if (
                not candidates
                and "ATTRIBUTED_ENGINEERING_JUDGMENT" in policy["admissible_evidence_modes"]
            ):
                rationale = str(node.get("engineering_rationale") or "").strip()
                premises = [str(item) for item in (node.get("assumptions") or []) if str(item).strip()]
                semantics = _judgment_semantics(node, claim_id)
                if rationale and premises and semantics:
                    candidates.append(
                        attribute_engineering_judgment(
                            claim_id=claim_id,
                            payload_id=payload_id,
                            subject_ref=node_id,
                            reviewer_identity=str(clean_draft.get("reviewer_identity") or "constructability_engineer"),
                            premises=premises,
                            derivation_method=rationale,
                            limitations=[str(item) for item in (node.get("limitations") or [])],
                            semantic_details=semantics,
                        )
                    )

            compatible_proofs: list[VerifiedConstructabilityProof] = []
            for candidate in candidates:
                if type(candidate) is VerifiedConstructabilityProof:
                    proof = candidate
                    proof_record = _capability_record(proof, VerifiedConstructabilityProof)
                    if proof_record.get("payload_id") != payload_id:
                        raise EvidenceVerificationError("Proof is bound to another Payload")
                else:
                    proof = _proof_from_evidence(
                        candidate,
                        payload_id=payload_id,
                        subject_ref=node_id,
                        claim_id=claim_id,
                    )
                compatible_proofs.append(proof)

            if compatible_proofs:
                proof_records = [
                    _capability_record(item, VerifiedConstructabilityProof)
                    for item in compatible_proofs
                ]
                state = _resolution_state(str(proof_records[0]["mode"]))
                evidence_ids: list[str] = []
                for proof_record in proof_records:
                    evidence_record = dict(proof_record["evidence"])
                    runtime_records.append(evidence_record)
                    evidence_ids.append(proof_record["evidence_digest"])
                node_evidence_ids[claim_id] = evidence_ids
                limitations = [
                    str(item)
                    for record in runtime_records
                    if record.get("claim_id") == claim_id and record.get("subject_ref") == node_id
                    for item in (record.get("limitations") or [])
                ]
                obligation_record = None
            else:
                state = str(policy["unavailable_evidence_behavior"])
                if state not in RESOLVED_STATES:
                    state = "INSUFFICIENT_EVIDENCE"
                limitations = [
                    str(item) for item in (node.get("limitations") or [])
                ] or ["No policy-compatible evidence was verified."]
                obligation_record = None
                if state == "DOWNSTREAM_VALIDATION_REQUIRED":
                    obligation = create_downstream_test_obligation(
                        claim_id=claim_id,
                        payload_id=payload_id,
                        subject_ref=node_id,
                        consumer_stage=str(request.get("consumer_stage") or "responsive_or_builder_runtime"),
                        required_test=str(request.get("required_test") or f"Verify {claim_id} on rendered output."),
                        blocking_behavior=str(request.get("blocking_behavior") or "block_builder_handoff"),
                        completion_criteria=str(request.get("completion_criteria") or f"Observed {claim_id} evidence passes."),
                    )
                    generated_obligations.append(obligation)
                    obligation_record = _capability_record(obligation, DownstreamTestObligation)
                    runtime_records.append(obligation_record)
                unresolved_evidence.append(
                    {
                        "unresolved_id": f"unresolved-{node_id}-{claim_id}",
                        "claim_ref": f"{node_id}:{claim_id}",
                        "owner": policy["authority_owner"],
                        "reason": state,
                        "required_source": list(policy["admissible_evidence_modes"]),
                    }
                )
                blocking_dependencies.append(f"{node_id}:{claim_id}:{state}")

            node_resolutions[claim_id] = state
            authority_resolution.append(
                {
                    "claim_ref": f"{node_id}:{claim_id}",
                    "claim_id": claim_id,
                    "subject_ref": node_id,
                    "policy": policy,
                    "submitted_judgment": str(node.get("engineering_rationale") or "") or None,
                    "verified_evidence": node_evidence_ids.get(claim_id, []),
                    "resolved_state": state,
                    "limitations": limitations,
                    "downstream_obligation": obligation_record,
                }
            )

        def resolved(claim_id: str) -> str:
            return node_resolutions.get(claim_id, "NOT_APPLICABLE")

        def proven(claim_id: str) -> bool | None:
            if claim_id not in requests:
                return None
            return resolved(claim_id) in {"VERIFIED", "ATTRIBUTED_SUPPORTED"}

        geometry_required = "geometry" in requests
        overlay_required = "overlay_strategy" in requests
        responsive_requested = "responsive_behavior" in requests
        interaction_requested = "interaction_approval" in requests
        dynamic_requested = "dynamic_loop_approval" in requests
        accessibility_requested = "accessibility" in requests
        ui_requested = "ui_control_path" in requests
        asset_requested = "asset_source" in requests
        placeholder_requested = "placeholder_policy" in requests
        node_blockers = [
            item
            for item in blocking_dependencies
            if item.startswith(f"{node_id}:")
        ]
        if any("ARCHITECT_DECISION_REQUIRED" in item for item in node_blockers):
            node_status = "needs_architect_amendment"
        elif node_blockers:
            node_status = "needs_user_evidence"
        else:
            node_status = "executable_ready"

        reviewed_nodes.append(
            {
                "node_id": node_id,
                "node_type": str(node.get("node_type") or "implementation_node"),
                "action_proposed": str(node["proposed_action"]),
                "node_status": node_status,
                "blocking_reason": "; ".join(node_blockers) or None,
                "engineering_rationale": str(node.get("engineering_rationale") or ""),
                "interrogation_result": {
                    "geometry_required": geometry_required,
                    "geometry_proven": proven("geometry"),
                    "geometry_proof": (
                        {"evidence_ids": node_evidence_ids.get("geometry", [])}
                        if proven("geometry")
                        else None
                    ),
                    "asset_required": asset_requested,
                    "asset_source_present": proven("asset_source"),
                    "placeholder_policy_present": proven("placeholder_policy"),
                    "overlay_strategy_required": overlay_required,
                    "overlay_strategy_proven": proven("overlay_strategy"),
                    "overlay_strategy": (
                        {"evidence_ids": node_evidence_ids.get("overlay_strategy", [])}
                        if proven("overlay_strategy")
                        else None
                    ),
                    "responsive_behavior": (
                        "evidence_backed"
                        if resolved("responsive_behavior") == "VERIFIED"
                        else "blocked"
                        if responsive_requested
                        else "not_applicable"
                    ),
                    "action_targets_responsive": responsive_requested,
                    "interaction_implied": interaction_requested,
                    "interaction_approved": proven("interaction_approval"),
                    "dynamic_loop_implied": dynamic_requested,
                    "dynamic_loop_approved": proven("dynamic_loop_approval"),
                    "dynamic_loop_binding_map": (
                        {"evidence_ids": node_evidence_ids.get("dynamic_loop_approval", [])}
                        if proven("dynamic_loop_approval")
                        else None
                    ),
                    "accessibility_claimed": accessibility_requested,
                    "accessibility_evidenced": proven("accessibility"),
                    "exact_ui_control_path_used": ui_requested,
                    "ui_control_evidence_present": proven("ui_control_path"),
                    "ui_control_evidence": (
                        {"evidence_ids": node_evidence_ids.get("ui_control_path", [])}
                        if proven("ui_control_path")
                        else None
                    ),
                    "reversible_if_wrong": bool(node.get("reversible_if_wrong", False)),
                    "requires_class_change": bool(node.get("requires_class_change", False)),
                    "requires_structure_change": bool(node.get("requires_structure_change", False)),
                    "architect_decomposition_permission": bool(node.get("architect_decomposition_permission", False)),
                },
            }
        )

    constructability_status = "executable_ready" if not blocking_dependencies else (
        "needs_architect_amendment"
        if any("ARCHITECT_DECISION_REQUIRED" in item for item in blocking_dependencies)
        else "needs_user_evidence"
    )
    actions = _derive_builder_actions(clean_draft)
    strategy_proposal = clean_draft.get("implementation_strategy_proposal")
    strategy_map = copy.deepcopy(strategy_proposal) if isinstance(strategy_proposal, dict) else None
    if isinstance(strategy_map, dict):
        strategy_map.setdefault("strategy_map_id", f"strategy-{payload_id[-16:]}")
        strategy_map["review_ref"] = review_id
        strategy_map["selected_candidate_id"] = intake_record["selected_candidate_id"]
        strategies = strategy_map.get("strategies")
        if isinstance(strategies, list):
            for strategy in strategies:
                if isinstance(strategy, dict):
                    strategy["builder_decisions_required"] = 0
                    strategy["architect_amendment_required"] = False

    builder_eligible = (
        constructability_status == "executable_ready"
        and not unresolved_evidence
        and bool(actions)
        and isinstance(strategy_map, dict)
    )
    builder_package = None
    if builder_eligible:
        action_ids = [item["action_id"] for item in actions]
        builder_package = {
            "schema": BUILDER_PACKAGE_SCHEMA_ID,
            "package_id": f"builder-{payload_id[-24:]}",
            "review_ref": review_id,
            "strategy_map_ref": strategy_map["strategy_map_id"],
            "architect_contract": {
                "source_ref": intake_record["source_ref"],
                "selected_candidate_id": intake_record["selected_candidate_id"],
                "approved_class_names": intake_record["approved_class_names"],
            },
            "selected_candidate_id": intake_record["selected_candidate_id"],
            "approved_class_names": intake_record["approved_class_names"],
            "builder_package_status": "executable_ready",
            "builder_decisions_required": 0,
            "blocking_dependencies": [],
            "selected_candidate_locked": True,
            "selected_candidate_id_unchanged": True,
            "approved_class_names_unchanged": True,
            "confirmation_request": {
                "confirmation_id": f"confirm-{payload_id[-16:]}",
                "confirmed_action_ids": action_ids,
                "expected_user_token": f"confirm {action_ids[0]}",
            },
            "first_safe_builder_batch": {
                "batch_id": f"batch-{payload_id[-16:]}",
                "risk": "low",
                "actions": actions,
            },
            "known_unknowns": {},
            "logged_assumptions": [],
            "qa_status": {"production_ready": False},
        }

    evidence_register = [
        _runtime_evidence_entry(record, index)
        for index, record in enumerate(runtime_records)
    ]
    resolution_digest = _sha256(canonical_bytes(authority_resolution))
    payload: dict[str, Any] = {
        "schema_id": VERIFIED_PAYLOAD_SCHEMA_ID,
        "schema_version": VERIFIED_PAYLOAD_SCHEMA_VERSION,
        "owner_repository": CE_REPOSITORY,
        "payload_status": "complete" if builder_eligible else "insufficient_evidence",
        "payload_identity": {
            "payload_id": payload_id,
            "pipeline_id": "ev4-ce-project-gate-producer-pipeline",
            "run_id": run_id,
            "synthetic": False,
        },
        "source_architect_intake": {
            "schema_id": intake_record["schema_id"],
            "schema_version": intake_record["schema_version"],
            "artifact_ref": intake_record["source_ref"],
            "artifact_hash": {
                "algorithm": "sha256",
                "value": intake_record["source_canonical_sha256"],
                "scope": "canonical_json",
            },
            "transition_metadata_is_review_evidence": False,
        },
        "source_bundle_binding": {
            "bundle_id": bundle_record["source_identity"],
            "artifact_ref": bundle_record["source_ref"],
            "canonical_sha256": bundle_record["source_canonical_sha256"],
            "bytes_sha256": bundle_record["source_bytes_sha256"],
        },
        "architecture_identity": {
            "selected_candidate_id": intake_record["selected_candidate_id"],
            "selected_candidate_locked": True,
            "selected_candidate_id_unchanged": True,
            "approved_class_names": intake_record["approved_class_names"],
            "approved_class_names_unchanged": True,
            "build_tree_identity_preserved": True,
            "architect_unknowns_preserved": True,
            "architect_forbidden_work_weakened": False,
            "review_unit_traces": [
                {
                    "architect_node_ref": item["node_id"],
                    "architect_evidence_refs": [],
                    "ce_review_unit_id": f"ce-unit-{item['node_id']}",
                    "identity_unchanged": True,
                }
                for item in clean_draft["reviewed_nodes"]
            ],
        },
        "constructability_review": {
            "schema_id": "ev4-constructability-review@1.1.0",
            "review_id": review_id,
            "architect_package_ref": intake_record["source_ref"],
            "selected_candidate_id": intake_record["selected_candidate_id"],
            "constructability_status": constructability_status,
            "builder_decisions_required": 0 if builder_eligible else len(blocking_dependencies),
            "blocking_dependencies": blocking_dependencies,
            "engineer_questions": list(clean_draft.get("unresolved_questions") or []),
            "logged_assumptions": [],
            "reviewed_nodes": reviewed_nodes,
            "qa_status": {"production_ready": False},
        },
        "implementation_strategy_map": strategy_map if builder_eligible else None,
        "builder_executable_package": builder_package,
        "builder_package_emitted": builder_eligible,
        "builder_package_not_emitted_reason": None if builder_eligible else "verified_claim_resolution_incomplete",
        "authority_resolution": authority_resolution,
        "authority_resolution_digest": resolution_digest,
        "evidence_register": evidence_register,
        "unresolved_evidence": unresolved_evidence,
        "downstream_test_obligations": [
            _capability_record(item, DownstreamTestObligation)
            for item in generated_obligations
        ],
        "repair_routing": {
            "repair_owner": "ce" if not blocking_dependencies else "claim_policy_owner",
            "status": "not_required" if not blocking_dependencies else "required",
        },
        "boundary_assertions": {
            "ce_did_not_redesign_architecture": True,
            "ce_did_not_claim_builder_execution": True,
            "ce_did_not_claim_responsive_completion": True,
            "production_ready": False,
        },
        "validation_contract": {
            "validator_id": RESOLVER_ID,
            "validator_version": RESOLVER_VERSION,
            "legacy_payload_validation_supported": True,
            "legacy_payload_authorization_supported": False,
            "successor_verified_payload_required_for_handoff": True,
        },
        "extension_records": [],
    }
    record = {
        "payload": payload,
        "payload_canonical_sha256": _sha256(canonical_bytes(payload)),
        "source_intake_canonical_sha256": intake_record["source_canonical_sha256"],
        "source_intake_bytes_sha256": intake_record["source_bytes_sha256"],
        "source_bundle_canonical_sha256": bundle_record["source_canonical_sha256"],
        "source_bundle_bytes_sha256": bundle_record["source_bytes_sha256"],
        "source_checks": [
            {
                "source_ref": item.get("source_ref"),
                "source_bytes_sha256": item.get("source_bytes_sha256"),
            }
            for item in runtime_records
            if item.get("mode") == "VERIFIED_ARTIFACT"
        ],
        "resolver": {"id": RESOLVER_ID, "version": RESOLVER_VERSION},
    }
    return _mint(VerifiedCEStagePayload, record)  # type: ignore[return-value]


def verified_payload_data(
    capability: VerifiedCEStagePayload,
    *,
    repo_root: Path,
    source_intake_bytes: bytes,
    source_bundle_bytes: bytes,
) -> dict[str, Any]:
    record = _capability_record(capability, VerifiedCEStagePayload)
    if record.get("source_intake_bytes_sha256") != _sha256(source_intake_bytes):
        raise CapabilityError("Verified Payload is stale for the current Architect intake bytes")
    if record.get("source_bundle_bytes_sha256") != _sha256(source_bundle_bytes):
        raise CapabilityError("Verified Payload is stale for the current source bundle bytes")
    root = repo_root.resolve(strict=True)
    for check in record.get("source_checks") or []:
        if not isinstance(check, dict):
            raise CapabilityError("Verified Payload source recheck record is invalid")
        source_ref = check.get("source_ref")
        expected = check.get("source_bytes_sha256")
        if not isinstance(source_ref, str) or not isinstance(expected, str):
            raise CapabilityError("Verified Payload source recheck record is incomplete")
        path = (root / source_ref).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise CapabilityError("Verified Payload source escaped repository root") from exc
        if _sha256(path.read_bytes()) != expected:
            raise CapabilityError(f"Verified evidence became stale: {source_ref}")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise CapabilityError("Verified Payload capability contains no payload")
    if record.get("payload_canonical_sha256") != _sha256(canonical_bytes(payload)):
        raise CapabilityError("Verified Payload canonical digest mismatch")
    return copy.deepcopy(payload)


def make_test_only_proof_capability(record: Mapping[str, Any]) -> VerifiedConstructabilityProof:
    """Create a deliberately non-production capability for adversarial tests only."""
    return _mint(VerifiedConstructabilityProof, record, production=False)  # type: ignore[return-value]
