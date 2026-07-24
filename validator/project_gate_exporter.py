from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ce_validation_transaction import (
    safe_output_path as _safe_output_path,
    secure_build_export as build_export,
    validate_transaction_artifact,
)
from .project_gate_exporter_core import (
    EXPECTED_STAGE_BUNDLE_SHA256,
    ExportDiagnostic,
    ExportResult,
    ExporterError,
    GitProvenance as GitProvenance,
    inspect_git_provenance,
)
from .project_gate_exporter_validation import (
    validate_stage_bundle_lock,
    validate_stage_bundle_schema,
    verify_export_identity,
)
from .project_gate_exporter_orchestration import _atomic_write
from .project_gate_export import canonical_bytes, validate_producer_gate_export
from .project_gate_exporter_core import _load_object


def _post_write_failure_diagnostic(exc: Exception, output_path: Path) -> ExportDiagnostic:
    if isinstance(exc, ExporterError):
        return exc.diagnostic
    return ExportDiagnostic(
        "CE_EXPORT_POST_WRITE_VALIDATION_FAILED",
        "post_write_validation",
        f"Post-write validation failed: {type(exc).__name__}: {exc}",
        str(output_path),
        "repository_owner",
    )


def _resolve_repository_root(repo_root: Path) -> Path:
    try:
        return repo_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_REPOSITORY_PATH_INSPECTION_FAILED",
                "repository_path_inspection",
                f"Failed to inspect the CE repository path safely: {exc}",
                str(repo_root),
                "repository_owner",
            )
        ) from exc


def _resolve_input_path(path: Path, input_name: str) -> Path:
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_INPUT_PATH_INSPECTION_FAILED",
                "input_path_inspection",
                f"Failed to inspect the {input_name} path safely: {exc}",
                str(path),
                "repository_owner",
            )
        ) from exc


def _inspect_git_provenance_safely(
    repo_root: Path,
    ignored_paths: tuple[Path, ...],
) -> GitProvenance:
    try:
        return inspect_git_provenance(repo_root, ignored_paths=ignored_paths)
    except ExporterError:
        raise
    except (OSError, RuntimeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_REPOSITORY_PATH_INSPECTION_FAILED",
                "repository_path_inspection",
                f"Failed to inspect repository paths while deriving Git provenance: {exc}",
                str(repo_root),
                "repository_owner",
            )
        ) from exc


def _read_prior_owned_output(path: Path) -> bytes | None:
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_EXISTING_OUTPUT_READ_FAILED",
                "output_safety",
                f"Failed to capture the existing owned output before replacement: {exc}",
                str(path),
                "repository_owner",
            )
        ) from exc


def _prior_state_summary(
    prior_output_bytes: bytes | None,
    *,
    replaced: bool,
    restored: bool,
) -> dict[str, bool]:
    existed = prior_output_bytes is not None
    return {
        "prior_artifact_existed": existed,
        "prior_artifact_replaced": existed and replaced,
        "prior_artifact_restored": existed and restored,
        "prior_artifact_preserved": existed and restored,
    }


def _inspect_failed_output_state(
    safe_output: Path,
    prior_output_bytes: bytes | None,
) -> tuple[bool, str, bool]:
    """Return output_written, artifact_state, and whether the prior bytes are restored."""
    try:
        if not safe_output.exists():
            return False, "invalid_artifact_removed_cleanup_reported_failed", False
        observed = safe_output.read_bytes()
    except OSError:
        return True, "invalid_artifact_persistence_unconfirmed", False

    prior_restored = prior_output_bytes is not None and observed == prior_output_bytes
    if prior_restored:
        return False, "prior_valid_artifact_restored_cleanup_reported_failed", True
    return True, "invalid_artifact_persisted", False


def _restore_or_remove_failed_output(
    safe_output: Path,
    prior_output_bytes: bytes | None,
    original_diagnostic: ExportDiagnostic,
) -> ExportResult:
    try:
        if prior_output_bytes is None:
            safe_output.unlink(missing_ok=True)
            return ExportResult(
                status="invalid",
                output_path=str(safe_output),
                output_written=False,
                handoff_allowed=False,
                diagnostics=(original_diagnostic,),
                summary={
                    "output_valid": False,
                    "output_cleanup_failed": False,
                    "artifact_state": "invalid_artifact_removed",
                    "artifact_must_not_be_consumed": True,
                    "artifact_integrity_status": "invalid",
                    "semantic_validation_status": "invalid",
                    "authorization_valid": False,
                    **_prior_state_summary(
                        prior_output_bytes,
                        replaced=False,
                        restored=False,
                    ),
                },
            )

        _atomic_write(safe_output, prior_output_bytes)
        if safe_output.read_bytes() != prior_output_bytes:
            raise OSError("restored bytes differ from the captured prior output")
        return ExportResult(
            status="invalid",
            output_path=str(safe_output),
            output_written=False,
            handoff_allowed=False,
            diagnostics=(original_diagnostic,),
            summary={
                "output_valid": False,
                "output_cleanup_failed": False,
                "artifact_state": "prior_valid_artifact_restored",
                "artifact_must_not_be_consumed": True,
                "artifact_integrity_status": "invalid_new_candidate",
                "semantic_validation_status": "invalid",
                "authorization_valid": False,
                **_prior_state_summary(
                    prior_output_bytes,
                    replaced=True,
                    restored=True,
                ),
            },
        )
    except (ExporterError, OSError, RuntimeError) as cleanup_exc:
        cleanup_diagnostic = ExportDiagnostic(
            "CE_EXPORT_POST_WRITE_CLEANUP_FAILED",
            "post_write_validation",
            "Invalid output could not be removed or the prior owned output could not "
            f"be restored; the target must not be consumed: {cleanup_exc}",
            str(safe_output),
            "repository_owner",
        )
        output_written, artifact_state, prior_restored = _inspect_failed_output_state(
            safe_output,
            prior_output_bytes,
        )
        return ExportResult(
            status="invalid",
            output_path=str(safe_output),
            output_written=output_written,
            handoff_allowed=False,
            diagnostics=(original_diagnostic, cleanup_diagnostic),
            summary={
                "output_valid": False,
                "output_cleanup_failed": True,
                "artifact_state": artifact_state,
                "artifact_must_not_be_consumed": True,
                "artifact_integrity_status": (
                    "prior_valid_artifact_observed"
                    if prior_restored
                    else "invalid_or_unconfirmed"
                ),
                "semantic_validation_status": "invalid",
                "authorization_valid": False,
                **_prior_state_summary(
                    prior_output_bytes,
                    replaced=prior_output_bytes is not None,
                    restored=prior_restored,
                ),
            },
        )


def export_file(
    *,
    repo_root: Path,
    payload_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    intermediate_inputs_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> ExportResult:
    try:
        root = _resolve_repository_root(repo_root)
        resolved_payload = _resolve_input_path(payload_path, "CE Stage Payload")
        resolved_source_intake = _resolve_input_path(
            source_intake_path,
            "Architect-to-CE source intake",
        )
        resolved_source_bundle = _resolve_input_path(
            source_bundle_path,
            "Architect source bundle",
        )
        resolved_intermediate_inputs = _resolve_input_path(
            intermediate_inputs_path,
            "CE intermediate validation inputs",
        )
        safe_output = _safe_output_path(
            root,
            output_path,
            overwrite,
            protected_inputs=(
                resolved_payload,
                resolved_source_intake,
                resolved_source_bundle,
                resolved_intermediate_inputs,
            ),
        )
        prior_output_bytes = _read_prior_owned_output(safe_output)
        observed_provenance = _inspect_git_provenance_safely(
            root,
            (
                resolved_payload,
                resolved_source_intake,
                resolved_source_bundle,
                resolved_intermediate_inputs,
                safe_output,
            ),
        )
        export, summary, diagnostics = build_export(
            repo_root=root,
            payload_path=resolved_payload,
            source_intake_path=resolved_source_intake,
            source_bundle_path=resolved_source_bundle,
            intermediate_inputs_path=resolved_intermediate_inputs,
            output_path=safe_output,
            provenance=observed_provenance,
        )
        data = canonical_bytes(export) + b"\n"
        _atomic_write(safe_output, data)
        try:
            reread_bytes = safe_output.read_bytes()
            if reread_bytes != data:
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_POST_WRITE_BYTE_MISMATCH",
                        "post_write_validation",
                        "Re-read output bytes differ from the validated publication bytes.",
                        str(safe_output),
                    )
                )
            reread = _load_object(safe_output, "post_write_validation")
            validate_stage_bundle_schema(root, reread["final_stage_bundle"])
            post_diagnostics = validate_producer_gate_export(root, reread)
            transaction_diagnostics = validate_transaction_artifact(root, reread)
            if post_diagnostics or transaction_diagnostics or not verify_export_identity(reread):
                first = (
                    post_diagnostics[0]
                    if post_diagnostics
                    else transaction_diagnostics[0]
                    if transaction_diagnostics
                    else None
                )
                raise ExporterError(
                    ExportDiagnostic(
                        first.code if first else "CE_EXPORT_POST_WRITE_IDENTITY_INVALID",
                        "post_write_validation",
                        first.message
                        if first
                        else "Post-write export identity validation failed.",
                        first.path if first else str(safe_output),
                    )
                )
        except Exception as validation_exc:
            original_diagnostic = _post_write_failure_diagnostic(
                validation_exc,
                safe_output,
            )
            return _restore_or_remove_failed_output(
                safe_output,
                prior_output_bytes,
                original_diagnostic,
            )
        prior_existed = prior_output_bytes is not None
        return ExportResult(
            status="successful" if export["handoff"]["allowed"] else export["handoff"]["status"],
            output_path=str(safe_output),
            output_written=True,
            handoff_allowed=bool(export["handoff"]["allowed"]),
            diagnostics=diagnostics,
            summary={
                **summary,
                "output_valid": True,
                "output_cleanup_failed": False,
                "artifact_state": (
                    "valid_authorized_export"
                    if export["handoff"]["allowed"]
                    else "valid_blocked_export"
                ),
                "artifact_must_not_be_consumed": False,
                **_prior_state_summary(
                    prior_output_bytes,
                    replaced=prior_existed,
                    restored=False,
                ),
            },
        )
    except ExporterError as exc:
        return ExportResult(
            status="invalid",
            output_path=str(output_path),
            output_written=False,
            handoff_allowed=False,
            diagnostics=(exc.diagnostic,),
            summary={
                "output_valid": False,
                "output_cleanup_failed": False,
                "artifact_state": "not_written_by_this_run",
                "artifact_must_not_be_consumed": True,
                "artifact_integrity_status": "invalid",
                "semantic_validation_status": "invalid_or_not_run",
                "authorization_valid": False,
                "prior_artifact_existed": False,
                "prior_artifact_replaced": False,
                "prior_artifact_restored": False,
                "prior_artifact_preserved": False,
            },
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Produce the official CE Gate-ready Project Gate export."
    )
    parser.add_argument(
        "--payload",
        required=True,
        type=Path,
        help="Validated CE Stage Payload JSON.",
    )
    parser.add_argument(
        "--source-intake",
        required=True,
        type=Path,
        help="Accepted Architect-to-CE intake JSON.",
    )
    parser.add_argument(
        "--source-bundle",
        required=True,
        type=Path,
        help="Architect Stage Evidence Bundle used to verify intake source binding.",
    )
    parser.add_argument(
        "--intermediate-inputs",
        required=True,
        type=Path,
        help=(
            "Independent CE intermediate-input artifact containing the current "
            "constructability review, Implementation Strategy Map, and Builder "
            "Executable Package."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ce-project-gate.json"),
        help="Output path inside the CE repository.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="CE repository root.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace an existing CE-owned output file.",
    )
    args = parser.parse_args(argv)
    result = export_file(
        repo_root=args.repo_root,
        payload_path=args.payload,
        source_intake_path=args.source_intake,
        source_bundle_path=args.source_bundle,
        intermediate_inputs_path=args.intermediate_inputs,
        output_path=args.output,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            result.as_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    if result.status == "invalid":
        return 1
    return 0 if result.handoff_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
