# Validation Notes — CE Builder Producer Contract

This note records the intended validation coverage for the CE→Builder producer boundary.

## Locked behavior

The CE schema and regression tests must preserve this boundary:

```text
CE output: connector_layer = {node, model}
Builder adapter output: connector_layer = node:model
```

The CE repository must reject Builder compact strings in CE output. The downstream adapter owns that projection.

## Regression test

```text
tests/test_ce_builder_producer_contract.py
```

Coverage:

- structured CE connector carrier passes package validation;
- compact Builder-style connector string fails CE package validation.

## CI workflow

```text
.github/workflows/ce-contract-validation.yml
```

Runs:

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
```
