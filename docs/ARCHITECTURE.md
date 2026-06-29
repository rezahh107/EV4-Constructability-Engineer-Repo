# Architecture Overview

The MVP is deliberately small but not shallow.

Layers:

1. Schemas define document shape.
2. Rules define fail-closed executable gates.
3. Engine loads YAML, applies schemas, then applies rules.
4. Fixtures encode expected pass/fail behavior.
5. Tests protect regressions.

The system is question-driven. It does not depend on explicit words such as unresolved or unknown. It infers required proof from the executable action.
