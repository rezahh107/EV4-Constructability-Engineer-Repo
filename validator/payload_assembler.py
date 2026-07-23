from __future__ import annotations
import copy
import json
from typing import Any, Mapping
from .claim_policy_registry import CLAIM_POLICIES, policy_projection
from .payload_projection import (
    BUILDER_PACKAGE_SCHEMA_ID, CE_REPOSITORY, EVALUATOR_ID, EVALUATOR_VERSION,
    PAYLOAD_SCHEMA_ID, PAYLOAD_SCHEMA_VERSION, REVIEW_SCHEMA_ID,
    _derived_actions, _draft_nodes, _node_status, _proof_ids, _required_value,
    _row_map, _strategy_map, canonical_bytes, sha256_json,
)
from .payload_evidence import (
    _architect_unresolved, _authority_resolution, _diagnostic_unresolved,
    _evidence_register,
)

def assemble_ce_stage_payload(identity_result: Mapping[str, Any], review_result: Mapping[str, Any], dependency_result: Mapping[str, Any], strategy_result: Mapping[str, Any], canonical_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Project one deterministic CE Payload from the canonical evaluation results."""
    architect_intake = canonical_inputs['architect_intake']
    source_bundle = canonical_inputs['source_bundle']
    review_draft = canonical_inputs['review_draft']
    input_metadata = canonical_inputs.get('input_metadata') or {}
    review_id = str(review_draft.get('review_id') or 'ce-review')
    selected_candidate_id = str(identity_result.get('selected_candidate_id') or 'unknown')
    payload_seed = {'architect_intake': architect_intake, 'source_bundle': source_bundle, 'review_draft': review_draft, 'runtime_results': canonical_inputs.get('runtime_results') or [], 'policy_registry': {claim: policy_projection(claim) for claim in sorted(CLAIM_POLICIES)}}
    payload_id = f'ce-verified-{sha256_json(payload_seed)}'
    run_id = f"ce-run-{sha256_json({'payload_id': payload_id})[:24]}"
    rows = _row_map(dependency_result)
    draft_nodes = _draft_nodes(review_draft)
    reviewed_nodes: list[dict[str, Any]] = []
    for node_id in review_result.get('required_nodes') or []:
        node_id = str(node_id)
        draft_node = draft_nodes.get(node_id, {})
        node_status, blocking_reason = _node_status(node_id, dependency_result, strategy_result)
        geometry = rows.get((node_id, 'geometry'))
        asset = rows.get((node_id, 'asset_source'))
        placeholder = rows.get((node_id, 'placeholder_policy'))
        overlay = rows.get((node_id, 'overlay_strategy'))
        responsive = rows.get((node_id, 'responsive_behavior'))
        interaction = rows.get((node_id, 'interaction_approval'))
        dynamic = rows.get((node_id, 'dynamic_loop_approval'))
        accessibility = rows.get((node_id, 'accessibility'))
        ui_control = rows.get((node_id, 'ui_control_path'))
        reviewed_nodes.append({'node_id': node_id, 'node_type': str(draft_node.get('node_type') or 'implementation_node'), 'action_proposed': str(draft_node.get('proposed_action') or 'review required'), 'node_status': node_status, 'blocking_reason': blocking_reason, 'engineering_rationale': str(draft_node.get('engineering_rationale') or ''), 'interrogation_result': {'geometry_required': geometry is not None, 'geometry_proven': _required_value(geometry), 'geometry_proof': {'evidence_ids': _proof_ids(geometry)} if _proof_ids(geometry) else None, 'asset_required': asset is not None, 'asset_source_present': _required_value(asset), 'placeholder_policy_present': _required_value(placeholder), 'overlay_strategy_required': overlay is not None, 'overlay_strategy_proven': _required_value(overlay), 'overlay_strategy': {'evidence_ids': _proof_ids(overlay)} if _proof_ids(overlay) else None, 'responsive_behavior': _required_value(responsive, responsive=True), 'action_targets_responsive': responsive is not None, 'interaction_implied': interaction is not None, 'interaction_approved': _required_value(interaction), 'dynamic_loop_implied': dynamic is not None, 'dynamic_loop_approved': _required_value(dynamic), 'dynamic_loop_binding_map': {'evidence_ids': _proof_ids(dynamic)} if _proof_ids(dynamic) else None, 'accessibility_claimed': accessibility is not None, 'accessibility_evidenced': _required_value(accessibility), 'exact_ui_control_path_used': ui_control is not None, 'ui_control_evidence_present': _required_value(ui_control), 'ui_control_evidence': {'evidence_ids': _proof_ids(ui_control)} if _proof_ids(ui_control) else None, 'reversible_if_wrong': bool(draft_node.get('reversible_if_wrong', False)), 'requires_class_change': bool(draft_node.get('requires_class_change', False)), 'requires_structure_change': bool(draft_node.get('requires_structure_change', False)), 'architect_decomposition_permission': bool(draft_node.get('architect_decomposition_permission', False))}})
    all_complete = all((result.get('status') == 'complete' for result in (identity_result, review_result, dependency_result, strategy_result)))
    blockers = [str(value) for value in dependency_result.get('blocking_dependencies') or []]
    hidden_decisions = int(strategy_result.get('builder_decisions_required') or 0)
    architect_amendment = bool(strategy_result.get('architect_amendment_required'))
    actions = _derived_actions(review_draft, strategy_result)
    architect_unresolved = _architect_unresolved(architect_intake)
    eligible = all_complete and (not blockers) and (not dependency_result.get('unresolved_evidence')) and (not architect_unresolved) and (hidden_decisions == 0) and (not architect_amendment) and bool(actions) and bool(strategy_result.get('first_safe_batch_complete'))
    if architect_amendment:
        constructability_status = 'needs_architect_amendment'
    elif blockers or dependency_result.get('unresolved_evidence') or architect_unresolved:
        constructability_status = 'needs_user_evidence'
    elif not eligible:
        constructability_status = 'blocked'
    else:
        constructability_status = 'executable_ready'
    strategy_map = _strategy_map(review_draft, strategy_result, review_id=review_id, selected_candidate_id=selected_candidate_id, payload_id=payload_id)
    builder_package = None
    if eligible and strategy_map is not None:
        action_ids = [item['action_id'] for item in actions]
        builder_package = {'schema': BUILDER_PACKAGE_SCHEMA_ID, 'package_id': f'builder-{payload_id[-24:]}', 'review_ref': review_id, 'strategy_map_ref': strategy_map['strategy_map_id'], 'architect_contract': {'source_ref': str(input_metadata.get('intake_source_ref') or 'architect-intake'), 'selected_candidate_id': selected_candidate_id, 'approved_class_names': list(identity_result.get('approved_class_names') or [])}, 'selected_candidate_id': selected_candidate_id, 'approved_class_names': list(identity_result.get('approved_class_names') or []), 'builder_package_status': 'executable_ready', 'builder_decisions_required': hidden_decisions, 'blocking_dependencies': [], 'selected_candidate_locked': bool(architect_intake.get('selected_architecture', {}).get('selected_candidate_locked')), 'selected_candidate_id_unchanged': bool(identity_result.get('selected_candidate_preserved')), 'approved_class_names_unchanged': bool(identity_result.get('approved_classes_preserved')), 'confirmation_request': {'confirmation_id': f'confirm-{payload_id[-16:]}', 'confirmed_action_ids': action_ids, 'expected_user_token': f'confirm {action_ids[0]}'}, 'first_safe_builder_batch': {'batch_id': f'batch-{payload_id[-16:]}', 'risk': 'low', 'actions': actions}, 'known_unknowns': {unresolved_id: 'preserved_from_architect' for unresolved_id in identity_result.get('architect_unknown_ids') or []}, 'logged_assumptions': [], 'qa_status': {'production_ready': False}}
    authority_resolution = _authority_resolution(dependency_result)
    unresolved = copy.deepcopy(list(dependency_result.get('unresolved_evidence') or []))
    unresolved.extend(architect_unresolved)
    unresolved.extend(_diagnostic_unresolved(identity_result, review_result, strategy_result))
    unresolved = list({str(item.get('unresolved_id') or sha256_json(item)): item for item in unresolved if isinstance(item, Mapping)}.values())
    unresolved.sort(key=lambda item: str(item.get('unresolved_id')))
    source_hash = str(input_metadata.get('intake_canonical_sha256') or sha256_json(architect_intake))
    source_bytes_hash = str(input_metadata.get('intake_bytes_sha256') or source_hash)
    bundle_hash = str(input_metadata.get('source_bundle_canonical_sha256') or sha256_json(source_bundle))
    bundle_bytes_hash = str(input_metadata.get('source_bundle_bytes_sha256') or bundle_hash)
    source_bundle_id = str(source_bundle.get('bundle_id') or 'unknown-bundle')
    source_ref = str(input_metadata.get('intake_source_ref') or 'architect-intake')
    bundle_ref = str(input_metadata.get('source_bundle_ref') or 'architect-source-bundle')
    synthetic = bool(architect_intake.get('synthetic') is True or source_bundle.get('synthetic') is True or canonical_inputs.get('synthetic') is True)
    payload: dict[str, Any] = {'schema_id': PAYLOAD_SCHEMA_ID, 'schema_version': PAYLOAD_SCHEMA_VERSION, 'owner_repository': CE_REPOSITORY, 'payload_status': 'complete' if eligible else 'insufficient_evidence', 'payload_identity': {'payload_id': payload_id, 'pipeline_id': 'ev4-ce-project-gate-producer-pipeline', 'run_id': run_id, 'synthetic': synthetic}, 'source_architect_intake': {'schema_id': str(architect_intake.get('schema_id')), 'schema_version': str(architect_intake.get('schema_version')), 'artifact_ref': source_ref, 'artifact_hash': {'algorithm': 'sha256', 'value': source_hash, 'scope': 'canonical_json'}, 'transition_metadata_is_review_evidence': False}, 'source_bundle_binding': {'bundle_id': source_bundle_id, 'artifact_ref': bundle_ref, 'canonical_sha256': bundle_hash, 'bytes_sha256': bundle_bytes_hash}, 'architecture_identity': {'selected_candidate_id': selected_candidate_id, 'selected_candidate_locked': bool(architect_intake.get('selected_architecture', {}).get('selected_candidate_locked')), 'selected_candidate_id_unchanged': bool(identity_result.get('selected_candidate_preserved')), 'approved_class_names': list(identity_result.get('approved_class_names') or []), 'approved_class_names_unchanged': bool(identity_result.get('approved_classes_preserved')), 'build_tree_identity_preserved': bool(identity_result.get('build_tree_nodes_preserved')), 'architect_unknowns_preserved': bool(identity_result.get('architect_unknowns_preserved')), 'architect_forbidden_work_weakened': not bool(identity_result.get('forbidden_work_preserved')), 'review_unit_traces': copy.deepcopy(list(identity_result.get('review_unit_traces') or []))}, 'constructability_review': {'schema_id': REVIEW_SCHEMA_ID, 'review_id': review_id, 'architect_package_ref': source_ref, 'selected_candidate_id': selected_candidate_id, 'constructability_status': constructability_status, 'builder_decisions_required': hidden_decisions, 'blocking_dependencies': blockers, 'engineer_questions': [str(value) for value in review_draft.get('unresolved_questions') or []], 'logged_assumptions': [], 'reviewed_nodes': reviewed_nodes, 'qa_status': {'production_ready': False}}, 'implementation_strategy_map': strategy_map if eligible else None, 'builder_executable_package': builder_package, 'builder_package_emitted': eligible, 'builder_package_not_emitted_reason': None if eligible else 'deterministic_evaluation_incomplete', 'authority_resolution': authority_resolution, 'authority_resolution_digest': sha256_json(authority_resolution), 'evidence_register': _evidence_register(dependency_result, payload_id), 'unresolved_evidence': unresolved, 'downstream_test_obligations': copy.deepcopy(list(dependency_result.get('downstream_test_obligations') or [])), 'repair_routing': {'repair_owner': 'ce' if eligible else 'claim_or_architecture_owner', 'status': 'not_required' if eligible else 'required'}, 'boundary_assertions': {'ce_did_not_redesign_architecture': bool(identity_result.get('unauthorized_redesign_absent')), 'ce_did_not_claim_builder_execution': True, 'ce_did_not_claim_responsive_completion': not any((row.get('claim_id') == 'responsive_behavior' and row.get('status') != 'satisfied' for row in dependency_result.get('rows') or [] if isinstance(row, Mapping))), 'production_ready': False}, 'validation_contract': {'validator_id': EVALUATOR_ID, 'validator_version': EVALUATOR_VERSION, 'legacy_payload_validation_supported': True, 'legacy_payload_authorization_supported': False, 'successor_verified_payload_required_for_handoff': True}, 'extension_records': [{'kind': 'architecture_identity_preservation', 'result': copy.deepcopy(identity_result)}, {'kind': 'review_units_and_interrogation', 'result': copy.deepcopy(review_result)}, {'kind': 'dependency_classification', 'result': copy.deepcopy(dependency_result)}, {'kind': 'implementation_strategy_coverage', 'result': copy.deepcopy(strategy_result)}, {'kind': 'claim_policy_registry', 'registry': {claim_id: policy_projection(claim_id) for claim_id in sorted(CLAIM_POLICIES)}}]}
    if not eligible and (not payload['unresolved_evidence']):
        payload['unresolved_evidence'] = [{'unresolved_id': 'unresolved-evaluation-incomplete', 'owner': 'constructability_engineer', 'reason': 'deterministic_evaluation_incomplete', 'state': 'insufficient_evidence'}]
    return json.loads(canonical_bytes(payload))
