#!/usr/bin/env python3
"""scripts/eval_token_report.py — lab 运行的 token / 墙钟 / 判定汇总表。

遍历 <root>/**/trajectory.json（及同目录的 cost.json、verdict.json），按
model × arm × 任务族 分组输出 markdown 表：

  任务族：g3_comp* → compliance（判 skill 自身产物格式）
          *teeth*   → teeth
          其余      → capability（纯功能题）

列：n、无 token 数据的 run 数（多为超时被杀、事件流丢失）、input/output/total
token 中位数、步数中位数、墙钟中位数、pass/fail/indeterminate。中位数只在有
token 数据的 run 上计算——无数据 ≠ 零成本，单列计数而不是填 0。

用法：
  python3 scripts/eval_token_report.py [--root tests/eval] [--out FILE]
  python3 scripts/eval_token_report.py --backfill   # 把汇总写进各 cost.json 的
                                                    # tokens 字段（幂等，只改该键）
"""
import argparse
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eval_tokens  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def family(scenario):
    if scenario.startswith("g3_comp"):
        return "compliance"
    if "teeth" in scenario:
        return "teeth"
    return "capability"


def _load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def collect(root):
    rows = []
    for traj_p in sorted(pathlib.Path(root).rglob("trajectory.json")):
        d = traj_p.parent
        traj = _load(traj_p)
        cost = _load(d / "cost.json")
        verdict = _load(d / "verdict.json")
        parts = d.name.split("__")
        scenario = traj.get("scenario") or parts[0]
        arm = cost.get("arm") or (parts[1] if len(parts) >= 3 else "?")
        stdout = (traj.get("agent") or {}).get("stdout", "")
        rows.append({
            "dir": d, "scenario": scenario, "family": family(scenario),
            "arm": arm, "model": cost.get("model") or "?",
            "wall": cost.get("wall_seconds"),
            "verdict": verdict.get("verdict"),
            "tokens": eval_tokens.summarize_tokens(stdout),
        })
    return rows


def _median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def aggregate(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r["model"], r["arm"], r["family"]), []).append(r)
    out = {}
    for key, rs in groups.items():
        tk = [r["tokens"] for r in rs if r["tokens"]]
        out[key] = {
            "n": len(rs),
            "no_tokens": len(rs) - len(tk),
            "median_input": _median([t["input"] for t in tk]),
            "median_output": _median([t["output"] + t["reasoning"] for t in tk]),
            "median_total": _median([t["total"] for t in tk]),
            "median_steps": _median([t["steps"] for t in tk]),
            "median_wall": _median([r["wall"] for r in rs]),
            "pass": sum(1 for r in rs if r["verdict"] == "pass"),
            "fail": sum(1 for r in rs if r["verdict"] == "fail"),
            "indeterminate": sum(1 for r in rs
                                 if r["verdict"] not in ("pass", "fail")),
        }
    return out


def _fmt(v):
    if v is None:
        return "—"
    return "%.0f" % v if isinstance(v, float) else str(v)


def render_markdown(groups):
    lines = [
        "| model | arm | family | n | no tokens | median input | median output |"
        " median total | median steps | median wall (s) | pass / fail / indet |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, arm, fam) in sorted(groups):
        g = groups[(model, arm, fam)]
        lines.append("| %s | %s | %s | %d | %d | %s | %s | %s | %s | %s | %d / %d / %d |" % (
            model, arm, fam, g["n"], g["no_tokens"], _fmt(g["median_input"]),
            _fmt(g["median_output"]), _fmt(g["median_total"]),
            _fmt(g["median_steps"]), _fmt(g["median_wall"]),
            g["pass"], g["fail"], g["indeterminate"]))
    return "\n".join(lines) + "\n"


def backfill(root):
    """Write the summary into cost.json `tokens` where it is missing. Returns
    the number of files changed; runs without step_finish events stay null."""
    changed = 0
    for r in collect(root):
        p = r["dir"] / "cost.json"
        if not r["tokens"] or not p.is_file():
            continue
        d = _load(p)
        if d.get("tokens") == r["tokens"]:
            continue
        d["tokens"] = r["tokens"]
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        changed += 1
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "tests" / "eval"))
    ap.add_argument("--out", default="")
    ap.add_argument("--backfill", action="store_true")
    a = ap.parse_args(argv)
    if a.backfill:
        print("backfilled %d cost.json file(s)" % backfill(a.root))
        return 0
    md = render_markdown(aggregate(collect(a.root)))
    if a.out:
        pathlib.Path(a.out).write_text(md, encoding="utf-8")
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
