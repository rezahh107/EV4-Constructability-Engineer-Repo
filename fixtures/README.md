# Fixtures

Fixture folders:

- valid: positive examples.
- invalid: executable-ready claims that must fail closed.
- regression: real failure patterns that must remain protected.

Critical regression fixture:

regression/r01_unflagged_connector_geometry_dependency.yaml

It proves that connector geometry dependencies are detected from the action itself, not from an explicit unresolved flag.
