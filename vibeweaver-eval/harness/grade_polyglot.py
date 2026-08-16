#!/usr/bin/env python3
"""Grade a polyglot run: copy hidden tests into workdir, run pytest, save JSON."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def grade(task_dir: Path, workdir: Path, out: Path) -> dict:
    meta = json.loads((task_dir / "task.json").read_text())
    result = {"task": meta["task_id"], "passed": False, "tests_passed": 0,
              "tests_total": 0, "output": ""}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # copy workdir contents (agent's solution) into a clean grading dir
        for item in workdir.iterdir():
            if item.name in ("node_modules", ".venv", "venv"):
                continue
            dst = td / item.name
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
        # inject hidden tests
        for t in meta["hidden_tests"]:
            shutil.copy(task_dir / "hidden_tests" / t, td / t)
        cmd = meta["test_command"] + meta["hidden_tests"]
        env = dict(os.environ)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        proc = subprocess.run(cmd, cwd=td, capture_output=True, text=True, timeout=600,
                              env=env)
        output = proc.stdout + proc.stderr
        result["output"] = output[-3000:]
        # parse pytest summary line: "X passed, Y failed" or "1 failed"
        try:
            tail = output.strip().splitlines()
            summary = tail[-1] if tail else ""
            import re
            m = re.search(r"(\d+) passed", summary)
            f = re.search(r"(\d+) failed", summary)
            passed = int(m.group(1)) if m else 0
            failed = int(f.group(1)) if f else 0
            result["tests_passed"] = passed
            result["tests_total"] = passed + failed
            result["passed"] = proc.returncode == 0 and failed == 0
        except Exception as e:
            result["output"] += f"\nPARSE ERROR: {e}"
            result["passed"] = False
    result["output"] = result["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    (out).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result

if __name__ == "__main__":
    task_dir, workdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    r = grade(task_dir, workdir, out)
    print(json.dumps({k: r[k] for k in ("task", "passed", "tests_passed", "tests_total")}))
