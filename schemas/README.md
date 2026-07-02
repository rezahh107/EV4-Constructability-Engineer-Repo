# Schemas

The MVP has three contracts:

- constructability_review.schema.json
- implementation_strategy_map.schema.json
- builder_executable_package.schema.json

The Builder package schema is intentionally strict. It uses hard gates such as const values and empty blocking dependencies for executable-ready output.

For visual-reference packages, `builder_executable_package.schema.json` intentionally keeps CE-side `paradigm_to_structure_map.connector_layer` structured as an object with `node` and `model`. The Builder-side compact `node:model` string is a downstream adapter projection, not a CE schema output shape.
