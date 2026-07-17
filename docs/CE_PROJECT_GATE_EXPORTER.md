# CE Project Gate Exporter

Status: `implemented_in_ce_pending_project_gate_integration_and_fresh_independent_rereview`

## Purpose

This repository owns the operator-facing CE export command for the manual JSON handoff:

```text
accepted Architect→CE intake
→ completed CE Stage Payload
→ CE-owned Gate-ready export
→ EV4 Project Gate
```

The command creates one complete `ce-project-gate.json`. It does not create a Project Gate receipt, a final Builder Context Package, Builder runtime authorization, or a downstream execution claim.

## Official command

Install the repository in editable mode, then run:

```bash
python -m pip install -e '.[dev]'

ev4-ce-project-gate-export \
  --payload path/to/ce-stage-payload.json \
  --source-intake path/to/ce-input.json \
  --source-bundle path/to/architect-stage-bundle.json \
  --output ce-project-gate.json
```

Equivalent repository-native script:

```bash
python scripts/export-ce-project-gate.py \
  --payload path/to/ce-stage-payload.json \
  --source-intake path/to/ce-input.json \
  --source-bundle path/to/architect-stage-bundle.json \
  --output ce-project-gate.json
```

`--source-bundle` must point to the actual source bundle object whose canonical JSON hash is declared by `project_gate_transition.source_bundle_hash`. A metadata wrapper around the bundle is not accepted as the source bundle itself.

The command refuses to replace an existing output unless `--overwrite` is supplied explicitly.

## Reused active contracts

```text
ev4-ce-architect-stage-intake@1.1.0
ev4-ce-stage-payload@1.0.0
ev4-builder-executable-package@1.0.0
stage-evidence-bundle.v1@1.0.0
producer-gate-export.v1@1.0.0
```

The common Project Gate contracts remain owned by `rezahh107/EV4-Project-Gate`. CE vendors exact pinned bytes only; the local copies are non-authoritative.

## Validation order

```text
live repository, origin, branch, HEAD, and dirty-state inspection
→ source-intake byte snapshot and JSON parsing
→ official CE Architect-intake validation
→ source-intake byte-stability verification
→ source-bundle identity and hash verification
→ CE Stage Payload schema validation
→ official CE constructability semantic validation
→ accepted architecture identity preservation
→ Builder Executable Package validation when emitted
→ Stage Evidence Bundle construction and validation
→ Producer Gate Export construction and validation
→ deterministic identity self-check
→ atomic write
→ post-write re-read and validation
→ invalid-output removal or explicit persistence reporting
```

Invalid semantic input, source-binding mismatch, source-intake read failure, or source-intake mutation produces no output.

A valid but blocked, insufficient-evidence, synthetic, or dirty-checkout run may produce a diagnostic Gate-ready artifact, but `handoff.allowed` remains `false`.

## Provenance and determinism

The public/operator `export_file` path always derives repository identity, named Git ref, exact `HEAD`, and dirty state from the live checkout. It has no caller-supplied provenance parameter, environment override, or alternate operator bypass. An unknown repository, wrong `origin`, detached `HEAD`, missing Git metadata, or dirty checkout fails closed or blocks handoff according to the documented policy.

The source intake is parsed from one captured byte snapshot. After the official intake validator runs, the exporter reads the file again and requires exact byte equality with that snapshot. Read failures are returned as structured `CE_EXPORT_SOURCE_INTAKE_READ_FAILED` diagnostics; mutation is returned as `CE_EXPORT_SOURCE_INTAKE_CHANGED_DURING_EXPORT`. Neither condition writes an output artifact.

The exporter reuses repository canonical JSON rules: UTF-8, sorted keys, compact separators, and rejection of `NaN`/`Infinity`. Content hashes exclude the final newline. The written file is canonical JSON followed by one newline.

`run_id` remains part of export identity, so independent CE executions are not collapsed merely because their semantic payloads match.

## Post-write failure state

If post-write revalidation rejects the artifact, the exporter first attempts to remove it.

Successful cleanup is reported as:

```yaml
status: invalid
output_written: false
output_valid: false
output_cleanup_failed: false
artifact_state: invalid_artifact_removed
artifact_must_not_be_consumed: true
handoff_allowed: false
```

If cleanup fails, the invalid artifact is not treated as an intentional blocked export. The result preserves the original validation diagnostic, adds the blocking `CE_EXPORT_POST_WRITE_CLEANUP_FAILED` diagnostic, returns exit code `1`, and reports:

```yaml
status: invalid
output_written: true
output_valid: false
output_cleanup_failed: true
artifact_state: invalid_artifact_persisted
artifact_must_not_be_consumed: true
handoff_allowed: false
```

A cleanup-failed artifact may still contain pre-failure content and must not be consumed, dispatched, or interpreted as authorized handoff evidence.

## Result output

The command prints structured JSON containing, when applicable:

```text
status
output_path
output_written
output_valid
output_cleanup_failed
artifact_state
artifact_must_not_be_consumed
export_id
source_intake_hash
source_bundle_hash
ce_payload_hash
builder_executable_package_hash
bundle_hash
export_hash
producer_commit
producer_ref
handoff_target
handoff_allowed
```

## Exit codes

```text
0  valid export with allowed Builder handoff
1  invalid input, contract, provenance, path, source read, mutation, or post-write validation; inspect artifact_state before touching the output path
2  valid diagnostic export written with handoff blocked or insufficient_evidence
```

Expected operational failures produce structured JSON and do not emit a traceback.

## Boundaries

CE does not:

- generate a final Builder Context Package;
- reproduce the Project Gate CE→Builder adapter;
- issue transition receipts;
- claim Builder acceptance or runtime execution;
- claim Responsive completion or production readiness;
- silently repair invalid CE facts or fabricate missing evidence.

A fresh independent PR Inspector review is required after repairs; this document does not claim that prior findings are finally closed.
