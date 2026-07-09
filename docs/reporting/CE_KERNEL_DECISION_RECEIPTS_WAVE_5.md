# CE Kernel Decision Receipts — Wave 5

```yaml
wave: 5
scope: presentation_layer_only
repository: EV4-Constructability-Engineer-Repo
status_claim: no_enforcement_upgrade
machine_trace_source_of_truth: true
```

## Purpose

Wave 5 adds a UX-safe human-readable receipt layer for CE decision-bearing surfaces.
The receipt is only a short explanation for the user. It does not replace the
machine-readable Kernel decision lineage and does not authorize Builder execution.

## Receipt surfaces

These CE surfaces may render `kernel_decision_receipt` when they contain or pass
a Kernel-governed decision:

- `ce_intake`
- `ce_output`
- `constructability_report`
- `constructability_review`
- `repair_request`
- `repair_handoff`
- `handoff`
- `builder_handoff`

## Required machine trace

A success receipt is allowed only when at least one `decision_lineage[]` entry has
all required machine-readable fields:

```text
decision_family
decision_card_ref
selected_option
rejected_options
evidence_refs
evidence_state
consumer_stage
```

If the trace is missing or incomplete, the formatter must render the
insufficient-evidence warning instead of a green success receipt.

## CE-specific wording

Success receipt:

```text
✅ تصمیم به decision card کرنل وصل است؛ CE فقط constructability آن را بررسی کرده و lineage تصمیم حفظ شده است.
```

Warning receipt:

```text
⚠️ این آیتم هنوز رسید معتبر کرنل ندارد؛ CE نمی‌تواند بدون machine-readable trace کامل آن را قابل‌عبور اعلام کند.
```

## Validator behavior

The receipt validator fails closed when:

- a green-check receipt appears without complete `decision_lineage`;
- `decision_card_ref` is missing;
- `evidence_refs` is missing or empty;
- CE claims `executable_ready`, Builder readiness, or constructability pass without trace;
- repair or handoff output emits success wording without trace.

The warning receipt is valid for incomplete trace because it explicitly prevents
CE from presenting the item as passable.

## Non-claims

This Wave 5 implementation does not claim:

- `ci_enforced`
- `sequence_ci_enforced`
- `downstream_contract_enforced`
- `runtime_monitor_enforced`
- `production_ready`
- constructability pass from receipt text alone
- Project Gate runtime acceptance
- real Elementor validation

## Validation commands

```bash
python scripts/validate-ce-kernel-decision-receipts.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_kernel_decision_receipts.py
pytest -q
```
