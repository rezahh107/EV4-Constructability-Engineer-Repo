from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=not capture,
        text=True,
        capture_output=capture,
    )


root = Path.cwd()
workflow = root / ".github/workflows/ce46-explicit-runtime-input-repair.yml"
text = workflow.read_text(encoding="utf-8")
marker = "          python - <<'PY'\n"
start = text.index(marker) + len(marker)
end = text.index("\n          PY", start)
lines = text[start:end].splitlines()
script = "\n".join(
    line[10:] if line.startswith("          ") else line
    for line in lines
) + "\n"
repair_script = Path("/tmp/ce46_apply_repair.py")
repair_script.write_text(script, encoding="utf-8")
run([sys.executable, str(repair_script)])

dirty_test = root / "tests/test_ce_exporter_explicit_inputs.py"
source = dirty_test.read_text(encoding="utf-8")
old = '    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:\n        assert command == ["git", "symbolic-ref", "--quiet", "--short", "HEAD"]\n        return subprocess.CompletedProcess(command, 0, "feature/explicit-inputs\\n", "")\n\n    monkeypatch.setattr(core_module, "_git", fake_git)\n'
new = '    original_run = core_module._run\n\n    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:\n        if command == ["git", "symbolic-ref", "--quiet", "--short", "HEAD"]:\n            return subprocess.CompletedProcess(command, 0, "feature/explicit-inputs\\n", "")\n        return original_run(command, cwd)\n\n    monkeypatch.setattr(core_module, "_git", fake_git)\n'
if source.count(old) != 1:
    raise SystemExit("expected dirty metadata mock not found")
dirty_test.write_text(source.replace(old, new, 1), encoding="utf-8")

argument_pattern = re.compile(
    r'intermediate_inputs_path=(.+)\.with_name\("ce-intermediate-export-inputs\.json"\),'
)
cli_pattern = re.compile(
    r'str\((.+)\.with_name\("ce-intermediate-export-inputs\.json"\)\)'
)
for path in sorted((root / "tests").glob("test_*.py")):
    current = path.read_text(encoding="utf-8")
    updated = argument_pattern.sub(
        r'intermediate_inputs_path=Path(\1).with_name("ce-intermediate-export-inputs.json"),',
        current,
    )
    updated = cli_pattern.sub(
        r'str(Path(\1).with_name("ce-intermediate-export-inputs.json"))',
        updated,
    )
    if updated != current and "from pathlib import Path" not in updated:
        anchor = "from __future__ import annotations\n"
        updated = updated.replace(anchor, anchor + "\nfrom pathlib import Path\n", 1)
    path.write_text(updated, encoding="utf-8")

run(["git", "checkout", "origin/main", "--", ".github/workflows/validate-ce-bootstrap.yml"])
for temporary in (
    root / ".github/workflows/ce46-explicit-runtime-input-repair.yml",
    root / ".github/workflows/ce46-explicit-runtime-input-repair-pr.yml",
):
    temporary.unlink(missing_ok=True)

run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[dev]"])
result = run([sys.executable, "-m", "pytest", "-q", "--tb=no"], capture=True)
output = (result.stdout + "\n" + result.stderr).splitlines()
print("\n".join(output[-120:]))
raise SystemExit(result.returncode)
