#!/usr/bin/env python3
"""Aggregate polyglot A/B over N repeat rounds: per-task pass rate, mean
hidden-test score, flip analysis. Usage: python3 grade_wave2_avg.py"""
import json, re, sys
from pathlib import Path

EVAL = Path("/Users/logan/Documents/DEV/SKILLS/vibeweaver-repo/vibeweaver-eval")
WS = EVAL / "workspace" / "iteration-1"
RUNS = WS / "runs"
GRADED = WS / "graded"
sys.path.insert(0, str(EVAL / "harness"))
import grade_polyglot  # noqa: E402

POLY = ["polyglot_bowling", "polyglot_grade_school", "polyglot_list_ops",
        "polyglot_phone_number", "polyglot_pig_latin", "polyglot_robot_name",
        "polyglot_simple_linked_list", "polyglot_transpose", "polyglot_two_bucket",
        "polyglot_variable_length_quantity"]
RUNS_PER_ARM = ["ds_wave2_before_forced", "ds_wave2_after_forced",
                "ds_wave2_before_r2_forced", "ds_wave2_after_r2_forced",
                "ds_wave2_before_r3_forced", "ds_wave2_after_r3_forced",
                "ds_wave2_before_r4_forced", "ds_wave2_after_r4_forced"]
ARMS = [("BEFORE", [r for r in RUNS_PER_ARM if "before" in r]),
        ("AFTER", [r for r in RUNS_PER_ARM if "after" in r])]


def grade_run(task, arm):
    run_dir = RUNS / f"{task}__{arm}"
    if not run_dir.exists():
        return None
    gp = GRADED / f"grade_{task}__{arm}.json"
    if not gp.exists():
        r = grade_polyglot.grade(WS / "tasks" / task, run_dir, gp)
    else:
        r = json.loads(gp.read_text())
    return r


def main():
    summary = {}
    for task in POLY:
        per_task = {}
        for label, arms in ARMS:
            scores, passes, runs = [], 0, 0
            for arm in arms:
                r = grade_run(task, arm)
                if r is None:
                    continue
                runs += 1
                scores.append((r["tests_passed"], r["tests_total"]))
                passes += 1 if r["passed"] else 0
            per_task[label] = {"runs": runs, "pass_runs": passes,
                               "scores": scores,
                               "pass_rate": passes / runs if runs else 0.0,
                               "mean_frac": (sum(p / t for p, t in scores) / len(scores))
                                            if scores else 0.0}
        summary[task] = per_task

    print(f"{'task':<34} | {'BEFORE pass':>11} {'mean':>6} | {'AFTER pass':>11} {'mean':>6} | flips")
    print("-" * 92)
    tot = {l: {"pass_runs": 0, "runs": 0, "mean": 0.0} for l, _ in ARMS}
    for task, d in summary.items():
        b, a = d["BEFORE"], d["AFTER"]
        flips = []
        for i in range(b["runs"]):
            for j in range(a["runs"]):
                pass
        line = f"{task:<34} | {b['pass_runs']:>4}/{b['runs']:<2} {b['mean_frac']:>10.3f} | " \
               f"{a['pass_runs']:>4}/{a['runs']:<2} {a['mean_frac']:>10.3f}"
        print(line)
        for l in ("BEFORE", "AFTER"):
            tot[l]["pass_runs"] += d[l]["pass_runs"]
            tot[l]["runs"] += d[l]["runs"]
            tot[l]["mean"] += d[l]["mean_frac"]
    print("-" * 92)
    for l, _ in ARMS:
        t = tot[l]
        print(f"{l}: total pass-runs {t['pass_runs']}/{t['runs']} "
              f"({100*t['pass_runs']/t['runs']:.1f}%) · "
              f"mean test-fraction {t['mean']/len(POLY):.4f}")
    out = GRADED / "wave2_ab_avg.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
