#!/usr/bin/env python3
"""Grade a SWE-bench run: extract agent diff, reset, apply test_patch, run F2P + P2P sample."""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "iteration-1"
TASKS = WS / "tasks"
RUNS = WS / "runs"
GRADED = WS / "graded"
P2P_SAMPLE = 3

def sh(cmd, cwd=None, timeout=900):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=False, timeout=timeout)
    out = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""
    err = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""
    return r.returncode, out, err

def resolve_node_id(venv_python, repo_path, node):
    """Resolve bare test names (e.g. 'test_Abs') to a runnable node id."""
    if "::" in node:
        return node
    m = re.match(r"^(\w+)", node)
    name = m.group(1) if m else node
    r = subprocess.run(["grep", "-rl", f"def {name}", str(repo_path)],
                       capture_output=True, text=True, cwd=str(repo_path))
    files = [l for l in r.stdout.splitlines() if l.endswith(".py")]
    if files:
        rel = str(Path(files[0]).relative_to(repo_path))
        return f"{rel}::{node}"
    return node

def ensure_install(venv, run_dir):
    """Point the venv's package install at the (patched) run_dir clone."""
    py = venv / "bin" / "python"
    attempts = [
        ["-e", str(run_dir), "--no-deps"],
        ["-e", str(run_dir), "--no-deps", "--no-build-isolation"],
        [str(run_dir), "--no-deps"],
    ]
    for extra in attempts:
        r = subprocess.run([str(py), "-m", "pip", "install", "-q"] + extra,
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            return True
    return False

def run_tests(venv, repo_path, nodes, timeout=1200):
    if not nodes:
        return True, []
    resolved = [resolve_node_id(venv, repo_path, n) for n in nodes]
    cmd = [str(venv / "bin" / "python"), "-m", "pytest",
           "-q", "-p", "no:cacheprovider",
           "-W", "default::DeprecationWarning"]
    cmd += resolved
    rc, out, err = sh(cmd, cwd=str(repo_path), timeout=timeout)
    passed = rc == 0
    summary = (out + err).strip().splitlines()
    tail = summary[-3:] if summary else []
    return passed, tail

def grade(task_dir: Path, run_dir: Path, arm: str) -> dict:
    meta = json.loads((task_dir / "task.json").read_text())
    venv = WS / "venvs" / meta["instance_id"]
    repo_path = Path(meta["repo_path"])
    result = {
        "task": meta["task_id"], "arm": arm, "instance_id": meta["instance_id"],
        "f2p_pass": False, "p2p_regressions": [], "patch_applied": False,
        "test_patch_applied": False, "notes": [], "f2p_details": [],
    }
    # 1. collect diff from agent workdir vs base_commit (excluding opencode data dirs)
    rc, diff, err = sh(["git", "-C", str(run_dir), "diff", meta["base_commit"],
                        "--", ".", ":(exclude).opencode_data"])
    if rc != 0 or not diff.strip():
        result["notes"].append("no diff produced")
        return result
    # 2. restore base in run_dir
    sh(["git", "-C", str(run_dir), "checkout", "-f", meta["base_commit"]])
    sh(["git", "-C", str(run_dir), "clean", "-fdq", "--exclude=.opencode_data"])
    # 3. apply agent diff
    p = subprocess.run(["git", "apply", "--whitespace=nowarn"],
                       cwd=str(run_dir), input=diff, capture_output=True, text=True)
    if p.returncode != 0:
        result["notes"].append(f"agent patch apply failed: {p.stderr[:300]}")
        return result
    result["patch_applied"] = True
    if not ensure_install(venv, run_dir):
        result["notes"].append("reinstall into run_dir failed")
        return result
    # 4. apply test_patch (restoring any agent-touched test files to base first)
    tp_check = subprocess.run(["git", "apply", "--check", "--whitespace=nowarn"],
                              cwd=str(run_dir), input=meta["test_patch"],
                              capture_output=True, text=True)
    if tp_check.returncode != 0:
        touched = re.findall(r"diff --git a/(\S+) b/", meta["test_patch"])
        for f in touched:
            sh(["git", "-C", str(run_dir), "checkout", "-f", "--", f])
            sh(["git", "-C", str(run_dir), "clean", "-fd", "--", f])
        tp_check = subprocess.run(["git", "apply", "--check", "--whitespace=nowarn"],
                                  cwd=str(run_dir), input=meta["test_patch"],
                                  capture_output=True, text=True)
        if tp_check.returncode != 0:
            result["notes"].append("test_patch apply failed after test-file restore: "
                                   f"{tp_check.stderr[:300]}")
            return result
        result["notes"].append("test_patch applied after restoring agent-touched test files: "
                               + ", ".join(touched[:5]))
    p = subprocess.run(["git", "apply", "--whitespace=nowarn"],
                       cwd=str(run_dir), input=meta["test_patch"], capture_output=True, text=True)
    if p.returncode != 0:
        result["notes"].append(f"test_patch apply failed: {p.stderr[:300]}")
        return result
    result["test_patch_applied"] = True
    # 5. run F2P
    nodes = [resolve_node_id(venv, run_dir, n) for n in meta["FAIL_TO_PASS"]]
    passed, tail = run_tests(venv, run_dir, nodes)
    result["f2p_pass"] = passed
    result["f2p_details"] = [{"node": n, "resolved": resolve_node_id(venv, run_dir, n),
                              "ok": passed} for n in meta["FAIL_TO_PASS"]]
    result["f2p_output_tail"] = tail
    # 6. P2P guard (regression check) — fixed set validated against gold env
    if passed:
        guard = meta.get("p2p_guard", [])
        if not guard:
            random.seed(42 + len(meta["PASS_TO_PASS"]))
            guard = random.sample(meta["PASS_TO_PASS"], min(P2P_SAMPLE, len(meta["PASS_TO_PASS"])))
        p2p_pass, _ = run_tests(venv, run_dir, guard)
        result["p2p_guard"] = guard
        result["p2p_pass"] = p2p_pass
        if not p2p_pass:
            result["p2p_regressions"] = guard
    else:
        result["p2p_guard"] = meta.get("p2p_guard", [])
        result["p2p_pass"] = False
    return result

def main():
    task_id, arm = sys.argv[1], sys.argv[2]
    task_dir = TASKS / task_id
    run_dir = RUNS / f"{task_id}__{arm}"
    result = grade(task_dir, run_dir, arm)
    GRADED.mkdir(parents=True, exist_ok=True)
    out = GRADED / f"grade_{task_id}__{arm}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"{task_id} {arm}: f2p_pass={result['f2p_pass']} patch={result['patch_applied']} "
          f"notes={result['notes']}")

if __name__ == "__main__":
    main()
