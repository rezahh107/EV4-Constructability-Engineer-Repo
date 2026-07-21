from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate-ce-policy-governance.py"
spec = importlib.util.spec_from_file_location("ce_policy_governance", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def result(relative: str):
    return module.validate_file(ROOT / relative)

def test_complete_kernel_lineage_is_accepted():
    value = result("fixtures/ce-policy-governance/valid/complete-kernel-lineage.json")
    assert value["passed"] is True
    assert value["matches_expected"] is True

def test_missing_kernel_lineage_fails_closed():
    value = result("fixtures/ce-policy-governance/invalid/missing-kernel-lineage.json")
    assert value["passed"] is False
    assert any(d["code"] == "CE_POLICY_KERNEL_LINEAGE_REQUIRED" for d in value["diagnostics"])

def test_kernel_option_mismatch_fails_closed():
    value = result("fixtures/ce-policy-governance/invalid/kernel-option-mismatch.json")
    assert value["passed"] is False
    assert any(d["code"] == "CE_POLICY_KERNEL_SELECTED_OPTION_MISMATCH" for d in value["diagnostics"])

def test_unverified_domain_cannot_change_outcome():
    value = result("fixtures/ce-policy-governance/invalid/unverified-domain-changes-outcome.json")
    assert value["passed"] is False
    assert any(d["code"] == "CE_POLICY_DOMAIN_ADVISORY_CANNOT_AUTHORIZE" for d in value["diagnostics"])

def test_policy_loading_mode_and_outline_are_truthful():
    text = (ROOT / "policies" / "EV4_CE_CONSTRUCTABILITY_DECISION_POLICY_r001.md").read_text(encoding="utf-8")
    assert "MANUAL_ADVISORY_ATTACHMENT_ONLY" in text
    assert "silent mandatory" not in text.lower()
    assert not __import__("re").search(r"^## 7\\.\\d+ ", text, __import__("re").M)
    for n in range(1, 20):
        assert f'<a id="ce-policy-7-{n}"></a>' in text
        assert f'[7.{n}](#ce-policy-7-{n})' in text
