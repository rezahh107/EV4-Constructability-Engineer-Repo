from __future__ import annotations

from typing import Any

from . import _project_gate_exporter_build_impl as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)


def _handoff_diagnostics(
    payload: dict[str, Any],
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    provenance: GitProvenance | None = None,
) -> list[ExportDiagnostic]:
    """Apply dirty-worktree blocking only to the historical non-authorizing Payload path."""
    diagnostics = list(_impl._handoff_diagnostics(payload, intake, source_bundle))
    verified_runtime = payload.get("schema_id") == "ev4-ce-stage-payload@1.1.0"
    if provenance is not None and provenance.dirty and not verified_runtime:
        diagnostics.insert(
            0,
            ExportDiagnostic(
                "CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF",
                "git_provenance",
                "Historical raw-Payload preview records a dirty producer checkout; "
                "the verified runtime treats dirty state as metadata only.",
                "$.producer.commit_sha",
                "repository_owner",
            ),
        )
    return diagnostics


globals()["_handoff_diagnostics"] = _handoff_diagnostics
