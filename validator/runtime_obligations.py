from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence

from .claim_policy_registry import CLAIM_POLICIES, POST_BUILDER_RUNTIME


class RuntimeObligationError(ValueError):
    """Raised when a mandatory post-Builder claim has no complete obligation."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


_REQUIRED = (
    "obligation_id",
    "claim_id",
    "subject_ref",
    "consumer_stage",
    "required_runner",
    "target_identity",
    "required_inputs",
    "expected_assertions",
    "completion_criteria",
    "blocking_boundary",
    "status",
)


def normalize_runtime_obligation(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeObligationError("Runtime obligation must be an object")
    result = copy.deepcopy(dict(value))
    missing = [key for key in _REQUIRED if result.get(key) in (None, "", [], {})]
    if missing:
        raise RuntimeObligationError(
            "Runtime obligation is incomplete: " + ", ".join(missing)
        )
    claim_id = str(result["claim_id"])
    policy = CLAIM_POLICIES.get(claim_id)
    if not policy or policy["lifecycle_phase"] != POST_BUILDER_RUNTIME:
        raise RuntimeObligationError(
            f"Runtime obligation uses a non-runtime claim: {claim_id}"
        )
    if result["status"] not in {
        "required",
        "executed_pass",
        "executed_fail",
        "not_applicable",
    }:
        raise RuntimeObligationError("Runtime obligation status is invalid")
    if result["blocking_boundary"] != "final_project_gate":
        raise RuntimeObligationError(
            "Open runtime obligations must block final_project_gate, not Builder handoff"
        )
    result["blocks_builder_handoff"] = False
    result["blocks_final_completion"] = result["status"] not in {
        "executed_pass",
        "not_applicable",
    }
    result["required_inputs"] = sorted(
        {str(item) for item in result.get("required_inputs") or [] if str(item)}
    )
    result["expected_assertions"] = [
        str(item) for item in result.get("expected_assertions") or [] if str(item)
    ]
    identity_seed = {
        key: result[key]
        for key in (
            "claim_id",
            "subject_ref",
            "required_runner",
            "target_identity",
            "required_inputs",
            "expected_assertions",
        )
    }
    expected_id = f"ce-runtime-obligation-{sha256_json(identity_seed)[:24]}"
    if result["obligation_id"] != expected_id:
        raise RuntimeObligationError("Runtime obligation identity is not deterministic")
    return json.loads(canonical_bytes(result))


def derive_runtime_obligations(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        claim_id = str(row.get("claim_id") or "")
        policy = CLAIM_POLICIES.get(claim_id)
        if not policy or policy["lifecycle_phase"] != POST_BUILDER_RUNTIME:
            continue
        subject_ref = str(row.get("subject_ref") or "")
        key = (subject_ref, claim_id)
        if key in seen:
            raise RuntimeObligationError(
                f"Duplicate runtime obligation source row: {subject_ref}:{claim_id}"
            )
        seen.add(key)
        raw = row.get("downstream_obligation")
        if not isinstance(raw, Mapping):
            raise RuntimeObligationError(
                f"Post-Builder claim has no obligation: {subject_ref}:{claim_id}"
            )
        obligation = normalize_runtime_obligation(raw)
        if obligation["subject_ref"] != subject_ref or obligation["claim_id"] != claim_id:
            raise RuntimeObligationError(
                f"Runtime obligation binding mismatch: {subject_ref}:{claim_id}"
            )
        obligations.append(obligation)
    obligations.sort(key=lambda item: (item["subject_ref"], item["claim_id"]))
    return obligations


def lifecycle_status(
    *, builder_ready: bool, obligations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    statuses = {str(item.get("status")) for item in obligations}
    if not obligations:
        runtime = "not_applicable"
        final_gate = "eligible" if builder_ready else "blocked"
    elif statuses.issubset({"executed_pass", "not_applicable"}):
        runtime = "passed"
        final_gate = "eligible" if builder_ready else "blocked"
    elif "executed_fail" in statuses:
        runtime = "failed"
        final_gate = "blocked"
    else:
        runtime = "pending"
        final_gate = "blocked"
    return {
        "ce_builder_ready": bool(builder_ready),
        "runtime_validated": runtime == "passed",
        "runtime_validation": runtime,
        "final_project_gate": final_gate,
        "production_ready": False,
    }


__all__ = [
    "RuntimeObligationError",
    "derive_runtime_obligations",
    "lifecycle_status",
    "normalize_runtime_obligation",
]
