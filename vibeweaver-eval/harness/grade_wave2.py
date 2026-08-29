#!/usr/bin/env python3
"""Grade the ds_wave2 A/B regression: hidden-test pass rates + vibeweaver
adherence artifacts. Usage: python3 grade_wave2.py [--runs ...]"""
import json, re, subprocess, sys
from pathlib import Path

EVAL = Path("/Users/logan/Documents/DEV/SKILLS/vibeweaver-repo/vibeweaver-eval")
WS = EVAL / "workspace" / "iteration-1"
TASKS = WS / "tasks"
RUNS = WS / "runs"
GRADED = WS / "graded"
sys.path.insert(0, str(EVAL / "harness"))
import grade_polyglot, grade_swebench  # noqa: E402

TASK_LIST = [
    "polyglot_bowling", "polyglot_grade_school", "polyglot_list_ops",
    "polyglot_phone_number", "polyglot_pig_latin", "polyglot_robot_name",
    "polyglot_simple_linked_list", "polyglot_transpose", "polyglot_two_bucket",
    "polyglot_variable_length_quantity",
    "swebench_pallets_flask_4045", "swebench_pallets_flask_4992",
    "swebench_psf_requests_3362", "swebench_pytest_dev_pytest_6116",
    "swebench_pytest_dev_pytest_9359", "swebench_sympy_sympy_21627",
]
ARMS = ["ds_wave2_before_forced", "ds_wave2_after_forced"]


def markers(run_dir: Path, arm: str) -> dict:
    m = {"acceptance": False, "verif_log": False, "iter_entries": 0,
         "mode_line": "", "decisions": 0, "decisions_line": False,
         "paused": 0, "gate_line": False, "hardgate1": False, "table": False,
         "covenant_recall": False, "convergence": False,
         "assert_exit": None, "memory": False, "script": False}
    wd_t = run_dir / "tests"
    m["acceptance"] = (wd_t / "acceptance.md").exists()
    vl = wd_t / "verification_log.md"
    m["verif_log"] = vl.exists()
    if vl.exists():
        txt = vl.read_text(errors="replace")
        m["iter_entries"] = len(re.findall(r"^- iter \d+ (?:PASS|FAIL):", txt, re.M))
    if m["acceptance"]:
        m["mode_line"] = ""
    m["decisions"] = 0 if not (wd_t / "decisions.md").exists() else \
        len(re.findall(r"D-\d+", (wd_t / "decisions.md").read_text(errors="replace")))
    m["memory"] = (run_dir / "memory" / "MEMORY.md").exists()
    m["script"] = (run_dir / "script").is_dir()
    log = run_dir / "run.log"
    if log.exists():
        t = log.read_text(errors="replace")
        mm = re.search(r"Mode: ?(AUTO|GUIDED)", t)
        if mm:
            m["mode_line"] = mm.group(1)
        else:
            m["mode_line"] = "(missing)"
        m["paused"] = len(re.findall(r"\[PAUSED\]", t))
        m["gate_line"] = "[Verification Gate]" in t
        m["hardgate1"] = "HARD-GATE-1: NO-TEST-NO-DONE" in t
        m["table"] = "| # | Problem | Research Sources" in t
        m["covenant_recall"] = "[Covenant Recall]" in t
        m["convergence"] = "[Convergence]" in t
        m["decisions_line"] = "[Decisions]" in t
    ap = wd_t / "assert_artifacts.py"
    if ap.exists():
        try:
            r = subprocess.run([sys.executable, str(ap), "--existing"],
                               cwd=run_dir, capture_output=True, text=True, timeout=60)
            m["assert_exit"] = r.returncode
        except Exception:
            m["assert_exit"] = "err"
    return m


def main():
    rows = {}
    for arm in ARMS:
        for task in TASK_LIST:
            run_dir = RUNS / f"{task}__{arm}"
            res_path = RUNS / f"result_{task}__{arm}.json"
            if not run_dir.exists():
                rows[(task, arm)] = {"missing": True}
                continue
            meta = json.loads((TASKS / task / "task.json").read_text())
            run_meta = json.loads(res_path.read_text()) if res_path.exists() else {}
            graded_path = GRADED / f"grade_{task}__{arm}.json"
            if meta["benchmark"] == "polyglot":
                if not graded_path.exists():
                    out = graded_path
                    r = grade_polyglot.grade(TASKS / task, run_dir, out)
                else:
                    r = json.loads(graded_path.read_text())
                passed = bool(r["passed"])
                score = f"{r['tests_passed']}/{r['tests_total']}"
            else:
                if not graded_path.exists():
                    r = grade_swebench.grade(TASKS / task, run_dir, arm)
                    (GRADED / f"grade_{task}__{arm}.json").write_text(
                        json.dumps(r, indent=2, ensure_ascii=False))
                else:
                    r = json.loads(graded_path.read_text())
                passed = bool(r["f2p_pass"]) and bool(r.get("p2p_pass", True))
                score = "f2p" + ("+p2p" if r.get("p2p_pass") else "-p2pFAIL")
            rows[(task, arm)] = {"passed": passed, "score": score,
                                 "wall": run_meta.get("wall_seconds"),
                                 "exit": run_meta.get("exit_code"),
                                 "timeout": run_meta.get("timed_out"),
                                 **markers(run_dir, arm)}
    # print comparison
    print(f"{'task':<38} | {'BEFORE':<28} | {'AFTER':<28} | delta")
    print("-" * 110)
    bp = ap_ = 0
    for task in TASK_LIST:
        b, a = rows.get((task, ARMS[0]), {}), rows.get((task, ARMS[1]), {})
        def cell(d):
            if d.get("missing"):
                return "MISSING"
            p = "PASS" if d["passed"] else "fail"
            wall = d.get("wall") or "?"
            ad = []
            if d["mode_line"]:
                ad.append(d["mode_line"][:5])
            if d["decisions"]:
                ad.append(f"D{d['decisions']}")
            if d["paused"]:
                ad.append(f"PAUSE{d['paused']}")
            if not d["gate_line"]:
                ad.append("NOGATE")
            if d["assert_exit"] not in (None, 0):
                ad.append(f"assert={d['assert_exit']}")
            return f"{p} {d['score']:<7} {str(wall)+'s':<6} {'/'.join(ad)}"
        bs, as_ = 1 if b.get("passed") else 0, 1 if a.get("passed") else 0
        bp += bs; ap_ += as_
        delta = {1: "+1", 0: "=", -1: "-1"}[as_ - bs]
        print(f"{task:<38} | {cell(b):<28} | {cell(a):<28} | {delta}")
    print("-" * 110)
    print(f"TOTAL hidden-test pass: BEFORE {bp}/16 ({100*bp//16}%)  AFTER {ap_}/16 ({100*ap_//16}%)  delta {ap_-bp:+d}")
    # adherence rollup
    for arm in ARMS:
        rs = [rows.get((t, arm), {}) for t in TASK_LIST]
        rs = [r for r in rs if not r.get("missing")]
        n = len(rs)
        if not n:
            continue
        print(f"\n{arm}: n={n} mode_declared={sum(1 for r in rs if r['mode_line'] in ('AUTO','GUIDED'))}/{n}"
              f" acceptance={sum(1 for r in rs if r['acceptance'])}/{n}"
              f" verif_log={sum(1 for r in rs if r['verif_log'])}/{n}"
              f" decisions={sum(1 for r in rs if r['decisions'])}/{n}"
              f" gate_line={sum(1 for r in rs if r['gate_line'])}/{n}"
              f" hardgate1={sum(1 for r in rs if r['hardgate1'])}/{n}"
              f" table={sum(1 for r in rs if r['table'])}/{n}"
              f" paused={sum(r['paused'] for r in rs)}"
              f" assert_exit0={sum(1 for r in rs if r['assert_exit']==0)}/{sum(1 for r in rs if r['assert_exit'] is not None)}")
    out = WS / "graded" / "wave2_ab_summary.json"
    out.write_text(json.dumps({f"{t}__{a}": v for (t, a), v in rows.items()}, indent=2, ensure_ascii=False, default=str))
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
