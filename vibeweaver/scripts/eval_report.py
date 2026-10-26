#!/usr/bin/env python3
"""eval_report.py — aggregate eval run dirs with Wilson intervals."""
import argparse
import json
import math
import pathlib
import sys


def wilson(k, n, z=1.959963984540054):
    if n <= 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(centre - half, 4), round(centre + half, 4)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="tests/eval/runs")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.runs)
    counts = {"pass": 0, "fail": 0, "indeterminate": 0}
    costs = []
    for v in sorted(root.glob("*/verdict.json")):
        try:
            d = json.loads(v.read_text(encoding="utf-8"))
            counts[d.get("verdict", "indeterminate")] = counts.get(d.get("verdict", "indeterminate"), 0) + 1
        except (OSError, ValueError):
            counts["indeterminate"] += 1
        c = v.parent / "cost.json"
        if c.is_file():
            try:
                w = json.loads(c.read_text(encoding="utf-8")).get("wall_seconds")
                if isinstance(w, (int, float)):
                    costs.append(w)
            except (OSError, ValueError):
                pass
    n = counts["pass"] + counts["fail"]
    summary = {"n": n, "counts": counts, "pass_rate": (counts["pass"] / n if n else None),
               "ci95": wilson(counts["pass"], n), "mean_wall_seconds": (sum(costs) / len(costs) if costs else None),
               "indeterminate_excluded_from_pass": True}
    out = pathlib.Path(args.out) if args.out else root / "summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
