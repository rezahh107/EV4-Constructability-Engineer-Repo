from __future__ import annotations
import copy
import hashlib
import json
from typing import Any, Mapping
from .claim_policy_registry import CLAIM_POLICIES, policy_projection
CE_REPOSITORY = "rezahh107/EV4-Constructability-Engineer-Repo"
REVIEW_SCHEMA_ID = "ev4-constructability-review@1.1.0"
PAYLOAD_SCHEMA_ID = "ev4-ce-stage-payload@1.1.0"
PAYLOAD_SCHEMA_VERSION = "1.1.0"
BUILDER_PACKAGE_SCHEMA_ID = "ev4-builder-executable-package@1.0.0"
EVALUATOR_ID = "ev4-ce-deterministic-evaluator"
EVALUATOR_VERSION = "2.0.0"

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def _draft_nodes(review_draft: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item['node_id']): dict(item) for item in review_draft.get('reviewed_nodes') or [] if isinstance(item, Mapping) and isinstance(item.get('node_id'), str)}

def _row_map(dependency_result: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in dependency_result.get('rows') or []:
        if not isinstance(item, Mapping):
            continue
        subject = item.get('subject_ref')
        claim = item.get('claim_id')
        if isinstance(subject, str) and isinstance(claim, str):
            result[subject, claim] = dict(item)
    return result

def _proof_ids(row: Mapping[str, Any] | None) -> list[str]:
    if not row or row.get('status') != 'satisfied':
        return []
    return [str(value) for value in row.get('evidence_refs') or []]

def _required_value(row: Mapping[str, Any] | None, *, responsive: bool=False) -> bool | str | None:
    if row is None:
        return 'not_applicable' if responsive else None
    if responsive:
        return 'evidence_backed' if row.get('status') == 'satisfied' else 'blocked'
    return row.get('status') == 'satisfied'

def _node_status(node_id: str, dependency_result: Mapping[str, Any], strategy_result: Mapping[str, Any]) -> tuple[str, str | None]:
    blockers = [str(value) for value in dependency_result.get('blocking_dependencies') or [] if str(value).startswith(f'{node_id}:')]
    amendment_nodes = set((str(value) for value in strategy_result.get('architect_amendment_nodes') or []))
    if node_id in amendment_nodes:
        return ('needs_architect_amendment', 'Architect permission is required for class/structure change.')
    if blockers:
        return ('needs_user_evidence', '; '.join(blockers))
    if strategy_result.get('status') != 'complete':
        return ('blocked', 'Implementation strategy coverage is incomplete.')
    return ('executable_ready', None)

def _derived_actions(review_draft: Mapping[str, Any], strategy_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    hidden_paths = [str(value) for value in strategy_result.get('hidden_builder_decisions') or []]
    result: list[dict[str, Any]] = []
    for index, item in enumerate(review_draft.get('builder_action_proposals') or []):
        if not isinstance(item, Mapping):
            continue
        prefix = f'$.actions[{index}].parameters'
        result.append({'action_id': str(item.get('action_id') or f'action-{index + 1}'), 'action_type': str(item.get('action_type') or 'unknown'), 'target_node': str(item.get('target_node') or 'unknown'), 'parameters': copy.deepcopy(dict(item.get('parameters') or {})), 'requires_decision': any((path.startswith(prefix) for path in hidden_paths))})
    return result

def _strategy_map(review_draft: Mapping[str, Any], strategy_result: Mapping[str, Any], *, review_id: str, selected_candidate_id: str, payload_id: str) -> dict[str, Any] | None:
    proposal = review_draft.get('implementation_strategy_proposal')
    if not isinstance(proposal, Mapping):
        return None
    result = copy.deepcopy(dict(proposal))
    result['strategy_map_id'] = str(result.get('strategy_map_id') or f'strategy-{payload_id[-16:]}')
    result['review_ref'] = review_id
    result['selected_candidate_id'] = selected_candidate_id
    amendment_nodes = set((str(value) for value in strategy_result.get('architect_amendment_nodes') or []))
    hidden_paths = [str(value) for value in strategy_result.get('hidden_builder_decisions') or []]
    strategies = result.get('strategies')
    if isinstance(strategies, list):
        for index, strategy in enumerate(strategies):
            if not isinstance(strategy, dict):
                continue
            prefix = f'$.strategies[{index}]'
            strategy['builder_decisions_required'] = sum((path.startswith(prefix) for path in hidden_paths))
            strategy['architect_amendment_required'] = str(strategy.get('node_id')) in amendment_nodes
    return result
