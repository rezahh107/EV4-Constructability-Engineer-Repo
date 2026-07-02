# CE Grid Layout Compatibility

Date: 2026-07-02  
Decision: Option A — grid is conditionally Builder-compatible with explicit left/right decomposition

## Summary

This patch keeps `layout_paradigm: grid` valid in CE, but prevents CE from marking bare grid output as Builder-ready unless the output includes explicit left/right decomposition metadata.

## Changed

- `validator/reference_paradigm_lock.py`
- `tests/test_reference_paradigm_lock.py`
- `tests/valid/grid_with_left_right_decomposition.json`
- `tests/invalid/grid_without_left_right_decomposition.json`
- `docs/CE_TO_BUILDER_LAYOUT_COMPATIBILITY.md`

## Failure code

```text
LAYOUT_PARADIGM_REQUIRES_DECOMPOSITION
```

## Validation expectation

```bash
pytest -q
python -m validator.reference_paradigm_lock tests/valid tests/invalid --repo-root .
```
