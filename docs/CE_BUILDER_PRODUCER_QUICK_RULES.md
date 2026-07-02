# CE Builder Producer Quick Rules

Use these rules when reviewing CE output that may be sent downstream to Builder.

```text
CE keeps source structure.
CE proves constructability.
CE emits {node, model} for connector_layer.
CE does not emit node:model.
The downstream adapter emits node:model.
Builder consumes the adapter output.
```

Fail closed if CE output collapses structured source evidence into Builder compact carriers before the downstream transformation layer runs.
