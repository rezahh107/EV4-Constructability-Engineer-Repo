from __future__ import annotations
from contextlib import contextmanager
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator
from .legacy_payload_preview import apply_legacy_preview_boundary
from .project_gate_export import PIPELINE_ID, validate_producer_gate_export
from .project_gate_exporter_core import HANDOFF_TARGET, PRODUCER_EXPORT_SCHEMA_ID, ExportDiagnostic, ExporterError, GitProvenance, _json_hash, _load_object, _reject_non_json_constant, assert_source_intake_unchanged, load_source_intake_snapshot, run_official_intake_validation, validate_builder_package, validate_identity_preservation, validate_payload_and_ce_semantics, verify_source_intake_binding
from .project_gate_exporter_build import _build_stage_bundle, _handoff_diagnostics, _stage_manifest
from .project_gate_exporter_validation import _export_identity_hash, validate_stage_bundle_schema, verify_export_identity

def _safe_output_path(repo_root: Path, output_path: Path, overwrite: bool) -> Path:
    try:
        root = repo_root.resolve(strict=True)
        candidate = output_path if output_path.is_absolute() else root / output_path
        if candidate.is_symlink():
            raise ExporterError(ExportDiagnostic('CE_EXPORT_OUTPUT_SYMLINK_FORBIDDEN', 'output_safety', 'Refusing to write through a symbolic link.', str(candidate), 'repository_owner'))
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ExporterError(ExportDiagnostic('CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY', 'output_safety', 'Output path must remain inside the CE repository.', str(output_path), 'repository_owner')) from exc
        if resolved.is_dir():
            raise ExporterError(ExportDiagnostic('CE_EXPORT_OUTPUT_IS_DIRECTORY', 'output_safety', 'Output path cannot be a directory.', str(resolved), 'repository_owner'))
        if resolved.exists() and (not overwrite):
            raise ExporterError(ExportDiagnostic('CE_EXPORT_OUTPUT_EXISTS', 'output_safety', 'Output already exists; use --overwrite for an explicit replacement.', str(resolved), 'repository_owner'))
        return resolved
    except ExporterError:
        raise
    except (OSError, RuntimeError) as exc:
        raise ExporterError(ExportDiagnostic('CE_EXPORT_OUTPUT_PATH_INSPECTION_FAILED', 'output_safety', f'Failed to inspect the output path safely: {exc}', str(output_path), 'repository_owner')) from exc

def _atomic_write(path: Path, data: bytes) -> None:
    temp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            temp_name = None
        finally:
            if temp_name is not None and os.path.exists(temp_name):
                os.unlink(temp_name)
    except OSError as exc:
        raise ExporterError(ExportDiagnostic('CE_EXPORT_WRITE_FAILED', 'atomic_write', f'Failed to write output file atomically: {exc}', str(path), 'repository_owner')) from exc

def _read_source_bundle_bytes(source_bundle_path: Path) -> bytes:
    try:
        return source_bundle_path.read_bytes()
    except OSError as exc:
        raise ExporterError(ExportDiagnostic('CE_EXPORT_SOURCE_BUNDLE_READ_FAILED', 'source_binding', f'Failed to read source Architect bundle: {exc}', str(source_bundle_path), 'repository_owner')) from exc

def _load_source_bundle_snapshot(source_bundle_path: Path) -> tuple[dict[str, Any], bytes]:
    raw = _read_source_bundle_bytes(source_bundle_path)
    try:
        decoded = raw.decode('utf-8')
        source_bundle = json.loads(decoded, parse_constant=_reject_non_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ExporterError(ExportDiagnostic('CE_EXPORT_INPUT_INVALID_JSON', 'source_bundle_parse', str(exc), str(source_bundle_path))) from exc
    if not isinstance(source_bundle, dict):
        raise ExporterError(ExportDiagnostic('CE_EXPORT_INPUT_INVALID_JSON', 'source_bundle_parse', f'Expected JSON object in {source_bundle_path}', str(source_bundle_path)))
    return (source_bundle, raw)

def _assert_source_bundle_unchanged(source_bundle_path: Path, expected_bytes: bytes) -> None:
    observed_bytes = _read_source_bundle_bytes(source_bundle_path)
    if observed_bytes != expected_bytes:
        raise ExporterError(ExportDiagnostic('CE_EXPORT_SOURCE_BUNDLE_CHANGED_DURING_EXPORT', 'source_binding', 'Source Architect bundle changed between parsing and binding validation.', str(source_bundle_path), 'repository_owner'))

def _write_validation_snapshot(directory: Path, *, prefix: str, data: bytes) -> Path:
    fd: int | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=prefix, suffix='.snapshot.json', dir=directory)
        with os.fdopen(fd, 'wb') as handle:
            fd = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        return Path(name)
    except OSError as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        raise ExporterError(ExportDiagnostic('CE_EXPORT_VALIDATION_SNAPSHOT_PREPARATION_FAILED', 'validation_snapshot', f'Failed to prepare a private validator snapshot: {exc}', str(directory), 'repository_owner')) from exc

@contextmanager
def _private_validation_snapshots(source_intake_bytes: bytes, source_bundle_bytes: bytes) -> Iterator[tuple[Path, Path]]:
    directory: Path | None = None
    try:
        try:
            directory = Path(tempfile.mkdtemp(prefix='ev4-ce-export-validation-'))
        except OSError as exc:
            raise ExporterError(ExportDiagnostic('CE_EXPORT_VALIDATION_SNAPSHOT_PREPARATION_FAILED', 'validation_snapshot', f'Failed to create a private validator snapshot directory: {exc}', '$temporary_validation_snapshot', 'repository_owner')) from exc
        intake_snapshot = _write_validation_snapshot(directory, prefix='source-intake-', data=source_intake_bytes)
        bundle_snapshot = _write_validation_snapshot(directory, prefix='source-bundle-', data=source_bundle_bytes)
        yield (intake_snapshot, bundle_snapshot)
    finally:
        if directory is not None:
            try:
                shutil.rmtree(directory)
            except OSError as exc:
                raise ExporterError(ExportDiagnostic('CE_EXPORT_VALIDATION_SNAPSHOT_CLEANUP_FAILED', 'validation_snapshot', f'Failed to remove private validator snapshots: {exc}', str(directory), 'repository_owner')) from exc

def _build_legacy_export(*, repo_root: Path, payload_path: Path, source_intake_path: Path, source_bundle_path: Path, output_path: Path, provenance: GitProvenance) -> tuple[dict[str, Any], dict[str, Any], tuple[ExportDiagnostic, ...]]:
    payload = _load_object(payload_path, 'ce_payload_parse')
    intake, source_intake_bytes = load_source_intake_snapshot(source_intake_path)
    source_bundle, source_bundle_bytes = _load_source_bundle_snapshot(source_bundle_path)
    with _private_validation_snapshots(source_intake_bytes, source_bundle_bytes) as (validator_intake_path, validator_bundle_path):
        intake_report = run_official_intake_validation(repo_root, validator_intake_path, validator_bundle_path)
    assert_source_intake_unchanged(source_intake_path, source_intake_bytes)
    _assert_source_bundle_unchanged(source_bundle_path, source_bundle_bytes)
    source_hash = verify_source_intake_binding(payload, intake, source_intake_path, source_intake_bytes)
    validate_payload_and_ce_semantics(repo_root, payload)
    validate_identity_preservation(payload, intake)
    builder_package_hash = validate_builder_package(payload)
    handoff_diagnostics = _handoff_diagnostics(payload, intake, source_bundle, provenance)
    handoff_allowed = not handoff_diagnostics
    insufficiency_codes = {'CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE', 'CE_EXPORT_PAYLOAD_INSUFFICIENT_EVIDENCE', 'CE_EXPORT_UNRESOLVED_EVIDENCE'}
    handoff_status = 'successful' if handoff_allowed else 'insufficient_evidence' if any((item.code in insufficiency_codes for item in handoff_diagnostics)) else 'blocked'
    bundle, bundle_hash = _build_stage_bundle(payload, intake, source_bundle, provenance, payload_path, source_intake_path, repo_root)
    validate_stage_bundle_schema(repo_root, bundle)
    manifest = _stage_manifest(payload, source_intake_path, source_hash, output_path, repo_root)
    export: dict[str, Any] = {'schema_version': PRODUCER_EXPORT_SCHEMA_ID, 'export_id': '', 'producer': {'stage': 'ce', 'repository': provenance.repository, 'ref': provenance.ref, 'commit_sha': provenance.commit_sha}, 'pipeline_id': PIPELINE_ID, 'run_id': payload['payload_identity']['run_id'], 'stage_manifest': manifest, 'final_stage_bundle': bundle, 'handoff': {'target': HANDOFF_TARGET, 'status': handoff_status, 'allowed': handoff_allowed, 'failure_reasons': [item.as_dict() for item in handoff_diagnostics], 'blocking_diagnostics': [item.as_dict() for item in handoff_diagnostics], 'unresolved_evidence': list(payload.get('unresolved_evidence') or [])}, 'validation': {'schema_valid': True, 'semantic_valid': True, 'validator_id': 'ev4-producer-gate-export-validator', 'validator_version': '1.0.0', 'diagnostics': []}, 'acquisition_mode': {'mode': 'producer_emitted_gate_artifact', 'silent_fallback_allowed': False}}
    identity_hash = _export_identity_hash(export)
    export['export_id'] = f'ce-project-gate-export-{identity_hash}'
    export['stage_manifest'][-1]['output']['artifact_hash']['value'] = identity_hash
    diagnostics = validate_producer_gate_export(repo_root, export)
    if diagnostics:
        first = diagnostics[0]
        raise ExporterError(ExportDiagnostic(first.code, 'producer_export_validation', first.message, first.path))
    if not verify_export_identity(export):
        raise ExporterError(ExportDiagnostic('CE_EXPORT_IDENTITY_SELF_CHECK_FAILED', 'hash_self_verification', 'Export identity hash self-check failed.'))
    summary = {'export_id': export['export_id'], 'source_intake_hash': source_hash['value'], 'source_intake_hash_scope': source_hash['scope'], 'source_bundle_hash': _json_hash(source_bundle), 'ce_payload_hash': _json_hash(payload), 'builder_executable_package_hash': builder_package_hash, 'bundle_hash': bundle_hash, 'export_identity_hash': identity_hash, 'export_hash': _json_hash(export), 'producer_commit': provenance.commit_sha, 'producer_ref': provenance.ref, 'repository_dirty': provenance.dirty, 'dirty_paths': list(provenance.dirty_paths), 'handoff_target': HANDOFF_TARGET, 'intake_validation_status': intake_report['status'], 'artifact_integrity_status': 'valid', 'semantic_validation_status': 'valid', 'authorization_valid': handoff_allowed}
    return (export, summary, tuple(handoff_diagnostics))

def build_export(*, repo_root: Path, payload_path: Path, source_intake_path: Path, source_bundle_path: Path, output_path: Path, provenance: GitProvenance) -> tuple[dict[str, Any], dict[str, Any], tuple[ExportDiagnostic, ...]]:
    """Named legacy preview path. It can validate but can never authorize Builder handoff."""
    return apply_legacy_preview_boundary(*_build_legacy_export(repo_root=repo_root, payload_path=payload_path, source_intake_path=source_intake_path, source_bundle_path=source_bundle_path, output_path=output_path, provenance=provenance))
