# CE → Builder Producer Contract

Version: 1.0.0  
Status: active  
Scope: Constructability Engineer output that may later be transformed into Builder intake

---

## Purpose

This document defines the producer-side contract for CE output before it reaches Builder.

CE is the producer of executable constructability evidence. Builder is the consumer of normalized execution-ready input. The CE repository must therefore emit structured, evidence-preserving data and must not pre-collapse CE fields into Builder-only compact strings.

---

## Boundary

```text
Constructability Engineer
→ CE Builder Executable Package
→ downstream CE→Builder transformation layer
→ Builder Context Package
→ Builder validation
→ Builder execution
```

CE does not emit raw Builder runtime carriers. CE emits structured source evidence that the downstream adapter can transform without guessing.

---

## Required producer shape

For visual-reference packages, CE must emit `paradigm_to_structure_map.connector_layer` as a structured object:

```yaml
connector_layer:
  node: Smart Home Section / Decorative Connector Layer
  model: card-edge-to-house-edge
```

CE must not emit the Builder-side compact projection:

```yaml
connector_layer: Smart Home Section / Decorative Connector Layer:card-edge-to-house-edge
```

That `node:model` compact string belongs only to the downstream CE→Builder adapter and Builder intake projection.

---

## Producer-side rules

```text
1. CE must preserve source structure.
2. CE must keep connector_layer.node and connector_layer.model as separate fields.
3. CE must not silently transform structured fields into Builder compact strings.
4. Any downstream projection must be performed by the declared CE→Builder transformation layer, not by CE output generation.
5. If CE cannot prove the structured source field, the package is not Builder-ready.
```

---

## Field-level handoff expectation

| CE output field | Producer requirement | Downstream expectation |
|---|---|---|
| `paradigm_to_structure_map.primary_anchor.node` | Preserve source node string | Adapter projects to Builder primary anchor carrier |
| `paradigm_to_structure_map.primary_anchor.role` | Preserve role string | Adapter retains role in IR when Builder has no direct field |
| `paradigm_to_structure_map.regions[]` | Preserve object records with id, distribution, expected_count, nodes | Adapter derives Builder region strings and retains raw region objects in IR |
| `paradigm_to_structure_map.repeated_units` | Preserve form and required_children | Adapter derives Builder repeated-unit carriers |
| `paradigm_to_structure_map.connector_layer.node` | Preserve connector carrier node | Adapter uses it in `node:model` projection and retains it in IR |
| `paradigm_to_structure_map.connector_layer.model` | Preserve connector strategy model | Adapter uses it in `node:model` projection and Builder connector strategy fields |
| `paradigm_to_structure_map.first_batch_requirements[]` | Preserve source requirement strings | Adapter derives Builder-safe flags and retains raw strings in IR |

---

## Validation expectation

The current CE schema already requires `connector_layer` to be an object with `node` and `model`. The regression test `tests/test_ce_builder_producer_contract.py` locks this behavior so a future change cannot replace CE structured output with Builder compact string output without failing validation.

---

## Compatibility note

This is not a breaking change to the CE public package shape. It documents and locks the existing CE producer format so it remains compatible with the downstream CE→Builder transformation registry in `EV4-Builder-Assistant-Repo`.
