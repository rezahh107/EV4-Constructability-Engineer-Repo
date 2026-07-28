# CE Output Path Policy

The shared output-safety authority is `validator.ce_validation_transaction.safe_output_path`.

Its default policy is repository-contained:

- relative output paths are resolved from the CE repository root;
- absolute paths inside the CE repository are accepted subject to the shared safety checks;
- absolute paths outside the CE repository are rejected with `CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY` unless the caller has an explicit internal opt-in.

Only the official verified Review Draft exporter in `validator._verified_project_gate_exporter_impl` enables safe external absolute publication. This capability is used by the public entry point:

```text
ev4-ce-project-gate-export = validator.verified_project_gate_exporter:main
```

The public identity and CLI remain unchanged:

```text
ev4-producer-gate-export-validator@1.1.0
--review-draft
--source-intake
--source-bundle
--output
--repo-root
--overwrite
```

The immutable `producer-gate-export.v1` artifact continues to carry `validator_version: 1.0.0`.

The historical `validator.project_gate_exporter` `--payload` route does not opt in. Its output remains repository-contained, and a Legacy external output is rejected before publication with `CE_EXPORT_OUTPUT_OUTSIDE_REPOSITORY`.

Alias, symlink, directory, existing-output ownership, explicit overwrite, atomic publication, post-write validation, cleanup, and prior-owned-output restoration remain centralized in the existing shared transaction implementation. No second output-safety authority is introduced.
