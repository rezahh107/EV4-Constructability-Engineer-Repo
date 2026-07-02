# CHANGELOG — EV4 Constructability Engineer Repo

## Unreleased — 2026-07-02

### Changed

- Required every emitted `builder_executable_package` to declare `schema: ev4-builder-executable-package@1.0.0`.
- Added CE validator failures for missing or unsupported Builder executable package schema values.
- Updated role-alignment prerequisites, fixtures, and docs to match the downstream Builder CE→Builder Contract Gate.

### Status

- No architecture scoring, recommendation, constructability review, redesign, or Builder execution was rerun.
- `selected_candidate_id` and approved class intent preservation remain unchanged.
- CE still emits structured source evidence; Builder-side projection remains downstream adapter responsibility.
