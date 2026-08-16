#!/usr/bin/env python3
"""Validate SWE-bench harness: empty run must FAIL f2p, gold run must PASS."""
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "iteration-1"
TASKS = WS / "tasks"
RUNS = WS / "runs"

def make_run(task_dir, arm):
    meta = json.loads((task_dir / "task.json").read_text())
    run_dir = RUNS / f"{meta['task_id']}__{arm}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    subprocess.run(["git", "clone", "--quiet", "--shared", meta["repo_path"], str(run_dir)], check=True)
    subprocess.run(["git", "-C", str(run_dir), "checkout", "--quiet", "-f", meta["base_commit"]], check=True)
    subprocess.run(["git", "-C", str(run_dir), "clean", "-fdq"], check=True)
    return run_dir

def main():
    import grade_swebench as gs
    tasks = sorted(d.name for d in TASKS.iterdir() if d.name.startswith("swebench_"))
    for tname in tasks:
        task_dir = TASKS / tname
        meta = json.loads((task_dir / "task.json").read_text())
        # empty
        make_run(task_dir, "goldcheck_empty")
        r_empty = gs.grade(task_dir, RUNS / f"{tname}__goldcheck_empty", "goldcheck_empty")
        # gold
        run_dir = make_run(task_dir, "goldcheck_gold")
        p = subprocess.run(["git", "apply", "--whitespace=nowarn"], cwd=str(run_dir),
                           input=meta["gold_patch"], capture_output=True, text=True)
        assert p.returncode == 0, f"gold apply failed: {p.stderr[:500]}"
        r_gold = gs.grade(task_dir, RUNS / f"{tname}__goldcheck_gold", "goldcheck_gold")
        # determine P2P guard: sample 4 seeded P2P, keep those passing with gold
        random.seed(7)
        candidates = random.sample(meta["PASS_TO_PASS"], min(4, len(meta["PASS_TO_PASS"])))
        guard = []
        for c in candidates:
            r = gs.run_tests(WS / "venvs" / meta["instance_id"], RUNS / f"{tname}__goldcheck_gold", [c])
            if r[0]:
                guard.append(c)
        meta["p2p_guard"] = guard
        (task_dir / "task.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        status = "OK " if (not r_empty["f2p_pass"] and r_gold["f2p_pass"] and guard) else "BAD"
        print(f"{status} {tname}: empty_f2p_pass={r_empty['f2p_pass']} "
              f"gold_f2p_pass={r_gold['f2p_pass']} gold_p2p={r_gold.get('p2p_pass')} "
              f"p2p_guard={guard} notes_empty={r_empty['notes']} notes_gold={r_gold['notes']}")

if __name__ == "__main__":
    main()
