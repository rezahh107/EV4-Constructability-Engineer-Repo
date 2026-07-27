from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

POLICY_ID = "EV4-PCVP"
POLICY_VERSION = "1.0.0"
ARCHITECTURE_LOCK_ID = "EV4-PCVP-ROLL-LOCK-20260727-R1"
CANONICAL_REPOSITORY = "rezahh107/EV4-Decision-Kernel"
CANONICAL_COMMIT = "069a50fa243b01fa578a7c1bcb8864d9e796d34b"
SOURCE_STAGE = "CONSTRUCTABILITY_ENGINEER"
CONSUMER_STAGE = "BUILDER_ASSISTANT"
PRODUCER_EMISSION_ENABLED = False
ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = Path("contracts/pcvp/pcvp-v1.lock.json")
PROFILE_PATH = Path("contracts/pcvp/constructability.profile.yaml")
VENDORED_ROOT = Path("contracts/pcvp/vendor/decision-kernel/v1.0.0")
SCHEMA_NAMES = (
    "authorization.schema.json",
    "claim.schema.json",
    "effect.schema.json",
    "handoff.schema.json",
)


class PCVPDormantProducerError(RuntimeError):
    """Raised when dormant CE producer identity or derivation fails closed."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise PCVPDormantProducerError(
            f"PCVP resource could not be loaded: {path} ({type(exc).__name__})"
        ) from exc


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PCVPDormantProducerError(
            f"PCVP identity input is not canonical JSON: {exc}"
        ) from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load_pinned_schemas(
    repository_root: Path,
) -> dict[str, dict[str, Any]]:
    lock = _load_json(repository_root / LOCK_PATH)
    if not isinstance(lock, dict):
        raise PCVPDormantProducerError("PCVP lock must be an object.")
    if (
        lock.get("schema_version") != "ev4-pcvp-contract-lock.v1"
        or lock.get("architecture_lock_id") != ARCHITECTURE_LOCK_ID
        or lock.get("policy")
        != {
            "id": POLICY_ID,
            "version": POLICY_VERSION,
            "adoption_status": "not_yet_adopted",
            "activation": "NONE",
        }
    ):
        raise PCVPDormantProducerError(
            "PCVP policy or architecture lock identity drifted."
        )
    canonical = lock.get("canonical")
    if not isinstance(canonical, dict) or (
        canonical.get("repository") != CANONICAL_REPOSITORY
        or canonical.get("commit_sha") != CANONICAL_COMMIT
    ):
        raise PCVPDormantProducerError(
            "PCVP canonical owner or immutable commit drifted."
        )
    if lock.get("producer") != {
        "repository": "rezahh107/EV4-Constructability-Engineer-Repo",
        "source_stage": SOURCE_STAGE,
        "consumer_stage": CONSUMER_STAGE,
        "carrier_path": "builder_executable_package.continuation_assurance",
        "emission_enabled": False,
        "caller_override_allowed": False,
    }:
        raise PCVPDormantProducerError(
            "PCVP CE producer must remain hard-disabled without caller override."
        )
    if lock.get("verification") != {
        "byte_equality_required": True,
        "compare_against_moving_default_branch": False,
    }:
        raise PCVPDormantProducerError(
            "PCVP immutable-byte verification policy drifted."
        )

    profile = lock.get("profile")
    if not isinstance(profile, dict) or profile.get("path") != str(PROFILE_PATH):
        raise PCVPDormantProducerError("PCVP Constructability profile drifted.")
    try:
        profile_hash = hashlib.sha256(
            (repository_root / PROFILE_PATH).read_bytes()
        ).hexdigest()
    except OSError as exc:
        raise PCVPDormantProducerError(
            f"PCVP profile is unavailable: {type(exc).__name__}"
        ) from exc
    if profile.get("sha256") != profile_hash:
        raise PCVPDormantProducerError("PCVP profile byte identity drifted.")

    entries = lock.get("files")
    if not isinstance(entries, list) or len(entries) != len(SCHEMA_NAMES):
        raise PCVPDormantProducerError(
            "PCVP lock must cover exactly four canonical schemas."
        )
    by_name = {
        entry.get("name"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    if set(by_name) != set(SCHEMA_NAMES):
        raise PCVPDormantProducerError("PCVP schema lock set drifted.")

    schemas: dict[str, dict[str, Any]] = {}
    for name in SCHEMA_NAMES:
        path = repository_root / VENDORED_ROOT / name
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise PCVPDormantProducerError(
                f"PCVP schema is unavailable: {name} ({type(exc).__name__})"
            ) from exc
        if hashlib.sha256(content).hexdigest() != by_name[name].get("sha256"):
            raise PCVPDormantProducerError(
                f"PCVP schema byte identity drifted: {name}"
            )
        value = _load_json(path)
        if not isinstance(value, dict):
            raise PCVPDormantProducerError(
                f"PCVP schema must be an object: {name}"
            )
        Draft202012Validator.check_schema(value)
        schemas[name] = value
    return schemas


def verify_dormant_producer_resources(
    repository_root: str | Path = ROOT,
) -> dict[str, Any]:
    schemas = _load_pinned_schemas(Path(repository_root))
    return {
        "architecture_lock_id": ARCHITECTURE_LOCK_ID,
        "canonical_commit": CANONICAL_COMMIT,
        "schema_count": len(schemas),
        "producer_emission": False,
        "adoption_status": "not_yet_adopted",
        "activation_effect": "NONE",
    }


def _validate_carrier(
    carrier: dict[str, Any],
    repository_root: str | Path,
) -> None:
    schemas = _load_pinned_schemas(Path(repository_root))
    runtime_schema = copy.deepcopy(schemas["handoff.schema.json"])
    continuation = runtime_schema["properties"]["continuation_assurance"][
        "properties"
    ]
    continuation["claims"]["items"] = schemas["claim.schema.json"]
    continuation["effects"]["items"] = schemas["effect.schema.json"]
    continuation["authorizations"]["items"] = schemas[
        "authorization.schema.json"
    ]
    document = {"continuation_assurance": carrier}
    errors = sorted(
        Draft202012Validator(runtime_schema).iter_errors(document),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "$"
        raise PCVPDormantProducerError(
            f"Generated PCVP carrier failed canonical schema at {path}: "
            f"{first.message}"
        )

    claims = carrier["claims"]
    effect = carrier["effects"][0]
    summary = carrier["stage_summary"]
    identifiers = [
        *[claim["claim_id"] for claim in claims],
        effect["effect_id"],
    ]
    claim_ids = {claim["claim_id"] for claim in claims}
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


def build_continuation_assurance(
    builder_package: dict[str, Any],
    repository_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Derive a bounded CE-to-Builder carrier without granting execution."""
    if not isinstance(builder_package, dict):
        raise PCVPDormantProducerError(
            "Builder executable package must be an object."
        )
    if "continuation_assurance" in builder_package:
        raise PCVPDormantProducerError(
            "Caller-supplied continuation_assurance is forbidden."
        )
    if (
        builder_package.get("schema")
        != "ev4-builder-executable-package@1.0.0"
        or builder_package.get("builder_package_status") != "executable_ready"
        or builder_package.get("builder_decisions_required") != 0
        or builder_package.get("blocking_dependencies") != []
        or builder_package.get("selected_candidate_locked") is not True
        or not isinstance(builder_package.get("confirmation_request"), dict)
        or not isinstance(builder_package.get("first_safe_builder_batch"), dict)
    ):
        raise PCVPDormantProducerError(
            "CE package is not deterministically Builder-ready."
        )

    verify_dormant_producer_resources(repository_root)
    package_hash = _sha256(builder_package)
    suffix = hashlib.sha256(
        _canonical_bytes(
            {
                "package_id": builder_package.get("package_id"),
                "package_hash": package_hash,
            }
        )
    ).hexdigest()[:16].upper()
    package_claim_id = f"CLM-CE-PACKAGE-{suffix}"
    downstream_claim_id = f"CLM-CE-DOWNSTREAM-{suffix}"
    effect_id = f"EFF-CE-BUILDER-BATCH-{suffix}"
    batch_id = str(
        builder_package["first_safe_builder_batch"].get("batch_id")
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
                "depends_on_claim_ids": [
                    package_claim_id,
                    downstream_claim_id,
                ],
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
                    "The existing Builder confirmation request has not yet "
                    "been satisfied by the owner."
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
                "impact": (
                    "The carrier cannot upgrade downstream completion claims."
                ),
            },
        ],
        "stage_summary": {
            "owner_projection": "YELLOW",
            "yellow_substate": "OWNER_CHOICE_REQUIRED",
            "derived_from_claim_ids": [
                package_claim_id,
                downstream_claim_id,
            ],
            "current_effect_id": effect_id,
            "lifecycle_state": "ACTIVE",
            "derivation_reason": (
                "CE established a bounded Builder-ready package, while the "
                "external Builder mutation still requires owner confirmation."
            ),
        },
    }
    _validate_carrier(carrier, repository_root)
    return copy.deepcopy(carrier)


def attach_to_builder_package_if_enabled(
    builder_package: dict[str, Any],
    *,
    repository_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Attach only after a separate reviewed activation changes the flag."""
    if not isinstance(builder_package, dict):
        raise PCVPDormantProducerError(
            "Builder executable package must be an object."
        )
    if "continuation_assurance" in builder_package:
        raise PCVPDormantProducerError(
            "Caller-supplied continuation_assurance is forbidden."
        )
    if not PRODUCER_EMISSION_ENABLED:
        return builder_package
    builder_package["continuation_assurance"] = build_continuation_assurance(
        builder_package,
        repository_root,
    )
    return builder_package


__all__ = [
    "ARCHITECTURE_LOCK_ID",
    "CANONICAL_COMMIT",
    "CANONICAL_REPOSITORY",
    "PCVPDormantProducerError",
    "POLICY_ID",
    "POLICY_VERSION",
    "PRODUCER_EMISSION_ENABLED",
    "attach_to_builder_package_if_enabled",
    "build_continuation_assurance",
    "verify_dormant_producer_resources",
]
