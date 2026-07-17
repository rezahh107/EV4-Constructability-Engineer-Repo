# CE-02 Project Gate Exporter Post-Merge Audit

## Audit identity

```yaml
prompt_id: P-004
task_id: CE-02
repository: rezahh107/EV4-Constructability-Engineer-Repo
default_branch: main
audited_main_commit: ebc73c28a154123b4c76f340ff0913934833789d
merged_pull_request: 36
merged_pr_head: 1804705c1ad86b4e414b2e5a40294bb8d1a9727a
merged_pr_base: 5fa3b8aec25a22f576e65c51ffb9dd843ddb727f
merge_commit: ebc73c28a154123b4c76f340ff0913934833789d
merge_commit_file_delta_from_validated_head: none
repair_pull_request: 37
repair_branch: audit/ce-02-exporter-audit-repair
remaining_defect_repair_starting_head: 70921a15b0c57f201de0f7c757a2164efde726a1
repair_merge_performed: false
status: implemented_pending_fresh_independent_rereview
```

## Mission boundary

The audited operator path is:

```text
accepted Architect→CE operational input
→ completed CE Stage Payload
→ ev4-ce-project-gate-export
→ ce-project-gate.json
→ no manual JSON editing
```

The audit and bounded repair do not claim Project Gate runtime acceptance, Builder acceptance, cross-repository E2E completion, Responsive completion, deployment, production readiness, or final closure by PR Inspector.

## Evidence inspected

- live PR #37 identity and exact starting head;
- merged PR #36 identity and changed paths;
- `AGENTS.md`, `README.md`, and mutable `STATUS.md`;
- active Architect intake, CE Stage Payload, Builder package, Stage Bundle, and Producer Gate Export identities;
- immutable Project Gate contract locks;
- official CLI registration in `pyproject.toml`;
- exporter entrypoint, orchestration, core validation, construction, hashing, atomic write, cleanup, and output-path code;
- all callers of `export_file`, `_safe_output_path`, `run_official_intake_validation`, `load_source_intake_snapshot`, and `_load_source_bundle_snapshot` found in the exporter modules and focused tests;
- exporter, cleanup-state, post-merge audit, intake, and repository-wide test suites;
- `.github/workflows/validate-fixtures.yml` and `.github/workflows/verify-project-gate-contract.yml`;
- exporter documentation and CE-02 status history.

## Baseline evidence retained

The merged PR #36 head had successful exact-head workflow evidence before merge:

```yaml
validate_fixtures_run: 29556024338
verify_project_gate_contract_run: 29556024536
pytest_tests: 273
pytest_failures: 0
pytest_errors: 0
pytest_skipped: 0
```

The merge commit is content-equivalent to the validated PR #36 head. No post-merge workflow run was observed on the merge commit itself.

PR #37 starting head `70921a15b0c57f201de0f7c757a2164efde726a1` had prior exact-head green evidence, but two independently identified residual defects remained. This follow-up repair supersedes the earlier exact-head evidence and requires fresh validation on the resulting head.

## Earlier CE-02 findings retained

The following earlier bounded repairs remain in place:

- source-bundle initial byte snapshot and persistent-mutation second-read check;
- leaf output symlink rejection before resolution;
- explicit output-directory rejection;
- structured output-path inspection failures;
- reuse of the canonical non-JSON numeric constant rejection helper;
- post-write invalid-output cleanup reporting.

No earlier public schema, contract identity, hash lock, dependency version, workflow permission, repository setting, or downstream ownership boundary is changed by this follow-up.

## Remaining defect 1 — Source Bundle and Source Intake ABA/TOCTOU

```yaml
severity: high
status: implemented_pending_fresh_independent_rereview
components:
  - validator/project_gate_exporter_orchestration.py
  - tests/test_project_gate_exporter_post_merge_audit.py
```

### Root cause

At the starting head, the exporter captured source bytes as snapshot `A`, then invoked the official validator against the original mutable operator path, and finally compared the original path with snapshot `A` again.

That sequence rejected persistent `A → B` mutation but did not bind validator consumption to the exporter snapshot. An `A → B → A` sequence could allow the validator to consume `B`, allow the second-read equality check to observe restored `A`, and allow export construction and hashing to continue from in-memory `A`.

The same shared-path weakness applied to both Source Bundle and Source Intake because both original paths were passed to the official validator.

### Required invariant

The exact Source Intake and Source Bundle bytes parsed, embedded, and hashed by the exporter must be the same bytes consumed by the official validator. Equality of the shared paths before and after validation is not sufficient evidence of consumed-byte identity.

### Precise repair

- capture Source Intake and Source Bundle bytes once;
- parse and retain the corresponding in-memory objects from those captured bytes;
- create a unique private temporary directory outside the requested output path;
- create private files with exclusive temporary-file creation and write exactly the captured bytes;
- flush and `fsync` each private file before validation;
- invoke `run_official_intake_validation` only with the two private snapshot paths;
- remove the private snapshot directory before export construction proceeds;
- retain second-read equality checks against the original operator paths to reject persistent mutation;
- continue source binding, construction, and hashing from the original captured in-memory snapshots;
- map private snapshot preparation failure to `CE_EXPORT_VALIDATION_SNAPSHOT_PREPARATION_FAILED`;
- map private snapshot cleanup failure to `CE_EXPORT_VALIDATION_SNAPSHOT_CLEANUP_FAILED`;
- write no output when snapshot preparation, official validation, cleanup, or original-path stability verification fails.

### Regression coverage

```text
test_source_bundle_aba_change_during_official_validation_fails_or_uses_private_snapshot
test_source_intake_aba_change_during_official_validation_uses_private_snapshot
test_private_validation_snapshots_are_removed_when_validation_fails
test_private_validation_snapshot_cleanup_failure_is_structured
```

The ABA tests mutate the shared path to `B`, restore it to `A` before the validator wrapper returns, and prove that the validator path is a private snapshot containing `A`. They also prove the private directory is not the output directory and is removed before export completion.

## Remaining defect 2 — Public CLI path resolution escaped the protected boundary

```yaml
severity: high
status: implemented_pending_fresh_independent_rereview
components:
  - validator/project_gate_exporter.py
  - validator/project_gate_exporter_orchestration.py
  - tests/test_project_gate_exporter_post_merge_audit.py
```

### Root cause

At the starting head, `repo_root.resolve()` executed before the `ExporterError` boundary in `export_file`. The CLI also called `.resolve()` on payload, Source Intake, and Source Bundle arguments before invoking `export_file`.

`Path.resolve()` may raise `OSError` or `RuntimeError`. Those operational filesystem failures could therefore escape as a traceback rather than deterministic JSON with exit code `1`. Output-path failures were already structured inside `_safe_output_path`, but the public CLI did not provide equivalent protection for repository and input paths.

### Required invariant

Every repository-root, operator-input, and output-path resolution failure reachable from the public exporter CLI must return structured invalid JSON, no traceback, exit code `1`, `output_written: false`, `handoff_allowed: false`, a stable diagnostic, and no output artifact.

### Precise repair

- remove all CLI-side `.resolve()` calls;
- resolve repository root inside `export_file` with a dedicated protected helper;
- resolve payload, Source Intake, and Source Bundle paths inside `export_file` with a dedicated protected helper;
- map repository-root and Git-provenance path-inspection failures to `CE_EXPORT_REPOSITORY_PATH_INSPECTION_FAILED`;
- map payload, Source Intake, and Source Bundle path-inspection failures to `CE_EXPORT_INPUT_PATH_INSPECTION_FAILED`;
- retain output-path inspection mapping to `CE_EXPORT_OUTPUT_PATH_INSPECTION_FAILED`;
- include the failing path and `repair_owner: repository_owner`;
- catch only relevant `OSError` and `RuntimeError` around filesystem/path inspection boundaries, without converting unrelated programming exceptions;
- preserve missing-file, invalid-JSON, outside-repository output, leaf-symlink, directory, and overwrite behavior.

### Regression coverage

```text
test_cli_path_resolution_failures_are_structured_and_write_no_output[repo_root]
test_cli_path_resolution_failures_are_structured_and_write_no_output[payload]
test_cli_path_resolution_failures_are_structured_and_write_no_output[source_intake]
test_cli_path_resolution_failures_are_structured_and_write_no_output[source_bundle]
test_cli_path_resolution_failures_are_structured_and_write_no_output[output]
```

Each case asserts exit code `1`, empty stderr, no traceback, `status: invalid`, `output_written: false`, `handoff_allowed: false`, the exact diagnostic code, the failing path, `repair_owner: repository_owner`, and absence of an output artifact.

## Adjacent-impact result

The repair preserves:

- `export_file` public arguments and return contract;
- `_safe_output_path` containment, symlink, directory, and overwrite behavior;
- `run_official_intake_validation` public signature;
- `load_source_intake_snapshot` and `_load_source_bundle_snapshot` return contracts;
- source hash semantics and canonical JSON behavior;
- Stage Bundle and Producer Gate Export identities;
- Builder package validation and handoff semantics;
- post-write cleanup-state truthfulness;
- workflow permissions and immutable action pins;
- Project Gate and downstream ownership boundaries.

## Files changed by this follow-up

```text
validator/project_gate_exporter.py
validator/project_gate_exporter_orchestration.py
tests/test_project_gate_exporter_post_merge_audit.py
docs/CE_PROJECT_GATE_EXPORTER.md
patch-reports/CE_02_PROJECT_GATE_EXPORTER_POST_MERGE_AUDIT.md
```

The existing PR-level changes to `.github/workflows/validate-fixtures.yml` and `STATUS.md` are inspected and preserved. No schema, public artifact identity, Project Gate pin, Builder semantic contract, repository setting, secret, dependency version, workflow permission, or downstream repository file is modified by this follow-up.

## Required validation

```bash
python -m pip install -e '.[dev]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_project_gate_exporter.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_project_gate_exporter_cleanup_state.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_project_gate_exporter_post_merge_audit.py
pytest -q --junitxml=pytest-report.xml
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
python scripts/validate-ce-decision-lineage-sequence.py
python scripts/validate-ce-kernel-decision-receipts.py
python scripts/validate-project-gate-producer-adoption.py
```

The pull-request workflow must additionally prove exact-head checkout identity, immutable action pins, governance evidence generation, and the separate Project Gate contract verification workflow.

## Evidence state at commit time

```yaml
bounded_remaining_defect_repair_implemented: true
focused_regressions_added: true
exact_head_ci: pending
fresh_independent_rereview: mandatory
repair_merged: false
main_remains_unrepaired_until_merge: true
pr_inspector_final_closure_claimed: false
status: implemented_pending_fresh_independent_rereview
```

## Remaining limitations

- No real operator payload or real-run handoff evidence is available in this repair.
- Project Gate runtime acceptance remains unverified and outside this repository's ownership.
- Cross-repository E2E, Builder acceptance, and Responsive completion remain unverified.
- A post-validation filesystem actor may still replace a path after inspection but before a later atomic replacement; process-local path checks do not eliminate that external race.
- Private snapshot cleanup can be blocked by the operating system; that condition now fails closed with a structured diagnostic and no output, but may require repository-owner cleanup of the temporary directory.
- No deployment or production-readiness claim is made.

## Audit verdict at commit time

```text
IMPLEMENTED_PENDING_FRESH_INDEPENDENT_REREVIEW
```
