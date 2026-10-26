#!/usr/bin/env python3
"""eval_power.py — MDE/power for the G3 paired design (W2 Task 12.5)."""
import argparse
import math
import sys

Z95 = 1.959963984540054
Z80 = 0.8416212335729143


def mde(n, seeds=3, p=0.5, alpha_z=Z95, power_z=Z80):
    n_eff = max(1, int(n) * max(1, int(seeds)))
    return (alpha_z + power_z) * math.sqrt(2 * p * (1 - p) / n_eff)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    val = mde(args.n, args.seeds)
    if args.json:
        print('{"n": %d, "seeds": %d, "p": 0.5, "mde": %.4f}' % (args.n, args.seeds, val))
    else:
        print(f"MDE n={args.n} seeds={args.seeds} p=0.5: {val:.3f} (absolute pass-rate difference, 95% CI / 80% power)")
        print("If MDE > expected effect: add seeds/tasks or label the result directional.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
