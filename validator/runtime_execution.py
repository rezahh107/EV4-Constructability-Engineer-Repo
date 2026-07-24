from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


class RuntimeExecutionBoundaryError(ValueError):
    """Raised when a runtime request crosses the repository execution boundary."""


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

_SCHEMA_BY_CLAIM = {
    "responsive_behavior": "ev4-ce-responsive-evaluation-target@1.0.0",
    "interaction_validation": "ev4-ce-interaction-evaluation-target@1.0.0",
    "accessibility": "ev4-ce-accessibility-evaluation-target@1.0.0",
    "QA": "ev4-ce-qa-evaluation-target@1.0.0",
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

_ALLOWED_REQUEST_FIELDS = {
    "claim_id",
    "subject_ref",
    "evaluator_id",
    "target_identity",
    "input_ref",
    "required_inputs",
    "expected_assertions",
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


def _duplicate_keys_forbidden(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeExecutionBoundaryError(
                f"Duplicate runtime target JSON key is forbidden: {key}"
            )
        result[key] = value
    return result


def _reject_non_json_constant(value: str) -> None:
    raise RuntimeExecutionBoundaryError(
        f"Non-standard runtime target JSON constant is forbidden: {value}"
    )


def _normalize_request(request: Mapping[str, Any]) -> dict[str, Any]:
    leaked = sorted(_PROHIBITED_COMPLETED_RESULT_FIELDS & set(request))
    if leaked:
        raise RuntimeExecutionBoundaryError(
            "Runtime requests cannot inject observed or completed-result fields: "
            + ", ".join(leaked)
        )
    unknown = sorted(str(key) for key in request if key not in _ALLOWED_REQUEST_FIELDS)
    if unknown:
        raise RuntimeExecutionBoundaryError(
            "Unknown runtime request fields: " + ", ".join(unknown)
        )
    claim_id = request.get("claim_id")
    subject_ref = request.get("subject_ref")
    evaluator_id = request.get("evaluator_id")
    target_identity = request.get("target_identity")
    if not all(
        isinstance(value, str) and value
        for value in (claim_id, subject_ref, evaluator_id, target_identity)
    ):
        raise RuntimeExecutionBoundaryError("Runtime request identity is incomplete")
    if claim_id not in _EVALUATOR_BY_CLAIM:
        raise RuntimeExecutionBoundaryError(f"Unsupported runtime-only claim: {claim_id}")
    if evaluator_id != _EVALUATOR_BY_CLAIM[claim_id]:
        raise RuntimeExecutionBoundaryError(
            f"Evaluator {evaluator_id!r} is not repository-owned for {claim_id}"
        )
    input_ref = request.get("input_ref")
    if input_ref is not None and (not isinstance(input_ref, str) or not input_ref):
        raise RuntimeExecutionBoundaryError("Runtime input_ref must be a non-empty string")
    for key in ("required_inputs", "expected_assertions"):
        value = request.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise RuntimeExecutionBoundaryError(f"Runtime {key} must be a string array")
    return {
        "declaration_kind": "RUNTIME_TEST_SPECIFICATION",
        "claim_id": str(claim_id),
        "subject_ref": str(subject_ref),
        "required_runner": str(evaluator_id),
        "evaluator_id": str(evaluator_id),
        "target_identity": str(target_identity),
        "input_ref": input_ref,
        "required_inputs": list(request.get("required_inputs") or []),
        "expected_assertions": list(request.get("expected_assertions") or []),
    }


def _resolve_input(repo_root: Path, input_ref: str) -> Path | None:
    try:
        root = repo_root.resolve(strict=True)
        candidate = Path(input_ref)
        path = candidate if candidate.is_absolute() else root / candidate
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _load_target(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_keys_forbidden,
            parse_constant=_reject_non_json_constant,
        )
    except RuntimeExecutionBoundaryError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeExecutionBoundaryError(
            f"Repository runtime target is not strict JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeExecutionBoundaryError("Repository runtime target must be a JSON object")
    return value


def _validate_binding(target: Mapping[str, Any], declaration: Mapping[str, Any]) -> None:
    claim_id = str(declaration["claim_id"])
    expected = {
        "schema_id": _SCHEMA_BY_CLAIM[claim_id],
        "claim_id": claim_id,
        "subject_ref": declaration["subject_ref"],
        "target_identity": declaration["target_identity"],
    }
    mismatched = [key for key, value in expected.items() if target.get(key) != value]
    if mismatched:
        raise RuntimeExecutionBoundaryError(
            "Runtime target binding mismatch: " + ", ".join(mismatched)
        )


def _run_responsive(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    cases = target.get("cases")
    if not isinstance(cases, list) or not cases:
        return False, {}, ["Responsive runtime target has no cases."]
    evaluated: list[dict[str, Any]] = []
    for item in cases:
        if not isinstance(item, Mapping):
            return False, {}, ["Responsive runtime case is not structured."]
        viewport = item.get("viewport")
        expected = item.get("expected_layout")
        observed = item.get("observed_layout")
        if not isinstance(viewport, str) or expected is None or observed is None:
            return False, {}, ["Responsive runtime case is incomplete."]
        evaluated.append(
            {
                "viewport": viewport,
                "expected_layout": expected,
                "observed_layout": observed,
                "passed": expected == observed,
            }
        )
    passed = all(item["passed"] for item in evaluated)
    return passed, {"cases": evaluated, "passed": passed}, list(target.get("limitations") or [])


def _run_interaction(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    transitions = target.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        return False, {}, ["Interaction runtime target has no transitions."]
    evaluated: list[dict[str, Any]] = []
    for item in transitions:
        if not isinstance(item, Mapping) or not isinstance(item.get("transition_id"), str):
            return False, {}, ["Interaction transition is not structured."]
        expected = item.get("expected_state")
        observed = item.get("observed_state")
        evaluated.append(
            {
                "transition_id": item["transition_id"],
                "expected_state": expected,
                "observed_state": observed,
                "passed": expected == observed,
            }
        )
    passed = all(item["passed"] for item in evaluated)
    return passed, {"transitions": evaluated, "passed": passed}, list(target.get("limitations") or [])


def _run_accessibility(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    nodes = target.get("interactive_nodes")
    if not isinstance(nodes, list) or not nodes:
        return False, {}, ["Accessibility runtime target has no interactive nodes."]
    evaluated: list[dict[str, Any]] = []
    for item in nodes:
        if not isinstance(item, Mapping):
            return False, {}, ["Accessibility runtime node is not structured."]
        node_id = item.get("node_id")
        role = item.get("role")
        name = item.get("accessible_name")
        keyboard_operable = item.get("keyboard_operable", True)
        passed = (
            all(isinstance(value, str) and value for value in (node_id, role, name))
            and keyboard_operable is True
        )
        evaluated.append(
            {
                "node_id": node_id,
                "role": role,
                "accessible_name": name,
                "keyboard_operable": keyboard_operable,
                "passed": passed,
            }
        )
    passed = all(item["passed"] for item in evaluated)
    return passed, {"interactive_nodes": evaluated, "passed": passed}, list(target.get("limitations") or [])


def _run_qa(target: Mapping[str, Any]) -> tuple[bool, dict[str, Any], list[str]]:
    assertions = target.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        return False, {}, ["QA runtime target has no assertions."]
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
    return passed, {"assertions": evaluated, "passed": passed}, list(target.get("limitations") or [])


_RUNNER_BY_CLAIM: dict[
    str, Callable[[Mapping[str, Any]], tuple[bool, dict[str, Any], list[str]]]
] = {
    "responsive_behavior": _run_responsive,
    "interaction_validation": _run_interaction,
    "accessibility": _run_accessibility,
    "QA": _run_qa,
}


def _execute_if_available(
    *,
    repo_root: Path,
    transaction_id: str,
    declaration: Mapping[str, Any],
) -> RepositoryExecutionResult | None:
    input_ref = declaration.get("input_ref")
    if not isinstance(input_ref, str) or not input_ref:
        return None
    path = _resolve_input(repo_root, input_ref)
    if path is None:
        return None
    target = _load_target(path)
    _validate_binding(target, declaration)
    claim_id = str(declaration["claim_id"])
    runner = _RUNNER_BY_CLAIM[claim_id]
    passed, captured, limitations = runner(target)
    captured = {
        **captured,
        "input_ref": input_ref,
        "input_bytes_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    return RepositoryExecutionResult(
        transaction_id=transaction_id,
        claim_id=claim_id,
        subject_ref=str(declaration["subject_ref"]),
        evaluator_id=str(declaration["evaluator_id"]),
        method_or_command=f"validator.runtime_execution:{runner.__name__}",
        target_identity=str(declaration["target_identity"]),
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
    declarations: list[dict[str, Any]] = []
    results: list[RepositoryExecutionResult] = []
    seen: set[tuple[str, str]] = set()
    for raw in requests:
        if not isinstance(raw, Mapping):
            raise RuntimeExecutionBoundaryError("Runtime request must be an object")
        declaration = _normalize_request(raw)
        key = (str(declaration["claim_id"]), str(declaration["subject_ref"]))
        if key in seen:
            raise RuntimeExecutionBoundaryError(
                f"Duplicate runtime request for {key[0]}:{key[1]}"
            )
        seen.add(key)
        declarations.append(declaration)
        result = _execute_if_available(
            repo_root=repo_root,
            transaction_id=transaction_id,
            declaration=declaration,
        )
        if result is not None:
            results.append(result)
    declarations.sort(key=lambda item: (item["subject_ref"], item["claim_id"]))
    results.sort(key=lambda item: (item.subject_ref, item.claim_id, item.evaluator_id))
    return RuntimeExecutionBatch(
        transaction_id=transaction_id,
        results=tuple(results),
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
