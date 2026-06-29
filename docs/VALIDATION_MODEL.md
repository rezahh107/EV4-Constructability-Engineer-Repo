# Validation Model

The validator checks executable-ready claims.

A correct non-executable review may return `needs_user_evidence`, `blocked`, or `needs_architect_amendment` without emitting a Builder package.

MVP note:

- `builder_executable_package` schema enforces hard executable gates.
- rule evaluation detects invalid executable-ready claims.
- future patches may add separate report-quality validation for non-executable review reports.

This separation avoids treating a correct evidence request as a failed Builder package.
