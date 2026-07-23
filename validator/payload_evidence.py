from __future__ import annotations
import copy
from typing import Any, Mapping
from .claim_policy_registry import policy_projection
from .payload_projection import EVALUATOR_ID, sha256_json

def _authority_state(row: Mapping[str, Any]) -> str:
    status = str(row.get('status'))
    if status == 'satisfied':
        modes = {str(item.get('mode')) for item in row.get('evidence_records') or [] if isinstance(item, Mapping)}
        return 'ATTRIBUTED_SUPPORTED' if modes == {'ATTRIBUTED_ENGINEERING_JUDGMENT'} else 'VERIFIED'
    return {'not_applicable': 'NOT_APPLICABLE', 'insufficient_evidence': 'INSUFFICIENT_EVIDENCE', 'downstream_validation_required': 'DOWNSTREAM_VALIDATION_REQUIRED', 'architect_decision_required': 'ARCHITECT_DECISION_REQUIRED', 'invalid': 'REJECTED_PROVENANCE_MISMATCH', 'blocked': 'UNVERIFIED'}.get(status, 'UNVERIFIED')

def _authority_resolution(dependency_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in dependency_result.get('rows') or []:
        if not isinstance(row, Mapping):
            continue
        claim_id = str(row['claim_id'])
        result.append({'claim_ref': f"{row['subject_ref']}:{claim_id}", 'claim_id': claim_id, 'subject_ref': str(row['subject_ref']), 'policy': policy_projection(claim_id), 'submitted_judgment': None, 'verified_evidence': [str(value) for value in row.get('evidence_refs') or []], 'resolved_state': _authority_state(row), 'limitations': [str(value) for value in row.get('limitations') or []], 'downstream_obligation': copy.deepcopy(row.get('downstream_obligation'))})
    return result

def _evidence_register(dependency_result: Mapping[str, Any], payload_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in dependency_result.get('evidence_records') or []:
        if not isinstance(item, Mapping):
            continue
        mode = str(item.get('mode') or 'DOWNSTREAM_TEST_OBLIGATION')
        source: dict[str, Any]
        verification_status: str
        if mode == 'VERIFIED_ARTIFACT':
            source = {'type': 'repo_path', 'reference': str(item.get('source_ref') or 'unknown'), 'bytes_sha256': str(item.get('source_bytes_sha256') or '')}
            verification_status = 'VERIFIED'
        elif mode == 'VERIFIED_TOOL_EXECUTION':
            source = {'type': 'tool_execution', 'reference': str(item.get('target_identity') or 'unknown'), 'bytes_sha256': str(item.get('result_digest') or '')}
            verification_status = 'VERIFIED'
        elif mode == 'VERIFIED_ARCHITECT_DECISION':
            source = {'type': 'architect_intake', 'reference': str(item.get('decision_ref') or item.get('claim_id') or 'unknown'), 'bytes_sha256': str(item.get('source_digest') or '')}
            verification_status = 'VERIFIED'
        elif mode == 'ATTRIBUTED_ENGINEERING_JUDGMENT':
            source = {'type': 'attributed_judgment', 'reference': str(item.get('reviewer_identity') or 'constructability_engineer')}
            verification_status = 'ATTRIBUTED'
        else:
            source = {'type': 'downstream_obligation', 'reference': f"{item.get('subject_ref')}:{item.get('claim_id')}"}
            verification_status = 'UNPROVEN'
        evidence_id = str(item.get('evidence_id') or sha256_json(item))
        result.append({'evidence_id': evidence_id, 'claim_refs': [f"{item.get('subject_ref')}:{item.get('claim_id')}"], 'subject_ref': str(item.get('subject_ref') or 'unknown'), 'assurance_kind': mode, 'source': source, 'producer': {'kind': {'VERIFIED_ARTIFACT': 'CE_VERIFIED_ADAPTER', 'VERIFIED_TOOL_EXECUTION': 'CE_TOOL_EXECUTION_ADAPTER', 'VERIFIED_ARCHITECT_DECISION': 'CE_VERIFIED_ADAPTER', 'ATTRIBUTED_ENGINEERING_JUDGMENT': 'CE_ATTRIBUTION_ADAPTER', 'DOWNSTREAM_TEST_OBLIGATION': 'CE_OBLIGATION_ADAPTER'}.get(mode, 'CE_OBLIGATION_ADAPTER'), 'tool_or_method': EVALUATOR_ID}, 'target_binding': {'payload_id': payload_id, 'subject_ref': str(item.get('subject_ref') or 'unknown')}, 'verification': {'method': str(item.get('verification') or 'deterministic_evaluation'), 'status': verification_status}, 'limitations': [str(value) for value in item.get('limitations') or []]})
    return result

def _diagnostic_unresolved(*results: Mapping[str, Any]) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        for item in result.get('diagnostics') or []:
            if not isinstance(item, Mapping):
                continue
            code = str(item.get('code') or 'CE_EVALUATION_INCOMPLETE')
            key = (str(result.get('result_kind') or 'evaluation'), code)
            if key in seen:
                continue
            seen.add(key)
            unresolved.append({'unresolved_id': f'unresolved-{sha256_json(key)[:16]}', 'owner': 'constructability_engineer', 'reason': code, 'state': 'insufficient_evidence', 'details': copy.deepcopy(dict(item))})
    return unresolved

def _architect_unresolved(architect_intake: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, item in enumerate(architect_intake.get('unresolved_evidence') or []):
        if not isinstance(item, Mapping):
            continue
        unresolved_id = str(item.get('unresolved_id') or f'architect-unresolved-{index + 1}')
        result.append({'unresolved_id': unresolved_id, 'owner': str(item.get('owner') or 'architect'), 'reason': str(item.get('reason') or 'Architect evidence remains unresolved.'), 'state': str(item.get('state') or 'insufficient_evidence'), 'evidence_refs': [str(value) for value in item.get('evidence_refs') or []], 'source': 'verified_architect_intake'})
    return result
