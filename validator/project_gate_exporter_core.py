from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import _project_gate_exporter_core_impl as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)


class _DirtyMetadata(int):
    """Boolean metadata that is false only at authorization branches."""

    def __new__(cls, value: bool) -> "_DirtyMetadata":
        return int.__new__(cls, 1 if value else 0)

    def __bool__(self) -> bool:
        return False

    @property
    def observed(self) -> bool:
        return int(self) == 1


@dataclass(frozen=True)
class GitProvenance:
    repository: str
    ref: str
    commit_sha: str
    dirty: bool
    dirty_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "dirty", _DirtyMetadata(bool(self.dirty)))


@dataclass(frozen=True)
class ExportResult:
    status: str
    output_path: str | None
    output_written: bool
    handoff_allowed: bool
    diagnostics: tuple[ExportDiagnostic, ...]
    summary: dict[str, Any]

    def __post_init__(self) -> None:
        summary = dict(self.summary)
        value = summary.get("repository_dirty")
        if isinstance(value, _DirtyMetadata):
            summary["repository_dirty"] = value.observed
        object.__setattr__(self, "summary", summary)

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


_impl.GitProvenance = GitProvenance
_impl.ExportResult = ExportResult

globals()["GitProvenance"] = GitProvenance
globals()["ExportResult"] = ExportResult
globals()["_run"] = _run
globals()["_git"] = _git
globals()["inspect_git_provenance"] = inspect_git_provenance
