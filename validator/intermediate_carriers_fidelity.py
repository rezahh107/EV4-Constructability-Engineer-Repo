from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .intermediate_carriers_common import *  # noqa: F403


def validate_carrier(
    carrier: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    diagnostics: list[CarrierDiagnostic] = []
    kind = str(carrier.get("carrier_kind") or "unknown")
    if repo_root is not None:
        schema_path = Path(repo_root) / "schemas/ce_intermediate_validation_carriers.v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(carrier), key=lambda item: list(item.path)):
            path = "$" + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in error.path
            )
            diagnostics.append(
                _diag("CE_INTERMEDIATE_SCHEMA_INVALID", kind, "invalid", error.message, path)
            )
    if carrier.get("schema_id") != SCHEMA_ID or carrier.get("schema_version") != SCHEMA_VERSION:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_SCHEMA_IDENTITY_INVALID",
                kind,
                "invalid",
                "Carrier schema identity is invalid.",
                "$.schema_id",
            )
        )
    if carrier.get("owner_repository") != OWNER_REPOSITORY:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_OWNER_INVALID",
                kind,
                "invalid",
                "Carrier owner repository is invalid.",
                "$.owner_repository",
            )
        )
    if kind not in CARRIER_KINDS:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_KIND_INVALID",
                kind,
                "invalid",
                "Unsupported carrier_kind.",
                "$.carrier_kind",
            )
        )
    raw_diagnostics = [
        item for item in _as_list(carrier.get("diagnostics")) if isinstance(item, dict)
    ]
    if raw_diagnostics != sorted(raw_diagnostics, key=_diagnostic_key):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_DIAGNOSTIC_ORDER_INVALID",
                kind,
                "invalid",
                "Carrier diagnostics are not deterministically ordered.",
                "$.diagnostics",
            )
        )
    source_identities = [
        item for item in _as_list(carrier.get("source_identities")) if isinstance(item, dict)
    ]
    if source_identities != sorted(
        source_identities,
        key=lambda item: (
            str(item.get("source_kind", "")),
            str(item.get("identity", "")),
            str(item.get("sha256", "")),
        ),
    ):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_SOURCE_ORDER_INVALID",
                kind,
                "invalid",
                "Source identities are not deterministically ordered.",
                "$.source_identities",
            )
        )
    expected_status = _status(
        [
            CarrierDiagnostic(
                code=str(item.get("code", "")),
                carrier_kind=str(item.get("carrier_kind", kind)),
                severity_or_status=str(item.get("severity_or_status", "invalid")),
                message=str(item.get("message", "")),
                path_or_source_ref=str(item.get("path_or_source_ref", "$")),
                repair_owner=str(item.get("repair_owner", "ce")),
                related_ids=tuple(str(value) for value in _as_list(item.get("related_ids"))),
            )
            for item in raw_diagnostics
        ]
    )
    if carrier.get("status") != expected_status:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_STATUS_NOT_DERIVED",
                kind,
                "invalid",
                "Carrier status does not match its diagnostics.",
                "$.status",
            )
        )

    derived = _as_dict(carrier.get("derived_data"))
    if kind == "ce_review_units_and_interrogation_results":
        units = [
            item for item in _as_list(derived.get("review_units")) if isinstance(item, dict)
        ]
        unit_ids = [str(item.get("review_unit_id")) for item in units]
        source_refs = [str(item.get("architect_node_ref")) for item in units]
        duplicate_units = sorted({value for value in unit_ids if unit_ids.count(value) > 1})
        duplicate_sources = sorted(
            {value for value in source_refs if source_refs.count(value) > 1}
        )
        if duplicate_units:
            diagnostics.append(
                _diag(
                    "CE_REVIEW_UNIT_DUPLICATE_ID",
                    kind,
                    "invalid",
                    "Review-unit IDs must be unique.",
                    "$.derived_data.review_units",
                    related_ids=duplicate_units,
                )
            )
        if duplicate_sources:
            diagnostics.append(
                _diag(
                    "CE_REVIEW_UNIT_DUPLICATE_SOURCE_MAPPING",
                    kind,
                    "blocked",
                    "Review-unit source mappings must be unique.",
                    "$.derived_data.review_units",
                    related_ids=duplicate_sources,
                )
            )
    elif kind == "dependency_classification":
        classifications = [
            item
            for item in _as_list(derived.get("classifications"))
            if isinstance(item, dict)
        ]
        ids = [str(item.get("dependency_id")) for item in classifications]
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            diagnostics.append(
                _diag(
                    "CE_DEPENDENCY_DUPLICATE_CLASSIFICATION",
                    kind,
                    "invalid",
                    "Dependency classifications must be unique.",
                    "$.derived_data.classifications",
                    related_ids=duplicates,
                )
            )
        allowed = {
            "satisfied",
            "non_blocking_obligation",
            "blocking",
            "insufficient_evidence",
            "not_applicable",
        }
        invalid_classes = sorted(
            {
                str(item.get("classification"))
                for item in classifications
                if item.get("classification") not in allowed
            }
        )
        if invalid_classes:
            diagnostics.append(
                _diag(
                    "CE_DEPENDENCY_CLASSIFICATION_VALUE_INVALID",
                    kind,
                    "invalid",
                    "Dependency classification value is unsupported.",
                    "$.derived_data.classifications",
                    related_ids=invalid_classes,
                )
            )
        units = _strings(derived.get("review_unit_ids") or [])
        expected_pairs = {
            (unit_id, dimension) for unit_id in units for dimension in DEPENDENCY_RULES
        }
        observed_pairs = {
            (str(item.get("review_unit_id")), str(item.get("dependency_kind")))
            for item in classifications
        }
        missing_pairs = sorted(
            f"{unit}:{dimension}" for unit, dimension in expected_pairs - observed_pairs
        )
        if missing_pairs:
            diagnostics.append(
                _diag(
                    "CE_DEPENDENCY_CLASSIFICATION_COVERAGE_INCOMPLETE",
                    kind,
                    "invalid",
                    "A review unit is missing dependency classification dimensions.",
                    "$.derived_data.classifications",
                    related_ids=missing_pairs,
                )
            )
    elif kind == "implementation_strategy_coverage_result":
        unit_rows = [
            item
            for item in _as_list(derived.get("coverage_by_review_unit"))
            if isinstance(item, dict)
        ]
        unit_ids = [str(row.get("review_unit_id")) for row in unit_rows]
        duplicate_units = sorted({value for value in unit_ids if unit_ids.count(value) > 1})
        if duplicate_units:
            diagnostics.append(
                _diag(
                    "CE_STRATEGY_COVERAGE_DUPLICATE_REVIEW_UNIT",
                    kind,
                    "invalid",
                    "Strategy coverage rows must be unique by review unit.",
                    "$.derived_data.coverage_by_review_unit",
                    related_ids=duplicate_units,
                )
            )
    return [item.as_dict() for item in sorted(diagnostics, key=_diagnostic_key)]


def _compare_ce_payload_with_derived_carriers(
    *,
    payload: dict[str, Any],
    identity_carrier: dict[str, Any],
    review_carrier: dict[str, Any],
    dependency_carrier: dict[str, Any],
    strategy_carrier: dict[str, Any],
    builder_executable_package: dict[str, Any] | None,
) -> dict[str, Any]:
    kind = "final_ce_payload_fidelity"
    diagnostics: list[CarrierDiagnostic] = []
    carriers = [identity_carrier, review_carrier, dependency_carrier, strategy_carrier]
    run_ids = {carrier.get("run_id") for carrier in carriers}
    payload_run_id = _as_dict(payload.get("payload_identity")).get("run_id")
    if len(run_ids) != 1 or payload_run_id not in run_ids:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_RUN_ID_MISMATCH",
                kind,
                "invalid",
                "Payload and carriers must share one run_id.",
                "$.payload_identity.run_id",
            )
        )

    identity_projection = _as_dict(
        _as_dict(identity_carrier.get("derived_data")).get("payload_projection")
    )
    observed_identity = _as_dict(payload.get("architecture_identity"))
    for field, expected in identity_projection.items():
        if observed_identity.get(field) != expected:
            diagnostics.append(
                _diag(
                    "CE_INTERMEDIATE_FIDELITY_ARCHITECTURE_IDENTITY_MISMATCH",
                    kind,
                    "blocked",
                    f"Payload architecture_identity.{field} differs from Carrier 1.",
                    f"$.architecture_identity.{field}",
                )
            )

    review_projection = _as_dict(
        _as_dict(review_carrier.get("derived_data")).get("payload_projection")
    )
    if _normalized_review_nodes(_as_dict(payload.get("constructability_review"))) != review_projection.get("reviewed_nodes"):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_REVIEWED_NODES_MISMATCH",
                kind,
                "blocked",
                "Payload reviewed_nodes differ from Carrier 2.",
                "$.constructability_review.reviewed_nodes",
            )
        )
    if observed_identity.get("review_unit_traces") != review_projection.get("review_unit_traces"):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_REVIEW_TRACES_MISMATCH",
                kind,
                "blocked",
                "Payload review_unit_traces differ from Carrier 2.",
                "$.architecture_identity.review_unit_traces",
            )
        )

    dependency_projection = _as_dict(
        _as_dict(dependency_carrier.get("derived_data")).get("payload_projection")
    )
    observed_blockers = _strings(
        _as_dict(payload.get("constructability_review")).get("blocking_dependencies") or []
    )
    if observed_blockers != _strings(dependency_projection.get("blocking_dependencies") or []):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_BLOCKING_DEPENDENCIES_MISMATCH",
                kind,
                "blocked",
                "Payload blocking_dependencies differ from Carrier 3.",
                "$.constructability_review.blocking_dependencies",
            )
        )
    unresolved_ids = set(_unknown_ids(payload.get("unresolved_evidence")))
    required_unresolved = set(
        _strings(dependency_projection.get("required_unresolved_ids") or [])
    )
    if not required_unresolved.issubset(unresolved_ids):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_UNRESOLVED_DEPENDENCY_OMITTED",
                kind,
                "blocked",
                "Payload unresolved_evidence omits Carrier 3 dependencies.",
                "$.unresolved_evidence",
                related_ids=sorted(required_unresolved - unresolved_ids),
            )
        )
    evidence_ids = {
        item.get("id")
        for item in _as_list(payload.get("evidence_register"))
        if isinstance(item, dict)
    }
    required_evidence = set(
        _strings(dependency_projection.get("required_evidence_refs") or [])
    )
    if not required_evidence.issubset(evidence_ids):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_EVIDENCE_REF_OMITTED",
                kind,
                "blocked",
                "Payload evidence_register omits evidence used by Carrier 3.",
                "$.evidence_register",
                related_ids=sorted(required_evidence - evidence_ids),
            )
        )

    strategy_projection = _as_dict(
        _as_dict(strategy_carrier.get("derived_data")).get("payload_projection")
    )
    expected_map = strategy_projection.get("implementation_strategy_map")
    observed_map = payload.get("implementation_strategy_map")
    if canonical_json_bytes(observed_map) != canonical_json_bytes(expected_map):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_STRATEGY_MAP_MISMATCH",
                kind,
                "blocked",
                "Payload implementation_strategy_map differs from Carrier 4.",
                "$.implementation_strategy_map",
            )
        )
    expected_reason = strategy_projection.get("builder_package_not_emitted_reason")
    if payload.get("builder_package_not_emitted_reason") != expected_reason:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_STRATEGY_ABSENCE_REASON_MISMATCH",
                kind,
                "blocked",
                "Payload Builder-package non-emission reason differs from Carrier 4 projection.",
                "$.builder_package_not_emitted_reason",
            )
        )
    strategy_unresolved = set(
        _strings(strategy_projection.get("required_unresolved_ids") or [])
    )
    if not strategy_unresolved.issubset(unresolved_ids):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_STRATEGY_UNRESOLVED_OMITTED",
                kind,
                "blocked",
                "Payload unresolved_evidence omits Carrier 4 items.",
                "$.unresolved_evidence",
                related_ids=sorted(strategy_unresolved - unresolved_ids),
            )
        )

    strategy_ready = strategy_carrier.get("status") == "complete"
    if strategy_ready:
        if payload.get("builder_package_emitted") is not True:
            diagnostics.append(
                _diag(
                    "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_EMISSION_MISMATCH",
                    kind,
                    "blocked",
                    "A complete Strategy carrier requires Builder package emission.",
                    "$.builder_package_emitted",
                )
            )
        if payload.get("builder_package_not_emitted_reason") is not None:
            diagnostics.append(
                _diag(
                    "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_REASON_PRESENT_WHEN_READY",
                    kind,
                    "blocked",
                    "A ready Builder package cannot carry a non-emission reason.",
                    "$.builder_package_not_emitted_reason",
                )
            )
        if not isinstance(builder_executable_package, dict) or canonical_json_bytes(
            payload.get("builder_executable_package")
        ) != canonical_json_bytes(builder_executable_package):
            diagnostics.append(
                _diag(
                    "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_MISMATCH",
                    kind,
                    "blocked",
                    "Final Payload Builder package differs from the raw package validated in this transaction.",
                    "$.builder_executable_package",
                )
            )
    else:
        if payload.get("builder_package_emitted") is not False:
            diagnostics.append(
                _diag(
                    "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_EMISSION_MISMATCH",
                    kind,
                    "blocked",
                    "An incomplete Strategy carrier requires Builder package non-emission.",
                    "$.builder_package_emitted",
                )
            )
        if payload.get("builder_executable_package") is not None:
            diagnostics.append(
                _diag(
                    "CE_INTERMEDIATE_FIDELITY_BUILDER_PACKAGE_PRESENT_WHEN_NOT_READY",
                    kind,
                    "blocked",
                    "An incomplete Strategy carrier forbids a Builder package in the final Payload.",
                    "$.builder_executable_package",
                )
            )

    candidates = {
        _as_dict(_as_dict(identity_carrier.get("derived_data")).get("selected_candidate")).get("expected"),
        _as_dict(payload.get("architecture_identity")).get("selected_candidate_id"),
        _as_dict(payload.get("constructability_review")).get("selected_candidate_id"),
        _as_dict(payload.get("implementation_strategy_map")).get("selected_candidate_id"),
        _as_dict(payload.get("builder_executable_package")).get("selected_candidate_id"),
    }
    candidates.discard(None)
    if len(candidates) != 1:
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_SELECTED_CANDIDATE_MISMATCH",
                kind,
                "blocked",
                "Selected candidate identity is inconsistent across final surfaces.",
                "$.architecture_identity.selected_candidate_id",
                related_ids=[str(value) for value in candidates],
            )
        )

    incomplete = [
        carrier.get("carrier_kind")
        for carrier in carriers
        if carrier.get("status") != "complete"
    ]
    if incomplete and (
        payload.get("payload_status") == "complete"
        or payload.get("builder_package_emitted") is True
    ):
        diagnostics.append(
            _diag(
                "CE_INTERMEDIATE_FIDELITY_FALSE_COMPLETE",
                kind,
                "blocked",
                "Final Payload claims completion while an intermediate carrier is not complete.",
                "$.payload_status",
                related_ids=[str(value) for value in incomplete],
            )
        )

    ordered = sorted(diagnostics, key=_diagnostic_key)
    return {
        "passed": not ordered,
        "diagnostics": [item.as_dict() for item in ordered],
        "carrier_statuses": {
            str(carrier.get("carrier_kind")): carrier.get("status")
            for carrier in carriers
        },
    }


def _diagnose_ce_payload_against_serialized_carriers(
    *,
    payload: dict[str, Any],
    identity_carrier: dict[str, Any],
    review_carrier: dict[str, Any],
    dependency_carrier: dict[str, Any],
    strategy_carrier: dict[str, Any],
) -> dict[str, Any]:
    """Non-authoritative debugging comparison for serialized carrier artifacts."""

    result = _compare_ce_payload_with_derived_carriers(
        payload=payload,
        identity_carrier=identity_carrier,
        review_carrier=review_carrier,
        dependency_carrier=dependency_carrier,
        strategy_carrier=strategy_carrier,
        builder_executable_package=_as_dict(payload.get("builder_executable_package")) or None,
    )
    return {
        "diagnostic_match": bool(result.get("passed")),
        "authoritative": False,
        "diagnostics": result.get("diagnostics") or [],
        "carrier_statuses": result.get("carrier_statuses") or {},
    }


__all__ = ["validate_carrier"]
