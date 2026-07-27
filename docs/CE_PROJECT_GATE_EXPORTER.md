# CE Project Gate Exporter

Status: active verified exporter merged through `PR #45` and available on `main`.

## Purpose

This repository owns the CE-side producer command for the Project Gate handoff:

```text
verified Architect intake
+ verified Architect source bundle
+ CE Review Draft
→ canonical CE evaluation
→ verified CE Stage Payload
→ deterministic CE Stage Bundle and Producer Gate Export
→ EV4 Project Gate
```

The command creates one complete `ce-project-gate.json`. It does not create a Project Gate receipt, a final Builder Context Package, downstream runtime evidence, deployment evidence, or production-readiness evidence.

## Official entry point

The installed command is defined by `pyproject.toml`:

```text
ev4-ce-project-gate-export = validator.verified_project_gate_exporter:main
```

The public exporter identity remains `ev4-producer-gate-export-validator`; the public exporter version is `1.1.0`.

Install and run:

```bash
python -m pip install -e '.[dev]'

ev4-ce-project-gate-export \
  --review-draft path/to/ce-review-draft.json \
  --source-intake path/to/architect-ce-intake.json \
  --source-bundle path/to/architect-source-bundle.json \
  --output ce-project-gate.json
```

Equivalent module invocation:

```bash
python -m validator.verified_project_gate_exporter \
  --review-draft path/to/ce-review-draft.json \
  --source-intake path/to/architect-ce-intake.json \
  --source-bundle path/to/architect-source-bundle.json \
  --output ce-project-gate.json
```

Optional arguments:

```text
--repo-root <repository path>
--overwrite
```

All authoritative inputs are explicit. No sibling filename, directory adjacency, repository scan, `--intermediate-inputs`, or silent fallback participates in authority.

A relative `--output` remains rooted inside the CE repository. A caller-selected absolute `--output` may resolve outside the CE checkout and is published directly by the same official CE exporter. An existing output is replaced only when `--overwrite` is supplied and the existing artifact is recognized as CE-owned.

## Canonical runtime

The official command converges on the single canonical evaluator:

```text
validator.payload_fidelity.evaluate_ce_transaction
```

The flow is:

```text
CE Review Draft
→ mandatory review units and phase-aware claim derivation
→ closed Builder Action IR
→ claim-specific evaluation and runtime-obligation derivation
→ four internal deterministic results
→ validator.payload_assembler
→ verified ev4-ce-stage-payload@1.1.0
→ independent fidelity replay
→ verified Project Gate export
```

The four intermediate results are internal deterministic evaluation products. They are not operator-supplied Carrier files and do not create a parallel authority path.

## Active contracts

```text
ev4-ce-review-draft@1.0.0
ev4-ce-architect-stage-intake@1.1.0
ev4-ce-stage-payload@1.1.0
ev4-constructability-review@1.1.0
ev4-builder-executable-package@1.0.0
stage-evidence-bundle.v1@1.0.0
producer-gate-export.v1@1.0.0
```

The common Project Gate envelope contracts remain owned by `rezahh107/EV4-Project-Gate`. CE consumes the pinned local copies and verifies their exact expected bytes and hashes.

## Validation and publication order

```text
repository-root resolution
→ explicit Review Draft, intake, source-bundle, and output path handling
→ relative-output CE-root binding or absolute caller-path resolution
→ strict JSON read of every authoritative input
→ exact-byte snapshots
→ output/input alias rejection
→ prior CE-owned output capture when replacement is requested
→ Git provenance inspection for reporting
→ Architect intake and source-bundle identity/binding verification
→ canonical evaluate_ce_transaction execution
→ verified Payload Schema, semantic, authority, and fidelity validation
→ Builder-package eligibility validation when emitted
→ Stage Evidence Bundle construction and validation
→ Producer Gate Export construction and validation
→ deterministic export-identity self-check
→ authoritative input byte-stability checks
→ atomic write at the resolved output path
→ persisted-byte re-read
→ post-write Stage Bundle, Schema, semantic, transaction, and identity validation
→ retain valid output, or restore/remove on failure
```

Strict JSON behavior includes:

```yaml
duplicate_object_keys: rejected
invalid_utf8: rejected
non_json_constants: rejected
object_root_required: true
```

A missing, malformed, mismatched, mutated, or semantically invalid authoritative input produces a structured invalid result and no newly consumable artifact.

## Phase-aware Builder boundary

Pre-Builder static and capability claims must be satisfied before handoff.

A mandatory `post_builder_runtime` claim must carry a complete deterministic runtime obligation. A missing or incomplete obligation blocks Builder handoff. A complete obligation with `status: required` may permit Builder handoff, but keeps `final_project_gate: blocked` until an actual repository-owned downstream runner records an accepted pass or explicit non-applicability.

An obligation is not execution evidence. Caller-authored `observed`, `passed`, `execution_status`, `exit_code`, `captured_result`, or similar fields cannot create `VERIFIED_TOOL_EXECUTION`.

## Git provenance and dirty state

Repository identity, ref, commit, dirty state, and dirty paths are observed for reporting.

Paths outside the CE repository are excluded from CE-relative dirty-path comparison. An external output therefore does not become a CE dirty path merely because it is supplied to the exporter.

Dirty worktree state is not functional authority. It does not change:

```text
claim resolution
Payload fidelity
Builder readiness
handoff.allowed
exporter status
exit code
```

When present, it remains visible only in result metadata:

```yaml
repository_dirty: true | false
dirty_paths: []
```

`CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF` is excluded from the authoritative handoff path.

## Determinism and path safety

The exporter preserves:

- UTF-8 canonical JSON with sorted keys and compact separators;
- rejection of `NaN` and `Infinity`;
- one trailing newline in the written artifact;
- deterministic export and bundle identities;
- exact source and selected-candidate/class binding;
- output/input alias protection;
- symlink and directory rejection;
- CE-root containment for relative outputs;
- direct safe publication to caller-selected absolute external outputs;
- existing-output ownership validation and explicit overwrite;
- synthetic-evidence handoff blocking;
- atomic replacement;
- post-write recomputation and validation;
- no silent fallback.

These controls establish repository-level functional correctness. They do not claim elimination of every operating-system filesystem race or hostile in-process mutation.

## Post-write failure state

If a new output fails post-write validation, it is removed. If a prior CE-owned output was being replaced, its exact captured bytes are restored at the same resolved path, including an absolute external path.

A failure result marks the candidate as non-consumable:

```yaml
status: invalid
output_valid: false
artifact_must_not_be_consumed: true
handoff_allowed: false
authorization_valid: false
```

If cleanup or restoration itself fails, the result adds `CE_EXPORT_POST_WRITE_CLEANUP_FAILED` and reports the observed artifact state. The target must not be consumed.

## Result output

The command prints structured JSON containing the result envelope and summary. Fields may include:

```text
status
output_path
output_written
handoff_allowed
diagnostics
output_valid
artifact_state
artifact_must_not_be_consumed
export_id
source_intake_hash
source_bundle_hash
ce_payload_hash
builder_executable_package_hash
bundle_hash
export_identity_hash
export_hash
producer_commit
producer_ref
repository_dirty
dirty_paths
handoff_target
authorization_valid
verified_payload_schema
```

## Exit codes

```text
0  valid export with allowed Builder handoff
1  invalid input, path, contract, authority, snapshot, publication, or post-write validation
2  valid export whose Builder handoff remains blocked
```

Expected operational failures return structured JSON rather than an unhandled traceback.

## Legacy raw-Payload route

The historical command path based on `validator.project_gate_exporter` and `--payload` is not the official successor exporter. It remains validation and migration-preview compatibility only.

A raw `ev4-ce-stage-payload@1.0.0` cannot authorize Builder handoff or Project Gate transition and is bounded by:

```text
CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN
```

Do not describe `scripts/export-ce-project-gate.py` as equivalent to the verified Review Draft command.

## Boundaries

CE does not:

- generate a final Builder Context Package;
- reproduce the Project Gate CE-to-Builder adapter;
- issue transition receipts;
- fabricate runtime execution evidence;
- claim real Browser, Elementor, Responsive, accessibility, interaction, QA, deployment, or production completion without compatible evidence;
- silently repair invalid CE facts or fabricate missing evidence.

Merged implementation does not by itself establish production readiness, cross-repository E2E acceptance, or downstream runtime completion.
