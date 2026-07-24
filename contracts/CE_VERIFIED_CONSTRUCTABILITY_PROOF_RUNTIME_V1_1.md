# CE deterministic constructability runtime v1.1

This historical filename is retained for documentation-link compatibility. The runtime no longer
uses opaque proof capabilities, exact private classes, object identity, copy/deepcopy rejection, or
import-time patching as correctness mechanisms.

The authoritative successor description is:

- `contracts/CE_DETERMINISTIC_CONSTRUCTABILITY_EVALUATION_V1_1.md`
- canonical registry: `validator/claim_policy_registry.py`
- obligation derivation: `validator/review_obligations.py`
- claim evaluators: `validator/claim_evaluators.py`
- four results: `validator/intermediate_results.py`
- assembler: `validator/payload_assembler.py`
- fidelity recomputation: `validator/payload_fidelity.py`

The compatibility identities remain:

```yaml
review_draft_schema: ev4-ce-review-draft@1.0.0
successor_payload_schema: ev4-ce-stage-payload@1.1.0
constructability_review_schema: ev4-constructability-review@1.1.0
builder_package_schema: ev4-builder-executable-package@1.0.0
legacy_payload_validation_supported: true
legacy_payload_authorization_supported: false
```

A Draft proposes engineering analysis. Mandatory claims are derived by the repository. File
integrity is not claim correctness. Runtime-only claims require actual captured execution or remain
blocking downstream obligations. Before export, expected results and Payload are recomputed from
canonical inputs and compared with the persisted projection.
