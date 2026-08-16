#!/usr/bin/env python3
"""Run opencode eval for both arms: baseline (no skill) vs with_skill (vibeweaver).

Usage:
  python3 run_eval.py --arm baseline|with_skill|both [--benchmark polyglot|swebench_lite|all]
                      [--tasks id1,id2] [--concurrency 3] [--timeout 2400]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "iteration-1"
TASKS = WS / "tasks"
RUNS = WS / "runs"
MODEL = os.environ.get("EVAL_MODEL", "local/qwen3.6-27b")
ARMS = {
    "baseline": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "baseline"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "baseline" / "data"),
    },
    "with_skill": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "with_skill"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "with_skill" / "data"),
    },
    "with_skill_v2": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "with_skill_v2"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "with_skill_v2" / "data"),
    },
    "with_skill_mini": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "with_skill_mini"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "with_skill_mini" / "data"),
    },
    "ds_baseline": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "ds_baseline"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "ds_baseline" / "data"),
    },
    "ds_full": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "ds_full"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "ds_full" / "data"),
    },
    "ds_mini": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "ds_mini"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "ds_mini" / "data"),
    },
    "with_skill_mini_v2": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "with_skill_mini"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "with_skill_mini" / "data"),
    },
    "ds_mini_v2": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "ds_mini"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "ds_mini" / "data"),
    },
    "with_skill_mini_v1b": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "with_skill_mini_v1b"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "with_skill_mini_v1b" / "data"),
    },
    "q38_baseline": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "q38_baseline"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "q38_baseline" / "data"),
    },
    "q38_mini_v2": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "q38_mini"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "q38_mini" / "data"),
    },
    "q38_v2": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "q38_v2"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "q38_v2" / "data"),
    },
    "q38_mini_new": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "q38_mini_new"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "q38_mini_new" / "data"),
    },
    "a3b_baseline": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "a3b_baseline"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "a3b_baseline" / "data"),
    },
    "a3b_mini_old": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "a3b_mini_old"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "a3b_mini_old" / "data"),
    },
    "a3b_mini_new": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "a3b_mini_new"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "a3b_mini_new" / "data"),
    },
    "a3b_full": {
        "XDG_CONFIG_HOME": str(ROOT / "configs" / "a3b_full"),
        "XDG_DATA_HOME": str(ROOT / "configs" / "a3b_full" / "data"),
    },
}
ENV_EXTRA = {
    "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
}

POLYGLOT_PROMPT = """You are working in a coding exercise workspace.

Task: read the file prompt.md and implement the exercise it describes.

Requirements:
- Implement the solution in: {solution_files}
- The starter files contain stubs; replace them with a working implementation.
- Do NOT create or modify any test files.
- Run your code to verify it has no syntax or runtime errors.
When finished, report what you implemented and how you verified it.
"""

SWEBENCH_PROMPT = """You are working in a software repository (the current working directory is a checkout of {repo} at git base commit {base_commit}).

Task: fix the issue described in prompt.md (a real GitHub issue from this project).

Requirements:
- Investigate the codebase to understand the issue, then implement the fix in the SOURCE code (not in tests).
- Hidden tests will verify your fix; also make sure you do not break existing behavior.
- Run relevant existing tests to verify your change where feasible.
When finished, report what you changed and how you verified it.
"""


def build_prompt(task_dir: Path, force_skill: bool = False, cfg_arm: str = "with_skill") -> str:
    meta = json.loads((task_dir / "task.json").read_text())
    if meta["benchmark"] == "polyglot":
        base = POLYGLOT_PROMPT.format(solution_files=", ".join(meta["solution_files"]))
    elif meta["benchmark"] == "flow":
        base = (
            "You are building a small backend service from scratch in the current directory.\n\n"
            "Task: read prompt.md and implement the service it specifies, exactly matching the API contract.\n\n"
            "Requirements:\n"
            "- Implement the service in the current directory; the file(s) must be importable by uvicorn as specified in prompt.md.\n"
            "- Verify your implementation actually works: start the service, call the endpoints, and check the full business flow (not just single calls).\n"
            "- Do NOT modify any files outside the current directory.\n"
            "When finished, report what you implemented and how you verified the whole flow."
        )
    else:
        base = SWEBENCH_PROMPT.format(repo=meta["repo"], base_commit=meta["base_commit"])
    if force_skill:
        skills_dir = ROOT / "configs" / cfg_arm / "opencode" / "skills"
        skill_files = sorted(skills_dir.glob("*/SKILL.md"))
        if not skill_files:
            raise FileNotFoundError(f"no skill found under {skills_dir}")
        content = skill_files[0].read_text()
        return (
            "You MUST follow the workflow rules below for this task. "
            "They come from the skill, which is attached here in full.\n\n"
            "--- SKILL (MANDATORY WORKFLOW) ---\n"
            f"{content}\n"
            "--- END SKILL ---\n\n"
            f"TASK:\n{base}"
        )
    return base


def make_workdir(meta: dict, arm_dir: Path) -> None:
    arm_dir.mkdir(parents=True, exist_ok=True)
    if meta["benchmark"] == "polyglot":
        starter = TASKS / meta["task_id"] / "starter"
        for f in starter.iterdir():
            shutil.copy2(f, arm_dir / f.name)
    elif meta["benchmark"] == "flow":
        sk = TASKS / meta["task_id"] / "skeleton"
        if sk.exists():
            for f in sk.iterdir():
                shutil.copy2(f, arm_dir / f.name)
        return  # else empty scratch dir
    else:
        # local shared-object clone for speed; checkout base commit
        if not (arm_dir / ".git").exists():
            subprocess.run(["git", "clone", "--quiet", "--shared",
                            meta["repo_path"], str(arm_dir)], check=True)
        subprocess.run(["git", "-C", str(arm_dir), "checkout", "--quiet", "-f",
                        meta["base_commit"]], check=True)
        subprocess.run(["git", "-C", str(arm_dir), "clean", "-fdq"], check=True)


def run_one(task_id: str, arm: str, timeout: int, force_skill: bool = False) -> dict:
    task_dir = TASKS / task_id
    meta = json.loads((task_dir / "task.json").read_text())
    cfg_arm = arm
    if force_skill:
        arm = f"{arm}_forced"
    arm_dir = RUNS / f"{task_id}__{arm}"
    make_workdir(meta, arm_dir)
    shutil.copy2(task_dir / "prompt.md", arm_dir / "prompt.md")
    prompt = build_prompt(task_dir, force_skill, cfg_arm)
    env = dict(os.environ)
    env.update(ARMS[cfg_arm])
    env.update(ENV_EXTRA)
    env["XDG_DATA_HOME"] = str(WS / ".run_data" / f"{task_id}__{arm}")
    log_path = arm_dir / "run.log"
    t0 = time.monotonic()
    proc = subprocess.Popen(
        ["opencode", "run", "--auto", "--model", MODEL, "--dir", str(arm_dir), prompt],
        stdout=open(log_path, "w"), stderr=subprocess.STDOUT, env=env,
    )
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        timed_out = True
    wall = time.monotonic() - t0
    result = {
        "task": task_id, "arm": arm, "exit_code": proc.returncode,
        "wall_seconds": round(wall, 1), "timed_out": timed_out,
        "log": str(log_path), "workdir": str(arm_dir),
    }
    rp = RUNS / f"result_{task_id}__{arm}.json"
    rp.write_text(json.dumps(result, indent=2))
    print(f"[{arm}] {task_id} done in {wall:.0f}s exit={proc.returncode} timeout={timed_out}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["baseline", "with_skill", "with_skill_v2",
                                      "with_skill_mini", "ds_baseline", "ds_full",
                                      "ds_mini", "with_skill_mini_v2", "ds_mini_v2",
                                      "with_skill_mini_v1b", "q38_baseline",
                                      "q38_mini_v2", "q38_v2", "q38_mini_new",
                                      "a3b_baseline", "a3b_mini_old", "a3b_mini_new",
                                      "a3b_full",
                                      "both"], default="both")
    ap.add_argument("--benchmark", choices=["polyglot", "swebench_lite", "all"], default="all")
    ap.add_argument("--tasks", default="", help="comma separated task ids (override benchmark filter)")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--force-skill", action="store_true",
                    help="inject the vibeweaver SKILL.md content into the prompt (forced-load arm)")
    args = ap.parse_args()

    tasks = sorted(d.name for d in TASKS.iterdir() if (d / "task.json").exists())
    if args.tasks:
        wanted = set(args.tasks.split(","))
        tasks = [t for t in tasks if t in wanted]
    elif args.benchmark != "all":
        bench = "polyglot" if args.benchmark == "polyglot" else "swebench_lite"
        prefix = "swebench_" if bench == "swebench_lite" else "polyglot_"
        tasks = [t for t in tasks if t.startswith(prefix)]

    arms = ["baseline", "with_skill"] if args.arm == "both" else [args.arm]
    jobs = [(t, a) for t in tasks for a in arms]
    print(f"jobs: {len(jobs)}  ({len(tasks)} tasks x {len(arms)} arms)")
    results = {}
    idx = 0
    import threading
    lock = threading.Lock()
    def worker():
        nonlocal idx
        while True:
            with lock:
                if idx >= len(jobs):
                    return
                job = jobs[idx]
                idx += 1
            t, a = job
            run_one(t, a, args.timeout, force_skill=args.force_skill)
    threads = [threading.Thread(target=worker) for _ in range(min(args.concurrency, len(jobs)))]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    print("ALL DONE")

if __name__ == "__main__":
    main()
