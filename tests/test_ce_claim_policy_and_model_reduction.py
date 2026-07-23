from __future__ import annotations
import ast
import importlib
from pathlib import Path
from validator.claim_policy_registry import ACTION_CLAIMS, CLAIM_POLICIES
ROOT = Path(__file__).resolve().parents[1]

def test_one_canonical_claim_policy_registry_exists() -> None:
    declarations: list[tuple[str, int]] = []
    for path in (ROOT / 'validator').glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                names = []
                if isinstance(node, ast.Assign):
                    names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                elif isinstance(node.target, ast.Name):
                    names = [node.target.id]
                if 'CLAIM_POLICIES' in names:
                    declarations.append((path.name, node.lineno))
    assert declarations == [('claim_policy_registry.py', declarations[0][1])]
    assert set(CLAIM_POLICIES) == {'geometry', 'asset_source', 'placeholder_policy', 'overlay_strategy', 'responsive_behavior', 'interaction_approval', 'dynamic_loop_approval', 'ui_control_path', 'accessibility', 'QA'}

def test_supported_actions_have_explicit_claim_or_no_claim_rule() -> None:
    assert ACTION_CLAIMS['configure_layout'] == ('geometry',)
    assert ACTION_CLAIMS['configure_overlay'] == ('geometry', 'overlay_strategy')
    assert ACTION_CLAIMS['preserve_existing'] == ()
    assert ACTION_CLAIMS['inspect_only'] == ()

def test_importing_validator_has_no_authority_install_side_effect() -> None:
    package = importlib.import_module('validator')
    assert not hasattr(package, 'install_authority_boundary')
    source = (ROOT / 'validator/__init__.py').read_text(encoding='utf-8')
    assert 'install_authority_boundary' not in source
    assert 'authority_boundary' not in source

def test_runtime_contains_no_object_identity_authority_registry() -> None:
    runtime_source = (ROOT / 'validator/verified_constructability.py').read_text(encoding='utf-8')
    assert '_CAPABILITY_REGISTRY' not in runtime_source
    assert '__copy__' not in runtime_source
    assert '__deepcopy__' not in runtime_source
    assert 'id(' not in runtime_source
    assert 'install_authority_boundary' not in runtime_source

def test_single_payload_assembler_and_single_fidelity_validator() -> None:
    assembler_definitions = []
    fidelity_definitions = []
    for path in (ROOT / 'validator').glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == 'assemble_ce_stage_payload':
                    assembler_definitions.append(path.name)
                if node.name == 'compare_persisted_payload':
                    fidelity_definitions.append(path.name)
    assert assembler_definitions == ['payload_assembler.py']
    assert fidelity_definitions == ['payload_fidelity.py']
