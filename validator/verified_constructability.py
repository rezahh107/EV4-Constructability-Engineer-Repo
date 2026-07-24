from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .claim_policy_registry import CLAIM_POLICIES
from .payload_assembler import (
    EVALUATOR_ID as RESOLVER_ID,
    EVALUATOR_VERSION as RESOLVER_VERSION,
    PAYLOAD_SCHEMA_ID as VERIFIED_PAYLOAD_SCHEMA_ID,
    PAYLOAD_SCHEMA_VERSION as VERIFIED_PAYLOAD_SCHEMA_VERSION,
    canonical_bytes,
    sha256_json,
)
from .payload_fidelity import compare_persisted_payload, recompute_expected_payload
from .runtime_execution import RuntimeExecutionBoundaryError


class EvaluationBoundaryError(ValueError):
    """Raised when canonical input identity or recomputation fidelity fails."""


class DraftValidationError(ValueError):
    """Raised when a CE Review Draft is structurally invalid."""


class EvidenceVerificationError(ValueError):
    """Raised when Architect input/source identity cannot be established."""


CapabilityError = EvaluationBoundaryError
VerifiedCEStagePayload = dict


def _canonical_clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(canonical_bytes(value))


def _schema_errors(schema: Mapping[str, Any], value: Mapping[str, Any]) -> list[str]:
    return [
        f"${''.join((f'[{p}]' if isinstance(p, int) else f'.{p}' for p in error.absolute_path))}: {error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    ]


def validate_review_draft(draft: Mapping[str, Any], repo_root: Path) -> None:
    schema_path = repo_root / "schemas/ce_review_draft.v1.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DraftValidationError(f"CE Review Draft Schema is unavailable: {exc}") from exc
    errors = _schema_errors(schema, draft)
    if errors:
        raise DraftValidationError("; ".join(errors))


def verify_architect_intake(
    *, intake: Mapping[str, Any], intake_bytes: bytes, source_ref: str
) -> dict[str, Any]:
    if intake.get("schema_id") != "ev4-ce-architect-stage-intake@1.1.0":
        raise EvidenceVerificationError(
            "Architect intake must use ev4-ce-architect-stage-intake@1.1.0"
        )
    if not isinstance(intake.get("selected_architecture"), Mapping):
        raise EvidenceVerificationError("Architect intake selected architecture is missing")
    if not isinstance(intake.get("structure_projection"), Mapping):
        raise EvidenceVerificationError("Architect intake structure projection is missing")
    observed_bytes = hashlib.sha256(intake_bytes).hexdigest()
    canonical_sha = sha256_json(intake)
    return {
        "kind": "verified_architect_intake",
        "data": _canonical_clone(intake),
        "source_ref": str(source_ref),
        "bytes_sha256": observed_bytes,
        "canonical_sha256": canonical_sha,
    }


def verify_source_bundle(
    *,
    source_bundle: Mapping[str, Any],
    source_bundle_bytes: bytes,
    verified_intake: Mapping[str, Any],
    source_ref: str,
) -> dict[str, Any]:
    if verified_intake.get("kind") != "verified_architect_intake":
        raise EvidenceVerificationError(
            "Source bundle requires a verified Architect intake record"
        )
    intake = verified_intake["data"]
    expected_id = intake.get("project_gate_transition", {}).get("source_bundle_id")
    if source_bundle.get("bundle_id") != expected_id:
        raise EvidenceVerificationError(
            "Source bundle identity does not match Architect intake"
        )
    canonical_sha = sha256_json(source_bundle)
    expected_hash = intake.get("project_gate_transition", {}).get(
        "source_bundle_hash", {}
    ).get("value")
    if isinstance(expected_hash, str) and expected_hash and expected_hash != canonical_sha:
        raise EvidenceVerificationError(
            "Source bundle canonical hash does not match Architect intake"
        )
    payload = source_bundle.get("payload")
    if not isinstance(payload, Mapping):
        raise EvidenceVerificationError("Source bundle payload is missing")
    return {
        "kind": "verified_source_bundle",
        "data": _canonical_clone(source_bundle),
        "source_ref": str(source_ref),
        "bytes_sha256": hashlib.sha256(source_bundle_bytes).hexdigest(),
        "canonical_sha256": canonical_sha,
    }


def verify_repo_artifact(*, repo_root: Path, source_ref: str) -> dict[str, Any]:
    root = repo_root.resolve(strict=True)
    candidate = Path(source_ref)
    path = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise EvidenceVerificationError(
            f"Repository artifact is unavailable: {source_ref}"
        ) from exc
    if not resolved.is_file():
        raise EvidenceVerificationError(
            f"Repository artifact is not a file: {source_ref}"
        )
    raw = resolved.read_bytes()
    return {
        "source_ref": str(source_ref),
        "bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _metadata(
    verified_intake: Mapping[str, Any],
    verified_source_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "intake_source_ref": verified_intake["source_ref"],
        "intake_bytes_sha256": verified_intake["bytes_sha256"],
        "intake_canonical_sha256": verified_intake["canonical_sha256"],
        "source_bundle_ref": verified_source_bundle["source_ref"],
        "source_bundle_bytes_sha256": verified_source_bundle["bytes_sha256"],
        "source_bundle_canonical_sha256": verified_source_bundle["canonical_sha256"],
    }


def assemble_verified_ce_stage_payload(
    *,
    draft: Mapping[str, Any],
    verified_intake: Mapping[str, Any],
    verified_source_bundle: Mapping[str, Any],
    repo_root: Path,
    runtime_execution_requests: Sequence[Mapping[str, Any]] = (),
    **legacy_ignored: Any,
) -> dict[str, Any]:
    """Evaluate canonical inputs through repository-owned deterministic boundaries.

    Runtime-only claims accept execution *requests*, not completed-result mappings. The repository
    invokes its supported adapter during this evaluation transaction and stores only the request in
    replayable input state; results are recomputed rather than caller-supplied.
    """
    legacy_results = legacy_ignored.pop("runtime_results", ())
    if legacy_results:
        raise EvaluationBoundaryError(
            "Completed runtime_results mappings are forbidden; provide execution requests only"
        )
    if legacy_ignored:
        unsupported = ", ".join(sorted(legacy_ignored))
        raise EvaluationBoundaryError(
            f"Unsupported legacy authority inputs: {unsupported}"
        )
    if verified_intake.get("kind") != "verified_architect_intake":
        raise EvaluationBoundaryError("Architect intake verification record is invalid")
    if verified_source_bundle.get("kind") != "verified_source_bundle":
        raise EvaluationBoundaryError("Source bundle verification record is invalid")
    validate_review_draft(draft, repo_root)
    metadata = _metadata(verified_intake, verified_source_bundle)
    requests = [copy.deepcopy(dict(item)) for item in runtime_execution_requests]
    try:
        payload, results = recompute_expected_payload(
            architect_intake=verified_intake["data"],
            source_bundle=verified_source_bundle["data"],
            review_draft=draft,
            repo_root=repo_root,
            runtime_execution_requests=requests,
            input_metadata=metadata,
        )
    except RuntimeExecutionBoundaryError as exc:
        raise EvaluationBoundaryError(str(exc)) from exc
    return {
        "kind": "ce_deterministic_evaluation_run",
        "architect_intake": _canonical_clone(verified_intake["data"]),
        "source_bundle": _canonical_clone(verified_source_bundle["data"]),
        "review_draft": _canonical_clone(draft),
        "runtime_execution_requests": requests,
        "input_metadata": metadata,
        "evaluation_results": results,
        "payload": payload,
        "run_digest": sha256_json(
            {
                "inputs": {
                    "architect_intake": verified_intake["data"],
                    "source_bundle": verified_source_bundle["data"],
                    "review_draft": draft,
                    "runtime_execution_requests": requests,
                },
                "payload": payload,
            }
        ),
    }


def verified_payload_data(
    evaluation_run: Mapping[str, Any],
    *,
    repo_root: Path,
    source_intake_bytes: bytes,
    source_bundle_bytes: bytes,
) -> dict[str, Any]:
    if evaluation_run.get("kind") != "ce_deterministic_evaluation_run":
        raise EvaluationBoundaryError("Expected a deterministic CE evaluation run mapping")
    metadata = evaluation_run.get("input_metadata")
    if not isinstance(metadata, Mapping):
        raise EvaluationBoundaryError("Evaluation run input metadata is missing")
    if hashlib.sha256(source_intake_bytes).hexdigest() != metadata.get(
        "intake_bytes_sha256"
    ):
        raise EvaluationBoundaryError("Architect intake bytes changed after evaluation")
    if hashlib.sha256(source_bundle_bytes).hexdigest() != metadata.get(
        "source_bundle_bytes_sha256"
    ):
        raise EvaluationBoundaryError("Architect source bundle bytes changed after evaluation")
    try:
        expected, expected_results = recompute_expected_payload(
            architect_intake=evaluation_run["architect_intake"],
            source_bundle=evaluation_run["source_bundle"],
            review_draft=evaluation_run["review_draft"],
            repo_root=repo_root,
            runtime_execution_requests=evaluation_run.get(
                "runtime_execution_requests"
            )
            or [],
            input_metadata=metadata,
        )
    except RuntimeExecutionBoundaryError as exc:
        raise EvaluationBoundaryError(str(exc)) from exc
    persisted = evaluation_run.get("payload")
    if not isinstance(persisted, Mapping):
        raise EvaluationBoundaryError("Evaluation run Payload is missing")
    diagnostics = compare_persisted_payload(persisted, expected)
    if diagnostics:
        first = diagnostics[0]
        raise EvaluationBoundaryError(
            f"{first['code']} at {first['path']}: {first['message']}"
        )
    if canonical_bytes(evaluation_run.get("evaluation_results")) != canonical_bytes(
        expected_results
    ):
        raise EvaluationBoundaryError(
            "Intermediate evaluation results differ from recomputation"
        )
    return copy.deepcopy(expected)


def evaluation_record(evaluation_run: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(evaluation_run))


def capability_record(evaluation_run: Mapping[str, Any]) -> dict[str, Any]:
    """Deprecated name retained as a data-copy compatibility shim."""
    return evaluation_record(evaluation_run)


__all__ = [
    "CLAIM_POLICIES",
    "CapabilityError",
    "DraftValidationError",
    "EvaluationBoundaryError",
    "EvidenceVerificationError",
    "RESOLVER_ID",
    "RESOLVER_VERSION",
    "VERIFIED_PAYLOAD_SCHEMA_ID",
    "VERIFIED_PAYLOAD_SCHEMA_VERSION",
    "VerifiedCEStagePayload",
    "assemble_verified_ce_stage_payload",
    "capability_record",
    "evaluation_record",
    "validate_review_draft",
    "verified_payload_data",
    "verify_architect_intake",
    "verify_repo_artifact",
    "verify_source_bundle",
]
