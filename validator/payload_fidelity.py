from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .intermediate_results import evaluate_all
from .payload_assembler import assemble_ce_stage_payload, canonical_bytes


class PayloadFidelityError(ValueError):
    """Raised when persisted output differs from independently recomputed CE results."""


def recompute_expected_payload(
    *,
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    repo_root: Path,
    runtime_results: Sequence[Mapping[str, Any]] = (),
    input_metadata: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    results = evaluate_all(
        architect_intake,
        source_bundle,
        review_draft,
        repo_root=repo_root,
        runtime_results=runtime_results,
    )
    payload = assemble_ce_stage_payload(
        results["identity_result"],
        results["review_result"],
        results["dependency_result"],
        results["strategy_result"],
        {
            "architect_intake": architect_intake,
            "source_bundle": source_bundle,
            "review_draft": review_draft,
            "runtime_results": list(runtime_results),
            "input_metadata": dict(input_metadata or {}),
        },
    )
    return payload, results


def compare_persisted_payload(
    persisted_payload: Mapping[str, Any], expected_payload: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if canonical_bytes(persisted_payload) == canonical_bytes(expected_payload):
        return []
    diagnostics: list[dict[str, Any]] = []
    surfaces = (
        "payload_status",
        "architecture_identity",
        "constructability_review",
        "implementation_strategy_map",
        "builder_executable_package",
        "builder_package_emitted",
        "authority_resolution",
        "unresolved_evidence",
        "downstream_test_obligations",
        "boundary_assertions",
    )
    for key in surfaces:
        if canonical_bytes(persisted_payload.get(key)) != canonical_bytes(expected_payload.get(key)):
            diagnostics.append(
                {
                    "code": "CE_PAYLOAD_FIDELITY_MISMATCH",
                    "path": f"$.{key}",
                    "message": f"Persisted {key} differs from deterministic recomputation.",
                }
            )
    if not diagnostics:
        diagnostics.append(
            {
                "code": "CE_PAYLOAD_FIDELITY_MISMATCH",
                "path": "$",
                "message": "Persisted payload differs from deterministic recomputation.",
            }
        )
    return diagnostics


def validate_payload_fidelity(
    persisted_payload: Mapping[str, Any],
    *,
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    repo_root: Path,
    runtime_results: Sequence[Mapping[str, Any]] = (),
    input_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected, results = recompute_expected_payload(
        architect_intake=architect_intake,
        source_bundle=source_bundle,
        review_draft=review_draft,
        repo_root=repo_root,
        runtime_results=runtime_results,
        input_metadata=input_metadata,
    )
    diagnostics = compare_persisted_payload(persisted_payload, expected)
    return {
        "passed": not diagnostics,
        "diagnostics": diagnostics,
        "expected_payload": expected,
        "evaluation_results": results,
    }


def validate_export_fidelity(
    export: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    payload = (
        export.get("final_stage_bundle", {}).get("payload", {}).get("data")
        if isinstance(export.get("final_stage_bundle"), Mapping)
        else None
    )
    if not isinstance(payload, Mapping):
        return {
            "passed": False,
            "diagnostics": [
                {
                    "code": "CE_EXPORT_FIDELITY_PAYLOAD_MISSING",
                    "path": "$.final_stage_bundle.payload.data",
                    "message": "Export does not contain a CE Payload to compare.",
                }
            ],
        }
    return validate_payload_fidelity(payload, **kwargs)


def assert_payload_fidelity(*args: Any, **kwargs: Any) -> None:
    report = validate_payload_fidelity(*args, **kwargs)
    if report["diagnostics"]:
        first = report["diagnostics"][0]
        raise PayloadFidelityError(f"{first['code']} at {first['path']}: {first['message']}")


def cloned(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))
