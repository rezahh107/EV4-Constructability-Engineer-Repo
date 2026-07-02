# CE Builder Producer Contract Hardening

Date: 2026-07-02  
Branch: `hardening/ce-builder-producer-contract-clean`  
Scope: producer-side CE contract boundary for downstream CE→Builder transformation

---

## Summary

This patch hardens the CE side of the CE→Builder handoff after the Builder repository added a formal downstream transformation layer.

CE remains the producer of structured constructability evidence. It must not pre-collapse structured CE fields into Builder-only compact carrier strings.

---

## Added

- `docs/CE_TO_BUILDER_PRODUCER_CONTRACT.md`
- `tests/test_ce_builder_producer_contract.py`

---

## Updated

- `README.md`
- `docs/PROTOCOL.md`
- `schemas/README.md`

---

## Locked behavior

- CE visual-reference packages keep `paradigm_to_structure_map.connector_layer` as:

```yaml
connector_layer:
  node: string
  model: string
```

- CE must not emit Builder's downstream compact projection:

```yaml
connector_layer: node:model
```

- The downstream CE→Builder adapter owns the `node:model` projection.

---

## Validation expectation

Run:

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
```

This connector session did not run local validation in a checked-out CE workspace.
