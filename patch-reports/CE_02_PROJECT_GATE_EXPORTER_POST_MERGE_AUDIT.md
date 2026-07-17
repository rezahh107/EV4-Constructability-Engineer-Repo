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
repair_branch: audit/ce-02-exporter-audit-repair
repair_merge_performed: false
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

The audit does not claim Project Gate runtime acceptance, Builder acceptance, cross-repository E2E completion, Responsive completion, deployment, or production readiness.

## Evidence inspected

- live repository identity and current `main`;
- merged PR #36 identity and changed paths;
- `AGENTS.md`, `README.md`, and mutable `STATUS.md`;
- active Architect intake, CE Stage Payload, Builder package, Stage Bundle, and Producer Gate Export identities;
- immutable Project Gate contract locks;
- official CLI registration in `pyproject.toml`;
- exporter entrypoint, orchestration, validation, construction, hashing, atomic write, cleanup, and output-path code;
- exporter, cleanup-state, intake, and repository-wide tests;
- `.github/workflows/validate-fixtures.yml`;
- exact-head PR workflow runs and artifacts for `1804705c1ad86b4e414b2e5a40294bb8d1a9727a`;
- `planning/DECISION_ESCAPE_ROUTES.yml` for scope and enforcement interaction.

## Baseline evidence retained

The merged PR head had successful exact-head workflow evidence before merge:

```yaml
validate_fixtures_run: 29556024338
verify_project_gate_contract_run: 29556024536
pytest_tests: 273
pytest_failures: 0
pytest_errors: 0
pytest_skipped: 0
```

The merge commit is content-equivalent to the validated PR head. No post-merge workflow run was observed on the merge commit itself.

## Finding CE02-F001 — source-bundle snapshot was not stable

```yaml
severity: high
status: defect_reproduced_repair_in_pr
component: validator/project_gate_exporter_orchestration.py
```

The exporter captured `source_intake` bytes and required a second-read equality check, but loaded `source_bundle` once as an object, invoked the official validator against the mutable path, and then continued with the earlier in-memory object without proving byte equality.

A source bundle could therefore change between the exporter's initial read and the official subprocess validation. The official validator and the final exported artifact could operate on different source-bundle bytes while the run still appeared successful.

### Repair

- capture the source bundle as one byte snapshot;
- parse only that snapshot;
- run the official intake/source-bundle validator;
- read the source bundle again and require byte equality;
- return `CE_EXPORT_SOURCE_BUNDLE_READ_FAILED` for read failure;
- return `CE_EXPORT_SOURCE_BUNDLE_CHANGED_DURING_EXPORT` for mutation;
- write no artifact for either failure.

### Regression

`test_source_bundle_change_after_official_validation_fails_closed`

`test_source_bundle_second_read_failure_is_structured_and_writes_no_output`

## Finding CE02-F002 — leaf output symlink refusal was ineffective

```yaml
severity: high
status: defect_reproduced_repair_in_pr
component: validator/project_gate_exporter_orchestration.py
```

The prior implementation resolved the output path before checking `is_symlink()`. Resolution dereferenced an existing leaf symlink, so the subsequent check inspected the target rather than the operator-supplied symlink.

This could allow the command to replace an in-repository symlink target despite the documented symlink refusal.

### Repair

- inspect the operator-supplied candidate before resolution;
- reject an existing leaf symlink with `CE_EXPORT_OUTPUT_SYMLINK_FORBIDDEN`;
- retain repository-containment validation after resolution;
- preserve explicit overwrite behavior for ordinary files.

### Regression

`test_cli_refuses_existing_leaf_symlink_with_structured_json`

## Finding CE02-F003 — path-inspection exceptions could escape the CLI contract

```yaml
severity: medium
status: defect_reproduced_repair_in_pr
component: validator/project_gate_exporter_orchestration.py
```

`Path.resolve()`, `is_symlink()`, and related filesystem inspection can raise `OSError` or `RuntimeError`. The previous path helper did not convert these failures to `ExporterError`, while the public CLI catches and serializes only exporter diagnostics.

An operational path-resolution failure could therefore produce a traceback instead of deterministic JSON.

### Repair

- convert `OSError` and `RuntimeError` during output-path inspection to `CE_EXPORT_OUTPUT_PATH_INSPECTION_FAILED`;
- preserve `repository_owner` repair routing;
- keep exit code `1` through the existing CLI result contract.

### Regression

`test_output_path_resolution_failure_has_stable_diagnostic`

## Files changed by the bounded repair

```text
.github/workflows/validate-fixtures.yml
STATUS.md
docs/CE_PROJECT_GATE_EXPORTER.md
patch-reports/CE_02_PROJECT_GATE_EXPORTER_POST_MERGE_AUDIT.md
tests/test_project_gate_exporter_post_merge_audit.py
validator/project_gate_exporter_orchestration.py
```

No schema, public contract identity, Project Gate pin, Builder semantic contract, repository setting, secret, dependency version, or workflow permission was changed.

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

## Current evidence state

```yaml
bounded_repair_implemented: true
focused_regressions_added: true
exact_head_ci: pending
independent_repair_review: pending
repair_merged: false
main_remains_unrepaired_until_merge: true
post_merge_implementation_evidence_closed: false
```

## Remaining limitations

```yaml
real_operator_payload: not_available
real_run_handoff_evidence: not_available
project_gate_runtime_acceptance: unverified
cross_repository_e2e: unverified
builder_acceptance: unverified
responsive_completion: unverified
filesystem_race_after_path_validation: not_eliminated_by_process_local_checks
production_ready: false
```

## Audit verdict at commit time

```text
REPAIR_IMPLEMENTED_PENDING_EXACT_HEAD_VALIDATION_AND_INDEPENDENT_REVIEW
```
