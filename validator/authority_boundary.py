from __future__ import annotations

from pathlib import Path
from typing import Any

from .project_gate_exporter_core import ExportDiagnostic, ExporterError
from .verified_project_gate_exporter import (
    reject_legacy_payload_export,
    secure_build_export,
)

_INSTALLED = False


def _reject_legacy_orchestration_build(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    raise ExporterError(
        ExportDiagnostic(
            "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN",
            "legacy_preview_boundary",
            "Raw CE Stage Payload mappings and paths cannot enter the official export transaction.",
            "$.payload_path",
        )
    )


def install_authority_boundary() -> None:
    """Replace every former raw-payload authorization entrypoint with the sealed boundary."""
    global _INSTALLED
    if _INSTALLED:
        return

    from . import ce_validation_transaction as transaction
    from . import project_gate_exporter as exporter
    from . import project_gate_exporter_orchestration as legacy_orchestration

    transaction.secure_build_export = secure_build_export  # type: ignore[assignment]
    exporter.build_export = secure_build_export  # type: ignore[assignment]
    exporter.export_file = reject_legacy_payload_export  # type: ignore[assignment]
    legacy_orchestration.build_export = _reject_legacy_orchestration_build  # type: ignore[assignment]
    _INSTALLED = True


def legacy_payload_authorization_is_closed() -> bool:
    from . import ce_validation_transaction as transaction
    from . import project_gate_exporter as exporter
    from . import project_gate_exporter_orchestration as legacy_orchestration

    return (
        transaction.secure_build_export is secure_build_export
        and exporter.build_export is secure_build_export
        and exporter.export_file is reject_legacy_payload_export
        and legacy_orchestration.build_export is _reject_legacy_orchestration_build
    )


def reject_raw_payload_path(path: Path) -> None:
    raise ExporterError(
        ExportDiagnostic(
            "CE_EXPORT_VERIFIED_PAYLOAD_CAPABILITY_REQUIRED",
            "verified_payload_boundary",
            f"Raw Payload path is non-authoritative: {path}",
            "$.verified_payload",
        )
    )
