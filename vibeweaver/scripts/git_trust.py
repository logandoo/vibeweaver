#!/usr/bin/env python3
"""Trusted Git resolution for evidence gates.

The gate must not inherit a caller-controlled `PATH` wrapper or `GIT_DIR`.
Resolve a standard absolute git once and strip GIT_* environment overrides.
This is tamper-evident hygiene for the declared trust model; it is not a
defense against a hostile root that can replace the git binary itself.
"""
import os
from pathlib import Path
import shutil
import subprocess


def _candidates():
    if os.name == "nt":
        roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LOCALAPPDATA")]
        out = []
        for root in roots:
            if root:
                out.extend([str(Path(root) / "Git" / "cmd" / "git.exe"),
                            str(Path(root) / "Programs" / "Git" / "cmd" / "git.exe"),
                            str(Path(root) / "Git" / "bin" / "git.exe")])
        return out
    return ["/usr/bin/git", "/opt/homebrew/bin/git", "/usr/local/bin/git"]


def _resolve():
    for candidate in _candidates():
        try:
            if Path(candidate).is_file():
                return candidate
        except OSError:
            continue
    found = shutil.which("git")
    return found if found else None


GIT = _resolve()


def clean_env():
    """Return an environment without GIT_DIR / GIT_WORK_TREE / GIT_CONFIG*
    and other repository-selection overrides. PATH is kept only for git's own
    exec helpers; the git binary itself is absolute."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def run_git(root, *args, timeout=30, text=True):
    if not GIT:
        raise RuntimeError("trusted git not found")
    return subprocess.run(
        [GIT, "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=text, timeout=timeout, env=clean_env(),
    )
