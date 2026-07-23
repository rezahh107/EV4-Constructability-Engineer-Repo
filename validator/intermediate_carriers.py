"""Deterministic CE intermediate validation carriers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .intermediate_carriers_common import (
    CARRIER_KINDS,
    DEPENDENCY_RULES,
    LEGAL_STATUSES,
    OWNER_REPOSITORY,
    SCHEMA_ID,
    SCHEMA_VERSION,
    _as_dict,
    _as_list,
    _diag,
    _diagnostic_key,
    _strings,
    canonical_json_bytes,
    canonical_sha256,
)
from .intermediate_carriers_dependency import derive_dependency_classification
from .intermediate_carriers_fidelity import (
    _compare_ce_payload_with_derived_carriers,
    validate_carrier,
)
from .intermediate_carriers_identity import derive_architecture_identity_preservation
from .intermediate_carriers_review import derive_review_units_and_interrogation_results
from .intermediate_carriers_strategy import derive_implementation_strategy_coverage


def _transaction_status(
    carrier_statuses: dict[str, Any],
    diagnostics: list[dict[str, Any]],
) -> str:
    observed = {str(value) for value in carrier_statuses.values()}
    observed.update(str(item.get("severity_or_status")) for item in diagnostics)
    for status in ("invalid", "blocked", "insufficient_evidence", "complete"):
        if status in observed:
            return status
    return "invalid"


def _carrier_map(carriers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(carrier.get("carrier_kind")): carrier
        for carrier in carriers
    }


def evaluate_ce_intermediate_validation(
    *,
    run_id: str,
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    constructability_review: dict[str, Any],
    implementation_strategy_map: dict[str, Any] | None,
    builder_executable_package: dict[str, Any] | None,
    final_payload: dict[str, Any],
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run the authoritative raw-input CE intermediate validation transaction.

    Serialized carrier dictionaries are outputs only. This API deliberately
    accepts no caller-supplied carriers, so the final fidelity decision always
    uses carriers rederived in this function execution.
    """

    carrier_validation_diagnostics: list[dict[str, Any]] = []

    identity_carrier = derive_architecture_identity_preservation(
        run_id=run_id,
        intake=intake,
        source_bundle=source_bundle,
        constructability_review=constructability_review,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(identity_carrier, repo_root=repo_root)
    )

    review_carrier = derive_review_units_and_interrogation_results(
        run_id=run_id,
        intake=intake,
        constructability_review=constructability_review,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(review_carrier, repo_root=repo_root)
    )

    dependency_carrier = derive_dependency_classification(
        run_id=run_id,
        review_carrier=review_carrier,
        constructability_review=constructability_review,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(dependency_carrier, repo_root=repo_root)
    )

    strategy_carrier = derive_implementation_strategy_coverage(
        run_id=run_id,
        identity_carrier=identity_carrier,
        review_carrier=review_carrier,
        dependency_carrier=dependency_carrier,
        implementation_strategy_map=implementation_strategy_map,
        builder_executable_package=builder_executable_package,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(strategy_carrier, repo_root=repo_root)
    )

    carriers = [
        identity_carrier,
        review_carrier,
        dependency_carrier,
        strategy_carrier,
    ]
    carrier_statuses = {
        str(carrier.get("carrier_kind")): carrier.get("status")
        for carrier in carriers
    }

    review_data = _as_dict(review_carrier.get("derived_data"))
    review_unit_ids = _strings(
        item.get("review_unit_id")
        for item in _as_list(review_data.get("review_units"))
        if isinstance(item, dict)
    )
    dependency_review_unit_ids = _strings(
        _as_dict(dependency_carrier.get("derived_data")).get("review_unit_ids")
        or []
    )
    consistency_diagnostics: list[dict[str, Any]] = []
    if review_unit_ids != dependency_review_unit_ids:
        consistency_diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_REVIEW_UNIT_IDENTITY_MISMATCH",
                "ce_intermediate_validation_transaction",
                "invalid",
                "Carrier 2 and Carrier 3 disagree on canonical CE review_unit_id values.",
                "$.carriers",
                related_ids=sorted(
                    set(review_unit_ids).symmetric_difference(
                        dependency_review_unit_ids
                    )
                ),
            ).as_dict()
        )

    fidelity = _compare_ce_payload_with_derived_carriers(
        payload=final_payload,
        identity_carrier=identity_carrier,
        review_carrier=review_carrier,
        dependency_carrier=dependency_carrier,
        strategy_carrier=strategy_carrier,
        builder_executable_package=builder_executable_package,
    )

    fidelity_passed = bool(fidelity.get("passed")) and not (
        carrier_validation_diagnostics or consistency_diagnostics
    )
    builder_ready = (
        fidelity_passed
        and all(status == "complete" for status in carrier_statuses.values())
        and strategy_carrier.get("status") == "complete"
        and isinstance(builder_executable_package, dict)
    )

    all_diagnostics = [
        item
        for carrier in carriers
        for item in _as_list(carrier.get("diagnostics"))
        if isinstance(item, dict)
    ]
    all_diagnostics.extend(carrier_validation_diagnostics)
    all_diagnostics.extend(consistency_diagnostics)
    all_diagnostics.extend(
        item
        for item in _as_list(fidelity.get("diagnostics"))
        if isinstance(item, dict)
    )
    ordered_diagnostics = sorted(all_diagnostics, key=_diagnostic_key)

    return {
        "transaction_status": _transaction_status(
            carrier_statuses,
            ordered_diagnostics,
        ),
        "fidelity_passed": fidelity_passed,
        "builder_ready": builder_ready,
        "carrier_statuses": carrier_statuses,
        "carriers": _carrier_map(carriers),
        "diagnostics": ordered_diagnostics,
    }


__all__ = [
    "CARRIER_KINDS",
    "DEPENDENCY_RULES",
    "LEGAL_STATUSES",
    "OWNER_REPOSITORY",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "canonical_json_bytes",
    "canonical_sha256",
    "derive_architecture_identity_preservation",
    "derive_review_units_and_interrogation_results",
    "derive_dependency_classification",
    "derive_implementation_strategy_coverage",
    "validate_carrier",
    "evaluate_ce_intermediate_validation",
]
