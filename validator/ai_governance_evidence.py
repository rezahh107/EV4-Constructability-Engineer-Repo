from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .ai_governance_core import (
    EXPECTED_REPOSITORY,
    SHA,
    _GATE_EVIDENCE_MARKER,
    _diagnostic,
    _list,
    _mapping,
    _sha256,
    ValidatedGovernanceState,
    is_validated_governance_state,
)


def compute_scope_disclosure(state: Mapping[str, Any], head_sha: str) -> dict[str, Any]:
    if not SHA.fullmatch(head_sha):
        raise ValueError("head_sha must be a full lowercase 40-character commit SHA")
    scope = _mapping(state.get("scope_projection"))
    sets = {
        "long_term_target_ids": sorted(set(_list(scope.get("long_term_target_ids")))),
        "committed_now_ids": sorted(set(_list(scope.get("committed_now_ids")))),
        "deferred_not_deleted_ids": sorted(set(_list(scope.get("deferred_not_deleted_ids")))),
        "rejected_ids": sorted(set(_list(scope.get("rejected_ids")))),
        "superseded_ids": sorted(set(_list(scope.get("superseded_ids")))),
        "implemented_ids": sorted(set(_list(scope.get("implemented_ids")))),
    }
    counts = {name.replace("_ids", "_count"): len(values) for name, values in sets.items()}
    decision_provenance = _mapping(scope.get("decision_provenance"))
    repository = _mapping(state.get("repository"))
    plan = _mapping(state.get("plan"))
    return {
        "schema_version": 1,
        "plan_id": plan.get("plan_id"),
        "scope_revision": scope.get("scope_revision"),
        "reviewed_head_sha": head_sha,
        "source_object_identities": {
            "repository": repository.get("name"),
            "default_branch": repository.get("default_branch"),
            "scope_state_path": "planning/GOVERNANCE_SCOPE_STATE.yml",
        },
        "sets": sets,
        "computed_counts": counts,
        "owner_facing": {
            "long_term_target_count": counts["long_term_target_count"],
            "committed_now_count": counts["committed_now_count"],
            "deferred_not_deleted_count": counts["deferred_not_deleted_count"],
            "permanently_deleted_count": 0,
            "scope_change_reason": decision_provenance.get("reason"),
            "computed_from_exact_head": head_sha,
        },
    }


def _git_head(repository_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value if SHA.fullmatch(value) else None


def record_ci_context(
    verification: ValidatedGovernanceState,
    *,
    head_sha: str,
    pr_number: int,
    output_path: str | Path,
    environ: Mapping[str, str] | None = None,
    git_head: str | None = None,
) -> dict[str, Any]:
    if not is_validated_governance_state(verification):
        raise ValueError("CI context requires verifier-created governance state")
    env = dict(os.environ if environ is None else environ)
    actual_git_head = git_head or _git_head(verification.repository_root)
    errors: list[str] = []
    if env.get("GITHUB_ACTIONS") != "true":
        errors.append("GITHUB_ACTIONS=true is required")
    if env.get("GITHUB_EVENT_NAME") != "pull_request":
        errors.append("GITHUB_EVENT_NAME must be pull_request")
    if env.get("GITHUB_REPOSITORY") != verification.state["repository"]["name"]:
        errors.append("GITHUB_REPOSITORY does not match canonical repository")
    if actual_git_head != head_sha:
        errors.append("git rev-parse HEAD does not match requested head")
    run_id = env.get("GITHUB_RUN_ID", "")
    job = env.get("GITHUB_JOB", "")
    if not run_id.isdigit() or not job:
        errors.append("GitHub run/job identity is incomplete")
    if errors:
        raise ValueError("; ".join(errors))
    context = {
        "schema_version": 1,
        "repository": verification.state["repository"]["name"],
        "pr_number": pr_number,
        "head_sha": head_sha,
        "scope_revision": verification.state["scope_projection"]["scope_revision"],
        "run_id": run_id,
        "job": job,
        "event_name": env["GITHUB_EVENT_NAME"],
        "completed_commands": list(verification.state["progress_gate"]["required_validation"]),
        "evidence_state": "TOOL_CONFIRMED",
        "limitation": "current workflow completion must be confirmed externally after this step exits",
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return context


@dataclass(frozen=True, slots=True)
class VerifiedGateEvidence:
    repository: str
    pr_number: int
    head_sha: str
    scope_revision: str
    scope_gate_passed: bool
    progress_gate_passed: bool
    exact_head_context_verified: bool
    exact_head_ci_passed: bool
    evidence_state: str
    artifact_records: tuple[Mapping[str, Any], ...]
    ci_context_sha256: str | None
    diagnostics: tuple[str, ...]
    state: Mapping[str, Any] = field(repr=False, compare=False)
    _marker: object = field(repr=False, compare=False, default=None)


def is_verified_gate_evidence(value: object) -> bool:
    return isinstance(value, VerifiedGateEvidence) and value._marker is _GATE_EVIDENCE_MARKER


def derive_gate_evidence(
    verification: ValidatedGovernanceState,
    *,
    head_sha: str,
    pr_number: int,
    ci_context_path: str | Path | None = None,
    git_head: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> VerifiedGateEvidence:
    if not is_validated_governance_state(verification):
        raise ValueError("gate evidence requires verifier-created governance state")
    if not SHA.fullmatch(head_sha):
        raise ValueError("head_sha must be a full lowercase 40-character commit SHA")
    env = dict(os.environ if environ is None else environ)
    actual_git_head = git_head or _git_head(verification.repository_root)
    diagnostics: list[str] = []
    context_verified = False
    context_hash: str | None = None
    if ci_context_path is not None:
        path = Path(ci_context_path)
        try:
            raw = path.read_bytes()
            context = json.loads(raw.decode("utf-8"))
            if not isinstance(context, dict):
                raise ValueError("CI context must be a JSON object")
            expected = (
                verification.state["repository"]["name"],
                pr_number,
                head_sha,
                verification.state["scope_projection"]["scope_revision"],
                env.get("GITHUB_RUN_ID"),
                env.get("GITHUB_JOB"),
                "pull_request",
                list(verification.state["progress_gate"]["required_validation"]),
            )
            actual = (
                context.get("repository"),
                context.get("pr_number"),
                context.get("head_sha"),
                context.get("scope_revision"),
                context.get("run_id"),
                context.get("job"),
                context.get("event_name"),
                context.get("completed_commands"),
            )
            if actual != expected:
                raise ValueError("CI context identity or validation sequence mismatch")
            if env.get("GITHUB_ACTIONS") != "true":
                raise ValueError("CI context is not executing inside GitHub Actions")
            if env.get("GITHUB_REPOSITORY") != verification.state["repository"]["name"]:
                raise ValueError("GitHub repository environment mismatch")
            if actual_git_head != head_sha:
                raise ValueError("git rev-parse HEAD does not match requested head")
            context_verified = True
            context_hash = _sha256(raw)
        except Exception as exc:
            diagnostics.append(f"CI execution context rejected: {exc}")
    else:
        diagnostics.append("authoritative exact-head CI completion evidence is not attached")

    exact_head_ci_passed = False
    evidence_state = "TOOL_CONFIRMED" if context_verified else "INSUFFICIENT_EVIDENCE"
    return VerifiedGateEvidence(
        verification.state["repository"]["name"],
        pr_number,
        head_sha,
        verification.state["scope_projection"]["scope_revision"],
        True,
        all(record["exists"] and record["non_empty"] for record in verification.artifact_records),
        context_verified,
        exact_head_ci_passed,
        evidence_state,
        verification.artifact_records,
        context_hash,
        tuple(diagnostics),
        verification.state,
        _GATE_EVIDENCE_MARKER,
    )


def compute_completion_receipt(
    gate_evidence: VerifiedGateEvidence,
    review_capability: VerifiedReviewCapability | None = None,
) -> dict[str, Any]:
    from .ai_governance_review import is_verified_review_capability

    if not is_verified_gate_evidence(gate_evidence):
        raise ValueError("completion receipt requires verifier-created gate evidence")
    blocking_state = "INSUFFICIENT_EVIDENCE"
    blocking_count: int | None = None
    if is_verified_review_capability(review_capability):
        blocking_state = "AI_REVIEW_SIGNAL"
        blocking_count = review_capability.blocking_findings_count
    repository = _mapping(gate_evidence.state.get("repository"))
    progress = _mapping(gate_evidence.state.get("progress_gate"))
    scope = _mapping(gate_evidence.state.get("scope_projection"))
    return {
        "schema_version": 2,
        "phase": scope.get("phase"),
        "scope_revision": gate_evidence.scope_revision,
        "implementation_status": "implemented_pending_rereview",
        "repository": {
            "name": gate_evidence.repository,
            "default_branch": repository.get("default_branch"),
            "base_sha": repository.get("audit_base_sha"),
            "reviewed_head_sha": gate_evidence.head_sha,
        },
        "required_artifacts": [dict(record) for record in gate_evidence.artifact_records],
        "gates": {
            "scope_gate_passed": gate_evidence.scope_gate_passed,
            "progress_gate_passed": gate_evidence.progress_gate_passed,
            "exact_head_context_verified": gate_evidence.exact_head_context_verified,
            "exact_head_ci_passed": gate_evidence.exact_head_ci_passed,
            "blocking_findings": {
                "count": blocking_count,
                "evidence": blocking_state,
            },
        },
        "validation": {
            "exact_head": {
                "tested_sha": gate_evidence.head_sha,
                "reviewed_head_sha": gate_evidence.head_sha,
                "exact_head_match": gate_evidence.exact_head_context_verified,
                "synthetic_merge": False,
                "evidence": gate_evidence.evidence_state,
            },
            "ci_context_sha256": gate_evidence.ci_context_sha256,
            "diagnostics": list(gate_evidence.diagnostics),
        },
        "open_gates": [
            "authoritative_exact_head_ci_confirmation",
            "independent_ai_review",
            "user_merge",
            "post_merge_verification",
        ],
        "prohibited_claims": progress.get("prohibited_claims", []),
    }
