#!/usr/bin/env python3
"""Grade a flow task: start the agent's service, run the hidden workflow test, stop service."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "iteration-1"
TASKS = WS / "tasks"
RUNS = WS / "runs"
GRADED = WS / "graded"
FLOW_VENV = WS / "venvs" / "flow_bench"

def sh(cmd, cwd=None, timeout=300, env=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=False, timeout=timeout, env=env)
    out = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""
    err = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""
    return r.returncode, out, err

def kill_port(port):
    """Kill any process listening on the port (orphaned agent services)."""
    try:
        out = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True,
                             timeout=15).stdout
        for pid in out.split():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ValueError, ProcessLookupError):
                pass
        if out.strip():
            time.sleep(1)
    except Exception:
        pass

def start_service(run_dir, port, attempts):
    kill_port(port)
    py = FLOW_VENV / "bin" / "python"
    proc = None
    for app in attempts:
        cmd = [str(py), "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port),
               "--log-level", "warning"]
        try:
            proc = subprocess.Popen(cmd, cwd=str(run_dir),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except FileNotFoundError:
            proc = None
            continue
        deadline = time.time() + 30
        ok = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/docs", timeout=1)
                ok = True
                break
            except Exception:
                time.sleep(0.5)
        if ok:
            return proc, f"uvicorn {app}", ""
        proc.kill()
        proc.wait()
        proc = None
    return None, "", "service failed to start on any attempt"

def grade(task_dir: Path, run_dir: Path, arm: str) -> dict:
    meta = json.loads((task_dir / "task.json").read_text())
    port = meta["port"]
    result = {"task": meta["task_id"], "arm": arm, "passed": False,
              "service_started": False, "notes": []}
    # skip if the agent produced no main.py/app.py
    has_main = (run_dir / "main.py").exists() or (run_dir / "app.py").exists()
    if not has_main:
        result["notes"].append("no main.py/app.py in workdir")
        return result
    # grade in a fresh COPY of the workdir so agent-persisted state
    # (sqlite files, caches) cannot leak into this run (clean-start rule)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for item in run_dir.iterdir():
            if item.name in (".opencode_data", "run.log"):
                continue
            dst = td / item.name
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
        proc, how, err = start_service(td, port, meta["start_attempts"])
        if proc is None:
            result["notes"].append(err)
            return result
        result["service_started"] = True
        result["start_method"] = how
        try:
            env = dict(os.environ)
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            test_path = task_dir / meta["hidden_workflow"]
            rc, out, _ = sh([str(FLOW_VENV / "bin" / "python"), "-m", "pytest", "-q", str(test_path)],
                            cwd=str(td), timeout=300, env=env)
            result["output"] = (out or "")[-3000:]
            result["passed"] = rc == 0
        finally:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            kill_port(port)
    return result

def main():
    task_id, arm = sys.argv[1], sys.argv[2]
    result = grade(TASKS / task_id, RUNS / f"{task_id}__{arm}", arm)
    GRADED.mkdir(parents=True, exist_ok=True)
    (GRADED / f"grade_{task_id}__{arm}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False))
    print(f"{task_id} {arm}: passed={result['passed']} started={result['service_started']} "
          f"notes={result['notes']}")

if __name__ == "__main__":
    main()
