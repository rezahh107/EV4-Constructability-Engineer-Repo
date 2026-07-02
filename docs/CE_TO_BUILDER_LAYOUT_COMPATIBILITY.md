# CE → Builder Layout Compatibility

Version: 1.0.0  
Status: active  
Decision: Option A — `grid` is Builder-compatible only with explicit left/right decomposition

## Rule

CE may keep `layout_paradigm: grid` as a valid reference-paradigm value, but CE must not mark grid output as Builder-ready unless it includes explicit Builder-compatible left/right decomposition metadata.

## Required metadata for Builder-ready grid

```text
- paradigm_to_structure_map.regions[] has an explicit left region
- paradigm_to_structure_map.regions[] has an explicit right region
- left and right regions have positive expected_count
- left and right regions have non-empty nodes[]
- reference_paradigm_lock.distribution_model includes left/right decomposition evidence
```

## Failure code

```text
LAYOUT_PARADIGM_REQUIRES_DECOMPOSITION
```

## Registry source of truth

The Builder-side CE→Builder registry declares the compatibility matrix:

```text
EV4-Builder-Assistant-Repo/data/ce-builder-transformation-registry.v1.json
layout_compatibility.contract_name = CE_TO_BUILDER_LAYOUT_COMPATIBILITY
```
