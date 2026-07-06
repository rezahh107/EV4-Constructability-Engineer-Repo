# CHANGELOG — EV4 Constructability Engineer Repo

## Unreleased — 2026-07-07

### Added

- Added canonical CE pipeline manifest `manifests/ce_pipeline_manifest.v1.json` and schema `schemas/ce_pipeline_manifest.v1.schema.json`.
- Added CE Stage Payload schema `schemas/ce_stage_payload.v1.schema.json` for Project Gate producer export composition.
- Vendored Project Gate `producer-gate-export.v1` contract bytes under `contracts/project-gate/` with immutable lock file.
- Added deterministic CE producer adoption validator and script: `validator/project_gate_export.py` and `scripts/validate-project-gate-producer-adoption.py`.
- Added synthetic Project Gate export fixtures and tests for blocked export, silent fallback rejection, exact-byte vendoring, deterministic serialization, NaN rejection, and Infinity rejection.
- Added malformed-input fail-closed regression tests for mixed schema paths, invalid ordinals, and non-object final stage entries.
- Added immutable reusable workflow caller `.github/workflows/verify-project-gate-contract.yml` pinned to Project Gate merge commit `ea19c22c32458068e167b267da8b819e9263cdf7`.
- Added official-source Elementor capability registry with explicit `insufficient_evidence` entries where current official evidence was not established.

### Changed

- Reconciled README/STATUS wording so CE producer adoption is implemented in CE while `project_gate_runtime` remains `not_implemented`.
- Documented optional `builder_executable_package.schema` in JSON Schema while preserving missing schema identity as a semantic validator gate.
- Hardened `validator/project_gate_export.py` so malformed inputs return deterministic diagnostics instead of crashing.
- Added `python scripts/validate-project-gate-producer-adoption.py` to the fixture validation workflow.

### Status

- `project_gate_runtime_integration`: `not_implemented`.
- `builder_acceptance`: `not_implemented`.
- `cross_repository_e2e`: `insufficient_evidence`.
- `real_elementor_validation`: `insufficient_evidence`.
- `responsive_completion`: `insufficient_evidence`.
- `production_ready`: `false`.

## Unreleased — 2026-07-02

### Changed

- Required every emitted `builder_executable_package` to declare `schema: ev4-builder-executable-package@1.0.0`.
- Added CE validator failures for missing or unsupported Builder executable package schema values.
- Updated role-alignment prerequisites, fixtures, and docs to match the downstream Builder CE→Builder Contract Gate.

### Status

- No architecture scoring, recommendation, constructability review, redesign, or Builder execution was rerun.
- `selected_candidate_id` and approved class intent preservation remain unchanged.
- CE still emits structured source evidence; Builder-side projection remains downstream adapter responsibility.
