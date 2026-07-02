# CE Builder Producer Contract Review Checklist

Use this checklist when reviewing CE output that may be transformed downstream for Builder.

- `paradigm_to_structure_map.connector_layer` is an object, not a string.
- `connector_layer.node` is present and non-empty.
- `connector_layer.model` is present and non-empty.
- The package does not include Builder compact `node:model` projection as CE source data.
- Any compact projection is left to the downstream CE→Builder adapter.
