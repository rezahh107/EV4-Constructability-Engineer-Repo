from __future__ import annotations
import copy
from pathlib import Path
from typing import Any
import pytest
from validator.claim_evaluators import evaluate_claim, sha256_json
from validator.intermediate_results import evaluate_all
from validator.payload_fidelity import compare_persisted_payload
from validator.review_obligations import ObligationDerivationError, derive_review_obligations
from validator.verified_constructability import EvaluationBoundaryError, verified_payload_data
from deterministic_runtime_support import canonical_bundle, canonical_draft, canonical_intake, evaluation_run
ROOT = Path(__file__).resolve().parents[1]

def _results(draft: dict[str, Any], *, runtime_results=()):
    bundle = canonical_bundle()
    intake = canonical_intake(bundle=bundle)
    return evaluate_all(intake, bundle, draft, repo_root=ROOT, runtime_results=runtime_results)

def _geometry_row(draft: dict[str, Any]):
    return _results(draft)['dependency_result']['rows'][0]

def test_ce_auth_001_empty_requested_claims_cannot_omit_mandatory_geometry() -> None:
    draft = canonical_draft()
    draft['reviewed_nodes'][0]['requested_claims'] = []
    obligations = derive_review_obligations(canonical_intake(), canonical_bundle(), draft)
    assert obligations['required_claims_by_node']['node-root'] == ['geometry']

def test_ce_auth_002_harmless_request_cannot_hide_mandatory_claim() -> None:
    draft = canonical_draft()
    draft['reviewed_nodes'][0]['requested_claims'] = ['placeholder_policy']
    claims = derive_review_obligations(canonical_intake(), canonical_bundle(), draft)['required_claims_by_node']['node-root']
    assert claims == ['geometry', 'placeholder_policy']

def test_ce_auth_003_unknown_action_fails_closed() -> None:
    draft = canonical_draft()
    draft['builder_action_proposals'][0]['action_type'] = 'invent_layout_magic'
    result = _results(draft)
    assert result['obligations']['complete'] is False
    assert 'CE_OBLIGATION_UNKNOWN_ACTION_TYPE' in {item['code'] for item in result['obligations']['diagnostics']}
    assert result['strategy_result']['status'] != 'complete'

def test_ce_auth_004_required_node_missing_from_draft() -> None:
    draft = canonical_draft()
    draft['reviewed_nodes'] = draft['reviewed_nodes'][:1]
    result = _results(draft)
    assert result['review_result']['missing_nodes'] == ['node-child']
    assert result['review_result']['complete'] is False

def test_ce_auth_005_orphan_node_fails_closed() -> None:
    draft = canonical_draft()
    orphan = copy.deepcopy(draft['reviewed_nodes'][0])
    orphan['node_id'] = 'node-orphan'
    draft['reviewed_nodes'].append(orphan)
    result = _results(draft)
    assert result['review_result']['orphan_nodes'] == ['node-orphan']

def test_ce_auth_006_duplicate_review_units_fail_closed() -> None:
    draft = canonical_draft()
    draft['reviewed_nodes'].append(copy.deepcopy(draft['reviewed_nodes'][0]))
    result = _results(draft)
    assert result['review_result']['duplicate_nodes'] == ['node-root']

def test_ce_auth_007_builder_action_unknown_node_fails_closed() -> None:
    draft = canonical_draft()
    draft['builder_action_proposals'][0]['target_node'] = 'node-missing'
    result = _results(draft)
    assert result['obligations']['unknown_action_targets'] == ['node-missing']
    assert result['strategy_result']['builder_actions_valid'] is False

def test_ce_auth_008_strategy_omits_required_node() -> None:
    draft = canonical_draft()
    draft['implementation_strategy_proposal']['strategies'] = draft['implementation_strategy_proposal']['strategies'][:1]
    result = _results(draft)
    assert result['strategy_result']['required_review_units_covered'] is False

def test_ce_auth_009_required_dependency_row_removal_is_detected() -> None:
    run, _, _ = evaluation_run(ROOT)
    expected = run['payload']
    tampered = copy.deepcopy(expected)
    tampered['authority_resolution'] = []
    assert compare_persisted_payload(tampered, expected)[0]['path'] == '$.authority_resolution'

def test_ce_auth_010_unrelated_existing_file_does_not_prove_geometry(tmp_path: Path) -> None:
    unrelated = tmp_path / 'unrelated.json'
    unrelated.write_text('{"stable": true}', encoding='utf-8')
    draft = canonical_draft()
    node = draft['reviewed_nodes'][0]
    node['candidate_source_refs'] = [{'claim_id': 'geometry', 'mode': 'VERIFIED_ARTIFACT', 'source_ref': str(unrelated)}]
    row = evaluate_claim('geometry', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': tmp_path})
    assert row['status'] == 'insufficient_evidence'
    assert row['evidence_refs'] == []

def test_ce_auth_011_valid_digest_without_geometry_semantics_fails(tmp_path: Path) -> None:
    source = tmp_path / 'geometry.json'
    source.write_text('{"node-root": "present"}', encoding='utf-8')
    draft = canonical_draft()
    node = draft['reviewed_nodes'][0]
    node['claim_semantics']['geometry'].pop('coordinate_or_layout_model')
    node['candidate_source_refs'] = [{'claim_id': 'geometry', 'mode': 'VERIFIED_ARTIFACT', 'source_ref': 'geometry.json'}]
    row = evaluate_claim('geometry', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': tmp_path})
    assert row['status'] == 'insufficient_evidence'

def test_ce_auth_012_overlay_requires_containment_positioning_and_stacking(tmp_path: Path) -> None:
    source = tmp_path / 'overlay.txt'
    source.write_text('contained absolute', encoding='utf-8')
    draft = canonical_draft()
    node = draft['reviewed_nodes'][0]
    node['candidate_source_refs'] = [{'claim_id': 'overlay_strategy', 'mode': 'VERIFIED_ARTIFACT', 'source_ref': 'overlay.txt'}]
    node['claim_semantics']['overlay_strategy'] = {'containment_model': 'contained', 'positioning_model': 'absolute', 'stacking_model': 'z-index-10', 'derivation_method': 'source parse'}
    row = evaluate_claim('overlay_strategy', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': tmp_path})
    assert row['status'] == 'insufficient_evidence'

def test_ce_auth_013_ui_control_file_must_contain_exact_path(tmp_path: Path) -> None:
    source = tmp_path / 'ui.txt'
    source.write_text('Advanced > Layout', encoding='utf-8')
    draft = canonical_draft()
    node = draft['reviewed_nodes'][0]
    node['candidate_source_refs'] = [{'claim_id': 'ui_control_path', 'mode': 'VERIFIED_ARTIFACT', 'source_ref': 'ui.txt'}]
    node['claim_semantics']['ui_control_path'] = {'control_path': 'Advanced > Positioning'}
    row = evaluate_claim('ui_control_path', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': tmp_path})
    assert row['status'] == 'insufficient_evidence'

def test_ce_auth_014_asset_existence_without_suitability_fails(tmp_path: Path) -> None:
    source = tmp_path / 'asset.svg'
    source.write_text("<svg id='node-root'/>", encoding='utf-8')
    draft = canonical_draft()
    node = draft['reviewed_nodes'][0]
    node['candidate_source_refs'] = [{'claim_id': 'asset_source', 'mode': 'VERIFIED_ARTIFACT', 'source_ref': 'asset.svg'}]
    node['claim_semantics']['asset_source'] = {'subject_token': 'node-root'}
    row = evaluate_claim('asset_source', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': tmp_path})
    assert row['status'] == 'insufficient_evidence'

def test_ce_auth_015_architect_approval_absent_fails() -> None:
    draft = canonical_draft()
    row = evaluate_claim('interaction_approval', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': ROOT})
    assert row['status'] == 'architect_decision_required'

def test_ce_auth_016_caller_described_execution_is_not_runtime_proof() -> None:
    draft = canonical_draft()
    runtime = [{'claim_id': 'responsive_behavior', 'subject_ref': 'node-root', 'evaluator_id': 'ce-responsive-evaluator', 'method_or_command': 'described, not executed', 'target_identity': 'node-root', 'execution_status': 'success', 'exit_code': 0, 'captured_result': {'passed': True}, 'result_digest': 'caller-authored', 'limitations': []}]
    row = evaluate_claim('responsive_behavior', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': ROOT}, runtime)
    assert row['status'] == 'downstream_validation_required'

def test_ce_auth_017_evidence_for_another_node_is_ignored() -> None:
    draft = canonical_draft()
    captured = {'passed': True}
    runtime = [{'claim_id': 'responsive_behavior', 'subject_ref': 'node-child', 'evaluator_id': 'ce-responsive-evaluator', 'method_or_command': 'python scripts/check.py', 'target_identity': 'node-child', 'execution_status': 'success', 'exit_code': 0, 'captured_result': captured, 'result_digest': sha256_json(captured), 'limitations': []}]
    row = evaluate_claim('responsive_behavior', 'node-root', {}, canonical_intake(), canonical_bundle(), draft, {'repo_root': ROOT}, runtime)
    assert row['status'] == 'downstream_validation_required'

def test_ce_auth_018_fidelity_rejects_another_bundle_or_candidate_binding() -> None:
    run, intake_bytes, bundle_bytes = evaluation_run(ROOT)
    tampered = copy.deepcopy(run)
    tampered['payload']['architecture_identity']['selected_candidate_id'] = 'OTHER'
    with pytest.raises(EvaluationBoundaryError):
        verified_payload_data(tampered, repo_root=ROOT, source_intake_bytes=intake_bytes, source_bundle_bytes=bundle_bytes)

def test_ce_auth_019_unresolved_builder_choice_is_detected() -> None:
    draft = canonical_draft()
    draft['builder_action_proposals'][0]['parameters']['layout'] = 'tbd'
    result = _results(draft)
    assert result['strategy_result']['builder_decisions_required'] == 1

def test_ce_auth_020_draft_zero_cannot_override_detected_decision() -> None:
    draft = canonical_draft()
    draft['implementation_strategy_proposal']['builder_decisions_required'] = 0
    draft['builder_action_proposals'][0]['parameters']['layout_options'] = ['grid', 'flex']
    run, _, _ = evaluation_run(ROOT, draft=draft)
    assert run['payload']['constructability_review']['builder_decisions_required'] > 0
    assert run['payload']['builder_package_emitted'] is False

def test_ce_auth_021_architect_amendment_is_derived() -> None:
    draft = canonical_draft()
    draft['reviewed_nodes'][0]['requires_structure_change'] = True
    draft['reviewed_nodes'][0]['architect_decomposition_permission'] = False
    run, _, _ = evaluation_run(ROOT, draft=draft)
    assert run['evaluation_results']['strategy_result']['architect_amendment_required'] is True
    assert run['payload']['constructability_review']['constructability_status'] == 'needs_architect_amendment'

def test_ce_auth_022_class_change_requires_architect_permission() -> None:
    draft = canonical_draft()
    draft['reviewed_nodes'][0]['requires_class_change'] = True
    result = _results(draft)
    assert result['identity_result']['unauthorized_redesign_absent'] is False

def test_ce_auth_023_architect_unknown_removal_is_detected() -> None:
    bundle = canonical_bundle()
    intake = canonical_intake(bundle=bundle)
    intake['unresolved_evidence'] = [{'unresolved_id': 'ARCH-UNK-1'}]
    draft = canonical_draft()
    draft['architecture_echo']['architect_unknown_ids'] = []
    result = evaluate_all(intake, bundle, draft, repo_root=ROOT)
    assert result['identity_result']['architect_unknowns_preserved'] is False

def test_ce_auth_024_forbidden_work_weakening_is_detected() -> None:
    draft = canonical_draft()
    draft['architecture_echo']['forbidden_work'] = []
    assert _results(draft)['identity_result']['forbidden_work_preserved'] is False

def test_ce_auth_025_build_tree_identity_change_is_detected() -> None:
    draft = canonical_draft()
    draft['architecture_echo']['build_tree_node_ids'] = ['node-root']
    assert _results(draft)['identity_result']['build_tree_nodes_preserved'] is False

def test_ce_auth_026_empty_architecture_evidence_trace_is_not_claimed_complete() -> None:
    bundle = canonical_bundle()
    for node in bundle['payload']['approved_structure_model']['structure_nodes']:
        node['evidence_refs'] = []
    intake = canonical_intake(bundle=bundle)
    result = evaluate_all(intake, bundle, canonical_draft(), repo_root=ROOT)
    traces = result['identity_result']['review_unit_traces']
    assert all((trace['architect_evidence_refs'] == [] for trace in traces))
    assert result['identity_result']['review_unit_trace_complete'] is False
    assert result['identity_result']['status'] == 'blocked'
    assert 'CE_IDENTITY_ARCHITECT_EVIDENCE_REFS_MISSING' in {item['code'] for item in result['identity_result']['diagnostics']}

@pytest.mark.parametrize(('mutation_id', 'mutator', 'expected_surface'), [('CE-AUTH-027', lambda p: p['authority_resolution'][0].__setitem__('resolved_state', 'UNVERIFIED'), '$.authority_resolution'), ('CE-AUTH-028', lambda p: p.__setitem__('unresolved_evidence', []), '$.unresolved_evidence'), ('CE-AUTH-029', lambda p: p.__setitem__('downstream_test_obligations', []), '$.downstream_test_obligations'), ('CE-AUTH-030', lambda p: p.__setitem__('builder_executable_package', {'forged': True}), '$.builder_executable_package'), ('CE-AUTH-031', lambda p: p['constructability_review'].__setitem__('builder_decisions_required', 7), '$.constructability_review'), ('CE-AUTH-032', lambda p: p['extension_records'][3]['result'].__setitem__('architect_amendment_required', True), '$'), ('CE-AUTH-033', lambda p: p.__setitem__('builder_package_emitted', False), '$.builder_package_emitted'), ('CE-AUTH-034', lambda p: p.__setitem__('payload_status', 'insufficient_evidence'), '$.payload_status'), ('CE-AUTH-035', lambda p: p['architecture_identity'].__setitem__('selected_candidate_id', 'OTHER'), '$.architecture_identity'), ('CE-AUTH-036', lambda p: p['implementation_strategy_map'].__setitem__('selected_candidate_id', 'OTHER'), '$.implementation_strategy_map')])
def test_persisted_output_mutations_are_detected(mutation_id, mutator, expected_surface) -> None:
    if mutation_id in {'CE-AUTH-028', 'CE-AUTH-029'}:
        blocked_draft = canonical_draft()
        blocked_draft['builder_action_proposals'][0]['action_type'] = 'set_responsive'
        blocked_draft['reviewed_nodes'][0]['proposed_action'] = 'responsive behavior'
        run, _, _ = evaluation_run(ROOT, draft=blocked_draft)
    else:
        run, _, _ = evaluation_run(ROOT)
    expected = run['payload']
    tampered = copy.deepcopy(expected)
    mutator(tampered)
    diagnostics = compare_persisted_payload(tampered, expected)
    assert diagnostics
    assert diagnostics[0]['path'] == expected_surface

def test_ce_auth_037_and_038_deterministic_intermediates_payload_and_export_projection() -> None:
    first, _, _ = evaluation_run(ROOT)
    second, _, _ = evaluation_run(ROOT)
    assert first['evaluation_results'] == second['evaluation_results']
    assert first['payload'] == second['payload']

def test_ce_auth_039_builder_contract_identity_is_preserved() -> None:
    run, _, _ = evaluation_run(ROOT)
    assert run['payload']['builder_executable_package']['schema'] == 'ev4-builder-executable-package@1.0.0'

def test_ce_auth_040_project_gate_contract_identity_is_not_redefined() -> None:
    schema = (ROOT / 'contracts/project-gate/stage-bundle.v1.schema.json').read_text(encoding='utf-8')
    assert 'stage-evidence-bundle.v1' in schema

def test_ce_auth_041_legacy_payload_path_is_preview_only_source_level() -> None:
    source = (ROOT / 'validator/ce_validation_transaction.py').read_text(encoding='utf-8')
    assert 'apply_legacy_preview_boundary' in source
    assert 'legacy_payload_authorization_supported' not in source or 'False' in source

def test_ce_auth_042_import_has_no_hidden_monkeypatch() -> None:
    source = (ROOT / 'validator/__init__.py').read_text(encoding='utf-8')
    assert 'install_authority_boundary' not in source
    assert 'monkeypatch' not in source

def test_ce_auth_043_single_registry_definition() -> None:
    sources = list((ROOT / 'validator').glob('*.py'))
    declarations = [path.name for path in sources if 'CLAIM_POLICIES: Final' in path.read_text(encoding='utf-8')]
    assert declarations == ['claim_policy_registry.py']

def test_ce_auth_044_only_deterministic_assembler_authorizes_successor_payload() -> None:
    source = (ROOT / 'validator/payload_assembler.py').read_text(encoding='utf-8')
    assert source.count('def assemble_ce_stage_payload(') == 1
    assert 'builder_package_emitted' in source and 'eligible' in source
