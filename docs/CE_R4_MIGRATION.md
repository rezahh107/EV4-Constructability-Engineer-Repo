# CE R4 Migration Notes

## Draft authors

- Keep `ev4-ce-review-draft@1.0.0`.
- Use only action types and parameters declared in `validator/action_contract_registry.py`.
- Legacy aliases such as `layout` and `class_name` are normalized; ambiguous aliases fail closed.
- Original artifact candidates may use `source_ref` or `original_source_ref`; the referenced file must
  be the original JSON/HTML/CSS/SVG source, not a CE `facts` extract.
- `cached_extract_ref` is optional and must regenerate byte-semantically from the original source.

## Canonical evaluation path

Direct Python use, CLI execution, fidelity replay, and the official exporter all resolve through
`validator.payload_fidelity.evaluate_ce_transaction`. No separate direct-Python authority path is
supported.

## Payload consumers

- `payload_status=complete` is CE-stage completion and Builder readiness only.
- Read `downstream_test_obligations` and the `lifecycle_status` extension.
- `runtime_validation=pending` and `final_project_gate=blocked` are normal at Builder handoff.
- Do not treat a runtime obligation as an executed result.
- Builder actions remain compatible with `ev4-builder-executable-package@1.0.0`; their parameter
  values are now sourced exclusively from normalized Action IR.

## Legacy path

Raw `ev4-ce-stage-payload@1.0.0` remains validation/preview-only. It cannot authorize Builder
handoff.
