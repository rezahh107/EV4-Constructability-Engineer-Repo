# CE Project Gate Exporter

Status: `implemented_in_ce_pending_project_gate_integration`

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
JSON parsing
→ official CE Architect-intake validation
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
```

Invalid semantic input or a source-binding mismatch produces no output.

A valid but blocked, insufficient-evidence, synthetic, or dirty-checkout run may produce a diagnostic Gate-ready artifact, but `handoff.allowed` remains `false`.

## Provenance and determinism

The exporter derives repository identity, named Git ref, and exact `HEAD` from the live checkout. An unknown repository, wrong `origin`, detached `HEAD`, or missing Git metadata fails closed.

The exporter reuses repository canonical JSON rules: UTF-8, sorted keys, compact separators, and rejection of `NaN`/`Infinity`. Content hashes exclude the final newline. The written file is canonical JSON followed by one newline.

`run_id` remains part of export identity, so independent CE executions are not collapsed merely because their semantic payloads match.

## Success output

The command prints JSON containing, when applicable:

```text
status
output_path
output_written
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
1  invalid input, contract, provenance, path, or post-write validation; no output
2  valid diagnostic export written with handoff blocked or insufficient_evidence
```

## Boundaries

CE does not:

- generate a final Builder Context Package;
- reproduce the Project Gate CE→Builder adapter;
- issue transition receipts;
- claim Builder acceptance or runtime execution;
- claim Responsive completion or production readiness;
- silently repair invalid CE facts or fabricate missing evidence.
