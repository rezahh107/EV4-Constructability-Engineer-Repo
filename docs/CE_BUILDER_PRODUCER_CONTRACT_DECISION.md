# CE Builder Producer Contract Decision

Decision: CE output keeps structured connector-layer evidence.

Accepted CE producer shape:

```yaml
connector_layer:
  node: string
  model: string
```

Rejected CE producer shape:

```yaml
connector_layer: node:model
```

Reason: the compact string is a downstream Builder adapter projection, not CE source evidence.
