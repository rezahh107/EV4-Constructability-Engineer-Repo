# Validator

The validator has two layers:

1. JSON Schema structure checks for known package sections.
2. Rule checks for executable-ready claims.

Run one fixture:

```bash
python -m validator.engine fixtures/regression/r01_unflagged_connector_geometry_dependency.yaml
```

Run tests:

```bash
pytest -q
```
