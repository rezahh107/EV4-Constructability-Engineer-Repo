from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_adapters import ArtifactAdapterError, ArtifactBinding, evaluate_artifact_source
from .claim_policy_registry import CLAIM_POLICIES, POST_BUILDER_RUNTIME, policy_projection



class ClaimEvaluationError(ValueError):
    """Raised when claim inputs are malformed rather than merely incomplete."""


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


def _draft_node(review_draft: Mapping[str, Any], subject_ref: str) -> dict[str, Any]:
    for item in review_draft.get("reviewed_nodes") or []:
        if isinstance(item, Mapping) and item.get("node_id") == subject_ref:
            return dict(item)
    return {}


def _semantics(node: Mapping[str, Any], claim_id: str) -> dict[str, Any]:
    raw = node.get("claim_semantics")
    if isinstance(raw, Mapping) and isinstance(raw.get(claim_id), Mapping):
        return dict(raw[claim_id])
    return {}


def _candidate_sources(node: Mapping[str, Any], claim_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    raw = node.get("candidate_source_refs")
    if not isinstance(raw, list):
        return result
    for item in raw:
        if isinstance(item, Mapping) and item.get("claim_id") == claim_id:
            result.append(dict(item))
    return result


def _base_evaluation(
    claim_id: str,
    subject_ref: str,
    *,
    status: str,
    facts: Mapping[str, Any] | None = None,
    evidence_refs: Sequence[str] = (),
    limitations: Sequence[str] = (),
    diagnostics: Sequence[Mapping[str, Any]] = (),
    downstream_obligation: Mapping[str, Any] | None = None,
    evidence_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    policy = CLAIM_POLICIES[claim_id]
    return {
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "lifecycle_phase": policy["lifecycle_phase"],
        "status": status,
        "blocking": (
            policy["lifecycle_phase"] != POST_BUILDER_RUNTIME
            and status not in {"satisfied", "not_applicable"}
        ),
        "authority_owner": policy["authority_owner"],
        "applicable_rule": policy["applicable_rule"],
        "facts": dict(facts or {}),
        "evidence_refs": sorted(str(value) for value in evidence_refs),
        "limitations": [str(value) for value in limitations],
        "diagnostics": [dict(value) for value in diagnostics],
        "downstream_obligation": (
            dict(downstream_obligation) if downstream_obligation else None
        ),
        "evidence_records": [dict(value) for value in evidence_records],
        "policy": policy_projection(claim_id),
    }


def _semantic_missing(claim_id: str, semantics: Mapping[str, Any]) -> list[str]:
    required = CLAIM_POLICIES[claim_id]["required_semantics"]
    return [str(key) for key in required if semantics.get(key) in (None, "", [], {})]


def _attributed_evaluation(
    claim_id: str,
    subject_ref: str,
    node: Mapping[str, Any],
    semantics: Mapping[str, Any],
) -> dict[str, Any]:
    missing = _semantic_missing(claim_id, semantics)
    rationale = str(node.get("engineering_rationale") or "").strip()
    assumptions = [
        str(item) for item in node.get("assumptions") or [] if str(item).strip()
    ]
    if missing or not rationale or not assumptions:
        details: list[str] = []
        if missing:
            details.append(f"missing semantics: {', '.join(missing)}")
        if not rationale:
            details.append("engineering rationale is missing")
        if not assumptions:
            details.append("explicit premises are missing")
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="insufficient_evidence",
            limitations=details,
            diagnostics=[{"code": "CE_CLAIM_ATTRIBUTED_JUDGMENT_INCOMPLETE"}],
        )
    record = {
        "mode": "ATTRIBUTED_ENGINEERING_JUDGMENT",
        "claim_id": claim_id,
        "subject_ref": subject_ref,
        "reviewer_identity": str(
            node.get("reviewer_identity") or "constructability_engineer"
        ),
        "premises": assumptions,
        "derivation_method": rationale,
        "semantic_facts": dict(semantics),
        "limitations": [str(item) for item in node.get("limitations") or []],
    }
    evidence_id = sha256_json(record)
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="satisfied",
        facts=semantics,
        evidence_refs=[evidence_id],
        limitations=record["limitations"],
        evidence_records=[{**record, "evidence_id": evidence_id}],
    )


def _resolve_repo_path(repo_root: Path, source_ref: str) -> Path:
    root = repo_root.resolve(strict=True)
    candidate = Path(source_ref)
    path = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ClaimEvaluationError(
            "Repository source escaped repo root or is unavailable"
        ) from exc
    if not resolved.is_file():
        raise ClaimEvaluationError("Repository source is not a file")
    return resolved


def _source_ref(source: Mapping[str, Any]) -> str | None:
    # Legacy source_ref is treated as the original artifact for compatibility. A facts envelope
    # at that path is rejected by the parser and cannot become evidence.
    value = source.get("original_source_ref", source.get("source_ref"))
    return str(value) if isinstance(value, str) and value else None


def _artifact_source_evaluation(
    claim_id: str,
    subject_ref: str,
    node: Mapping[str, Any],
    semantics: Mapping[str, Any],
    repo_root: Path,
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = _candidate_sources(node, claim_id)
    if not candidates:
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="insufficient_evidence",
            limitations=["No original source artifact was supplied."],
            diagnostics=[{"code": "CE_CLAIM_ORIGINAL_SOURCE_REQUIRED"}],
        )
    candidate_id = architect_intake.get("selected_architecture", {}).get(
        "selected_candidate_id"
    )
    bundle_id = source_bundle.get("bundle_id")
    if not isinstance(candidate_id, str) or not isinstance(bundle_id, str):
        raise ClaimEvaluationError("Canonical artifact binding identity is incomplete")
    binding = ArtifactBinding(
        claim_id=claim_id,
        subject_ref=subject_ref,
        selected_candidate_id=candidate_id,
        source_bundle_id=bundle_id,
        intake_digest=sha256_json(architect_intake),
    )
    diagnostics: list[dict[str, Any]] = []
    limitations: list[str] = []
    for source in candidates:
        if source.get("mode") not in {None, "VERIFIED_ARTIFACT", "ORIGINAL_SOURCE"}:
            diagnostics.append({"code": "CE_CLAIM_SOURCE_MODE_INVALID"})
            continue
        original_ref = _source_ref(source)
        if original_ref is None:
            diagnostics.append({"code": "CE_CLAIM_ORIGINAL_SOURCE_REQUIRED"})
            continue
        try:
            path = _resolve_repo_path(repo_root, original_ref)
            declared_type = source.get("source_type")
            actual_type = {
                ".json": "json",
                ".html": "html",
                ".htm": "html",
                ".css": "css",
                ".svg": "svg",
            }.get(path.suffix.casefold())
            if declared_type is not None and declared_type != actual_type:
                raise ClaimEvaluationError(
                    f"Declared source_type {declared_type!r} does not match original source"
                )
            declared_digest = source.get("source_bytes_sha256")
            observed_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if (
                declared_digest is not None
                and declared_digest != observed_digest
            ):
                raise ClaimEvaluationError(
                    "Original source digest differs from the declared digest"
                )
            cached_path = None
            cached_ref = source.get("cached_extract_ref")
            if isinstance(cached_ref, str) and cached_ref:
                cached_path = _resolve_repo_path(repo_root, cached_ref)
            facts, adapter_metadata = evaluate_artifact_source(
                claim_id=claim_id,
                path=path,
                semantics=semantics,
                binding=binding,
                cached_extract_path=cached_path,
            )
        except (OSError, ClaimEvaluationError, ArtifactAdapterError) as exc:
            limitations.append(str(exc))
            diagnostics.append(
                {
                    "code": "CE_CLAIM_ORIGINAL_SOURCE_UNSUPPORTED_OR_MISMATCHED",
                    "source_ref": original_ref,
                }
            )
            continue
        record = {
            "mode": "VERIFIED_ARTIFACT",
            "claim_id": claim_id,
            "subject_ref": subject_ref,
            "source_ref": original_ref,
            "source_identity": str(source.get("source_identity") or original_ref),
            "source_bytes_sha256": adapter_metadata["source_bytes_sha256"],
            "source_schema_id": adapter_metadata["schema_id"],
            "source_role": adapter_metadata["source_role"],
            "adapter_id": adapter_metadata["adapter_id"],
            "cached_extract_sha256": adapter_metadata.get("cached_extract_sha256"),
            "semantic_facts": facts,
            "verification": "original_source_claim_specific_parser",
        }
        evidence_id = sha256_json(record)
        return _base_evaluation(
            claim_id,
            subject_ref,
            status="satisfied",
            facts=facts,
            evidence_refs=[evidence_id],
            evidence_records=[{**record, "evidence_id": evidence_id}],
        )
    return _base_evaluation(
        claim_id,
        subject_ref,
        status="insufficient_evidence",
        limitations=limitations
        or ["No original source parser semantically established the claim."],
        diagnostics=diagnostics,
    )


