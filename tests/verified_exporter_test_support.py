from __future__ import annotations
import copy
import json
from pathlib import Path
import validator.project_gate_exporter as legacy_exporter
import validator.verified_project_gate_exporter as verified_exporter
from exporter_test_support import _provenance, _real_source_pair, _write_json

def _install_test_provenance() -> None:
    inspect = lambda repo_root, ignored_paths=(): _provenance(dirty=False)
    verified_exporter.inspect_git_provenance = inspect
    legacy_exporter.inspect_git_provenance = inspect

def _intake_context(intake_path: Path) -> tuple[dict, list[dict], str, list[str], list[str], list[str]]:
    intake = json.loads(intake_path.read_text(encoding='utf-8'))
    structure = intake.get('structure_projection') or {}
    nodes = [dict(item) for item in structure.get('nodes') or [] if isinstance(item, dict)]
    selected = intake.get('selected_architecture') or {}
    intent = intake.get('architect_intent_preserved') or {}
    candidate = str(selected.get('selected_candidate_id') or 'unknown')
    classes = [str(value) for value in (intent.get('class_intent') or {}).get('approved_class_names') or []]
    unknowns = [str(item['unresolved_id']) for item in intake.get('unresolved_evidence') or [] if isinstance(item, dict) and isinstance(item.get('unresolved_id'), str)]
    forbidden = [str(value) for value in intake.get('forbidden_work') or []]
    return (intake, nodes, candidate, classes, unknowns, forbidden)

def _draft(intake_path: Path, *, claims: list[dict] | None=None) -> dict:
    _, nodes, candidate, classes, unknowns, forbidden = _intake_context(intake_path)
    reviewed_nodes = []
    strategies = []
    actions = []
    for index, source_node in enumerate(nodes):
        node_id = str(source_node.get('source_node_id') or source_node.get('node_id'))
        is_root = index == 0
        reviewed_nodes.append({'node_id': node_id, 'node_type': str(source_node.get('node_kind') or 'implementation_node'), 'proposed_action': 'configure layout' if is_root else 'preserve existing', 'engineering_rationale': 'Derive a bounded CE layout from explicit retained Architect anchors.' if is_root else 'Preserve the accepted Architect node without technical mutation.', 'requested_claims': copy.deepcopy(claims or []) if is_root else [], 'candidate_source_refs': [], 'claim_semantics': {}, 'assumptions': ['The accepted Architect structure remains unchanged.'], 'limitations': [], 'reversible_if_wrong': True, 'requires_class_change': False, 'requires_structure_change': False, 'architect_decomposition_permission': False})
        strategies.append({'strategy_id': f'STR-VERIFIED-{index + 1:03d}', 'node_id': node_id, 'strategy_selected': 'bounded-layout' if is_root else 'preserve-approved-node', 'alternatives_considered': [], 'rationale': 'Accepted architecture identity is preserved.', 'evidence_source': 'architect_package', 'class_names_affected': []})
        actions.append({'action_id': f'ACTION-VERIFIED-{index + 1:03d}', 'action_type': 'configure_layout' if is_root else 'preserve_existing', 'target_node': node_id, 'parameters': {'layout': 'normal-flow'} if is_root else {}})
    return {'schema_id': 'ev4-ce-review-draft@1.0.0', 'review_id': 'CRR-VERIFIED-001', 'reviewer_identity': 'ce-test-reviewer', 'source_intake_ref': str(intake_path), 'architecture_echo': {'selected_candidate_id': candidate, 'approved_class_names': classes, 'build_tree_node_ids': sorted((str(item['node_id']) for item in reviewed_nodes)), 'architect_unknown_ids': unknowns, 'forbidden_work': forbidden}, 'reviewed_nodes': reviewed_nodes, 'implementation_strategy_proposal': {'strategy_map_id': 'ISM-VERIFIED-001', 'selected_candidate_id': candidate, 'approved_class_names': classes, 'strategies': strategies}, 'builder_action_proposals': actions, 'unresolved_questions': [], 'downstream_test_obligations': []}

def _geometry_draft(intake_path: Path) -> dict:
    draft = _draft(intake_path, claims=[{'claim_id': 'geometry', 'required': True}])
    node = draft['reviewed_nodes'][0]
    node['claim_semantics'] = {'geometry': {'anchor_model': {'root': node['node_id']}, 'coordinate_or_layout_model': 'normal-flow flex container', 'derivation_method': 'bounded CE layout derivation'}}
    return draft

def _write_verified_inputs(tmp_path: Path, *, geometry: bool=False):
    _install_test_provenance()
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _geometry_draft(intake_path) if geometry else _draft(intake_path)
    draft_path = _write_json(tmp_path / 'ce-review-draft.json', draft)
    return (intake, source, intake_path, source_path, draft, draft_path)
_install_test_provenance()
__all__ = ['_draft', '_geometry_draft', '_provenance', '_write_verified_inputs']
