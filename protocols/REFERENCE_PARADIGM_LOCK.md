# Reference Paradigm Lock

Version: 1.0.0
Status: active
Owner: Constructability Engineer

## Rule

No visual reference may be passed downstream as an image-only artifact.

Before any visual-parity Builder-ready package is emitted, Constructability Engineer must extract and validate:

```text
reference_paradigm_lock
paradigm_to_structure_map
```

## Required contract

The lock must identify the source reference, extraction owner, layout paradigm, primary anchor, distribution model, repeated unit form, connector model, symmetry, and completion signature.

The structure map must translate the paradigm into planned build nodes, including primary anchor, regions, repeated units, connector layer, and first batch requirements.

## Builder-ready gate

A visual-parity Builder-ready package is blocked unless:

```text
reference_paradigm_lock.paradigm_locked == true
reference_paradigm_lock.layout_paradigm != unknown
paradigm_to_structure_map exists
paradigm_to_structure_map.first_batch_requirements is non-empty
reference paradigm validation passes
```

## Boundary

This repo validates the paradigm contract. Builder still executes only the approved package and must not read the original image as the source of truth.
