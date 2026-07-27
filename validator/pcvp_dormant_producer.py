from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .payload_assembler import canonical_bytes, sha256_json
from .pcvp_identity import (
    ARCHITECTURE_LOCK_ID,
    CANONICAL_COMMIT,
    CANONICAL_REPOSITORY,
    POLICY_ID,
    POLICY_VERSION,
    ROOT,
    SOURCE_STAGE,
    PCVPIdentityError,
    PCVPResources,
    load_pcvp_resources,
)
from .verified_constructability import (
    DraftValidationError,
    EvaluationBoundaryError,
    EvidenceVerificationError,
    assemble_verified_ce_stage_payload,
    verified_payload_data,
    verify_architect_intake,
    verify_source_bundle,
)

BUILDER_PACKAGE_SCHEMA_PATH = Path("schemas/builder_executable_package.schema.json")


class PCVPDormantProducerError(RuntimeError):
    """Raised when dormant CE carrier derivation cannot prove its authority inputs."""


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-JSON constant is forbidden: {value}")


def _strict_object(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise PCVPDormantProducerError(f"{label} exact bytes must be bytes.")
    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate object key: {key}")
            result[key] = value
        return result

    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_pairs_hook,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError) as exc:
        raise PCVPDormantProducerError(
            f"{label} exact bytes are not strict JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise PCVPDormantProducerError(f"{label} exact bytes must contain an object.")
    return parsed


def _verify_mapping_fidelity(
    value: Mapping[str, Any],
    raw: bytes,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PCVPDormantProducerError(f"{label} must be an object mapping.")
    parsed = _strict_object(raw, label)
    try:
        if canonical_bytes(parsed) != canonical_bytes(value):
            raise PCVPDormantProducerError(
                f"{label} mapping does not match its exact source bytes."
            )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, PCVPDormantProducerError):
            raise
        raise PCVPDormantProducerError(
            f"{label} cannot be represented as canonical JSON: {exc}"
        ) from exc
    return copy.deepcopy(parsed)


def verify_dormant_producer_resources(
    repository_root: str | Path = ROOT,
) -> dict[str, Any]:
    resources = load_pcvp_resources(repository_root)
    return {
        "architecture_lock_id": resources.descriptor.architecture_lock_id,
        "canonical_commit": resources.descriptor.canonical_commit,
        "schema_count": len(resources.schemas),
        "producer_emission": False,
        "adoption_status": "not_yet_adopted",
        "activation_effect": "NONE",
    }


def _load_builder_schema(repository_root: Path) -> dict[str, Any]:
    path = repository_root / BUILDER_PACKAGE_SCHEMA_PATH
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise PCVPDormantProducerError(
            f"Builder package schema is unavailable: {type(exc).__name__}"
        ) from exc
    if not isinstance(schema, dict):
        raise PCVPDormantProducerError("Builder package schema must be an object.")
    Draft202012Validator.check_schema(schema)
    return schema


def _validate_complete_builder_package(
    builder_package: Mapping[str, Any],
    repository_root: Path,
) -> dict[str, Any]:
    if not isinstance(builder_package, Mapping):
        raise PCVPDormantProducerError(
            "Verified CE payload did not contain a Builder package object."
        )
    package = copy.deepcopy(dict(builder_package))
    errors = sorted(
        Draft202012Validator(_load_builder_schema(repository_root)).iter_errors(package),
        key=lambda item: (list(item.absolute_path), item.message),
    )
    if errors:
        first = errors[0]
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in first.absolute_path
        )
        raise PCVPDormantProducerError(
            f"Full Builder package schema failure at {path}: {first.message}"
        )
    if (
        package.get("schema") != "ev4-builder-executable-package@1.0.0"
        or package.get("builder_package_status") != "executable_ready"
        or package.get("builder_decisions_required") != 0
        or package.get("blocking_dependencies") != []
        or package.get("selected_candidate_locked") is not True
        or package.get("selected_candidate_id_unchanged") is not True
        or package.get("approved_class_names_unchanged") is not True
        or not isinstance(package.get("architect_contract"), Mapping)
        or not isinstance(package.get("confirmation_request"), Mapping)
        or not isinstance(package.get("first_safe_builder_batch"), Mapping)
        or not isinstance(package.get("strategy_map_ref"), str)
    ):
        raise PCVPDormantProducerError(
            "Recomputed CE package is not deterministically Builder-ready."
        )
    if "continuation_assurance" in package:
        raise PCVPDormantProducerError(
            "Recomputed active CE package unexpectedly contains continuation_assurance."
        )
    return package


def _validate_carrier(
    carrier: dict[str, Any],
    resources: PCVPResources,
) -> None:
    runtime_schema = copy.deepcopy(resources.schemas["handoff.schema.json"])
    continuation = runtime_schema["properties"]["continuation_assurance"]["properties"]
    continuation["claims"]["items"] = resources.schemas["claim.schema.json"]
    continuation["effects"]["items"] = resources.schemas["effect.schema.json"]
    continuation["authorizations"]["items"] = resources.schemas[
        "authorization.schema.json"
    ]
    errors = sorted(
        Draft202012Validator(runtime_schema).iter_errors(
            {"continuation_assurance": carrier}
        ),
        key=lambda item: (list(item.absolute_path), item.message),
    )
    if errors:
        first = errors[0]
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in first.absolute_path
        )
        raise PCVPDormantProducerError(
            f"Generated PCVP carrier failed canonical schema at {path}: {first.message}"
        )

    claims = carrier["claims"]
    effect = carrier["effects"][0]
    summary = carrier["stage_summary"]
    claim_ids = {claim["claim_id"] for claim in claims}
    identifiers = [*claim_ids, effect["effect_id"]]
    if (
        carrier["source_stage"] != SOURCE_STAGE
        or len(identifiers) != len(set(identifiers))
        or set(effect["depends_on_claim_ids"]) != claim_ids
        or effect["continuation_state"] != "AUTHORIZATION_REQUIRED"
        or effect["authorization_ref"] is not None
        or carrier["authorizations"] != []
        or summary["current_effect_id"] != effect["effect_id"]
        or set(summary["derived_from_claim_ids"]) != claim_ids
        or summary["owner_projection"] != "YELLOW"
        or summary["yellow_substate"] != "OWNER_CHOICE_REQUIRED"
    ):
        raise PCVPDormantProducerError(
            "Generated PCVP carrier violated the locked CE-to-Builder semantics."
        )


def _project_continuation_assurance(
    builder_package: Mapping[str, Any],
    resources: PCVPResources,
) -> dict[str, Any]:
    package = copy.deepcopy(dict(builder_package))
    package_hash = sha256_json(package)
    suffix = hashlib.sha256(
        canonical_bytes(
            {
                "package_id": package.get("package_id"),
                "package_hash": package_hash,
            }
        )
    ).hexdigest()[:16].upper()
    package_claim_id = f"CLM-CE-PACKAGE-{suffix}"
    downstream_claim_id = f"CLM-CE-DOWNSTREAM-{suffix}"
    effect_id = f"EFF-CE-BUILDER-BATCH-{suffix}"
    batch_id = str(
        package.get("first_safe_builder_batch", {}).get("batch_id")
        or "unknown-batch"
    )
    permitted_scope = (
        f"Execute only CE first Builder batch {batch_id} after explicit owner "
        "confirmation; no Responsive, deployment, or production claim."
    )
    carrier = {
        "policy_id": POLICY_ID,
        "policy_version": POLICY_VERSION,
        "source_stage": SOURCE_STAGE,
        "claims": [
            {
                "claim_id": package_claim_id,
                "statement": (
                    "The bounded CE Builder package passed the existing "
                    "deterministic Builder-readiness boundary."
                ),
                "criticality": "CRITICAL",
                "applicability_state": "APPLICABLE",
                "verification_state": "VERIFIED",
                "lifecycle_state": "COMPLETE",
                "evidence_refs": [f"sha256:{package_hash}"],
                "dependency_refs": [],
                "assumption_refs": [],
            },
            {
                "claim_id": downstream_claim_id,
                "statement": (
                    "Builder execution, Responsive completion, deployment, "
                    "and production readiness remain unverified."
                ),
                "criticality": "MATERIAL",
                "applicability_state": "APPLICABLE",
                "verification_state": "UNVERIFIED",
                "lifecycle_state": "ACTIVE",
                "evidence_refs": [],
                "dependency_refs": [package_claim_id],
                "assumption_refs": [],
            },
        ],
        "effects": [
            {
                "effect_id": effect_id,
                "effect_class": "EXTERNAL_MUTATION",
                "depends_on_claim_ids": [package_claim_id, downstream_claim_id],
                "continuation_state": "AUTHORIZATION_REQUIRED",
                "authorization_ref": None,
                "blocker_reason": "OWNER_DECISION_REQUIRED",
                "permitted_scope": permitted_scope,
            }
        ],
        "authorizations": [],
        "unresolved_items": [
            {
                "id": f"UNRES-CE-OWNER-{suffix}",
                "class": "OWNER_DECISION_REQUIRED",
                "statement": (
                    "The existing Builder confirmation request has not yet been "
                    "satisfied by the owner."
                ),
                "impact": (
                    "The first Builder batch must not execute before explicit "
                    "owner confirmation."
                ),
            },
            {
                "id": f"UNRES-CE-DOWNSTREAM-{suffix}",
                "class": "VERIFICATION_PATH_UNAVAILABLE",
                "statement": (
                    "Builder, Responsive, deployment, and production outcomes "
                    "have not been verified by their owning authorities."
                ),
                "impact": "The carrier cannot upgrade downstream completion claims.",
            },
        ],
        "stage_summary": {
            "owner_projection": "YELLOW",
            "yellow_substate": "OWNER_CHOICE_REQUIRED",
            "derived_from_claim_ids": [package_claim_id, downstream_claim_id],
            "current_effect_id": effect_id,
            "lifecycle_state": "ACTIVE",
            "derivation_reason": (
                "CE established a bounded Builder-ready package, while the external "
                "Builder mutation still requires owner confirmation."
            ),
        },
    }
    _validate_carrier(carrier, resources)
    return copy.deepcopy(carrier)


def derive_continuation_assurance(
    *,
    architect_intake: Mapping[str, Any],
    architect_intake_bytes: bytes,
    source_bundle: Mapping[str, Any],
    source_bundle_bytes: bytes,
    review_draft: Mapping[str, Any],
    repository_root: str | Path = ROOT,
    architect_intake_ref: str = "architect-intake.json",
    source_bundle_ref: str = "architect-source-bundle.json",
    runtime_execution_requests: Sequence[Mapping[str, Any]] = (),
    **unsupported_authority_inputs: Any,
) -> dict[str, Any]:
    """Dormantly derive a carrier only by replaying the authoritative CE runtime."""
    if unsupported_authority_inputs:
        unsupported = ", ".join(sorted(unsupported_authority_inputs))
        raise PCVPDormantProducerError(
            f"Unsupported authority inputs are forbidden: {unsupported}"
        )
    root = Path(repository_root)
    try:
        resources = load_pcvp_resources(root)
        intake = _verify_mapping_fidelity(
            architect_intake, architect_intake_bytes, "Architect intake"
        )
        bundle = _verify_mapping_fidelity(
            source_bundle, source_bundle_bytes, "Architect source bundle"
        )
        verified_intake = verify_architect_intake(
            intake=intake,
            intake_bytes=architect_intake_bytes,
            source_ref=architect_intake_ref,
            repo_root=root,
        )
        verified_bundle = verify_source_bundle(
            source_bundle=bundle,
            source_bundle_bytes=source_bundle_bytes,
            verified_intake=verified_intake,
            source_ref=source_bundle_ref,
        )
        evaluation_run = assemble_verified_ce_stage_payload(
            draft=copy.deepcopy(dict(review_draft)),
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=root,
            runtime_execution_requests=runtime_execution_requests,
        )
        payload = verified_payload_data(
            evaluation_run,
            repo_root=root,
            source_intake_bytes=architect_intake_bytes,
            source_bundle_bytes=source_bundle_bytes,
        )
    except PCVPDormantProducerError:
        raise
    except (
        PCVPIdentityError,
        DraftValidationError,
        EvaluationBoundaryError,
        EvidenceVerificationError,
        TypeError,
        ValueError,
    ) as exc:
        raise PCVPDormantProducerError(
            f"Authoritative CE replay failed closed: {exc}"
        ) from exc

    if payload.get("payload_status") != "complete" or payload.get(
        "builder_package_emitted"
    ) is not True:
        raise PCVPDormantProducerError(
            "Authoritative CE replay did not establish Builder readiness."
        )
    package = _validate_complete_builder_package(
        payload.get("builder_executable_package"),
        root,
    )
    return _project_continuation_assurance(package, resources)


__all__ = [
    "ARCHITECTURE_LOCK_ID",
    "CANONICAL_COMMIT",
    "CANONICAL_REPOSITORY",
    "PCVPDormantProducerError",
    "POLICY_ID",
    "POLICY_VERSION",
    "derive_continuation_assurance",
    "verify_dormant_producer_resources",
]
