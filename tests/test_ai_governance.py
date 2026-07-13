from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import validator.ai_governance as gov

ROOT = Path(__file__).resolve().parents[1]
HEAD = "f" * 40
PR_NUMBER = 35
SCOPE_REVISION = "CE-GOV-ALL-v2"


def _canonical_json(value: dict[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _write_review_bundle(
    directory: Path,
    *,
    head_sha: str = HEAD,
    scope_revision: str = SCOPE_REVISION,
    protocol_version: str = "v1.9.0",
    include_session_id: bool = True,
    technical_status: str = "RED_DO_NOT_MERGE",
    blocking_findings_count: int = 1,
    include_self_declared_separation: bool = False,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    identity: dict[str, object] = {
        "target_repository": gov.EXPECTED_REPOSITORY,
        "pr_number": PR_NUMBER,
        "reviewed_head_sha": head_sha,
        "reviewed_scope_revision": scope_revision,
        "review_validity": "CURRENT",
        "inspector_repository": gov.EXPECTED_INSPECTOR_REPOSITORY,
        "inspector_commit_sha": "1" * 40,
    }
    if include_session_id:
        identity["review_session_id"] = "review-session-001"
    if include_self_declared_separation:
        identity["session_is_separate"] = True
    findings = [
        {"finding_id": f"PRF-{index + 1:03d}", "blocking": True}
        for index in range(blocking_findings_count)
    ]
    package = {
        "protocol_version": protocol_version,
        "protocol_sha256": "a" * 64,
        "review_identity": identity,
        "scope": {
            "coverage_complete": True,
            "files_fully_reviewed": ["planning/GOVERNANCE_SCOPE_STATE.yml"],
        },
        "decision": {
            "technical_status": technical_status,
            "blocking_findings_count": blocking_findings_count,
        },
        "findings": findings,
    }
    projection = {
        "protocol_version": protocol_version,
        "review_identity": {
            "reviewed_head_sha": head_sha,
            "reviewed_scope_revision": scope_revision,
            "validity": "CURRENT",
        },
        "technical_status": technical_status,
    }
    package_bytes = json.dumps(package, indent=2, ensure_ascii=False).encode("utf-8")
    projection_bytes = json.dumps(projection, indent=2, ensure_ascii=False).encode("utf-8")
    (directory / "review-package.json").write_bytes(package_bytes)
    (directory / "DECISION_PROJECTION.json").write_bytes(projection_bytes)
    manifest = {
        "schema_version": 2,
        "canonical_review_package": {
            "path": "review-package.json",
            "canonical_hash_scope": "canonical_sorted_compact_utf8_json",
            "canonical_sha256": hashlib.sha256(_canonical_json(package)).hexdigest(),
            "file_hash_scope": "final_file_bytes",
            "file_sha256": hashlib.sha256(package_bytes).hexdigest(),
        },
        "decision_projection": {
            "path": "DECISION_PROJECTION.json",
            "hash_scope": "final_file_bytes",
            "sha256": hashlib.sha256(projection_bytes).hexdigest(),
        },
    }
    (directory / "artifact-manifest.json").write_text(
        json.dumps(manifest, separators=(",", ":")),
        encoding="utf-8",
    )
    return directory


def _validated_state() -> gov.ValidatedGovernanceState:
    result = gov.validate_repository_state(repository_root=ROOT)
    assert result["passed"], result["diagnostics"]
    return result["verification"]


def _gate_evidence() -> gov.VerifiedGateEvidence:
    verification = _validated_state()
    return gov.derive_gate_evidence(
        verification,
        head_sha=HEAD,
        pr_number=PR_NUMBER,
        git_head=HEAD,
        environ={},
    )


def test_repository_governance_state_is_valid() -> None:
    result = gov.validate_repository_state(repository_root=ROOT)
    assert result["passed"], result["diagnostics"]
    assert gov.is_validated_governance_state(result["verification"])


@pytest.mark.parametrize(
    ("field", "required"),
    [
        ("minimum_security_controls", gov.MINIMUM_SECURITY_CONTROLS_V1),
        ("intentionally_out_of_scope_controls", gov.INTENTIONAL_EXCLUSIONS_V1),
        ("activation_triggers", gov.ACTIVATION_TRIGGERS_V1),
    ],
)
def test_security_identity_sets_reject_each_deleted_identity(
    field: str,
    required: tuple[str, ...],
) -> None:
    for identity in required:
        profile = gov.load_yaml(gov.DEFAULT_PROFILE)
        profile[field].remove(identity)
        errors = gov.validate_profile(profile)
        assert any(identity in error or "exactly" in error for error in errors), identity


@pytest.mark.parametrize(
    "field",
    [
        "minimum_security_controls",
        "intentionally_out_of_scope_controls",
        "activation_triggers",
    ],
)
def test_security_identity_sets_reject_substitution_and_duplicate_padding(field: str) -> None:
    profile = gov.load_yaml(gov.DEFAULT_PROFILE)
    profile[field][-1] = "substituted_dummy_identity"
    errors = gov.validate_profile(profile)
    assert any("substituted" in error for error in errors)

    profile = gov.load_yaml(gov.DEFAULT_PROFILE)
    profile[field][-1] = profile[field][0]
    errors = gov.validate_profile(profile)
    assert any("duplicate padding" in error for error in errors)


def test_profile_null_fields_return_diagnostics_not_tracebacks() -> None:
    profile = gov.load_yaml(gov.DEFAULT_PROFILE)
    profile["technical_authority"] = None
    profile["review_protocol"] = None
    profile["evidence_states"] = None
    profile["minimum_security_controls"] = None
    errors = gov.validate_profile(profile)
    assert errors
    assert any("technical_authority" in error for error in errors)
    assert any("review protocol" in error for error in errors)


def test_schema_failure_skips_semantic_dereference(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yml"
    state_path = tmp_path / "state.yml"
    schema_path = tmp_path / "schema.json"
    profile_path.write_text(gov.DEFAULT_PROFILE.read_text(encoding="utf-8"), encoding="utf-8")
    state = gov.load_yaml(gov.DEFAULT_STATE)
    state["scope_projection"] = None
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
    schema_path.write_text(gov.DEFAULT_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    result = gov.validate_repository_state(
        profile_path=profile_path,
        state_path=state_path,
        schema_path=schema_path,
        repository_root=ROOT,
    )
    assert result["passed"] is False
    assert any(item["stage"] == "state_schema" for item in result["diagnostics"])
    assert not any(item["stage"] == "scope_semantics" for item in result["diagnostics"])


@pytest.mark.parametrize("missing_path", sorted(gov.CANONICAL_REQUIRED_ARTIFACTS))
def test_each_missing_required_artifact_blocks_progress(
    tmp_path: Path,
    missing_path: str,
) -> None:
    state = gov.load_yaml(gov.DEFAULT_STATE)
    for relative in state["progress_gate"]["required_artifacts"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("evidence\n", encoding="utf-8")
    (tmp_path / missing_path).unlink()
    records, errors = gov.validate_required_artifacts(state, repository_root=tmp_path)
    assert any(missing_path in error for error in errors)
    assert any(record["path"] == missing_path and record["exists"] is False for record in records)


def test_empty_required_artifact_blocks_progress(tmp_path: Path) -> None:
    state = gov.load_yaml(gov.DEFAULT_STATE)
    for relative in state["progress_gate"]["required_artifacts"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("evidence\n", encoding="utf-8")
    empty_path = state["progress_gate"]["required_artifacts"][0]
    (tmp_path / empty_path).write_bytes(b"")
    _, errors = gov.validate_required_artifacts(state, repository_root=tmp_path)
    assert any("empty" in error and empty_path in error for error in errors)


def test_locally_generated_context_is_not_ci_confirmed(tmp_path: Path) -> None:
    verification = _validated_state()
    context_path = tmp_path / "ci-context.json"
    env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REPOSITORY": gov.EXPECTED_REPOSITORY,
        "GITHUB_RUN_ID": "12345",
        "GITHUB_JOB": "test",
    }
    gov.record_ci_context(
        verification,
        head_sha=HEAD,
        pr_number=PR_NUMBER,
        output_path=context_path,
        environ=env,
        git_head=HEAD,
    )
    evidence = gov.derive_gate_evidence(
        verification,
        head_sha=HEAD,
        pr_number=PR_NUMBER,
        ci_context_path=context_path,
        environ=env,
        git_head=HEAD,
    )
    assert evidence.exact_head_context_verified is True
    assert evidence.exact_head_ci_passed is False
    assert evidence.evidence_state == "TOOL_CONFIRMED"
    receipt = gov.compute_completion_receipt(evidence)
    assert receipt["gates"]["exact_head_ci_passed"] is False
    assert receipt["validation"]["exact_head"]["evidence"] != "CI_CONFIRMED"


def test_plain_mappings_and_caller_true_predicates_cannot_unlock_green() -> None:
    result = gov.evaluate_merge_gate(
        gate_evidence={
            "exact_head_ci_passed": True,
            "scope_gate_passed": True,
            "progress_gate_passed": True,
        },
        review_capability={
            "verdict": gov.GREEN,
            "blocking_findings": 0,
        },
    )
    assert result["passed"] is False
    assert result["merge_recommendation"] is False
    assert result["status"] == "FAIL-CLOSED"


def test_missing_review_stays_pending_rereview() -> None:
    result = gov.evaluate_merge_gate(gate_evidence=_gate_evidence(), review_capability=None)
    assert result["passed"] is False
    assert result["merge_recommendation"] is False
    assert result["status"] == "IMPLEMENTED_PENDING_REREVIEW"


def test_canonical_bundle_alone_cannot_unlock_green(tmp_path: Path) -> None:
    bundle_dir = _write_review_bundle(
        tmp_path / "bundle",
        technical_status=gov.GREEN,
        blocking_findings_count=0,
    )
    evidence = gov.inspect_canonical_review_bundle(
        bundle_dir,
        expected_repository=gov.EXPECTED_REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
        expected_scope_revision=SCOPE_REVISION,
        minimum_protocol_version="v1.9.0",
    )
    result = gov.evaluate_merge_gate(
        gate_evidence=_gate_evidence(),
        review_capability=evidence,
    )
    assert result["passed"] is False
    assert "official PR Inspector" in result["errors"][0]


def test_old_protocol_version_cannot_pass(tmp_path: Path) -> None:
    bundle_dir = _write_review_bundle(tmp_path / "bundle", protocol_version="v0.0.1")
    with pytest.raises(ValueError, match="below the required minimum"):
        gov.inspect_canonical_review_bundle(
            bundle_dir,
            expected_repository=gov.EXPECTED_REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
            expected_scope_revision=SCOPE_REVISION,
            minimum_protocol_version="v1.9.0",
        )


def test_missing_review_session_id_cannot_pass_even_with_self_declared_separation(
    tmp_path: Path,
) -> None:
    bundle_dir = _write_review_bundle(
        tmp_path / "bundle",
        include_session_id=False,
        include_self_declared_separation=True,
    )
    with pytest.raises(ValueError, match="review_session_id"):
        gov.inspect_canonical_review_bundle(
            bundle_dir,
            expected_repository=gov.EXPECTED_REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
            expected_scope_revision=SCOPE_REVISION,
            minimum_protocol_version="v1.9.0",
        )


def test_stale_head_and_scope_are_rejected(tmp_path: Path) -> None:
    stale_head = _write_review_bundle(tmp_path / "head", head_sha="e" * 40)
    with pytest.raises(ValueError, match="repository/PR/head/scope"):
        gov.inspect_canonical_review_bundle(
            stale_head,
            expected_repository=gov.EXPECTED_REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
            expected_scope_revision=SCOPE_REVISION,
            minimum_protocol_version="v1.9.0",
        )
    stale_scope = _write_review_bundle(tmp_path / "scope", scope_revision="CE-GOV-OLD-v1")
    with pytest.raises(ValueError, match="repository/PR/head/scope"):
        gov.inspect_canonical_review_bundle(
            stale_scope,
            expected_repository=gov.EXPECTED_REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
            expected_scope_revision=SCOPE_REVISION,
            minimum_protocol_version="v1.9.0",
        )


def test_manifest_hash_tampering_is_rejected(tmp_path: Path) -> None:
    bundle_dir = _write_review_bundle(tmp_path / "bundle")
    package_path = bundle_dir / "review-package.json"
    package_path.write_text(package_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="file hash mismatch"):
        gov.inspect_canonical_review_bundle(
            bundle_dir,
            expected_repository=gov.EXPECTED_REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
            expected_scope_revision=SCOPE_REVISION,
            minimum_protocol_version="v1.9.0",
        )


def test_forged_capability_marker_cannot_unlock_green() -> None:
    forged = gov.VerifiedReviewCapability(
        gov.EXPECTED_REPOSITORY,
        PR_NUMBER,
        HEAD,
        SCOPE_REVISION,
        "v1.9.0",
        gov.EXPECTED_INSPECTOR_REPOSITORY,
        "1" * 40,
        "fake-session",
        gov.GREEN,
        0,
        {},
        True,
        object(),
    )
    assert gov.is_verified_review_capability(forged) is False
    result = gov.evaluate_merge_gate(gate_evidence=_gate_evidence(), review_capability=forged)
    assert result["passed"] is False
    assert result["merge_recommendation"] is False


def test_cli_malformed_profile_returns_structured_fail_closed_json(tmp_path: Path) -> None:
    profile = gov.load_yaml(gov.DEFAULT_PROFILE)
    profile["technical_authority"] = None
    profile_path = tmp_path / "profile.yml"
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-ai-governance.py"),
            "--profile",
            str(profile_path),
            "--head-sha",
            HEAD,
            "--pr-number",
            str(PR_NUMBER),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "FAIL-CLOSED"
    assert isinstance(payload["diagnostics"], list)
    assert "Traceback" not in completed.stderr
