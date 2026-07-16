from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .engine import validate_document
from .project_gate_export import (
    CE_REPOSITORY,
    canonical_bytes,
    load_json,
    sha256_bytes,
    validate_ce_stage_payload,
)

EXPORTER_ID = "ev4-ce-project-gate-exporter"
EXPORTER_VERSION = "1.0.0"
STAGE_BUNDLE_SCHEMA_ID = "stage-evidence-bundle.v1"
PRODUCER_EXPORT_SCHEMA_ID = "producer-gate-export.v1"
BUILDER_PACKAGE_SCHEMA_ID = "ev4-builder-executable-package@1.0.0"
HANDOFF_TARGET = "builder"
ZERO_SHA256 = "0" * 64
EXPECTED_PROJECT_GATE_COMMIT = "ea19c22c32458068e167b267da8b819e9263cdf7"
EXPECTED_STAGE_BUNDLE_SHA256 = "fc1ec6d3f7aecbabaeb0a3455d9eb42788779d2fa1531e8c7b2cb3bde706a886"


@dataclass(frozen=True)
class ExportDiagnostic:
    code: str
    stage: str
    message: str
    path: str = "$"
    repair_owner: str = "ce"
    blocking: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "stage": self.stage,
            "message": self.message,
            "path": self.path,
            "repair_owner": self.repair_owner,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class GitProvenance:
    repository: str
    ref: str
    commit_sha: str
    dirty: bool
    dirty_paths: tuple[str, ...]


@dataclass(frozen=True)
class ExportResult:
    status: str
    output_path: str | None
    output_written: bool
    handoff_allowed: bool
    diagnostics: tuple[ExportDiagnostic, ...]
    summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "output_path": self.output_path,
            "output_written": self.output_written,
            "handoff_allowed": self.handoff_allowed,
            "handoff_prohibited": not self.handoff_allowed,
            "diagnostics": [item.as_dict() for item in self.diagnostics],
            **self.summary,
        }


class ExporterError(RuntimeError):
    def __init__(self, diagnostic: ExportDiagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_COMMAND_EXECUTION_FAILED",
                "subprocess_execution",
                f"Failed to execute command {' '.join(command)}: {exc}",
                repair_owner="repository_owner",
            )
        ) from exc


def _git(repo_root: Path, *args: str) -> str:
    result = _run(["git", *args], repo_root)
    if result.returncode != 0:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_GIT_COMMAND_FAILED",
                "git_provenance",
                result.stderr.strip() or f"git {' '.join(args)} failed.",
                repair_owner="repository_owner",
            )
        )
    return result.stdout.strip()


def _normalize_remote(remote: str) -> str | None:
    value = remote.strip()
    if value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:")
    elif value.startswith("ssh://git@github.com/"):
        value = value.removeprefix("ssh://git@github.com/")
    elif value.startswith("https://github.com/"):
        value = value.removeprefix("https://github.com/")
    elif value.startswith("http://github.com/"):
        value = value.removeprefix("http://github.com/")
    else:
        return None
    return value.removesuffix(".git").strip("/")


def _relative_if_inside(path: Path, root: Path) -> str | None:
    try:
        return path.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _artifact_ref(path: Path, repo_root: Path) -> str:
    return _relative_if_inside(path, repo_root) or str(path.resolve(strict=False))


def inspect_git_provenance(repo_root: Path, ignored_paths: Iterable[Path] = ()) -> GitProvenance:
    root = Path(_git(repo_root, "rev-parse", "--show-toplevel")).resolve()
    if root != repo_root.resolve():
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_REPOSITORY_ROOT_MISMATCH",
                "git_provenance",
                "Exporter must run from the expected repository root.",
                repair_owner="repository_owner",
            )
        )
    remote = _normalize_remote(_git(root, "remote", "get-url", "origin"))
    if remote != CE_REPOSITORY:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_REPOSITORY_IDENTITY_INVALID",
                "git_provenance",
                f"Expected origin {CE_REPOSITORY!r}, observed {remote!r}.",
                repair_owner="repository_owner",
            )
        )
    ref_result = _run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], root)
    if ref_result.returncode != 0 or not ref_result.stdout.strip():
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_DETACHED_HEAD_FORBIDDEN",
                "git_provenance",
                "A named branch is required for reliable producer provenance.",
                repair_owner="repository_owner",
            )
        )
    commit_sha = _git(root, "rev-parse", "HEAD")
    if len(commit_sha) != 40 or any(ch not in "0123456789abcdef" for ch in commit_sha):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_COMMIT_SHA_INVALID",
                "git_provenance",
                "Git HEAD is not a valid 40-character commit SHA.",
                repair_owner="repository_owner",
            )
        )
    ignored = {
        rel
        for item in ignored_paths
        if (rel := _relative_if_inside(item, root)) is not None
    }
    dirty_paths: list[str] = []
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    for line in status.splitlines():
        if not line:
            continue
        raw_path = line[3:]
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1]
        raw_path = raw_path.strip().strip('"')
        if raw_path not in ignored:
            dirty_paths.append(raw_path)
    return GitProvenance(
        repository=CE_REPOSITORY,
        ref=ref_result.stdout.strip(),
        commit_sha=commit_sha,
        dirty=bool(dirty_paths),
        dirty_paths=tuple(sorted(set(dirty_paths))),
    )


def _json_hash(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _hash_record(value: str, scope: str = "canonical_json") -> dict[str, str]:
    return {"algorithm": "sha256", "value": value, "scope": scope}


def _load_object(path: Path, stage: str) -> dict[str, Any]:
    try:
        return load_json(path)
    except FileNotFoundError as exc:
        raise ExporterError(
            ExportDiagnostic("CE_EXPORT_INPUT_MISSING", stage, f"Input file does not exist: {path}", str(path))
        ) from exc
    except (json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        raise ExporterError(
            ExportDiagnostic("CE_EXPORT_INPUT_INVALID_JSON", stage, str(exc), str(path))
        ) from exc


def run_official_intake_validation(
    repo_root: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
) -> dict[str, Any]:
    script = repo_root / "scripts/validate-ce-architect-stage-intake.py"
    command = [
        sys.executable,
        str(script),
        "--repo-root",
        str(repo_root),
        "--file",
        str(source_intake_path),
        "--source-bundle",
        str(source_bundle_path),
        "--format",
        "json",
    ]
    result = _run(command, repo_root)
    try:
        report = json.loads(result.stdout)
        if not isinstance(report, dict):
            raise TypeError("Expected a JSON object from the official intake validator.")
    except (json.JSONDecodeError, TypeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INTAKE_VALIDATOR_OUTPUT_INVALID",
                "source_intake_validation",
                result.stderr.strip()
                or f"Official intake validator did not return a valid JSON object: {exc}",
                repair_owner="ce",
            )
        ) from exc
    if report.get("status") == "invalid" or result.returncode == 1:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_INVALID",
                "source_intake_validation",
                "Official CE Architect-stage intake validation failed.",
                details_path(report),
                repair_owner="architect_or_project_gate",
            )
        )
    if report.get("status") not in {"valid", "insufficient_evidence"}:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_STATUS_UNKNOWN",
                "source_intake_validation",
                f"Unexpected intake validator status: {report.get('status')!r}.",
                repair_owner="ce",
            )
        )
    return report


def details_path(report: dict[str, Any]) -> str:
    diagnostics = report.get("diagnostics")
    if isinstance(diagnostics, list) and diagnostics and isinstance(diagnostics[0], dict):
        return str(diagnostics[0].get("path") or "$")
    return "$"


def verify_source_intake_binding(
    payload: dict[str, Any],
    intake: dict[str, Any],
    source_intake_path: Path,
) -> dict[str, str]:
    source = payload.get("source_architect_intake")
    if not isinstance(source, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_REFERENCE_MISSING",
                "source_binding",
                "CE Stage Payload must declare source_architect_intake.",
                "$.source_architect_intake",
            )
        )
    if source.get("schema_id") != intake.get("schema_id") or source.get("schema_version") != intake.get("schema_version"):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_SCHEMA_MISMATCH",
                "source_binding",
                "Payload source intake identity does not match the supplied intake.",
                "$.source_architect_intake",
                repair_owner="ce",
            )
        )
    declared = source.get("artifact_hash")
    if not isinstance(declared, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_HASH_MISSING",
                "source_binding",
                "Payload must declare source Architect intake hash.",
                "$.source_architect_intake.artifact_hash",
            )
        )
    scope = declared.get("scope")
    if scope == "canonical_json":
        observed = _json_hash(intake)
    elif scope in {"file_bytes", "external_artifact"}:
        observed = hashlib.sha256(source_intake_path.read_bytes()).hexdigest()
    else:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_HASH_SCOPE_UNSUPPORTED",
                "source_binding",
                f"Unsupported source intake hash scope: {scope!r}.",
                "$.source_architect_intake.artifact_hash.scope",
            )
        )
    if declared.get("value") != observed:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SOURCE_INTAKE_HASH_MISMATCH",
                "source_binding",
                "Declared source intake hash does not match supplied source bytes.",
                "$.source_architect_intake.artifact_hash.value",
                repair_owner="ce",
            )
        )
    return {"algorithm": "sha256", "value": observed, "scope": str(scope)}


def validate_payload_and_ce_semantics(repo_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    diagnostics = validate_ce_stage_payload(repo_root, payload)
    if diagnostics:
        first = diagnostics[0]
        raise ExporterError(
            ExportDiagnostic(first.code, "ce_payload_validation", first.message, first.path)
        )
    result = validate_document(payload, repo_root=repo_root, mode="full")
    if not result.get("passed"):
        first_error = (result.get("schema_errors") or [None])[0]
        first_violation = (result.get("violations") or [None])[0]
        if first_error:
            message = str(first_error)
            path = message.split(":", 1)[0]
            code = "CE_EXPORT_CE_SCHEMA_VALIDATION_FAILED"
        elif isinstance(first_violation, dict):
            message = str(first_violation.get("message") or "Official CE semantic validation failed.")
            path = str(first_violation.get("location") or "$")
            code = str(first_violation.get("rule_id") or "CE_EXPORT_CE_SEMANTIC_VALIDATION_FAILED")
        else:
            message, path, code = "Official CE semantic validation failed.", "$", "CE_EXPORT_CE_SEMANTIC_VALIDATION_FAILED"
        raise ExporterError(ExportDiagnostic(code, "ce_semantic_validation", message, path))
    return result


def validate_identity_preservation(payload: dict[str, Any], intake: dict[str, Any]) -> None:
    payload_identity = payload.get("architecture_identity") if isinstance(payload.get("architecture_identity"), dict) else {}
    intake_identity = intake.get("selected_architecture") if isinstance(intake.get("selected_architecture"), dict) else {}
    payload_classes = payload_identity.get("approved_class_names")
    intake_intent = intake.get("architect_intent_preserved") if isinstance(intake.get("architect_intent_preserved"), dict) else {}
    class_intent = intake_intent.get("class_intent") if isinstance(intake_intent.get("class_intent"), dict) else {}
    intake_classes = class_intent.get("approved_class_names")
    if payload_identity.get("selected_candidate_id") != intake_identity.get("selected_candidate_id"):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_SELECTED_CANDIDATE_MISMATCH",
                "identity_lock_validation",
                "CE payload selected_candidate_id differs from accepted Architect intake.",
                "$.architecture_identity.selected_candidate_id",
            )
        )
    if payload_classes != intake_classes:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_APPROVED_CLASSES_MISMATCH",
                "identity_lock_validation",
                "CE payload approved_class_names differ from accepted Architect intake.",
                "$.architecture_identity.approved_class_names",
            )
        )


def validate_builder_package(payload: dict[str, Any]) -> str | None:
    emitted = payload.get("builder_package_emitted") is True
    package = payload.get("builder_executable_package")
    review = payload.get("constructability_review") if isinstance(payload.get("constructability_review"), dict) else {}
    if not emitted:
        return None
    if not isinstance(package, dict):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_BUILDER_PACKAGE_MISSING",
                "builder_package_validation",
                "builder_package_emitted=true requires a Builder Executable Package.",
                "$.builder_executable_package",
            )
        )
    if package.get("schema") != BUILDER_PACKAGE_SCHEMA_ID:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_BUILDER_PACKAGE_SCHEMA_INVALID",
                "builder_package_validation",
                f"Builder package schema must be {BUILDER_PACKAGE_SCHEMA_ID}.",
                "$.builder_executable_package.schema",
            )
        )
    if review.get("constructability_status") not in {"executable_ready", "executable_with_logged_assumption"}:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_BUILDER_PACKAGE_NOT_AUTHORIZED",
                "builder_package_validation",
                "Builder package cannot be emitted for a non-executable constructability result.",
                "$.constructability_review.constructability_status",
            )
        )
    if package.get("builder_package_status") != "executable_ready" or package.get("builder_decisions_required") != 0 or package.get("blocking_dependencies") != []:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_BUILDER_PACKAGE_NOT_ELIGIBLE",
                "builder_package_validation",
                "Builder package has unresolved decisions, blockers, or a non-ready status.",
                "$.builder_executable_package",
            )
        )
    return _json_hash(package)
