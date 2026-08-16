#!/usr/bin/env python3
"""Prepare polyglot tasks: build task dirs with prompt + starter, hide tests."""
import json
import shutil
from pathlib import Path

SRC = Path("/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/opencode/polyglot-benchmark")
TASKS = Path(__file__).resolve().parent.parent / "workspace" / "iteration-1" / "tasks"

EXERCISES = [
    "phone-number", "grade-school", "list-ops",       # easy
    "variable-length-quantity", "simple-linked-list", "transpose",
    "pig-latin", "robot-name",                          # medium
    "two-bucket", "bowling",                            # medium-hard / hard
]

def main():
    for name in EXERCISES:
        src = SRC / "python" / "exercises" / "practice" / name
        dst = TASKS / f"polyglot_{name.replace('-', '_')}"
        if dst.exists():
            shutil.rmtree(dst)
        hidden = dst / "hidden_tests"
        starter = dst / "starter"
        hidden.mkdir(parents=True)
        starter.mkdir(parents=True)
        prompt = (src / ".docs" / "instructions.md").read_text()
        (dst / "prompt.md").write_text(prompt)
        py_files = sorted(src.glob("*.py"))
        test_files = [f for f in py_files if f.name.endswith("_test.py")]
        sol_files = [f for f in py_files if not f.name.endswith("_test.py")]
        for f in test_files:
            shutil.copy(f, hidden / f.name)
        for f in sol_files:
            shutil.copy(f, starter / f.name)
        meta = {
            "benchmark": "polyglot",
            "task_id": f"polyglot_{name.replace('-', '_')}",
            "exercise": name,
            "prompt_file": "prompt.md",
            "hidden_tests": [f.name for f in test_files],
            "solution_files": [f.name for f in sol_files],
            "test_command": ["python3", "-m", "pytest", "-q"],
        }
        (dst / "task.json").write_text(json.dumps(meta, indent=2))
        print(f"prepared {meta['task_id']}: tests={[f.name for f in test_files]} sol={[f.name for f in sol_files]}")

if __name__ == "__main__":
    main()
