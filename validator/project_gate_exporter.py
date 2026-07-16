from __future__ import annotations

import argparse
import json
from pathlib import Path

from .project_gate_exporter_core import (
    EXPECTED_STAGE_BUNDLE_SHA256,
    ExportDiagnostic,
    ExportResult,
    ExporterError,
    inspect_git_provenance,
)
from .project_gate_exporter_validation import (
    validate_stage_bundle_lock,
    validate_stage_bundle_schema,
    verify_export_identity,
)
from .project_gate_exporter_orchestration import (
    _atomic_write,
    _safe_output_path,
    build_export,
)
from .project_gate_export import canonical_bytes, validate_producer_gate_export
from .project_gate_exporter_core import _load_object


def export_file(
    *,
    repo_root: Path,
    payload_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> ExportResult:
    root = repo_root.resolve()
    try:
        safe_output = _safe_output_path(root, output_path, overwrite)
        observed_provenance = inspect_git_provenance(
            root,
            ignored_paths=(payload_path, source_intake_path, source_bundle_path, safe_output),
        )
        export, summary, diagnostics = build_export(
            repo_root=root,
            payload_path=payload_path,
            source_intake_path=source_intake_path,
            source_bundle_path=source_bundle_path,
            output_path=safe_output,
            provenance=observed_provenance,
        )
        data = canonical_bytes(export) + b"\n"
        _atomic_write(safe_output, data)
        try:
            reread = _load_object(safe_output, "post_write_validation")
            if canonical_bytes(reread) != canonical_bytes(export):
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_POST_WRITE_MISMATCH",
                        "post_write_validation",
                        "Re-read output differs from the validated in-memory artifact.",
                        str(safe_output),
                    )
                )
            validate_stage_bundle_schema(root, reread["final_stage_bundle"])
            post_diagnostics = validate_producer_gate_export(root, reread)
            if post_diagnostics or not verify_export_identity(reread):
                first = post_diagnostics[0] if post_diagnostics else None
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
        except Exception:
            try:
                safe_output.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_POST_WRITE_CLEANUP_FAILED",
                        "post_write_validation",
                        f"Invalid output could not be removed: {cleanup_exc}",
                        str(safe_output),
                        "repository_owner",
                    )
                ) from cleanup_exc
            raise
        return ExportResult(
            status="successful" if export["handoff"]["allowed"] else export["handoff"]["status"],
            output_path=str(safe_output),
            output_written=True,
            handoff_allowed=bool(export["handoff"]["allowed"]),
            diagnostics=diagnostics,
            summary=summary,
        )
    except ExporterError as exc:
        return ExportResult(
            status="invalid",
            output_path=str(output_path),
            output_written=False,
            handoff_allowed=False,
            diagnostics=(exc.diagnostic,),
            summary={},
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce the official CE Gate-ready Project Gate export.")
    parser.add_argument("--payload", required=True, type=Path, help="Validated CE Stage Payload JSON.")
    parser.add_argument("--source-intake", required=True, type=Path, help="Accepted Architect-to-CE intake JSON.")
    parser.add_argument("--source-bundle", required=True, type=Path, help="Architect Stage Evidence Bundle used to verify intake source binding.")
    parser.add_argument("--output", type=Path, default=Path("ce-project-gate.json"), help="Output path inside the CE repository.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="CE repository root.")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace an existing output file.")
    args = parser.parse_args(argv)
    result = export_file(
        repo_root=args.repo_root,
        payload_path=args.payload.resolve(),
        source_intake_path=args.source_intake.resolve(),
        source_bundle_path=args.source_bundle.resolve(),
        output_path=args.output,
        overwrite=args.overwrite,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    if result.status == "invalid":
        return 1
    return 0 if result.handoff_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
