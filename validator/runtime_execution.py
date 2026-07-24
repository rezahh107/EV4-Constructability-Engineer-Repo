from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


class RuntimeExecutionBoundaryError(ValueError):
    """Raised when a runtime declaration attempts to masquerade as executed evidence."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class RepositoryExecutionResult:
    transaction_id: str
    claim_id: str
    subject_ref: str
    evaluator_id: str
    method_or_command: str
    target_identity: str
    execution_status: str
    exit_code: int
    captured_result: dict[str, Any]
    result_digest: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["limitations"] = list(self.limitations)
        return result


@dataclass(frozen=True)
class RuntimeExecutionBatch:
    transaction_id: str
    results: tuple[RepositoryExecutionResult, ...] = ()
    declarations: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "results": [item.as_dict() for item in self.results],
            "declarations": [dict(item) for item in self.declarations],
            "execution_available": bool(self.results),
        }


_EVALUATOR_BY_CLAIM = {
    "responsive_behavior": "ce-responsive-evaluator",
    "interaction_validation": "ce-interaction-evaluator",
    "accessibility": "ce-accessibility-evaluator",
    "QA": "ce-qa-evaluator",
}

_PROHIBITED_COMPLETED_RESULT_FIELDS = {
    "observed",
    "observed_layout",
    "accessible_name",
    "passed",
    "captured_result",
    "execution_status",
    "exit_code",
    "method_or_command",
    "result_digest",
    "limitations",
    "transaction_id",
}


def execution_transaction_id(
    *,
    architect_intake: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    review_draft: Mapping[str, Any],
    requests: Sequence[Mapping[str, Any]],
) -> str:
    seed = {
        "architect_intake": architect_intake,
        "source_bundle": source_bundle,
        "review_draft": review_draft,
        "runtime_execution_requests": [dict(item) for item in requests],
    }
    return f"ce-execution-{sha256_json(seed)[:32]}"


def _normalize_declaration(request: Mapping[str, Any]) -> dict[str, Any]:
    leaked = sorted(_PROHIBITED_COMPLETED_RESULT_FIELDS & set(request))
    if leaked:
        raise RuntimeExecutionBoundaryError(
            "Runtime declarations cannot inject observed or completed-result fields: "
            + ", ".join(leaked)
        )
    allowed = {
        "claim_id",
        "subject_ref",
        "evaluator_id",
        "target_identity",
        "input_ref",
        "required_inputs",
        "expected_assertions",
    }
    unknown = sorted(str(key) for key in request if key not in allowed)
    if unknown:
        raise RuntimeExecutionBoundaryError(
            "Unknown runtime declaration fields: " + ", ".join(unknown)
        )
    claim_id = request.get("claim_id")
    subject_ref = request.get("subject_ref")
    evaluator_id = request.get("evaluator_id")
    target_identity = request.get("target_identity")
    if not all(
        isinstance(value, str) and value
        for value in (claim_id, subject_ref, evaluator_id, target_identity)
    ):
        raise RuntimeExecutionBoundaryError("Runtime declaration identity is incomplete")
    if claim_id not in _EVALUATOR_BY_CLAIM:
        raise RuntimeExecutionBoundaryError(f"Unsupported runtime-only claim: {claim_id}")
    if evaluator_id != _EVALUATOR_BY_CLAIM[claim_id]:
        raise RuntimeExecutionBoundaryError(
            f"Evaluator {evaluator_id!r} is not the declared runner for {claim_id}"
        )
    # No actual Browser/Elementor/accessibility/QA runner exists in this repository.
    # input_ref is a specification carrier only and is never read as an observation.
    return {
        "declaration_kind": "RUNTIME_TEST_SPECIFICATION",
        "claim_id": str(claim_id),
        "subject_ref": str(subject_ref),
        "required_runner": str(evaluator_id),
        "target_identity": str(target_identity),
        "input_ref": request.get("input_ref"),
        "required_inputs": list(request.get("required_inputs") or []),
        "expected_assertions": list(request.get("expected_assertions") or []),
    }


def execute_runtime_requests(
    *,
    repo_root: Any,
    transaction_id: str,
    requests: Sequence[Mapping[str, Any]],
) -> RuntimeExecutionBatch:
    del repo_root
    declarations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in requests:
        if not isinstance(raw, Mapping):
            raise RuntimeExecutionBoundaryError("Runtime declaration must be an object")
        declaration = _normalize_declaration(raw)
        key = (declaration["claim_id"], declaration["subject_ref"])
        if key in seen:
            raise RuntimeExecutionBoundaryError(
                f"Duplicate runtime declaration for {key[0]}:{key[1]}"
            )
        seen.add(key)
        declarations.append(declaration)
    declarations.sort(key=lambda item: (item["subject_ref"], item["claim_id"]))
    return RuntimeExecutionBatch(
        transaction_id=transaction_id,
        results=(),
        declarations=tuple(declarations),
    )


def select_execution_result(
    batch: RuntimeExecutionBatch | None,
    *,
    transaction_id: str,
    claim_id: str,
    subject_ref: str,
) -> RepositoryExecutionResult | None:
    if batch is None or type(batch) is not RuntimeExecutionBatch:
        return None
    if batch.transaction_id != transaction_id:
        return None
    matches = [
        item
        for item in batch.results
        if item.transaction_id == transaction_id
        and item.claim_id == claim_id
        and item.subject_ref == subject_ref
    ]
    return matches[0] if len(matches) == 1 else None


__all__ = [
    "RepositoryExecutionResult",
    "RuntimeExecutionBatch",
    "RuntimeExecutionBoundaryError",
    "execute_runtime_requests",
    "execution_transaction_id",
    "select_execution_result",
]
