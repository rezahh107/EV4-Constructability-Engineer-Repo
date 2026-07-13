from __future__ import annotations

import importlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .ai_governance_core import (
    EXPECTED_INSPECTOR_REPOSITORY,
    GREEN,
    REQUIRED_REVIEW_ARTIFACTS,
    SHA,
    _CANONICAL_REVIEW_MARKER,
    _REVIEW_CAPABILITY_MARKER,
    _canonical_json,
    _mapping,
    _sha256,
    _version_tuple,
)


@dataclass(frozen=True, slots=True)
class CanonicalReviewBundleEvidence:
    directory: Path
    repository: str
    pr_number: int
    head_sha: str
    scope_revision: str
    protocol_version: str
    inspector_repository: str
    inspector_commit_sha: str
    review_session_id: str
    technical_status: str
    blocking_findings_count: int
    package_canonical_sha256: str
    package_file_sha256: str
    decision_projection_sha256: str
    artifact_manifest_sha256: str
    artifact_sha256: Mapping[str, str]
    _marker: object = field(repr=False, compare=False)


def is_canonical_review_bundle_evidence(value: object) -> bool:
    return (
        isinstance(value, CanonicalReviewBundleEvidence)
        and value._marker is _CANONICAL_REVIEW_MARKER
    )


def _load_json_bytes(name: str, raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse {name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return value


def inspect_canonical_review_bundle(
    directory: str | Path,
    *,
    expected_repository: str,
    expected_pr_number: int,
    expected_head_sha: str,
    expected_scope_revision: str,
    minimum_protocol_version: str,
    expected_inspector_repository: str = EXPECTED_INSPECTOR_REPOSITORY,
    implementer_session_id: str | None = None,
) -> CanonicalReviewBundleEvidence:
    target = Path(directory).resolve()
    if not target.is_dir():
        raise ValueError("review bundle directory is missing")
    if not SHA.fullmatch(expected_head_sha):
        raise ValueError("expected_head_sha must be a full lowercase 40-character SHA")
    required_bytes: dict[str, bytes] = {}
    for name in REQUIRED_REVIEW_ARTIFACTS:
        path = target / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing canonical review artifact: {name}")
        raw = path.read_bytes()
        if not raw:
            raise ValueError(f"canonical review artifact is empty: {name}")
        required_bytes[name] = raw
    package = _load_json_bytes("review-package.json", required_bytes["review-package.json"])
    projection = _load_json_bytes(
        "DECISION_PROJECTION.json", required_bytes["DECISION_PROJECTION.json"]
    )
    manifest = _load_json_bytes("artifact-manifest.json", required_bytes["artifact-manifest.json"])

    canonical = _mapping(manifest.get("canonical_review_package"))
    if canonical.get("path") != "review-package.json":
        raise ValueError("artifact manifest review-package path mismatch")
    package_canonical_hash = _sha256(_canonical_json(package))
    package_file_hash = _sha256(required_bytes["review-package.json"])
    if canonical.get("canonical_sha256") != package_canonical_hash:
        raise ValueError("canonical review package hash mismatch")
    if canonical.get("file_sha256") != package_file_hash:
        raise ValueError("review package file hash mismatch")

    projection_spec = _mapping(manifest.get("decision_projection"))
    projection_hash = _sha256(required_bytes["DECISION_PROJECTION.json"])
    if projection_spec.get("path") != "DECISION_PROJECTION.json":
        raise ValueError("decision projection path mismatch")
    if projection_spec.get("sha256") != projection_hash:
        raise ValueError("decision projection hash mismatch")

    artifact_hashes: dict[str, str] = {}
    for key, raw_spec in manifest.items():
        if key in {"schema_version", "canonical_review_package", "decision_projection"}:
            continue
        spec = _mapping(raw_spec)
        if spec.get("generated") is False:
            continue
        path_name = spec.get("path")
        expected_hash = spec.get("sha256")
        if not isinstance(path_name, str) or not isinstance(expected_hash, str):
            continue
        artifact_path = target / path_name
        if artifact_path.is_symlink() or not artifact_path.is_file():
            raise ValueError(f"manifest-referenced artifact is missing: {path_name}")
        digest = _sha256(artifact_path.read_bytes())
        if expected_hash != digest:
            raise ValueError(f"manifest-referenced artifact hash mismatch: {path_name}")
        artifact_hashes[path_name] = digest
    artifact_hashes.update(
        {
            "review-package.json": package_file_hash,
            "DECISION_PROJECTION.json": projection_hash,
            "artifact-manifest.json": _sha256(required_bytes["artifact-manifest.json"]),
        }
    )

    identity = _mapping(package.get("review_identity"))
    exact_identity = (
        identity.get("target_repository"),
        identity.get("pr_number"),
        identity.get("reviewed_head_sha"),
        identity.get("reviewed_scope_revision"),
    )
    if exact_identity != (
        expected_repository,
        expected_pr_number,
        expected_head_sha,
        expected_scope_revision,
    ):
        raise ValueError("canonical review identity does not match repository/PR/head/scope")
    if identity.get("review_validity") != "CURRENT":
        raise ValueError("canonical review validity must be CURRENT")
    inspector_repository = identity.get("inspector_repository")
    inspector_commit_sha = identity.get("inspector_commit_sha")
    if inspector_repository != expected_inspector_repository:
        raise ValueError("inspector repository provenance mismatch")
    if not isinstance(inspector_commit_sha, str) or not SHA.fullmatch(inspector_commit_sha):
        raise ValueError("inspector commit provenance is missing or invalid")
    session_id = identity.get("review_session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("review_identity.review_session_id is required")
    if implementer_session_id and session_id == implementer_session_id:
        raise ValueError("implementer session cannot self-issue independent review")

    package_protocol = package.get("protocol_version")
    projection_protocol = projection.get("protocol_version")
    actual_version = _version_tuple(str(package_protocol))
    minimum_version = _version_tuple(minimum_protocol_version)
    if actual_version is None or minimum_version is None or actual_version < minimum_version:
        raise ValueError("canonical review protocol version is below the required minimum")
    if projection_protocol != package_protocol:
        raise ValueError("decision projection protocol version mismatch")

    projection_identity = _mapping(projection.get("review_identity"))
    if (
        projection_identity.get("reviewed_head_sha"),
        projection_identity.get("reviewed_scope_revision"),
        projection_identity.get("validity"),
    ) != (expected_head_sha, expected_scope_revision, "CURRENT"):
        raise ValueError("decision projection identity is stale or incomplete")

    review_scope = _mapping(package.get("scope"))
    fully_reviewed = review_scope.get("files_fully_reviewed")
    if review_scope.get("coverage_complete") is not True or not isinstance(fully_reviewed, list):
        raise ValueError("canonical review scope coverage is incomplete")
    if "planning/GOVERNANCE_SCOPE_STATE.yml" not in fully_reviewed:
        raise ValueError("canonical review did not cover the scope authority")

    decision = _mapping(package.get("decision"))
    findings = package.get("findings")
    if not isinstance(findings, list):
        raise ValueError("canonical review findings must be an array")
    blocking_count = sum(
        1 for item in findings if isinstance(item, Mapping) and item.get("blocking") is True
    )
    if decision.get("blocking_findings_count") != blocking_count:
        raise ValueError("blocking finding count is not derived from canonical findings")
    technical_status = decision.get("technical_status")
    if projection.get("technical_status") != technical_status:
        raise ValueError("canonical decision and projection technical status mismatch")

    return CanonicalReviewBundleEvidence(
        target,
        expected_repository,
        expected_pr_number,
        expected_head_sha,
        expected_scope_revision,
        str(package_protocol),
        inspector_repository,
        inspector_commit_sha,
        session_id,
        str(technical_status),
        blocking_count,
        package_canonical_hash,
        package_file_hash,
        projection_hash,
        artifact_hashes["artifact-manifest.json"],
        MappingProxyType(dict(sorted(artifact_hashes.items()))),
        _CANONICAL_REVIEW_MARKER,
    )


@dataclass(frozen=True, slots=True)
class VerifiedReviewCapability:
    repository: str
    pr_number: int
    head_sha: str
    scope_revision: str
    protocol_version: str
    inspector_repository: str
    inspector_commit_sha: str
    review_session_id: str
    technical_status: str
    blocking_findings_count: int
    artifact_sha256: Mapping[str, str]
    authoritative_provenance_verified: bool
    _marker: object = field(repr=False, compare=False)


def is_verified_review_capability(value: object) -> bool:
    return (
        isinstance(value, VerifiedReviewCapability)
        and value._marker is _REVIEW_CAPABILITY_MARKER
        and value.authoritative_provenance_verified is True
    )


def _normalized_remote(value: str) -> str:
    text = value.strip()
    if text.endswith(".git"):
        text = text[:-4]
    if text.startswith("git@github.com:"):
        text = "https://github.com/" + text.removeprefix("git@github.com:")
    return text.rstrip("/")


def verify_pr_inspector_review_bundle(
    bundle: CanonicalReviewBundleEvidence,
    *,
    inspector_source_directory: str | Path,
    github_token: str | None = None,
    github_api_version: str = "2022-11-28",
) -> VerifiedReviewCapability:
    if not is_canonical_review_bundle_evidence(bundle):
        raise ValueError("authoritative review requires verifier-created canonical bundle evidence")
    source_dir = Path(inspector_source_directory).resolve()
    try:
        source_head = subprocess.run(
            ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "-C", str(source_dir), "config", "--get", "remote.origin.url"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"inspector source provenance is unavailable: {exc}") from exc
    if source_head != bundle.inspector_commit_sha:
        raise ValueError("inspector checkout commit does not match canonical review provenance")
    expected_remote = f"https://github.com/{bundle.inspector_repository}"
    if _normalized_remote(remote) != expected_remote:
        raise ValueError("inspector checkout repository does not match canonical provenance")
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(source_dir),
                "fetch",
                "--no-tags",
                "--depth=1",
                "origin",
                bundle.inspector_commit_sha,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        fetched_head = subprocess.run(
            ["git", "-C", str(source_dir), "rev-parse", "FETCH_HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"live inspector commit provenance could not be verified: {exc}") from exc
    if fetched_head != bundle.inspector_commit_sha:
        raise ValueError("live inspector repository did not resolve the declared commit")

    original_path = list(sys.path)
    try:
        sys.path.insert(0, str(source_dir))
        for name in list(sys.modules):
            if name == "pr_inspector" or name.startswith("pr_inspector."):
                del sys.modules[name]
        official = importlib.import_module("pr_inspector.official_review")
        module_path = Path(str(official.__file__)).resolve()
        module_path.relative_to(source_dir)
        head_source = official.github_pull_request_head_source(
            bundle.repository,
            bundle.pr_number,
            token=github_token,
            api_version=github_api_version,
        )
        completion = official.verify_completed_review(
            bundle.directory,
            head_source=head_source,
        )
        if not official.is_verified_review_completion(completion):
            raise ValueError("PR Inspector did not return verifier-created completion")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"official PR Inspector completion failed: {exc}") from exc
    finally:
        sys.path[:] = original_path

    completion_identity = (
        completion.target_repository,
        completion.pr_number,
        completion.reviewed_head_sha,
        completion.protocol_version,
        completion.review_package_canonical_sha256,
        completion.review_package_file_sha256,
        completion.decision_projection_sha256,
        completion.artifact_manifest_sha256,
    )
    expected_identity = (
        bundle.repository,
        bundle.pr_number,
        bundle.head_sha,
        bundle.protocol_version,
        bundle.package_canonical_sha256,
        bundle.package_file_sha256,
        bundle.decision_projection_sha256,
        bundle.artifact_manifest_sha256,
    )
    if completion_identity != expected_identity:
        raise ValueError("official PR Inspector completion identity or hashes mismatch")

    return VerifiedReviewCapability(
        bundle.repository,
        bundle.pr_number,
        bundle.head_sha,
        bundle.scope_revision,
        bundle.protocol_version,
        bundle.inspector_repository,
        bundle.inspector_commit_sha,
        bundle.review_session_id,
        bundle.technical_status,
        bundle.blocking_findings_count,
        bundle.artifact_sha256,
        True,
        _REVIEW_CAPABILITY_MARKER,
    )
