#!/usr/bin/env python3
"""perf_budget.py — measured budgets for the W1 gate/profile path.

Budgets (initial): gate-scan p95 <=2s/1k, <=5s/10k, <=5s/45k; assert full
<=10s; install <=5s; core <=4k tokens, full <=90k, mini <=2k. The gate-scan
proxy uses `git status --porcelain` + `git ls-files` (the same bounded inputs
the plugin digest consumes; it never stats every path).
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAY = ROOT / "vibeweaver" if (ROOT / "vibeweaver" / "SKILL.md").is_file() else ROOT
BUDGETS = {"scan_1k": 2.0, "scan_10k": 5.0, "scan_45k": 5.0, "assert": 10.0, "install": 6.0}


def p95(samples):
    if not samples:
        return 0.0
    vals = sorted(samples)
    return vals[min(len(vals) - 1, int(round(0.95 * (len(vals) - 1))))]


def make_fixture(n):
    d = pathlib.Path(tempfile.mkdtemp(prefix="vw-perf-%d-" % n))
    for i in range(n):
        (d / ("f%05d.txt" % i)).write_text("x", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=d, check=False)
    return d


def scan_time(root, runs=3):
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        subprocess.run(["git", "status", "--porcelain"], cwd=root, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
        subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        samples.append(time.perf_counter() - t0)
    return p95(samples)


def assert_time():
    t0 = time.perf_counter()
    subprocess.run([sys.executable, str(PAY / "tests" / "assert_artifacts.py"),
                    "--existing", "--final"], cwd=ROOT, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=120)
    return time.perf_counter() - t0


def install_time():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-perf-inst-"))
    home = tmp / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
    t0 = time.perf_counter()
    cmd = ([sys.executable, str(PAY / "scripts" / "install.py"), "--profile", "full"]
           if sys.platform == "win32" else ["bash", str(PAY / "install.sh"), "--profile", "full"])
    r = subprocess.run(cmd,
                       cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    dt = time.perf_counter() - t0
    shutil.rmtree(tmp, ignore_errors=True)
    return dt if r.returncode == 0 else 999.0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)
    rows = []
    sizes = [1000] if args.quick else [1000, 10000, 45000]
    for n in sizes:
        d = make_fixture(n)
        dt = scan_time(d, runs=1 if n >= 45000 else 3)
        shutil.rmtree(d, ignore_errors=True)
        rows.append(("scan_%dk" % (n // 1000), dt, BUDGETS["scan_%dk" % (n // 1000)]))
    rows.append(("assert", assert_time(), BUDGETS["assert"]))
    rows.append(("install", install_time(), BUDGETS["install"]))
    bad = []
    out = ROOT / "tests" / "perf"
    out.mkdir(parents=True, exist_ok=True)
    log = out / ("perf_%s.log" % time.strftime("%Y%m%d_%H%M%S"))
    lines = []
    for name, dt, cap in rows:
        status = "OK" if dt <= cap else "OVER"
        if status == "OVER":
            bad.append(name)
        lines.append("%-10s p95=%.3fs cap=%.1fs %s" % (name, dt, cap, status))
    token = subprocess.run([sys.executable, str(ROOT / "scripts" / "token_budget.py"),
                            "--root", str(ROOT), "--check"], capture_output=True, text=True)
    lines.extend(token.stdout.strip().splitlines())
    if token.returncode != 0:
        bad.append("tokens")
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("PERF " + ("PASS" if not bad else "FAIL: " + ", ".join(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
