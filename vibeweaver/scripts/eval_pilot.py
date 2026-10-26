#!/usr/bin/env python3
"""eval_pilot.py — G3 pilot 战役编排 + 聚合（对齐 docs/EVAL_G3_PREREG.md）。

用法：
  校准   python3 scripts/eval_pilot.py --model biklimax/qwen3.8_27b --phase calibrate
  pilot  python3 scripts/eval_pilot.py --model biklimax/qwen3.8_27b --phase pilot [--limit N]
  报告   python3 scripts/eval_pilot.py --phase report

arm 构造见 docs/EVAL_G3_ARMS.md（prereg 未规定，本波定稿）。
`indeterminate` 单列、永不计为 pass（prereg Analysis 段）。
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVAL_RUN = ROOT / "scripts" / "eval_run.py"
SCEN = ROOT / "tests" / "eval" / "lab" / "scenarios"
OUT_ROOT = ROOT / "tests" / "eval" / "g3" / "runs"
SUMMARY = ROOT / "tests" / "eval" / "g3" / "summary.json"
MANIFEST = ROOT / "tests" / "eval" / "g3" / "pilot_manifest.json"
DEFAULT_ARMS = ["bare", "core", "full_forced", "mini_forced"]
# v2 (2026-10-25): the product form. Kept OUT of DEFAULT_ARMS so the frozen G3
# campaign math never silently changes; v2 campaigns pass --arms full_deployed.


def tasks_all():
    return sorted(p.stem for p in SCEN.glob("g3_*.json"))


def run_id(task, arm, seed):
    return "%s__%s__s%d" % (task, arm, seed)


def label_paths(label):
    """label 隔离 manifest/summary（W2-T14b：comp 战役不得覆盖 pilot 的 58-run 记录）。
    label='pilot' 保持历史文件名（test_eval_validity 锚定 summary.json）。"""
    return (ROOT / "tests" / "eval" / "g3" / (("pilot_" if label == "pilot" else label + "_") + "manifest.json"),
            ROOT / "tests" / "eval" / "g3" / (LABEL_SUMMARY.get(label, label + "_summary.json")))


LABEL_SUMMARY = {"pilot": "summary.json"}


def run_one(task, arm, seed, model, out_root, timeout=2400):
    out = out_root / run_id(task, arm, seed)
    if (out / "verdict.json").is_file():
        return out, "cached"
    t0 = time.time()
    r = subprocess.run(
        [sys.executable, str(EVAL_RUN), "--scenario", task, "--agent", "opencode",
         "--model", model, "--arm", arm, "--seed", str(seed), "--out", str(out)],
        capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    meta = {"task": task, "arm": arm, "seed": seed, "model": model,
            "exit": r.returncode, "wall_seconds": round(time.time() - t0, 1),
            "stdout_tail": (r.stdout or "")[-500:], "stderr_tail": (r.stderr or "")[-500:]}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out, ("ok" if r.returncode == 0 else "nonzero-exit")


def wilson(k, n, z=1.959963984540054):
    if n <= 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(centre - half, 4), round(centre + half, 4)]


def collect(out_root):
    rows = []
    for v in sorted(out_root.glob("*/verdict.json")):
        try:
            d = json.loads(v.read_text(encoding="utf-8"))
            c = json.loads((v.parent / "cost.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rid = v.parent.name
        parts = rid.split("__")
        rows.append({
            "id": rid, "task": d.get("scenario") or (parts[0] if parts else ""),
            "model": c.get("model"),
            "arm": c.get("arm", "bare"), "seed": c.get("seed", 0),
            "verdict": d.get("verdict", "indeterminate"),
            "wall_seconds": c.get("wall_seconds"),
            "skill_fingerprint": (c.get("skill_fingerprint") or {}).get("sha256"),
        })
    return rows


def report(out_root, label="pilot", only=""):
    rows = collect(out_root)
    if only:
        rows = [r for r in rows if r["task"].startswith(only)]
    arms = sorted({r["arm"] for r in rows}) or DEFAULT_ARMS
    tasks = sorted({r["task"] for r in rows})
    manifest_path, summary_path = label_paths(label)
    by_arm = {}
    for arm in arms:
        rs = [r for r in rows if r["arm"] == arm]
        k = sum(1 for r in rs if r["verdict"] == "pass")
        f = sum(1 for r in rs if r["verdict"] == "fail")
        ind = sum(1 for r in rs if r["verdict"] == "indeterminate")
        n = k + f
        walls = [r["wall_seconds"] for r in rs if isinstance(r["wall_seconds"], (int, float))]
        by_arm[arm] = {
            "runs": len(rs), "pass": k, "fail": f, "indeterminate": ind,
            "n_effective": n, "pass_rate": (round(k / n, 4) if n else None),
            "ci95": wilson(k, n),
            "mean_wall_seconds": (round(sum(walls) / len(walls), 1) if walls else None),
        }
    # paired by task against bare (seed-level 1/0)；indeterminate 单列、不进配对
    # （prereg：「Report `indeterminate` separately; it is never counted as pass」——
    #  也不得计为 fail，否则会被算成 arm 的损失）
    paired = {}
    base = {r["task"]: {} for r in rows}
    for r in rows:
        if r["verdict"] not in ("pass", "fail"):
            continue
        base.setdefault(r["task"], {})[(r["arm"], r["seed"])] = (1 if r["verdict"] == "pass" else 0)
    for arm in arms:
        if arm == "bare":
            continue
        diffs = []
        for task, cells in base.items():
            for (a, seed), v in cells.items():
                if a != arm:
                    continue
                b = cells.get(("bare", seed))
                if b is not None:
                    diffs.append(v - b)
        paired[arm] = {
            "paired_n": len(diffs),
            "mean_diff_vs_bare": (round(sum(diffs) / len(diffs), 4) if diffs else None),
            "wins": sum(1 for d in diffs if d > 0), "losses": sum(1 for d in diffs if d < 0),
            "indeterminate_excluded": True,
        }
    mde = None
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_power.py"),
                            "--n", str(max(1, len(tasks))), "--seeds", "3", "--json"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            mde = json.loads(r.stdout).get("mde")
    except Exception:
        pass
    planned = len(tasks_all()) * len(DEFAULT_ARMS) * 3
    try:                      # 战役 manifest 才是计划口径（中途加任务不改变已完成战役的 planned）
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(m.get("planned"), int):
            planned = m["planned"]
    except (OSError, ValueError):
        pass
    if only:                  # 过滤口径：planned 按「manifest 的 arms/seeds × 过滤后任务集」重派生
        m = {}
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        scope_tasks = [t for t in (m.get("tasks") or tasks_all())
                       if isinstance(t, str) and t.startswith(only)]
        planned = (len(scope_tasks) * len(m.get("arms") or DEFAULT_ARMS)
                   * len(m.get("seeds") or [0, 1, 2]))
    summary = {
        "status": "complete" if len(rows) >= planned else "incomplete",
        "model": next((r.get("model") for r in rows if r.get("model")), None),
        "n_tasks": len(tasks), "tasks": tasks, "seeds": sorted({r["seed"] for r in rows}),
        "arms": by_arm, "paired_vs_bare": paired, "mde": mde,
        "planned_runs": planned, "observed_runs": len(rows),
        "cost": {"total_wall_seconds": round(sum(r["wall_seconds"] for r in rows
                                                 if isinstance(r["wall_seconds"], (int, float))), 1)},
        "indeterminate_excluded_from_pass": True,
        "seeds_are_replicates": True,
        "task_filter": only or None,
        "notes": "arm 构造见 docs/EVAL_G3_ARMS.md（prereg 未规定）；G1 set 外部不可得 → private held-out 任务集",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["calibrate", "pilot", "report"], default="report")
    ap.add_argument("--model", default="biklimax/qwen3.8_27b")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--arms", default="")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--out-root", default=str(OUT_ROOT))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--label", default="pilot",
                    help="campaign label; isolates manifest/summary per campaign (pilot|comp|…)")
    ap.add_argument("--run-budget", type=int, default=2400,
                    help="per-run subprocess budget in seconds (must exceed the scenario's "
                         "agent timeout_seconds or the harness kills a still-valid run)")
    ap.add_argument("--only", default="",
                    help="task prefix filter for the report (e.g. g3_comp_); planned is "
                         "re-derived over the filtered task set")
    args = ap.parse_args(argv)

    out_root = pathlib.Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    manifest_path, _ = label_paths(args.label)
    if args.phase == "report":
        report(out_root, args.label, args.only)
        return 0

    tasks = [t for t in args.tasks.split(",") if t] or tasks_all()
    if args.phase == "calibrate":
        arms, seeds = ["bare"], [0]
    else:
        arms = [a for a in args.arms.split(",") if a] or DEFAULT_ARMS
        seeds = [int(s) for s in args.seeds.split(",") if s.strip() != ""]

    plan = [(t, a, s) for t in tasks for a in arms for s in seeds]
    if args.limit:
        plan = plan[:args.limit]
    manifest = {"model": args.model, "phase": args.phase, "tasks": tasks, "arms": arms,
                "seeds": seeds, "planned": len(plan), "runs": []}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("eval_pilot: %d runs planned (%d tasks x %d arms x %d seeds) model=%s label=%s"
          % (len(plan), len(tasks), len(arms), len(seeds), args.model, args.label))
    done = 0
    for task, arm, seed in plan:
        out, state = run_one(task, arm, seed, args.model, out_root, timeout=args.run_budget)
        v = "n/a"
        if (out / "verdict.json").is_file():
            try:
                v = json.loads((out / "verdict.json").read_text(encoding="utf-8")).get("verdict")
            except (OSError, ValueError):
                v = "unreadable"
        done += 1
        print("[%d/%d] %s -> %s (%s)" % (done, len(plan), out.name, v, state), flush=True)
    manifest_path.write_text(json.dumps({
        "model": args.model, "phase": args.phase, "tasks": tasks, "arms": arms,
        "seeds": seeds, "planned": len(plan), "runs": sorted(p.name for p in out_root.glob("*/")),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report(out_root, args.label, args.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
