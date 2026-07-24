from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


class RuntimeExecutionBoundaryError(ValueError):
    """Raised when a runtime request attempts to inject a completed result."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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
        value = asdict(self)
        value["limitations"] = list(self.limitations)
        return value


@dataclass(frozen=True)
class RuntimeExecutionBatch:
    transaction_id: str
    results: tuple[RepositoryExecutionResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "results": [item.as_dict() for item in self.results],
        }


_EVALUATOR_BY_CLAIM = {
    "responsive_behavior": "ce-responsive-evaluator",
    "accessibility": "ce-accessibility-evaluator",
    "QA": "ce-qa-evaluator",
}

_SCHEMA_BY_CLAIM = {
    "responsive_behavior": "ev4-ce-responsive-evaluation-target@1.0.0",
    "accessibility": "ev4-ce-accessibility-evaluation-target@1.0.0",
    "QA": "ev4-ce-qa-evaluation-target@1.0.0",
}

_PROHIBITED_COMPLETED_RESULT_FIELDS = {
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


def _resolve_repo_file(repo_root: Path, source_ref: str) -> Path:
    root = repo_root.resolve(strict=True)
    candidate = Path(source_ref)
    path = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise RuntimeExecutionBoundaryError(
            f"Runtime evaluator input is unavailable inside the repository: {source_ref}"
        ) from exc
    if not resolved.is_file():
        raise RuntimeExecutionBoundaryError(
            f"Runtime evaluator input is not a file: {source_ref}"
        )
    return resolved


def _load_observation(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeExecutionBoundaryError(
            "Repository runtime adapter requires a structured JSON observation"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeExecutionBoundaryError(
            "Repository runtime observation must be a JSON object"
        )
    return value


def _validate_binding(
    observation: Mapping[str, Any],
    *,
    claim_id: str,
    subject_ref: str,
    target_identity: str,
) -> None:
    if observation.get("schema_id") != _SCHEMA_BY_CLAIM[claim_id]:
        raise RuntimeExecutionBoundaryError(
            f"Unsupported runtime observation Schema for {claim_id}"
        )
    if observation.get("claim_id") != claim_id:
        raise RuntimeExecutionBoundaryError("Runtime observation claim binding mismatch")
    if observation.get("subject_ref") != subject_ref:
        raise RuntimeExecutionBoundaryError("Runtime observation subject binding mismatch")
    if observation.get("target_identity") != target_identity:
        raise RuntimeExecutionBoundaryError("Runtime observation target binding mismatch")


def _run_responsive(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    cases = target.get("cases")
    if not isinstance(cases, list) or not cases:
        return False, {}, ["Responsive evaluation target has no cases."]
    evaluated: list[dict[str, Any]] = []
    for item in cases:
        if not isinstance(item, Mapping):
            return False, {}, ["Responsive evaluation case is not structured."]
        viewport = item.get("viewport")
        expected = item.get("expected_layout")
        observed = item.get("observed_layout")
        if not isinstance(viewport, str) or expected is None or observed is None:
            return False, {}, ["Responsive evaluation case is incomplete."]
        evaluated.append(
            {
                "viewport": viewport,
                "expected_layout": expected,
                "observed_layout": observed,
                "passed": expected == observed,
            }
        )
    passed = all(item["passed"] for item in evaluated)
    return passed, {"cases": evaluated, "passed": passed}, list(
        target.get("limitations") or []
    )


def _run_accessibility(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    nodes = target.get("interactive_nodes")
    if not isinstance(nodes, list) or not nodes:
        return False, {}, ["Accessibility evaluation target has no interactive nodes."]
    evaluated: list[dict[str, Any]] = []
    for item in nodes:
        if not isinstance(item, Mapping):
            return False, {}, ["Accessibility target node is not structured."]
        node_id = item.get("node_id")
        role = item.get("role")
        name = item.get("accessible_name")
        passed = all(isinstance(value, str) and value for value in (node_id, role, name))
        evaluated.append(
            {
                "node_id": node_id,
                "role": role,
                "accessible_name": name,
                "passed": passed,
            }
        )
    passed = all(item["passed"] for item in evaluated)
    return passed, {"interactive_nodes": evaluated, "passed": passed}, list(
        target.get("limitations") or []
    )


def _run_qa(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    assertions = target.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        return False, {}, ["QA evaluation target has no assertions."]
    evaluated: list[dict[str, Any]] = []
    for item in assertions:
        if not isinstance(item, Mapping) or not isinstance(item.get("assertion_id"), str):
            return False, {}, ["QA assertion is not structured."]
        expected = item.get("expected")
        observed = item.get("observed")
        evaluated.append(
            {
                "assertion_id": item["assertion_id"],
                "expected": expected,
                "observed": observed,
                "passed": expected == observed,
            }
        )
    passed = all(item["passed"] for item in evaluated)
    return passed, {"assertions": evaluated, "passed": passed}, list(
        target.get("limitations") or []
    )


_RUNNER_BY_CLAIM = {
    "responsive_behavior": _run_responsive,
    "accessibility": _run_accessibility,
    "QA": _run_qa,
}


def _execute_one(
    *,
    repo_root: Path,
    transaction_id: str,
    request: Mapping[str, Any],
) -> RepositoryExecutionResult:
    leaked = sorted(_PROHIBITED_COMPLETED_RESULT_FIELDS & set(request))
    if leaked:
        raise RuntimeExecutionBoundaryError(
            "Runtime execution requests cannot inject completed-result fields: "
            + ", ".join(leaked)
        )
    claim_id = request.get("claim_id")
    subject_ref = request.get("subject_ref")
    evaluator_id = request.get("evaluator_id")
    target_identity = request.get("target_identity")
    input_ref = request.get("input_ref")
    if not all(
        isinstance(value, str) and value
        for value in (claim_id, subject_ref, evaluator_id, target_identity, input_ref)
    ):
        raise RuntimeExecutionBoundaryError("Runtime execution request identity is incomplete")
    if claim_id not in _EVALUATOR_BY_CLAIM:
        raise RuntimeExecutionBoundaryError(f"Unsupported runtime-only claim: {claim_id}")
    if evaluator_id != _EVALUATOR_BY_CLAIM[claim_id]:
        raise RuntimeExecutionBoundaryError(
            f"Evaluator {evaluator_id!r} is not repository-owned for {claim_id}"
        )

    path = _resolve_repo_file(repo_root, input_ref)
    observation = _load_observation(path)
    _validate_binding(
        observation,
        claim_id=claim_id,
        subject_ref=subject_ref,
        target_identity=target_identity,
    )
    passed, captured, limitations = _RUNNER_BY_CLAIM[claim_id](observation)
    captured = {
        **captured,
        "input_ref": str(input_ref),
        "input_bytes_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    return RepositoryExecutionResult(
        transaction_id=transaction_id,
        claim_id=claim_id,
        subject_ref=subject_ref,
        evaluator_id=evaluator_id,
        method_or_command=(
            f"validator.runtime_execution:{_RUNNER_BY_CLAIM[claim_id].__name__}"
        ),
        target_identity=target_identity,
        execution_status="success" if passed else "failed",
        exit_code=0 if passed else 1,
        captured_result=captured,
        result_digest=sha256_json(captured),
        limitations=tuple(str(item) for item in limitations),
    )


def execute_runtime_requests(
    *,
    repo_root: Path,
    transaction_id: str,
    requests: Sequence[Mapping[str, Any]],
) -> RuntimeExecutionBatch:
    seen: set[tuple[str, str]] = set()
    results: list[RepositoryExecutionResult] = []
    for raw in requests:
        if not isinstance(raw, Mapping):
            raise RuntimeExecutionBoundaryError(
                "Runtime execution request must be a mapping"
            )
        key = (str(raw.get("claim_id")), str(raw.get("subject_ref")))
        if key in seen:
            raise RuntimeExecutionBoundaryError(
                f"Duplicate runtime execution request for {key[0]}:{key[1]}"
            )
        seen.add(key)
        results.append(
            _execute_one(
                repo_root=repo_root,
                transaction_id=transaction_id,
                request=raw,
            )
        )
    results.sort(key=lambda item: (item.subject_ref, item.claim_id, item.evaluator_id))
    return RuntimeExecutionBatch(transaction_id=transaction_id, results=tuple(results))


def select_execution_result(
    batch: RuntimeExecutionBatch | None,
    *,
    transaction_id: str,
    claim_id: str,
    subject_ref: str,
) -> RepositoryExecutionResult | None:
    if batch is None:
        return None
    if type(batch) is not RuntimeExecutionBatch or batch.transaction_id != transaction_id:
        return None
    matches = [
        item
        for item in batch.results
        if item.claim_id == claim_id
        and item.subject_ref == subject_ref
        and item.transaction_id == transaction_id
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
