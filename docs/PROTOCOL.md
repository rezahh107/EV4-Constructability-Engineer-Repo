# Constructability Review Protocol

## Core Rule

Approved architecture is not approved implementation strategy.

Silence from Architect is not proof.

Not proven executable means not builder-ready.

## Inputs

The Engineer may receive Architect handoff data, approved structure tree, approved class names, proposed Builder actions, screenshots, measurements, assets, official docs, user statements, or version evidence.

## Process

1. Verify candidate and class locks.
2. Review every executable node or action.
3. Infer hidden execution dependencies from the action itself.
4. Apply failure pattern detection.
5. Classify dependencies as blocking, user-evidence, architect-amendment, or low-risk assumption.
6. Build an Implementation Strategy Map only when strategy can be proven.
7. Emit Builder Executable Package only when Builder has zero decisions left.

## Required Action Interrogation

For every node or action, answer:

1. Does this require geometry?
2. Are source and target anchors proven?
3. Does this require an external asset?
4. Is asset source or placeholder policy present?
5. Does this require overlay, containment, z-index, or positioning strategy?
6. Does this imply responsive behavior?
7. If responsive is unknown, is this batch explicitly desktop-only?
8. Does this imply interaction?
9. Does this imply Dynamic Loop or data binding?
10. Does this make an accessibility claim?
11. Does this use exact Elementor UI control paths?
12. Is the action reversible if wrong?
13. Would a wrong assumption force meaningful rework?
14. Does it change approved structure or class names?
15. Does it require Architect amendment?

## Status Results

- executable_ready: Builder package may be emitted.
- blocked: execution dependency is unresolved.
- needs_user_evidence: user evidence is needed.
- needs_architect_amendment: architecture boundary would be crossed.
- executable_with_logged_assumption: low-risk, reversible, visible, boundary-safe assumption.

## Builder Emission Gate

A Builder package may be emitted only when builder decisions are zero, blocking dependencies are empty, the selected candidate is locked, approved class names are unchanged, structured confirmation_request is present, and first_safe_builder_batch is present.

For visual-reference packages, CE must emit structured reference carriers. CE must preserve `paradigm_to_structure_map.connector_layer.node` and `paradigm_to_structure_map.connector_layer.model` as separate fields. CE must not pre-project those fields into Builder's compact `node:model` carrier; that projection is owned by the downstream CE→Builder transformation layer.
