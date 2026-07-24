"""Deterministic CE intermediate validation carriers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .engine import validate_document
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
from .project_gate_export import validate_ce_stage_payload


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


def _resolve_repo_root(repo_root: str | Path) -> tuple[Path | None, list[dict[str, Any]]]:
    kind = "ce_intermediate_validation_transaction"
    try:
        root = Path(repo_root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        diagnostic = _diag(
            "CE_INTERMEDIATE_REPOSITORY_ROOT_INVALID",
            kind,
            "invalid",
            f"Authoritative repository root cannot be resolved: {exc}",
            "$.repo_root",
            repair_owner="repository_owner",
        )
        return None, [diagnostic.as_dict()]
    required = (
        root / "schemas/ce_stage_payload.v1.schema.json",
        root / "schemas/ce_intermediate_validation_carriers.v1.schema.json",
        root / "schemas/builder_executable_package.schema.json",
    )
    missing = [path.as_posix() for path in required if not path.is_file()]
    if missing:
        diagnostic = _diag(
            "CE_INTERMEDIATE_REPOSITORY_ROOT_INCOMPLETE",
            kind,
            "invalid",
            "Authoritative repository root is missing required validation schemas.",
            "$.repo_root",
            repair_owner="repository_owner",
            related_ids=missing,
        )
        return None, [diagnostic.as_dict()]
    return root, []


def _official_payload_diagnostics(
    final_payload: dict[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    kind = "ce_intermediate_validation_transaction"
    diagnostics: list[dict[str, Any]] = []
    for item in validate_ce_stage_payload(repo_root, final_payload):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_PAYLOAD_SCHEMA_INVALID",
                kind,
                "invalid",
                f"{item.code}: {item.message}",
                str(item.path or "$"),
                related_ids=[item.code],
            ).as_dict()
        )

    semantic = validate_document(final_payload, repo_root=repo_root, mode="full")
    for error in sorted(str(value) for value in semantic.get("schema_errors") or []):
        path = error.split(":", 1)[0] if ":" in error else "$"
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_PAYLOAD_SCHEMA_INVALID",
                kind,
                "invalid",
                error,
                path,
            ).as_dict()
        )
    violations = [
        item for item in semantic.get("violations") or [] if isinstance(item, dict)
    ]
    violations.sort(
        key=lambda item: (
            str(item.get("location") or "$"),
            str(item.get("rule_id") or ""),
            str(item.get("message") or ""),
        )
    )
    for item in violations:
        rule_id = str(item.get("rule_id") or "CE_SEMANTIC_VALIDATION_FAILED")
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_PAYLOAD_SEMANTIC_INVALID",
                kind,
                "invalid",
                str(item.get("message") or "Official CE semantic validation failed."),
                str(item.get("location") or "$"),
                related_ids=[rule_id],
            ).as_dict()
        )
    if not semantic.get("passed") and not diagnostics:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_PAYLOAD_SEMANTIC_INVALID",
                kind,
                "invalid",
                "Official CE Stage Payload validation failed without structured details.",
                "$",
            ).as_dict()
        )
    return sorted(diagnostics, key=_diagnostic_key)


def _invalid_transaction(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(diagnostics, key=_diagnostic_key)
    return {
        "transaction_status": "invalid",
        "fidelity_passed": False,
        "builder_ready": False,
        "carrier_statuses": {},
        "carriers": {},
        "diagnostics": ordered,
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
    repo_root: str | Path,
) -> dict[str, Any]:
    """Run the sole authoritative raw-input intermediate validation transaction.

    Serialized carriers are observational outputs only. The final Payload first
    passes the official CE Schema and semantic validators, then all four carriers
    are rederived from independent raw inputs in this same execution.
    """

    root, root_diagnostics = _resolve_repo_root(repo_root)
    if root is None:
        return _invalid_transaction(root_diagnostics)

    payload_diagnostics = _official_payload_diagnostics(final_payload, root)
    if payload_diagnostics:
        return _invalid_transaction(payload_diagnostics)

    carrier_validation_diagnostics: list[dict[str, Any]] = []

    identity_carrier = derive_architecture_identity_preservation(
        run_id=run_id,
        intake=intake,
        source_bundle=source_bundle,
        constructability_review=constructability_review,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(identity_carrier, repo_root=root)
    )

    review_carrier = derive_review_units_and_interrogation_results(
        run_id=run_id,
        intake=intake,
        constructability_review=constructability_review,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(review_carrier, repo_root=root)
    )

    dependency_carrier = derive_dependency_classification(
        run_id=run_id,
        review_carrier=review_carrier,
        constructability_review=constructability_review,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(dependency_carrier, repo_root=root)
    )

    strategy_carrier = derive_implementation_strategy_coverage(
        run_id=run_id,
        identity_carrier=identity_carrier,
        review_carrier=review_carrier,
        dependency_carrier=dependency_carrier,
        constructability_review=constructability_review,
        implementation_strategy_map=implementation_strategy_map,
        builder_executable_package=builder_executable_package,
        repo_root=root,
    )
    carrier_validation_diagnostics.extend(
        validate_carrier(strategy_carrier, repo_root=root)
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
