# CE Builder Transformation Pointer

The CE repository owns structured producer output.

The Builder repository owns normalized Builder intake and the formal CE→Builder transformation layer.

Current downstream reference:

```text
rezahh107/EV4-Builder-Assistant-Repo
docs/CE_TO_BUILDER_TRANSFORMATION_SPEC.md
data/ce-builder-transformation-registry.v1.json
```

Boundary summary:

```text
CE emits connector_layer: {node, model}
CE→Builder adapter projects connector_layer: node:model
Builder consumes the normalized compact carrier
```

This file is a pointer only. It does not make CE authoritative for Builder intake schemas.
