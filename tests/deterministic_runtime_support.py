from __future__ import annotations
import copy
from pathlib import Path
from typing import Any
from validator.payload_assembler import canonical_bytes, sha256_json
from validator.verified_constructability import assemble_verified_ce_stage_payload, verify_architect_intake, verify_source_bundle

def canonical_bundle() -> dict[str, Any]:
    return {'bundle_id': 'bundle-1', 'payload': {'approved_structure_model': {'structure_nodes': [{'node_id': 'node-root', 'node_kind': 'section', 'parent_node_id': None, 'children': ['node-child'], 'evidence_refs': ['architect-structure-root']}, {'node_id': 'node-child', 'node_kind': 'container', 'parent_node_id': 'node-root', 'children': [], 'evidence_refs': ['architect-structure-child']}]}, 'architecture_identity': {'selected_candidate_id': 'ARCH-FAM-C'}, 'architect_intent': {'class_intent': {'approved_class_names': ['smart-home__section']}}}}

def canonical_intake(*, bundle: dict[str, Any] | None=None) -> dict[str, Any]:
    bundle = bundle or canonical_bundle()
    return {'schema_id': 'ev4-ce-architect-stage-intake@1.1.0', 'schema_version': '1.1.0', 'selected_architecture': {'selected_candidate_id': 'ARCH-FAM-C', 'selected_candidate_locked': True}, 'structure_projection': {'nodes': [{'source_node_id': 'node-root', 'node_kind': 'section', 'parent_node_id': None, 'children': ['node-child']}, {'source_node_id': 'node-child', 'node_kind': 'container', 'parent_node_id': 'node-root', 'children': []}]}, 'architect_intent_preserved': {'class_intent': {'approved_class_names': ['smart-home__section']}}, 'unresolved_evidence': [], 'forbidden_work': ['no_hidden_redesign'], 'project_gate_transition': {'source_bundle_id': bundle['bundle_id'], 'source_bundle_hash': {'value': sha256_json(bundle)}}}

def canonical_draft() -> dict[str, Any]:
    return {'schema_id': 'ev4-ce-review-draft@1.0.0', 'review_id': 'review-1', 'reviewer_identity': 'constructability_engineer', 'source_intake_ref': 'architect-intake.json', 'architecture_echo': {'selected_candidate_id': 'ARCH-FAM-C', 'approved_class_names': ['smart-home__section'], 'build_tree_node_ids': ['node-child', 'node-root'], 'architect_unknown_ids': [], 'forbidden_work': ['no_hidden_redesign']}, 'reviewed_nodes': [{'node_id': 'node-root', 'node_type': 'section', 'proposed_action': 'configure layout', 'engineering_rationale': 'Derive a grid from the retained parent-child anchors.', 'requested_claims': [], 'candidate_source_refs': [], 'claim_semantics': {'geometry': {'anchor_model': {'root': 'node-root'}, 'coordinate_or_layout_model': 'css-grid', 'derivation_method': 'parent-child layout reasoning'}}, 'assumptions': ['Architect node identities are stable.'], 'limitations': [], 'reversible_if_wrong': True, 'requires_class_change': False, 'requires_structure_change': False, 'architect_decomposition_permission': False}, {'node_id': 'node-child', 'node_type': 'container', 'proposed_action': 'preserve existing', 'engineering_rationale': 'No technical mutation is proposed.', 'requested_claims': [], 'candidate_source_refs': [], 'claim_semantics': {}, 'assumptions': ['Existing node is retained.'], 'limitations': [], 'reversible_if_wrong': True, 'requires_class_change': False, 'requires_structure_change': False, 'architect_decomposition_permission': False}], 'implementation_strategy_proposal': {'selected_candidate_id': 'ARCH-FAM-C', 'approved_class_names': ['smart-home__section'], 'strategies': [{'strategy_id': 'strategy-root', 'node_id': 'node-root', 'strategy_selected': 'css-grid', 'rationale': 'Preserve the Architect hierarchy.'}, {'strategy_id': 'strategy-child', 'node_id': 'node-child', 'strategy_selected': 'preserve', 'rationale': 'No mutation is required.'}]}, 'builder_action_proposals': [{'action_id': 'action-root', 'action_type': 'configure_layout', 'target_node': 'node-root', 'parameters': {'layout': 'grid'}}, {'action_id': 'action-child', 'action_type': 'preserve_existing', 'target_node': 'node-child', 'parameters': {}}], 'unresolved_questions': [], 'downstream_test_obligations': []}

def verified_inputs() -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    bundle = canonical_bundle()
    intake = canonical_intake(bundle=bundle)
    intake_bytes = canonical_bytes(intake)
    bundle_bytes = canonical_bytes(bundle)
    verified_intake = verify_architect_intake(intake=intake, intake_bytes=intake_bytes, source_ref='architect-intake.json')
    verified_bundle = verify_source_bundle(source_bundle=bundle, source_bundle_bytes=bundle_bytes, verified_intake=verified_intake, source_ref='architect-source-bundle.json')
    return (verified_intake, verified_bundle, intake_bytes, bundle_bytes)

def evaluation_run(repo_root: Path, *, draft: dict[str, Any] | None=None, runtime_results=()):
    verified_intake, verified_bundle, intake_bytes, bundle_bytes = verified_inputs()
    run = assemble_verified_ce_stage_payload(draft=copy.deepcopy(draft or canonical_draft()), verified_intake=verified_intake, verified_source_bundle=verified_bundle, repo_root=repo_root, runtime_results=runtime_results)
    return (run, intake_bytes, bundle_bytes)
