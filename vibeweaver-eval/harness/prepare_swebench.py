#!/usr/bin/env python3
"""Prepare SWE-bench Lite tasks: clone repos at base_commit, create venvs, validate gold."""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "swebench_lite" / "test.parquet"
REPOS = ROOT / "workspace" / "iteration-1" / "repos"
VENVS = ROOT / "workspace" / "iteration-1" / "venvs"
TASKS = ROOT / "workspace" / "iteration-1" / "tasks"
PY = sys.executable

INSTANCES = [
    "pallets__flask-4045",
    "pallets__flask-4992",
    "psf__requests-3362",
    "pytest-dev__pytest-6116",
    "pytest-dev__pytest-9359",
    "sympy__sympy-21627",
]

# era-pinned extra deps per instance (validated against python 3.9)
PIP_EXTRA = {
    "pallets__flask-4045": ["werkzeug==2.2.3", "jinja2==3.0.3", "itsdangerous==2.0.1", "click==8.0.4"],
    "pallets__flask-4992": ["werkzeug==2.3.7", "jinja2==3.1.2", "itsdangerous==2.1.2", "click==8.1.7"],
    "pytest-dev__pytest-6116": ["iniconfig==1.1.1", "pluggy==0.13.1", "attrs==21.4.0", "py==1.11.0", "wcwidth", "packaging", "toml==0.10.2"],
    "pytest-dev__pytest-9359": ["iniconfig==1.1.1", "pluggy==1.0.0", "attrs==22.1.0", "py==1.11.0", "wcwidth", "packaging", "tomli"],
    "psf__requests-3362": [],
    "sympy__sympy-21627": [],
}

def sh(cmd, cwd=None, check=True, timeout=1800, capture=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"CMD FAILED: {cmd}\n{r.stdout}\n{r.stderr}")
    return r

def main():
    df = pd.read_parquet(DATA)
    df = df[df["instance_id"].isin(INSTANCES)]
    repos = {}
    for _, row in df.iterrows():
        iid = row["instance_id"]
        repo = row["repo"]
        repos.setdefault(repo, []).append(row)

    for repo, rows in repos.items():
        clone_dir = REPOS / repo.replace("/", "__")
        if not (clone_dir / ".git").exists():
            print(f"cloning {repo} ...")
            sh(["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(clone_dir)])
        else:
            print(f"repo exists: {repo}")

    for row in df.iterrows():
        row = row[1]
        iid = row["instance_id"]
        task_id = f"swebench_{iid}".replace("__", "_").replace("-", "_")
        repo = row["repo"]
        base = row["base_commit"]
        clone_dir = REPOS / repo.replace("/", "__")
        task_dir = TASKS / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        sh(["git", "-C", str(clone_dir), "checkout", "--quiet", "-f", base])
        sh(["git", "-C", str(clone_dir), "clean", "-fdq"])
        (task_dir / "prompt.md").write_text(
            f"# Task: fix this issue in the repository\n\n"
            f"The repository (checkout of {row['repo']} at commit {base}) is the CURRENT WORKING DIRECTORY.\n\n"
            + row["problem_statement"])
        task = {
            "benchmark": "swebench_lite",
            "task_id": task_id,
            "instance_id": iid,
            "repo": repo,
            "repo_path": str(clone_dir),
            "base_commit": base,
            "problem_statement": row["problem_statement"],
            "test_patch": row["test_patch"],
            "gold_patch": row["patch"],
            "FAIL_TO_PASS": json.loads(row["FAIL_TO_PASS"]),
            "PASS_TO_PASS": json.loads(row["PASS_TO_PASS"]),
        }
        (task_dir / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False))

        venv = VENVS / iid
        if not (venv / ".prepared").exists():
            print(f"creating venv {iid} ...")
            if not (venv / "bin" / "python").exists():
                sh([PY, "-m", "venv", str(venv)])
            vpy = venv / "bin" / "python"
            sh([str(vpy), "-m", "pip", "install", "-q", "-U", "pip", "wheel", "setuptools"])
            install_cmds = [
                ["-e", str(clone_dir)],
                ["-e", str(clone_dir), "--no-build-isolation"],
                [str(clone_dir)],
            ]
            for extra in install_cmds:
                try:
                    sh([str(vpy), "-m", "pip", "install", "-q"] + extra, timeout=2700)
                    break
                except RuntimeError as e:
                    last = e
                    print(f"  install attempt failed: {extra} -> {str(e)[:200]}")
            else:
                raise last
            sh([str(vpy), "-m", "pip", "install", "-q", "pytest"], timeout=2700)
            extra = PIP_EXTRA.get(iid, [])
            if extra:
                sh([str(vpy), "-m", "pip", "install", "-q"] + extra, timeout=2700)
            (venv / ".prepared").touch()
        else:
            print(f"venv ready: {iid}")
        print(f"task prepared: {iid}")

if __name__ == "__main__":
    main()
