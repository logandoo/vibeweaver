#!/usr/bin/env python3
"""eval_run.py — isolated eval lab (W2 Task 12).

Subject agent and evaluator are separate: the hidden test lives OUTSIDE the
worktree and is injected only at grading time. Verdict is three-valued:
pass / fail / indeterminate (setup/capture failure is never pass).

W2-ISO isolation contract (docs/PLAN_w2_iso_20261023.md):
  * the subject agent's session directory is the run's temp worktree — bound
    three ways: the `opencode run … <directory> <message>` positional, the
    process cwd, and `PWD` (measured: `opencode run` takes its session
    directory from the ENVIRONMENT's `$PWD`, not from the process cwd);
  * the agent runs with the run's temp HOME (auth material seeded there only),
    and every env value that can re-point the agent at the host (repo path,
    `XDG_*`, `OLDPWD`, `OPENCODE_*`, `SSH_AUTH_SOCK`) is dropped — W6 lesson:
    env/config are answer-leak channels too;
  * after the run, writes that left the worktree/sandbox are DETECTED and a
    violation fails closed as `indeterminate` — a contaminated measurement is
    never `pass`. Monitored legs: host-repo tree fingerprint (status `-uall` +
    numstat, evidence-dir exclusion by PATH PREFIX), task artifacts outside
    the worktree, symlinks escaping the sandbox, hidden test inside worktree.

Adversarial review 2026-10-23 (both reviewers, CRITICAL) hardened two points:
the seeded state DB is BUILT FRESH from an allowlist (a copy-then-DELETE leaves
host session bytes physically recoverable in free pages), and the evidence-dir
exclusion is a path-prefix test (a substring test lets a contaminated run pass).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import signal
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import gate_events   # noqa: E402  (same-dir module: the plugin-interception ledger)


class ProcessGroupTimeout(TimeoutError):
    """The agent's process group exceeded its budget (the whole group is killed)."""


def run_process_group(cmd, cwd, env, timeout):
    """Run cmd as its OWN process group; on timeout, kill the WHOLE group.

    `opencode run` is a CLI shell spawning a node worker tree:
    subprocess.run(timeout=...) only kills the direct child, leaving orphans
    that keep calling the model (W2-T14: full_forced 13/13 timed out at 900s
    with the tree still alive — burning the user's quota long after the run).
    Verified by tests/test_process_group_kill.py (criterion #62).
    """
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            proc.kill()   # belt: direct child already gone
        proc.communicate()
        raise ProcessGroupTimeout("process group of %r killed after %ss" % (cmd[0], timeout))
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def lab_root():
    for p in (ROOT / "vibeweaver-eval" / "lab", ROOT / "tests" / "eval" / "lab"):
        if p.is_dir():
            return p
    return ROOT / "tests" / "eval" / "lab"


def scenario(name):
    p = lab_root() / "scenarios" / (name + ".json")
    if not p.is_file():
        raise SystemExit("eval_run: scenario not found: " + str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def seed_auth(home):
    """Copy ONLY auth material so a temp HOME can still call the model.

    Measured (2026-10-23): provider/model ROUTING lives in the opencode state
    DB (`credential` table = per-provider API keys, `kv.models-dev:catalog`),
    not in auth.json — a fresh DB yields 12 models and zero provider routes.
    The same DB holds the host's session/message/part rows (42k+), which are
    ANSWER MATERIAL, so only an allowlist of auth-shaped rows is seeded (see
    seed_state_db).
    """
    src = pathlib.Path.home() / ".local" / "share" / "opencode" / "auth.json"
    if src.is_file():
        dst = home / ".local" / "share" / "opencode"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst / "auth.json")
    # model/provider registry is config, not evidence: seed only the config file
    cache = pathlib.Path.home() / ".cache" / "opencode" / "models.json"
    if cache.is_file():
        cdir = home / ".cache" / "opencode"
        cdir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cache, cdir / "models.json")
    cfg = pathlib.Path.home() / ".config" / "opencode" / "opencode.jsonc"
    if cfg.is_file():
        cdir = home / ".config" / "opencode"
        cdir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cfg, cdir / "opencode.jsonc")
    return seed_state_db(home)


# rows seeded into the state DB — AUTH/CONFIG SHAPED ONLY (allowlist: a table
# that is not here is never seeded, so schema evolution cannot leak content).
DB_KEEP_TABLES = ["credential", "kv", "migration", "__drizzle_migrations"]


def seed_state_db(home):
    """Seed a state DB BUILT FRESH from the host schema + allowlisted rows.

    Never copy-then-delete: a logical DELETE leaves the deleted rows physically
    recoverable in free pages (review 2026-10-23 carved session JSON out of
    such a copy). A freshly created file only ever contains what we INSERT.

    Returns True when the host DB existed and the seed was written.
    """
    src = pathlib.Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not src.is_file():
        return False
    dst = home / ".local" / "share" / "opencode" / "opencode.db"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    src_con = sqlite3.connect("file:%s?mode=ro" % src, uri=True)
    dst_con = sqlite3.connect(str(dst))
    try:
        created = set()
        for (name, ddl) in src_con.execute(
                "select name, sql from sqlite_master where sql is not null").fetchall():
            if name == "sqlite_sequence":        # reserved; auto-created
                continue
            try:
                dst_con.execute(ddl)             # schema only, zero rows
                created.add(name)
            except sqlite3.Error:
                continue                         # virtual/hostile DDL: skip, never crash
        for t in DB_KEEP_TABLES:
            if t not in created:
                continue
            info = list(src_con.execute("pragma table_info('%s')" % t))
            if not info:
                continue
            cols = [c[1] for c in info]
            rows = src_con.execute(
                "select %s from '%s'" % (", ".join('"%s"' % c for c in cols), t)).fetchall()
            if t == "kv" and "key" in cols:           # job markers are run state
                ki = cols.index("key")
                rows = [r for r in rows if not str(r[ki]).startswith("job.")]
            if rows:
                dst_con.executemany(
                    "insert or ignore into '%s' values (%s)"
                    % (t, ",".join("?" * len(cols))), rows)
        dst_con.commit()
    finally:
        src_con.close()
        dst_con.close()
    return True


# ---- G3 arms (docs/EVAL_G3_ARMS.md) ------------------------------------
# `forced` = skill content injected into the prompt; `core` = installed only
# (self-trigger). The arm is the ONLY variable between runs.
ARM_INJECT = ("full_forced", "mini_forced")


def skill_source_dir(arm):
    if arm == "core":
        return ROOT / "profiles" / "core"
    if arm in ("full_forced", "full_deployed"):
        p = pathlib.Path.home() / ".config" / "opencode" / "skills" / "vibeweaver"
        return p if p.is_dir() else ROOT
    if arm == "mini_forced":
        return pathlib.Path.home() / ".config" / "opencode" / "skills" / "vibeweaver-mini"
    return None


def stage_arm(home, arm):
    """Install the arm's skill content into the subject's temp HOME and return an
    auditable fingerprint (arm identity is measured, never self-reported).

    v2 (`full_deployed`): the PRODUCT form — skill payload + the host's plugin
    directory (gate + audit) staged into the temp HOME. No prompt injection:
    like a real install, the skill must self-trigger and the plugins must do
    the enforcing (user ruling 2026-10-25: md-only arms measured the wrong thing).
    """
    src = skill_source_dir(arm)
    if src is None or not src.is_dir():
        return {"arm": arm, "installed": None, "files": 0, "sha256": None}
    name = "vibeweaver-mini" if arm == "mini_forced" else "vibeweaver"
    dst = home / ".config" / "opencode" / "skills" / name
    dst.mkdir(parents=True, exist_ok=True)
    digest, n = hashlib.sha256(), 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        if any(part in ("node_modules", ".git", "__pycache__", "tests", "memory", "docs")
               for part in rel.parts):
            continue
        if arm == "core" and rel.as_posix() != "SKILL.md":
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(p.read_bytes())
        n += 1
    if arm == "full_deployed":
        psrc = pathlib.Path.home() / ".config" / "opencode" / "plugins"
        pdst = home / ".config" / "opencode" / "plugins"
        if not psrc.is_dir():
            raise SystemExit("eval_run: full_deployed needs the host plugin dir "
                             "(vibeweaver-gate.js / vibeweaver-audit.js): " + str(psrc))
        pdst.mkdir(parents=True, exist_ok=True)
        for p in sorted(psrc.iterdir()):
            if not p.is_file():
                continue
            shutil.copyfile(p, pdst / p.name)
            digest.update(("plugins/" + p.name).encode("utf-8"))
            digest.update(p.read_bytes())
            n += 1
    return {"arm": arm, "installed": str(dst), "files": n, "sha256": digest.hexdigest()}


def seed_setup_files(sc, work):
    """Scenario-declared pre-placed files (v2: gate activation markers — a real
    vibeweaver project is opt-in, so the sandbox must LOOK like one).

    Never overwrites an existing path; absolute/escaping rel paths are refused
    (the worktree is the only writable surface, same fail-closed spirit as W2-ISO).
    Returns the list of relative paths actually written.
    """
    written = []
    for rel, content in sorted((sc.get("setup_files") or {}).items()):
        rp = pathlib.Path(str(rel))
        if rp.is_absolute() or ".." in rp.parts:
            continue
        target = work / rp
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")
        written.append(rp.as_posix())
    return written


ARM_PREAMBLE = ("[skill-forced] You MUST read and follow this skill while doing "
                "the task.\n<skill>\n%s\n</skill>\n\n--- task ---\n")


def arm_prompt(prompt, arm):
    if arm not in ARM_INJECT:
        return prompt
    src = skill_source_dir(arm)
    skill_md = (src / "SKILL.md") if src else None
    if not skill_md or not skill_md.is_file():
        return prompt
    return ARM_PREAMBLE % skill_md.read_text(encoding="utf-8") + prompt


def build_env(work, home, root):
    """W2-ISO: bind the subject agent to the worktree + the run's temp HOME.

    Measured: `opencode run` takes its session directory from the
    ENVIRONMENT's `$PWD`, not from the process cwd (a run with cwd=/tmp/A and
    PWD=/tmp/B wrote its artifact into /tmp/B). `cwd=` alone is therefore not
    a binding — `PWD` is set to the worktree, the directory positional is
    passed on the CLI as well, and every env value that could re-point the
    agent at the host is dropped (`OPENCODE_CONFIG` / `OPENCODE_DB` would
    re-route it to the host config or the full host state DB).
    """
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("XDG_", "OPENCODE_")) or k in ("OLDPWD", "SSH_AUTH_SOCK", "SSH_AGENT_PID"):
            del env[k]
    for k in list(env):
        if k in ("PATH", "HOME", "PWD", "USER", "LOGNAME", "SHELL", "TERM", "LANG"):
            continue
        v = env[k]
        if isinstance(v, str) and str(root) in v:
            del env[k]
    env["HOME"] = str(home)
    env["PWD"] = str(work)
    return env


def git_status_lines(root):
    """Isolation leg (a), part 1: `git status --porcelain -uall` (every
    untracked file listed individually). None = not monitorable
    (missing != success: an unmonitorable tree is an isolation violation)."""
    try:
        r = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-uall"],
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return sorted(l for l in r.stdout.splitlines() if l.strip())


def git_numstat_lines(root):
    """Isolation leg (a), part 2: per-file +/- counts. A write into an
    ALREADY-modified tracked file does not change the porcelain line SET —
    the numstat counts make it visible."""
    try:
        r = subprocess.run(["git", "-C", str(root), "diff", "--numstat"],
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return sorted(l for l in r.stdout.splitlines() if l.strip())


def repo_fingerprint(root):
    """Host-repo fingerprint: status lines + per-file numstat + stat records for
    untracked files (a status line alone cannot see an append to a file that was
    ALREADY untracked, nor its deletion — review 2026-10-23 finding 3)."""
    s, n = git_status_lines(root), git_numstat_lines(root)
    if s is None or n is None:
        return None
    fp = ["status " + l for l in s] + ["numstat " + l for l in n]
    for l in s:
        if not l.startswith("?? "):
            continue
        p = root / _porcelain_path(l)
        try:
            st = p.stat()
            fp.append("stat %s %d %d" % (_porcelain_path(l), st.st_size, st.st_mtime_ns))
        except OSError:
            fp.append("stat %s gone" % _porcelain_path(l))
    return sorted(fp)


def _porcelain_path(status_line):
    """Path field of a `git status --porcelain` line (handles `old -> new`)."""
    body = status_line[3:] if len(status_line) > 3 else status_line
    if " -> " in body:
        body = body.split(" -> ", 1)[1]
    return body.strip().strip('"')


def _fp_path(line):
    """The path a fingerprint line refers to (used for prefix exclusion)."""
    if line.startswith("status "):
        return _porcelain_path(line[len("status "):])
    if line.startswith("numstat "):
        parts = line[len("numstat "):].split("\t")
        return parts[-1].strip().strip('"') if parts else ""
    if line.startswith("stat "):
        return line[len("stat "):].rsplit(" ", 2)[0]
    return ""


def _under(path, rel_root):
    """Path-prefix containment — NEVER substring (`tests` must not swallow
    `tests/eval/lab/hidden/smoke_test.py`, review 2026-10-23 CRITICAL)."""
    rel_root = rel_root.rstrip("/")
    return bool(rel_root) and (path == rel_root or path.startswith(rel_root + "/"))


def tree_files(base):
    """Every file under `base`, relative to it, sorted."""
    return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())


def sandbox_symlinks(tmp):
    """Symlinks under the sandbox whose target escapes it (resolve()-based:
    a parent-directory symlink defeats a leaf-only is_symlink() check)."""
    out = []
    root = tmp.resolve()
    for p in sorted(tmp.rglob("*")):
        if not p.is_symlink():
            continue
        try:
            p.resolve().relative_to(root)
        except Exception:
            out.append(str(p.relative_to(tmp)))
    return out


def containment_check(tmp, work, out, artifacts, hidden_name, before_repo, after_repo):
    """W2-ISO: detect writes that left the worktree/sandbox and fail closed.

    Legs: (a) host-repo tree fingerprint delta, excluding this run's evidence
    dir by PATH PREFIX; (b) task artifacts found outside the worktree inside
    the sandbox; (c) symlinks escaping the sandbox; (d) the hidden test inside
    the worktree. Residuals named in docs/PLAN_w2_iso_20261023.md.
    """
    out_rel = os.path.relpath(str(out), str(ROOT))
    work_files = tree_files(work)
    outside = []
    for rel in tree_files(tmp):
        try:
            (tmp / rel).relative_to(work)
        except ValueError:
            outside.append(rel)
    escapes = sandbox_symlinks(tmp)
    violations = []
    lab_rel = os.path.relpath(str(lab_root()), str(ROOT))
    if _under(lab_rel, out_rel) or _under(out_rel, lab_rel):
        # evidence dir overlapping the hidden-test lab tree (either direction)
        # blinds the monitor — review 2026-10-23: `--out tests/eval/lab/hidden`
        # would otherwise hide writes to the hidden test itself.
        violations.append("evidence dir overlaps the hidden-test lab tree: " + out_rel)
    monitored = before_repo is not None and after_repo is not None
    delta = []
    if monitored:
        # Host-governance self-noise exemption (comp-noise2320 + v2-smoke2
        # incidents): under vibeweaver governance the host's gate/lock chain
        # rewrites its OWN outputs (gate_result.json, .evidence.lock) and the
        # operator appends the verification log — inside a run window these are
        # self-inflicted "host-repo write" violations, not subject contamination.
        # The subject runs with a temp HOME and a worktree-only project root: it
        # cannot reach the host repo at all, so these governance paths are
        # exempted BY NAME (everything else still fails closed).
        GATE_SELF_NOISE = ("tests/gate_result.json", "tests/.evidence.lock",
                           "tests/verification_log.md")
        delta = [l for l in after_repo if l not in before_repo
                 and not _under(_fp_path(l), out_rel)
                 and _fp_path(l) not in GATE_SELF_NOISE]
        violations += ["host-repo write outside sandbox: " + l for l in delta]
    else:
        violations.append("host repo not monitorable (git failed) — isolation unverified")
    for rel in outside:
        if pathlib.Path(rel).name in artifacts:
            violations.append("task artifact outside worktree: " + rel)
    for rel in escapes:
        violations.append("symlink escaping sandbox: " + rel)
    for rel in work_files:
        if pathlib.Path(rel).name == hidden_name:
            violations.append("hidden test inside worktree: " + rel)
    return {
        "sandbox": str(tmp),
        "worktree": str(work),
        "work_files": work_files,
        "sandbox_outside_work": outside,
        "sandbox_symlink_escapes": escapes,
        "host_repo_delta": delta,
        "host_repo_monitored": monitored,
        "artifacts": list(artifacts),
        "violations": violations,
    }


# only the CLI's OWN error envelope can classify a run as "never started";
# a subject must not be able to print a magic string and downgrade its verdict.
CLI_SETUP_ERROR_TYPES = {
    "provider.no-route", "provider.auth", "provider.missing", "model_not_found",
    "model.not_found", "config.invalid", "auth.missing",
}


def cli_error_type(agent):
    """The CLI's `--format json` error type, or "" when none is present.

    Accepted only as a top-level object shaped like the CLI envelope
    `{"type":"error","timestamp":…,"sessionID":…,"error":{"type":…}}`.
    """
    out = (agent.get("stdout") or "").strip()
    objs = []
    try:
        objs.append(json.loads(out))
    except Exception:
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    objs.append(json.loads(line))
                except Exception:
                    continue
    for obj in objs:
        if not isinstance(obj, dict) or obj.get("type") != "error":
            continue
        if not all(k in obj for k in ("timestamp", "sessionID", "error")):
            continue
        return str((obj.get("error") or {}).get("type") or "")
    return ""


def is_setup_failure(agent):
    return cli_error_type(agent) in CLI_SETUP_ERROR_TYPES


def find_grading_escape(work, artifacts):
    """Anti-cheat scan (review A CRITICAL): the subject's module is loaded in the
    GRADER's process, so process-killing hooks can forge the exit code. Any
    artifact whose source contains one is graded `fail`, never `pass`.
    Residual (named): same-process execution cannot be made cheat-proof without
    an OS sandbox — this raises the cost from one line to deliberate forgery.
    """
    pat = re.compile(r"os\._exit|os\.kill\(|signal\.(raise_signal|alarm)|"
                     r"sys\.exit\s*=|builtins\.(exit|quit)\s*=|monkeypatch")
    hits = []
    for rel in artifacts:
        p = work / rel
        if not p.is_file():
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if pat.search(line):
                hits.append("%s:%d" % (rel, i))
    return hits


def run_agent(name, work, home, model, agent_kind):
    prompt = arm_prompt(scenario(name)["prompt"], getattr(args, "arm", "bare"))
    # Worktree/HOME are isolated; the model registry/auth material is seeded
    # into the temp HOME because a fresh HOME cannot discover providers —
    # documented partial isolation.
    if agent_kind == "mock":
        (work / "hello.txt").write_text("hello\n", encoding="utf-8")
        return {"exit": 0, "stdout": "mock agent", "stderr": "", "cmd": "mock"}
    env = build_env(work, home, ROOT)
    # `opencode run [flags] <directory> <message...>` — the directory positional
    # goes BEFORE the variadic message (v2.1.3; `opencode <dir> run` parses wrong).
    # `--format json` keeps the CLI's error envelope machine-readable so a
    # setup failure is distinguished from a subject failure structurally.
    cmd = ["opencode", "run", "--standalone", "-m", model, "--format", "json",
           "--auto", str(work), prompt]
    t0 = time.time()
    r = run_process_group(cmd, cwd=work, env=env,
                          timeout=scenario(name)["timeout_seconds"])
    # gate-event measurement needs the FULL event stream: the old 20k tail cut
    # every early GATE-BLOCKED message (v2 smoke 2026-10-25: agent demonstrably
    # ran the checker and built memory/, yet the parsed stream showed 0 events
    # because only the last 20k chars survived). Trajectories are evidence;
    # they are archived, so size is bounded by disk, not by a blind truncation.
    return {"exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr[-20000:],
            "cmd": " ".join(cmd), "seconds": time.time() - t0,
            "cwd": str(work), "home": str(home)}


def main(argv=None):
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="smoke")
    ap.add_argument("--agent", choices=["opencode", "mock"], default="opencode")
    ap.add_argument("--model", default="deepseek/deepseek-flash")
    ap.add_argument("--arm", choices=["bare", "core", "full_forced", "mini_forced",
                                      "full_deployed"], default="bare")
    ap.add_argument("--seed", type=int, default=0, help="replicate index (sampling seed is not CLI-controllable)")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)
    sc = scenario(args.scenario)
    artifacts = list(sc.get("artifacts") or [])
    hidden_name = pathlib.Path(sc["hidden_test"]).name
    out = pathlib.Path(args.out) if args.out else ROOT / "tests" / "eval" / "runs" / (
        sc["id"] + "-" + time.strftime("%Y%m%d_%H%M%S") + "-" + uuid.uuid4().hex[:6])
    if os.path.relpath(str(out), str(ROOT)) == ".":
        raise SystemExit("eval_run: --out must not be the repository root "
                         "(the containment monitor would blind itself)")
    out.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-eval-"))
    try:
        work, home = tmp / "work", tmp / "home"
        work.mkdir(); home.mkdir(); seed_auth(home)   # inside try: a seeding crash
        arm_fp = stage_arm(home, args.arm)            # G3 arm content (docs/EVAL_G3_ARMS.md)
        seeded = seed_setup_files(sc, work)           # v2: gate activation markers (#67)
        before_repo = repo_fingerprint(ROOT)          # must still clean up + report
        try:
            agent = run_agent(args.scenario, work, home, args.model, args.agent)
        except Exception as e:
            agent = {"exit": -1, "stdout": "", "stderr": str(e), "cmd": "opencode"}
        iso = containment_check(tmp, work, out, artifacts, hidden_name,
                                before_repo, repo_fingerprint(ROOT))
        # hidden test is NOT copied into work; run it from the lab (grading time)
        test = {"exit": None, "output": ""}
        if agent["exit"] != 0:
            verdict = "indeterminate" if (agent["exit"] == -1 or is_setup_failure(agent)) else "fail"
            test["output"] = "agent failed/could not run"
        else:
            tp = lab_root() / sc["hidden_test"]
            try:
                r = subprocess.run([sys.executable, str(tp), str(work)],
                                   capture_output=True, text=True, timeout=60)
                test = {"exit": r.returncode, "output": (r.stdout + r.stderr)[-8000:]}
                # 评审 A CRITICAL：被测模块在评分进程内被 `exec_module`，exit code
                # 可被 `os._exit(0)` 之类一行伪造。pass 因此还需要两条独立证据：
                #   ① 完成标记必须是 stdout 的最后一个非空行（隐藏测试在全部断言
                #      之后才打印；提前杀进程必然缺失）；
                #   ② 评分前扫描产物源码里的进程逃逸钩子（`os._exit` / `sys.exit =`
                #      等），命中即判 fail。
                # 残余（已命名）：同进程执行无法彻底防伪，彻底防伪需要 OS 沙箱
                # （与 memory/fix_eval_answer_leak_w6 的 W8 残余同类）。
                outs = [l for l in (r.stdout or "").splitlines() if l.strip()]
                marker_ok = bool(outs) and outs[-1].startswith("PASS:")
                escape = find_grading_escape(work, sc.get("artifacts") or [])
                test["completion_marker"] = outs[-1] if marker_ok else None
                test["grading_escape"] = escape
                if escape:
                    verdict = "fail"          # 反作弊：伪造/逃逸钩子永不计 pass
                elif r.returncode not in (0, 1):
                    verdict = "indeterminate"  # 评分器自身崩溃/异常退出
                elif marker_ok and r.returncode == 0:
                    verdict = "pass"
                else:
                    verdict = "fail"          # 未证明行为（含标记缺失）≠ pass
            except Exception as e:                   # capture failure is never pass
                test = {"exit": None, "output": "hidden-test capture failure: %s" % e}
                verdict = "indeterminate"
        if iso["violations"]:
            verdict = "indeterminate"  # fail-closed: a contaminated measurement is never pass
        (out / "isolation.json").write_text(json.dumps(iso, indent=2), encoding="utf-8")
        (out / "trajectory.json").write_text(json.dumps({"scenario": sc["id"], "agent": agent, "worktree": str(work)}, indent=2), encoding="utf-8")
        (out / "cost.json").write_text(json.dumps({
            "wall_seconds": agent.get("seconds"), "model": args.model,
            "arm": getattr(args, "arm", "bare"), "seed": getattr(args, "seed", 0),
            "skill_fingerprint": arm_fp, "tokens": agent.get("tokens"),
            "setup_files_seeded": seeded,
            "gate_events": gate_events.summarize({"agent": agent})}, indent=2), encoding="utf-8")
        (out / "verdict.json").write_text(json.dumps({"scenario": sc["id"], "verdict": verdict, "hidden_test": test, "agent_exit": agent["exit"], "isolation_violations": iso["violations"]}, indent=2), encoding="utf-8")
        print(f"EVAL {sc['id']}: {verdict} -> {out}")
        return 0 if verdict == "pass" else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)      # ALWAYS: seeded auth material


if __name__ == "__main__":
    sys.exit(main())
