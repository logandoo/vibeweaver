#!/usr/bin/env python3
"""Aggregate grading results into an A/B report."""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "iteration-1"
GRADED = WS / "graded"
RUNS = WS / "runs"
ARMS = ["baseline", "with_skill", "with_skill_forced", "with_skill_v2",
        "with_skill_mini", "with_skill_mini_forced", "ds_baseline", "ds_full",
        "ds_mini", "ds_full_forced", "with_skill_mini_v2", "ds_mini_v2"]

def load_all():
    rows = []
    for gf in sorted(GRADED.glob("grade_*.json")):
        g = json.loads(gf.read_text())
        g["arm"] = g.get("arm") or gf.stem.split("__")[-1]
        g["task"] = g.get("task") or gf.stem[len("grade_"):].split("__")[0]
        rp = RUNS / f"result_{g['task']}__{g['arm']}.json"
        r = json.loads(rp.read_text()) if rp.exists() else {}
        rows.append({"graded": g, "run": r})
    return rows

def main():
    rows = load_all()
    report = {"benchmarks": {}}
    tasks = sorted({r["graded"]["task"] for r in rows})
    for task in tasks:
        bench = "swebench_lite" if task.startswith("swebench_") else "polyglot"
        report["benchmarks"].setdefault(bench, []).append(task)
    print("=" * 100)
    print("VIBEWEAVER SKILL A/B EVAL — qwen3.6-27b  |  opencode 1.18.10")
    print("=" * 100)
    for bench, task_list in report["benchmarks"].items():
        print(f"\n### {bench}  ({len(task_list)} tasks)")
        print(f"{'task':<45} {'arm':<11} {'PASS':<5} {'wall_s':<8} {'detail'}")
        print("-" * 100)
        per_arm = {a: [] for a in ARMS}
        for task in task_list:
            for arm in ARMS:
                match = [r for r in rows if r["graded"]["task"] == task and r["graded"]["arm"] == arm]
                if not match:
                    print(f"{task:<45} {arm:<11} {'NO RUN':<5}")
                    continue
                g, r = match[0]["graded"], match[0]["run"]
                if bench == "polyglot":
                    ok = g["passed"]
                    detail = f"{g['tests_passed']}/{g['tests_total']} tests"
                else:
                    ok = g["f2p_pass"] and g.get("p2p_pass", False)
                    detail = f"f2p={g['f2p_pass']} p2p={g.get('p2p_pass')} notes={g['notes']}"
                wall = r.get("wall_seconds", "?")
                print(f"{task:<45} {arm:<11} {str(ok):<5} {str(wall):<8} {detail}")
                per_arm[arm].append(1 if ok else 0)
        print("-" * 100)
        for arm in ARMS:
            v = per_arm[arm]
            if v:
                print(f"{arm}: {sum(v)}/{len(v)} pass = {100*sum(v)/len(v):.0f}%")

    # timing / fidelity summary
    print("\n### Timing & process evidence")
    print(f"{'task':<45} {'arm':<11} {'wall_s':<8} {'artifacts'}")
    for task in sorted({r["graded"]["task"] for r in rows}):
        for arm in ARMS:
            match = [r for r in rows if r["graded"]["task"] == task and r["graded"]["arm"] == arm]
            if not match:
                continue
            r = match[0]["run"]
            wd = Path(r["workdir"])
            art = []
            if (wd / "tests" / "acceptance.md").exists(): art.append("acceptance.md")
            if (wd / "tests" / "verification_log.md").exists(): art.append("verif_log")
            if (wd / "script").is_dir(): art.append("script/")
            if (wd / "memory" / "MEMORY.md").exists(): art.append("memory")
            if (wd / "config.toml").exists(): art.append("config.toml")
            if (wd / "tests").is_dir(): art.append("tests/")
            print(f"{task:<45} {arm:<17} {r.get('wall_seconds','?'):<8} {','.join(art) or '-'}")

if __name__ == "__main__":
    main()
