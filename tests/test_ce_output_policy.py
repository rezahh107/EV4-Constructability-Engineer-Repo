from __future__ import annotations

import ast
import inspect
from pathlib import Path

from exporter_test_support import ROOT
from validator.ce_validation_transaction import safe_output_path


def _safe_output_call_inventory() -> list[tuple[str, int, bool | None]]:
    inventory: list[tuple[str, int, bool | None]] = []
    validator_root = ROOT / "validator"
    for path in sorted(validator_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        aliases: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module not in {
                "validator.ce_validation_transaction",
                "ce_validation_transaction",
            } and not (
                node.module == "ce_validation_transaction"
                or node.module == ".ce_validation_transaction"
            ):
                continue
            for item in node.names:
                if item.name == "safe_output_path":
                    aliases.add(item.asname or item.name)
        if not aliases:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in aliases:
                continue
            policy: bool | None = None
            for keyword in node.keywords:
                if keyword.arg == "allow_absolute_external":
                    if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, bool):
                        policy = keyword.value.value
                    else:
                        policy = None
            inventory.append((path.relative_to(ROOT).as_posix(), node.lineno, policy))
    return sorted(inventory)


def test_safe_output_path_has_keyword_only_contained_default() -> None:
    signature = inspect.signature(safe_output_path)
    policy = signature.parameters["allow_absolute_external"]
    assert policy.kind is inspect.Parameter.KEYWORD_ONLY
    assert policy.default is False


def test_only_verified_exporter_explicitly_enables_external_output() -> None:
    inventory = _safe_output_call_inventory()
    assert [(path, policy) for path, _line, policy in inventory] == [
        ("validator/_verified_project_gate_exporter_impl.py", True),
        ("validator/project_gate_exporter.py", None),
    ]

    unauthorized = [
        f"{path}:{line}"
        for path, line, policy in inventory
        if policy is True and path != "validator/_verified_project_gate_exporter_impl.py"
    ]
    assert unauthorized == [], f"unauthorized external-output opt-ins: {unauthorized}"


def test_legacy_cli_documents_repository_contained_output() -> None:
    source = (ROOT / "validator/project_gate_exporter.py").read_text(encoding="utf-8")
    assert 'help="Output path inside the CE repository."' in source
