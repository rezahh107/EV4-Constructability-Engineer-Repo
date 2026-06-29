# Validation Model

The validator supports three explicit modes:

```text
report
package
full
```

## report mode

Use `report` mode for Constructability Engineer review output that does not emit a Builder package.

Allowed examples:

- `blocked`
- `needs_user_evidence`
- `needs_architect_amendment`
- `executable_with_logged_assumption` when no Builder package is emitted

Contract:

```text
report mode must not include builder_executable_package
```

This mode allows a correct non-executable review to pass validation while still documenting why Builder must wait.

## package mode

Use `package` mode for Builder Executable Package output.

Contract:

```text
builder_executable_package must be present
constructability_status must be executable_ready
builder_package_status must be executable_ready
```

A package-mode document must leave Builder with zero decisions.

## full mode

Use `full` mode as the default regression mode. It validates the whole document and applies cross-section compatibility checks.

Contract:

```text
If constructability_review is non-executable, builder_executable_package must be absent.
If builder_executable_package is present, review/package statuses must be compatible.
```

## Core invariant

```text
A non-executable constructability review must not emit a Builder package.
```

This prevents a blocked review from being shadowed by an executable package section.
