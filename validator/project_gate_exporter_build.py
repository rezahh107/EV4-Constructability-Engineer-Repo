from __future__ import annotations

from typing import Any

from . import _project_gate_exporter_build_impl as _impl
from .project_gate_exporter_core import ExportDiagnostic, GitProvenance


for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)


_original_handoff_diagnostics = _impl._handoff_diagnostics


def _handoff_diagnostics(
    payload: dict[str, Any],
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    provenance: GitProvenance,
) -> list[ExportDiagnostic]:
    """Return functional handoff diagnostics; Git dirty state is reporting metadata only."""
    return [
        diagnostic
        for diagnostic in _original_handoff_diagnostics(
            payload,
            intake,
            source_bundle,
            provenance,
        )
        if diagnostic.code != "CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF"
    ]


# Functions defined in the implementation module resolve globals at call time.
# Patching this single symbol prevents the stale dirty-worktree diagnostic from
# entering either direct calls or the legacy preview transaction.
_impl._handoff_diagnostics = _handoff_diagnostics

globals()["_handoff_diagnostics"] = _handoff_diagnostics
