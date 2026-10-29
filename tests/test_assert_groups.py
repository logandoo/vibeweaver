"""Fixture tests for assert_artifacts.py groups 14-16.

Spec (doc-first, A4.7): COMPLETION_GATE.md §A4.4.1 rows 14/15/16 +
APPENDIX.md §A8. Black-box: builds real git fixture repos and runs the
canonical script by subprocess.

Secret literals are SPLIT in source ("AKIA" + "0"*16) so this file's own
added lines never trip group 14's scan of the dev repo's wave diff.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
CANON = REPO / "vibeweaver" / "scripts" / "assert_artifacts.py"
RESULTS = []


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)


def rec(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


class Fx:
    """A minimal fixture git project that PASSES groups 1-13 with --existing."""

    def __init__(self):
        self.d = pathlib.Path(tempfile.mkdtemp(prefix="vwfx-"))
        d = self.d
        (d / "memory").mkdir(parents=True)
        (d / "memory" / "MEMORY.md").write_text("# Index\n- [T](topic.md)\n")
        (d / "memory" / "topic.md").write_text("# t\n")
        (d / "script" / "linux").mkdir(parents=True)
        for s in ["start.sh", "stop.sh", "restart.sh", "project_build.sh"]:
            p = d / "script" / "linux" / s
            p.write_text("#!/bin/sh\nexit 0\n")
            p.chmod(0o755)
        (d / "tests").mkdir()
        (d / ".gitignore").write_text(
            ".DS_Store\n__pycache__/\n*.pyc\n.venv/\nvenv/\nnode_modules/\n"
            ".pnpm-store/\ndist/\nbuild/\n.env\n")
        shutil.copy(CANON, d / "tests" / "assert_artifacts.py")
        (d / "tests" / "acceptance.md").write_text("> cap=5  stall=3×\n1. ok\n")
        (d / "tests" / "verification_log.md").write_text(
            "# vl\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
            "- Baseline verified GREEN\n")
        self.sh("git", "init", "-q")
        self.sh("git", "config", "user.email", "fx@example.invalid")
        self.sh("git", "config", "user.name", "fx")
        self.commit("initial")
        run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], d)

    def sh(self, *args):
        run(list(args), self.d)

    def write(self, rel, content):
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def append_log(self, line):
        with open(self.d / "tests" / "verification_log.md", "a") as f:
            f.write(line + "\n")

    def commit(self, msg):
        self.sh("git", "add", "-A")
        run(["git", "commit", "-qm", msg], self.d)

    def assert_run(self):
        return run([sys.executable, "tests/assert_artifacts.py", "--existing"], self.d)


def main():
    # S1 — clean fixture: groups 1-13 regression (must pass pre AND post change)
    fx = Fx()
    r = fx.assert_run()
    rec("S1 clean fixture exit 0 (groups 1-13 regression)", r.returncode == 0,
        (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "no output")

    # S2 — secret on an ADDED committed line → exit 1 naming secret scan
    fx = Fx()
    fx.write("app/config.py",
             'AWS_KEY = "' + "AKIA" + "0" * 16 + '"\n'
             'password = "' + "x9Kp" + "2mQ7" + "vR4s" + '"\n')
    fx.commit("add config")
    r = fx.assert_run()
    rec("S2 secret on added line → exit 1 + 'secret scan'", r.returncode == 1 and "secret scan" in r.stdout,
        (r.stdout.strip().splitlines() or ["no output"])[0][:100])

    # S2b — secret in an UNTRACKED file (never git-added) → still exit 1
    fx = Fx()
    fx.write("app/keys.py", 'token = "' + "ghp_" + "a1B2" + "c3D4" + "e5F6" + "g7H8" + '"\n')
    r = fx.assert_run()
    rec("S2b secret in untracked file → exit 1", r.returncode == 1 and "secret scan" in r.stdout,
        (r.stdout.strip().splitlines() or ["no output"])[0][:100])

    # S3 — placeholder-marked value → exit 0
    fx = Fx()
    fx.write("app/config.py",
             'password = "' + "x9Kp" + "2mQ7" + "vR4s" + '"  # EXAMPLE placeholder value\n')
    fx.commit("add example config")
    r = fx.assert_run()
    rec("S3 placeholder-marked secret → exit 0", r.returncode == 0,
        (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "no output")

    # S4 — removed assertion with no justification → exit 1; with `- test-change:` → exit 0
    fx = Fx()
    fx.write("tests/test_math.py", "def test_add():\n    assert 1 + 1 == 2\n")
    fx.commit("add test")
    fx.write("tests/test_math.py", "def test_add():\n    pass\n")
    fx.commit("weaken test")
    r = fx.assert_run()
    ok_blocked = r.returncode == 1 and "test-change" in r.stdout
    fx.append_log("- test-change: tests/test_math.py — fixture intentionally relaxes the assertion")
    r2 = fx.assert_run()
    rec("S4 assertion removal → exit 1; justified → exit 0",
        ok_blocked and r2.returncode == 0,
        f"blocked={ok_blocked} after-justification-rc={r2.returncode}")

    # S5 — risk-tier path without review package → exit 1; with package → exit 0
    fx = Fx()
    fx.write("auth/login.py", "def login():\n    return True\n")
    fx.commit("add auth")
    r = fx.assert_run()
    ok_blocked = r.returncode == 1 and "risk-tier" in r.stdout
    fx.write("tests/review_package.md", "# review\ndiff range recorded\n")
    r2 = fx.assert_run()
    rec("S5 risk-tier auth path → exit 1; review_package.md → exit 0",
        ok_blocked and r2.returncode == 0,
        f"blocked={ok_blocked} after-package-rc={r2.returncode}")

    # S5b — risk-tier path in an UNTRACKED file → exit 1
    fx = Fx()
    fx.write("payments/charge.py", "def charge():\n    return 0\n")
    r = fx.assert_run()
    rec("S5b risk-tier untracked path → exit 1", r.returncode == 1 and "risk-tier" in r.stdout,
        (r.stdout.strip().splitlines() or ["no output"])[0][:100])

    # S6 — secret in a .md file → exit 0 with WARN on stdout
    fx = Fx()
    fx.write("docs/notes.md",
             "# notes\n\ncreds: password = \"" + "x9Kp" + "2mQ7" + "vR4s" + "\"\n")
    fx.commit("add notes")
    r = fx.assert_run()
    rec("S6 secret in .md → exit 0 + WARN printed",
        r.returncode == 0 and "WARN" in r.stdout and "secret scan" in r.stdout,
        f"rc={r.returncode} warn={'WARN' in r.stdout}")

    # S7 — whole-file deletions must NOT fail-open: deleting a test file →
    # group 15 fires; deleting an auth file → group 16 fires (reviewer #1)
    fx = Fx()
    fx.write("tests/test_math.py", "def test_add():\n    assert 1 + 1 == 2\n")
    fx.write("auth/login.py", "def login():\n    return True\n")
    fx.commit("seed test + auth")
    fx.sh("git", "rm", "-q", "tests/test_math.py", "auth/login.py")
    fx.commit("delete both")
    r = fx.assert_run()
    ok_blocked = (r.returncode == 1 and "test-change" in r.stdout
                  and "risk-tier" in r.stdout)
    fx.append_log("- test-change: tests/test_math.py — fixture deletes the test file intentionally")
    fx.write("tests/review_package.md", "# review\n")
    r2 = fx.assert_run()
    rec("S7 deleted test+auth files → exit 1 both guards; justified+packaged → exit 0",
        ok_blocked and r2.returncode == 0,
        f"blocked={ok_blocked} after-rc={r2.returncode}")

    # S8 — safe credential-handling reference values must NOT be flagged
    # (os.environ.get / process.env / config.x / self.x — reviewer #2)
    fx = Fx()
    fx.write("app/settings.py",
             "import os\n"
             'password = os.environ.get("PASSWORD")\n'
             'token = process.env.API_TOKEN\n'
             'db_pass = config.password\n'
             'pw_hash = self.password_hash\n')
    fx.commit("safe refs")
    r = fx.assert_run()
    rec("S8 reference values (env/config/self) → exit 0", r.returncode == 0,
        (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "no output")

    # S9 — JSON form + modern key formats are caught (reviewer #3)
    fx = Fx()
    fx.write("app/config.json",
             '{\n  "password": "' + "x9Kp" + "2mQ7" + "vR4s" + '"\n}\n')
    fx.write("app/keys.py",
             'oai = "' + "sk-proj-" + "a1B2c3D4" + "e5F6g7H8" + '"\n'
             'ant = "' + "sk-ant-api03-" + "Z9y8X7" + "w6V5u4T3" + '"\n'
             'ghp = "' + "github_pat_" + "11AA" + "22BB" + "33CC" + "44DD" + "55EE" + "66" + '"\n')
    fx.commit("json + modern keys")
    r = fx.assert_run()
    rec("S9 JSON-form + sk-proj/sk-ant/github_pat → exit 1",
        r.returncode == 1 and "secret scan" in r.stdout,
        (r.stdout.strip().splitlines() or ["no output"])[0][:100])

    # S10 — project profile: a library has no service lifecycle → group 5
    # skipped declaratively, everything else still enforced (exit 0 without
    # script/linux/start.sh); profile from tests/project_profile.json.
    fx = Fx()
    shutil.rmtree(fx.d / "script")
    fx.write("tests/project_profile.json", '{"profile": "library"}\n')
    r = fx.assert_run()
    ok_pass = r.returncode == 0 and "group 5 skipped" in r.stdout
    # profile must NOT weaken applicable groups: break acceptance.md → still exit 1
    fx.write("tests/acceptance.md", "1. ok\n")
    r2 = fx.assert_run()
    rec("S10 library profile → group 5 skipped, others enforced",
        ok_pass and r2.returncode == 1 and "cap=5" in r2.stdout,
        f"profiled-rc={r.returncode} weakened-rc={r2.returncode}")

    # S10b — --profile flag overrides/equals the JSON path; unknown project
    # without profile keeps the strict default (start.sh required).
    fx = Fx()
    shutil.rmtree(fx.d / "script")
    r = fx.assert_run()
    rec("S10b no profile + missing scripts → still exit 1 (strict default)",
        r.returncode == 1 and "start.sh" in r.stdout,
        (r.stdout.strip().splitlines() or ["no output"])[0][:100])

    # S11 — `vw-approved` inline marker on a line that MATCHES a credential
    # pattern: without the path-scoped `- secret-approved: <path>` pairing →
    # exit 1; with pairing → exit 0. A bare prose MENTION of the marker (no
    # credential pattern on the line) must be a no-op (reviewer critical fix).
    secret = "x9Kp" + "2mQ7" + "vR4s"
    fx = Fx()
    fx.write("app/config.py", f'password = "{secret}"  # vw-approved: user-requested local config\n')
    fx.commit("user-approved secret")
    fx.write("docs/notes.md", "we support the vw-approved marker flow\n")
    fx.commit("prose mention only")
    r = fx.assert_run()
    ok_blocked = r.returncode == 1 and "secret-approved" in r.stdout and "docs/notes.md" not in r.stdout
    fx.append_log("- secret-approved: app/config.py — user explicitly requested this local credential (task scope)")
    r2 = fx.assert_run()
    rec("S11 vw-approved w/o path-scoped pairing → exit 1; with pairing → exit 0; prose mention = no-op",
        ok_blocked and r2.returncode == 0,
        f"blocked={ok_blocked} after-pairing-rc={r2.returncode}")

    # S11b — pairing is PATH-SCOPED: an approval naming a different path does
    # not clear the marker; marker count > approvals for that path → exit 1.
    fx = Fx()
    fx.write("app/a.py", f'password = "{secret}"  # vw-approved: a\n')
    fx.write("app/b.py", f'password = "{secret}"  # vw-approved: b1\n')
    fx.write("app/c.py", f'password = "{secret}"  # vw-approved: b2\n')
    fx.commit("two files, three markers")
    fx.append_log("- secret-approved: app/b.py — approved for b")
    r = fx.assert_run()
    rec("S11b path-scoped pairing (a/c unapproved; b properly approved) → exit 1",
        r.returncode == 1 and "app/a.py" in r.stdout and "app/c.py" in r.stdout
        and "app/b.py" not in r.stdout,
        (r.stdout.strip().splitlines() or ["no output"])[0][:100])

    # S12 — profile hardening: non-bool override / non-dict JSON fail NAMED
    # (exit 1); unknown profile name warns but strict default still enforced.
    fx = Fx()
    fx.write("tests/project_profile.json", '{"profile": "library", "no_service": "false"}\n')
    r = fx.assert_run()
    ok1 = r.returncode == 1 and "must be boolean" in r.stdout
    fx = Fx()
    fx.write("tests/project_profile.json", '"library"\n')
    r = fx.assert_run()
    ok2 = r.returncode == 1 and "JSON object" in r.stdout
    fx = Fx()
    shutil.rmtree(fx.d / "script")
    fx.write("tests/project_profile.json", '{"profile": "no-such"}\n')
    r = fx.assert_run()
    ok3 = r.returncode == 1 and "unknown profile" in r.stdout and "start.sh" in r.stdout
    rec("S12 profile hardening: non-bool/non-dict named-fail; unknown name warns+strict",
        ok1 and ok2 and ok3,
        f"bool={ok1} dict={ok2} unknown={ok3}")

    # S13 — COV-9 backup commit is TRACKED-ONLY (W3 / BL-4): the wave anchor
    # commit must never sweep untracked USER files (.env) into the repo, and
    # the anchor must survive on a clean tree (--allow-empty) so the
    # wave-scope diff (groups 14/15/17a) keeps its boundary.
    fx = Fx()
    (fx.d / ".env").write_text("AWS_ACCESS_KEY_ID=" + "AKIA" + "0" * 16 + "\n")
    (fx.d / "notes.txt").write_text("user scratch — never the agent's to commit\n")
    run(["git", "add", "-u"], fx.d)  # the new COV-9 staging step (tracked-only)
    r_commit = run(["git", "commit", "--allow-empty", "-m", "backup: before changes"], fx.d)
    tracked = run(["git", "ls-files", ".env", "notes.txt"], fx.d).stdout.strip()
    env_history = run(["git", "log", "--all", "--name-only", "--format=", "--", ".env"], fx.d).stdout.strip()
    anchor = run(["git", "log", "--format=%s", "-1"], fx.d).stdout.strip()
    ok13 = (r_commit.returncode == 0 and not tracked and not env_history
            and anchor == "backup: before changes")
    rec("S13 COV-9 tracked-only backup: untracked .env never enters a commit (W3 PoC)",
        ok13,
        f"tracked={tracked!r} env_in_history={bool(env_history)} anchor={anchor!r}")

    # S14 — Review B5 (A4.9): group 9 is scoped to the CURRENT task block —
    # a historical green baseline must not license a later change-wave, and
    # the DOC skip needs an EXPLICIT class (unlabeled block is not DOC).
    fx = Fx()
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: wave1 (old)\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
        "- Baseline verified GREEN\n"
        "\n## Task: wave2 (current)\n- iter 1 PASS: x (evidence: log tests/x.log -> 1/1)\n")
    r = fx.assert_run()
    ok14a = r.returncode == 1 and "COV-9" in r.stdout
    # (C1 supersedes the explicit-class rule: an unlabeled DOCS-only wave
    # derives DOC and its skip is honest; the B5 hole is a CODE wave hiding
    # behind the skip — pinned below as ok14b2.)
    fx = Fx()
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: unlabeled doc\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
        "- COV-9 skipped — reason: documentation-only change\n")
    r = fx.assert_run()
    ok14b = r.returncode == 0
    fx = Fx()
    fx.write("app/hidden.py", "x = 1\n")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: unlabeled code\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
        "- COV-9 skipped — reason: documentation-only change\n")
    r = fx.assert_run()
    ok14b2 = r.returncode == 1 and "COV-9" in r.stdout
    fx = Fx()
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: doc labeled\n- class: DOC — docs-only wave\n"
        "- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
        "- COV-9 skipped — reason: documentation-only change (no runtime to baseline-test)\n")
    r = fx.assert_run()
    ok14c = r.returncode == 0
    # Review B6 token: "Baseline has N pre-existing failures" + disposition
    fx = Fx()
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: red baseline\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
        "- Baseline has 2 pre-existing failures → logged to tests/b.log; proceed quarantined by scope (AUTO)\n")
    r = fx.assert_run()
    ok14d = r.returncode == 0
    fx = Fx()
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: red baseline no disposition\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
        "- Baseline has 2 pre-existing failures\n")
    r = fx.assert_run()
    ok14e = r.returncode == 1
    rec("S14 COV-9 per-block: old-block never licenses; CODE-unlabeled skip fails (C1-derived); DOC skip passes",
        ok14a and ok14b and ok14b2 and ok14c and ok14d and ok14e,
        f"old-block={ok14a} doc-unlabeled={ok14b} code-unlabeled={ok14b2} doc={ok14c} red-baseline={ok14d} red-no-disposition={ok14e}")

    # S15 — Review A4/re-review R3: group-14 detail must NEVER echo matched
    # content (the gate routes details into tool results / session logs).
    fx = Fx()
    (fx.d / "cred.txt").write_text("K = \"" + "AKIA" + "0" * 16 + "\"\n")
    r = fx.assert_run()
    secret_body = "AKIA" + "0" * 16
    ok15 = (r.returncode == 1 and "secret scan" in r.stdout
            and "redacted" in r.stdout and secret_body not in r.stdout)
    rec("S15 group-14 detail is redacted (no secret material in output)",
        ok15, "redacted" if ok15 else r.stdout[-200:].replace("\n", " "))

    # S16 — C1 (P1): class derives from the wave diff's file kinds; a code
    # change labeled `class: DOC` must FAIL (the plan's own acceptance case).
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    fx.sh("git", "add", "-A")
    fx.sh("git", "commit", "-qm", "backup: before changes")  # anchor BEFORE the change
    (fx.d / "app" / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: mislabeled\n- class: DOC — docs-only wave\n"
        "- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n- Baseline verified GREEN\n")
    r = fx.assert_run()
    ok16a = r.returncode == 1 and "class mismatch" in r.stdout
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: honest\n- class: CODE — logic change per §V11.2\n"
        "- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n- Baseline verified GREEN\n")
    r = fx.assert_run()
    ok16b = r.returncode == 0
    rec("S16 C1 derived-class cross-check: a+b→a-b under class:DOC FAILS; honest class:CODE passes",
        ok16a and ok16b, f"mislabeled={ok16a} honest={ok16b}")

    # S17 — C2 (P1): a 1-byte "screenshot" named *.png is not evidence
    fx = Fx()
    (fx.d / "tests" / "fake.png").write_bytes(b"X")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: fake png\n- iter 1 PASS: shot (evidence: tests/fake.png -> 1/1)\n"
        "- Baseline verified GREEN\n")
    r = fx.assert_run()
    ok17a = r.returncode == 1 and "magic" in r.stdout
    fx = Fx()
    (fx.d / "tests" / "real.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (640).to_bytes(4, "big") + (400).to_bytes(4, "big") + b"\x08\x06\x00\x00\x00" + b"\x00" * 32)
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: real png\n- iter 1 PASS: shot (evidence: tests/real.png -> 1/1)\n"
        "- Baseline verified GREEN\n")
    r = fx.assert_run()
    ok17b = r.returncode == 0
    rec("S17 C2 media magic: 1-byte fake PNG FAILS; magic-clean PNG passes",
        ok17a and ok17b, f"fake={ok17a} real={ok17b}")

    # S18 — C2 (P1): delivered scripts must be runnable syntax
    fx = Fx()
    (fx.d / "script" / "linux" / "start.sh").write_bytes(b"")
    r = fx.assert_run()
    ok18a = r.returncode == 1 and "empty script" in r.stdout
    fx = Fx()
    (fx.d / "script" / "linux" / "start.sh").write_bytes(
        b"#!/bin/sh\nif [ then\n  echo broken\n")
    r = fx.assert_run()
    ok18b = r.returncode == 1 and "syntax" in r.stdout
    # CRLF is its own verdict (ShellCheck SC1017 = error): write_bytes keeps
    # the fixture LF-explicit on every platform; this one is deliberately CRLF
    fx = Fx()
    (fx.d / "script" / "linux" / "start.sh").write_bytes(b"#!/bin/sh\r\nexit 0\r\n")
    r = fx.assert_run()
    ok18c = r.returncode == 1 and "SC1017" in r.stdout
    rec("S18 C2 script syntax: 0-byte FAILS; broken shell FAILS; CRLF shell FAILS (SC1017)",
        ok18a and ok18b and ok18c, f"empty={ok18a} broken={ok18b} crlf={ok18c}")

    # S19 — C3 tamper: sealed evidence that changes afterwards FAILS
    SEAL = REPO / "scripts" / "evidence_seal.py"
    fx = Fx()
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (640).to_bytes(4, "big") + (400).to_bytes(4, "big") + b"\x08\x06\x00\x00\x00" + b"\x00" * 32
    (fx.d / "tests" / "shot.png").write_bytes(png)
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: sealed\n- iter 1 PASS: shot (evidence: tests/shot.png -> 1/1)\n- Baseline verified GREEN\n")
    r_seal = run([sys.executable, str(SEAL)], fx.d)
    r = fx.assert_run()
    ok19a = r_seal.returncode == 0 and r.returncode == 0
    (fx.d / "tests" / "shot.png").write_bytes(png + b"tampered")
    r = fx.assert_run()
    ok19b = r.returncode == 1 and "hash mismatch" in r.stdout
    rec("S19 C3 manifest: seal passes; tampered sealed evidence FAILS",
        ok19a and ok19b, f"sealed={ok19a} tamper={ok19b}")

    # S20 — C3 freshness: code changed AFTER sealing = stale evidence
    fx = Fx()
    (fx.d / "tests" / "shot.png").write_bytes(png)
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: stale\n- iter 1 PASS: shot (evidence: tests/shot.png -> 1/1)\n- Baseline verified GREEN\n")
    run([sys.executable, str(SEAL)], fx.d)
    (fx.d / "app").mkdir()
    (fx.d / "app" / "late.py").write_text("x = 2\n")  # code lands after the seal
    r = fx.assert_run()
    ok20 = r.returncode == 1 and "STALE" in r.stdout
    rec("S20 C3 freshness: code change after seal FAILS (先造证据后改代码)",
        ok20, "stale" if ok20 else (r.stdout[-120:]).replace("\n", " "))

    # S21 — C3b: skip markers need reasons; sealed baseline blocks silent weakenings
    fx = Fx()
    fx.write("tests/test_math.py", "def test_add():\n    assert 1 + 1 == 2\n")
    fx.commit("add test")
    run([sys.executable, str(SEAL)], fx.d)   # baseline created for test_math.py
    fx.write("tests/test_math.py", "import pytest\n\n@pytest.mark.skip\ndef test_add():\n    assert 1 + 1 == 2\n")
    fx.commit("weaken via skip")
    r = fx.assert_run()
    ok21a = r.returncode == 1 and "C3b" in r.stdout
    fx.append_log("- test-change: tests/test_math.py — fixture exercises skip semantics")
    run([sys.executable, str(SEAL)], fx.d)   # re-seal now licensed
    r2 = fx.assert_run()
    rec("S21 C3b: skip marker without reason FAILS; reasoned + re-sealed passes",
        ok21a and r2.returncode == 0, f"blocked={ok21a} after-rc={r2.returncode}")

    # S22 — Review R-C1 (BL-13): the baseline is licensed terrain — first
    # seal around a new test file, AND re-seal after deletion, both need the
    # `- test-change:` reason.
    fx = Fx()
    fx.write("tests/test_math.py", "def test_add():\n    assert 1 + 1 == 2\n")
    fx.commit("add test")
    r_first = run([sys.executable, str(SEAL)], fx.d)
    ok22a = r_first.returncode == 1 and "silent rebuild" in r_first.stdout
    fx.append_log("- test-change: tests/test_math.py — fixture adds a spec test")
    run([sys.executable, str(SEAL)], fx.d)   # licensed → baseline created
    (fx.d / "tests" / "test_baseline.json").unlink()   # the attack: delete it
    fx.write("tests/test_math.py", "def test_add():\n    pass\n")
    fx.commit("weaken test")
    # ... in a NEW task block with NO reason (an old block's reason must not
    # license a later wave's weakening — review R-I2)
    fx.write("tests/verification_log.md",
             fx.d.joinpath("tests/verification_log.md").read_text()
             + "\n## Task: later wave\n- iter 2 PASS: x (evidence: tests/acceptance.md, 1/1)\n")
    r_seal2 = run([sys.executable, str(SEAL)], fx.d)
    ok22 = r_seal2.returncode == 1 and "silent rebuild" in r_seal2.stdout
    fx.append_log("- test-change: tests/test_math.py — fixture exercises the licensing path")
    r_seal3 = run([sys.executable, str(SEAL)], fx.d)
    ok22b = r_seal3.returncode == 0
    rec("S22 C3b/BL-13: first seal + baseline deletion cannot silently re-baseline",
        ok22a and ok22 and ok22b, f"first-refused={ok22a} del-refused={ok22} licensed-seal={ok22b}")

    # S23 — repo hygiene (COV-9 preflight / group 21): a tracked vendor
    # path is a hard failure even when `.gitignore` covers it.
    fx = Fx()
    fx.write("node_modules/pkg/index.js", "module.exports = 1\n")
    fx.sh("git", "add", "-f", "node_modules/pkg/index.js")
    fx.commit("track a dependency tree")
    r = fx.assert_run()
    ok23 = r.returncode == 1 and "repo-hygiene" in r.stdout and "node_modules" in r.stdout
    rec("S23 repo-hygiene: tracked node_modules FAILS",
        ok23, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S24 — a git repo without `.gitignore` is RED before the baseline
    # commit (the incident's starting condition).
    fx = Fx()
    (fx.d / ".gitignore").unlink()
    fx.commit("remove .gitignore")
    r = fx.assert_run()
    ok24 = r.returncode == 1 and "repo-hygiene" in r.stdout and ".gitignore" in r.stdout
    rec("S24 repo-hygiene: missing .gitignore FAILS",
        ok24, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S25 — the gate must fail fast on an untracked path explosion instead
    # of walking/reading 2,001 files.
    fx = Fx()
    for i in range(2001):
        fx.write(f"scratch/f{i}.txt", "x\n")
    t0 = time.time()
    r = fx.assert_run()
    elapsed = time.time() - t0
    ok25 = (r.returncode == 1 and "repo-hygiene" in r.stdout
            and ("2001" in r.stdout or "untracked" in r.stdout)
            and elapsed < 30)
    rec("S25 repo-hygiene: >2,000 untracked files FAILS fast (no full scan)",
        ok25, f"elapsed={elapsed:.1f}s rc={r.returncode}")

    # S26 — a global excludesFile is not repo protection: the gate must
    # require the match to come from a COMMITTED .gitignore.
    fx = Fx()
    (fx.d / ".gitignore").write_text("")
    globdir = pathlib.Path(tempfile.mkdtemp(prefix="vwglob-"))
    (globdir / ".gitignore").write_text("node_modules/\n")
    fx.sh("git", "config", "core.excludesFile", str(globdir / ".gitignore"))
    fx.write("package.json", "{}\n")
    fx.commit("empty local ignore + global .gitignore")
    r = fx.assert_run()
    ok26 = r.returncode == 1 and "repo-hygiene" in r.stdout and "node_modules" in r.stdout
    rec("S26 repo-hygiene: global excludesFile does not satisfy committed .gitignore",
        ok26, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S27 — monorepo: frontend/package.json is covered by the root
    # .gitignore; the probe must use the manifest directory, not root only.
    fx = Fx()
    (fx.d / ".gitignore").write_text(".DS_Store\n__pycache__/\n.venv/\n.env\n")
    fx.write("frontend/.gitignore", "node_modules/\n")
    fx.write("frontend/package.json", "{}\n")
    fx.write("frontend/src/app.ts", "export const x = 1\n")
    fx.commit("nested-only ignore for frontend manifest")
    r = fx.assert_run()
    ok27 = r.returncode == 0
    rec("S27 repo-hygiene: nested tracked frontend/.gitignore covers its manifest",
        ok27, (r.stdout + r.stderr).strip().splitlines()[-1][:120] if (r.stdout + r.stderr).strip() else "no output")

    # S28 — an untracked .gitignore is local-only protection; collaborators
    # and CI never receive it.
    fx = Fx()
    (fx.d / ".gitignore").unlink()
    fx.commit("remove tracked ignore")
    (fx.d / ".gitignore").write_text("node_modules/\n")
    (fx.d / "package.json").write_text("{}\n")
    r = fx.assert_run()
    ok28 = r.returncode == 1 and "repo-hygiene" in r.stdout and ("untracked" in r.stdout or "not committed" in r.stdout)
    rec("S28 repo-hygiene: untracked .gitignore FAILS (must be committed)",
        ok28, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S29 — `--final` checks the largest blob unconditionally (a 41 MiB
    # incompressible blob is below the 1 GiB .git cap but still poisonous).
    fx = Fx()
    fx.write("assets/big.bin", "0" * (41 * 1024 * 1024))
    fx.commit("large blob")
    run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], fx.d)  # re-anchor: the blob is history, not this wave
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    ok29 = r.returncode == 1 and "largest blob" in r.stdout and "40 MiB" in r.stdout
    rec("S29 repo-hygiene: --final rejects a 41 MiB tracked blob",
        ok29, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S30 — an ignored `.env` is still scanned by group 14 (prevention is not
    # a blindfold); the 45k-file incident must not turn into a secret leak.
    fx = Fx()
    (fx.d / ".env").write_text("AWS_ACCESS_KEY_ID=" + "AKIA" + "0" * 16 + "\n")
    r = fx.assert_run()
    ok30 = r.returncode == 1 and "secret scan" in r.stdout and ".env" in r.stdout
    rec("S30 group 14 scans an ignored .env (not just untracked files)",
        ok30, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S31 — prefixed/suffixed credential names (DB_PASSWORD,
    # OPENAI_API_KEY, AWS_SECRET_ACCESS_KEY) must hit the generic rule.
    fx = Fx()
    (fx.d / ".env").write_text(
        "DB_PASSWORD=" + "supersecretvalue123456" + "\n"
        "OPENAI_API_KEY=" + "abcdefghijklmnopqrstuvwx" + "\n")
    r = fx.assert_run()
    ok31 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S31 group 14 generic rule catches prefixed credential names",
        ok31, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S32 — named-rule parity: Google API key and JWT also hit group 14.
    fx = Fx()
    fx.write("app/keys.py",
             'google = "' + "AIza" + "0" * 35 + '"\n'
             'jwt = "' + "eyJhbGciOiJIUzI1NiJ9." + "eyJzdWIiOiIxIn0." + "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c" + '"\n')
    fx.commit("google + jwt")
    r = fx.assert_run()
    ok32 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S32 group 14 named-rule parity (Google key + JWT)",
        ok32, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S33 — staged-only .gitignore is not committed protection.
    fx = Fx()
    fx.sh("git", "rm", "-q", ".gitignore")
    fx.commit("remove tracked ignore")
    (fx.d / ".gitignore").write_text("node_modules/\n.venv/\n")
    fx.write("package.json", "{}\n")
    fx.sh("git", "add", ".gitignore", "package.json")
    r = fx.assert_run()
    ok33 = r.returncode == 1 and "repo-hygiene" in r.stdout and "node_modules" in r.stdout
    rec("S33 repo-hygiene: staged-only .gitignore FAILS (HEAD must carry it)",
        ok33, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S34 — path-level approval licenses an ignored local secret file
    # (no inline marker on every .env line / PEM header required).
    fx = Fx()
    (fx.d / ".env").write_text("DB_PASSWORD=" + "supersecretvalue123456" + "\n")
    fx.append_log("- secret-approved: .env — local development config (ignored, never committed)")
    r = fx.assert_run()
    ok34 = r.returncode == 0
    rec("S34 path-level `- secret-approved: .env` licenses an ignored secret file",
        ok34, (r.stdout + r.stderr).strip().splitlines()[-1][:120] if (r.stdout + r.stderr).strip() else "no output")

    # S35 — non-git `--existing` project: group 14 still walks source/config
    # (group 21 is legitimately na, but the secret gate must not vanish).
    fx = Fx()
    shutil.rmtree(fx.d / ".git")
    fx.write("config.py", "DB_PASSWORD=" + "supersecretvalue123456" + "\n")
    r = fx.assert_run()
    ok35 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S35 non-git group 14 fallback catches a source credential",
        ok35, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S36 — an uncommitted pattern edit is not repo protection.
    fx = Fx()
    (fx.d / ".gitignore").write_text(".venv/\n")  # drops node_modules/, uncommitted
    fx.write("package.json", "{}\n")
    r = fx.assert_run()
    ok36 = r.returncode == 1 and "repo-hygiene" in r.stdout and "node_modules" in r.stdout
    rec("S36 repo-hygiene: uncommitted .gitignore pattern FAILS",
        ok36, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S37 — W9 P0-2: benign generic-credential shapes on added lines pass:
    # approval metadata, character-set constants, PWD path values, and safe
    # reference expressions (same semantics as scripts/scan_secrets.py).
    fx = Fx()
    fx.write("app/env.py",
             "PWD: /var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/envprobe-rfb827ir\n"
             'TOKEN_ALPHABET = "ABCDEFGHJKLNQRSTUVWXYZ234679"\n'
             'password = os.environ.get("PASSWORD")\n'
             'token = process.env.API_TOKEN\n'
             "- secret-approved: app/config.py — user explicitly requested this local credential (task scope)\n")
    fx.commit("benign env shapes")
    r = fx.assert_run()
    ok37 = r.returncode == 0
    rec("S37 group 14: PWD path / ALPHABET / safe refs / approval metadata pass",
        ok37, (r.stdout + r.stderr).strip().splitlines()[-1][:140] if (r.stdout + r.stderr).strip() else "no output")

    # S38 — W9 P0-2: a quoted real-looking password literal still fails.
    fx = Fx()
    secret = "q7Lm" + "2Pz9" + "Rt4V"
    fx.write("app/config.py", 'password = "' + secret + '"\n')
    fx.commit("real-looking password")
    r = fx.assert_run()
    ok38 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S38 group 14: quoted real-looking password literal fails",
        ok38, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S39 — W9 P0-2: a dotted prefixed key (SENDGRID_API_KEY=SG.…) is NOT a
    # reference expression; the stricter reference predicate must keep it.
    fx = Fx()
    (fx.d / ".env").write_text("SENDGRID_API_KEY=SG." + "abcdefghijklmnopqrstuvwx" + "\n")
    r = fx.assert_run()
    ok39 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S39 group 14: dotted prefixed key (SG.…) still fails",
        ok39, (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S40 — W9 review #1: `pwd` remains a generic key (path values are exempt
    # via PATH_KEY + PATH_VALUE, not by dropping the keyword).
    fx = Fx()
    fx.write("app/config.py", 'db_pwd = "' + "q7Lm2Pz9Rt4V" + '"\n')
    fx.commit("db_pwd secret")
    r = fx.assert_run()
    ok40 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S40 group 14: db_pwd still detected", ok40,
        (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S41 — approval metadata skips only the generic rule; named shapes on the
    # same line still fire (W9 review #4).
    fx = Fx()
    fx.write("app/notes.txt",
             "- secret-approved: app/config.py — " + "AKIA" + "0" * 16 + "\n")
    fx.commit("approval line with named secret")
    r = fx.assert_run()
    ok41 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S41 group 14: named secret on approval line still fails", ok41,
        (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S42 — path-value exemption is scoped to path-typed keys; an api_key with
    # a `/`-prefixed value is still a candidate (W9 review #4).
    fx = Fx()
    fx.write("app/config.py", "api_key = /secret/db/" + "password\n")
    fx.commit("path-shaped api key")
    r = fx.assert_run()
    ok42 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S42 group 14: api_key path-like value still fails", ok42,
        (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S43 — W9 review #4: a length/len key with a non-numeric value and a
    # dotted literal with a non-identifier segment are still credentials.
    fx = Fx()
    fx.write("app/config.py",
             'TOKEN_LEN = "' + "q7Lm2Pz9Rt4V" + '"\n'
             "password = config." + "9f2a8b7c6d5e4f3a2b1c\n")
    fx.commit("len + dotted literal")
    r = fx.assert_run()
    ok43 = r.returncode == 1 and "secret scan" in r.stdout
    rec("S43 group 14: non-numeric len + dotted literal fail", ok43,
        (r.stdout.strip().splitlines() or ["no output"])[0][:120])

    # S44 — W9 review #4: a path-typed key with a `/` value is clean.
    fx = Fx()
    fx.write("app/config.py", "DB_PASSWORD_FILE=/run/secrets/db_password\n")
    fx.commit("path-typed key")
    r = fx.assert_run()
    ok44 = r.returncode == 0
    rec("S44 group 14: path-typed key (/run/secrets) passes", ok44,
        (r.stdout + r.stderr).strip().splitlines()[-1][:140] if (r.stdout + r.stderr).strip() else "no output")

    # ---- W18 G1 three-state seal diagnostics (2026-10-21) ----
    # S45 — no-seal is a BOOTSTRAP state (WARN), not a violation (OWASP
    # CVE-lite first-run baseline: no baseline != violation). Plan G1
    # acceptance: 伪造无 seal 的项目根 → 输出 `evidence seal: none yet` 且不 BLOCK.
    fx = Fx()
    r = fx.assert_run()
    out45 = r.stdout + r.stderr
    ok45 = r.returncode == 0 and "evidence seal: none yet" in out45
    rec("S45 G1 no-seal root → WARN `evidence seal: none yet`, exit 0", ok45,
        f"rc={r.returncode} warn={('evidence seal: none yet' in out45)}")

    # S46 — bootstrap window (早期波次豁免): the seal obligation only goes
    # live after the first GREEN run — before any `- iter N PASS` in the
    # current task block, a stale seal is WARN, never FAIL.
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "a.py").write_text("x = 1\n")
    fx.commit("code")
    run([sys.executable, str(SEAL)], fx.d)
    (fx.d / "app" / "a.py").write_text("x = 2\n")  # code changes after the seal
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: w18-bootstrap\n- Baseline verified GREEN\n"
        "- iter 1 FAIL: criterion #1 | diagnosis: the validator ran before state hydration | changed: app/a.py\n"
        "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out46 = r.stdout + r.stderr
    stale_fail46 = "  - sealed evidence is STALE" in out46
    stale_warn46 = "WARN sealed evidence is STALE" in out46
    ok46 = r.returncode == 0 and (not stale_fail46) and stale_warn46
    rec("S46 G1 bootstrap (no green PASS yet): stale seal is WARN, not FAIL", ok46,
        f"rc={r.returncode} fail={stale_fail46} warn={stale_warn46}")
    # S47 — teeth stay: with green evidence in the block (seal live), a stale
    # seal FAILS and the message carries the STALE wording (plan acceptance:
    # touch code → seal → change code → BLOCK, 文案含 STALE).
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "a.py").write_text("x = 1\n")
    fx.commit("code")
    run([sys.executable, str(SEAL)], fx.d)
    (fx.d / "app" / "a.py").write_text("x = 2\n")
    r = fx.assert_run()
    out47 = r.stdout + r.stderr
    ok47 = r.returncode == 1 and "  - sealed evidence is STALE" in out47
    rec("S47 G1 seal-live stale seal → FAIL, message contains STALE", ok47,
        f"rc={r.returncode} msg={('sealed evidence is STALE' in out47)}")

    # S48 — no-seal + cited media at completion still FAILS (missing !=
    # success at the sealing moment): the bootstrap exemption must not gut
    # the media-seal rule.
    fx = Fx()
    (fx.d / "tests" / "shot.png").write_bytes(png)
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: noseal-media\n- iter 1 PASS: shot (evidence: tests/shot.png -> 1/1)\n- Baseline verified GREEN\n")
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out48 = r.stdout + r.stderr
    ok48 = r.returncode == 1 and "not sealed" in out48
    rec("S48 G1 no-seal + cited media at --final → FAIL (media rule keeps teeth)", ok48,
        f"rc={r.returncode} msg={('not sealed' in out48)}")

    # S49 — W18 review B: deleting tests/evidence_manifest.json while
    # tests/test_baseline.json survives must NOT downgrade tamper checks to
    # advisory — evidence_seal.py writes both files in one run, so a lone
    # baseline proves a seal once existed (C3 tamper, not bootstrap).
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "a.py").write_text("x = 1\n")
    fx.commit("code")
    run([sys.executable, str(SEAL)], fx.d)
    (fx.d / "tests" / "evidence_manifest.json").unlink()
    r = fx.assert_run()
    out49 = r.stdout + r.stderr
    ok49 = r.returncode == 1 and "evidence_manifest.json missing" in out49
    rec("S49 G1 partial seal (baseline survives, manifest deleted) → FAIL (C3)", ok49,
        f"rc={r.returncode} msg={('evidence_manifest.json missing' in out49)}")

    # S50 — W18 review A/B: the bootstrap exemption never reaches completion
    # — with no green PASS in the block, cited media at --final still FAILS
    # unconditionally (missing != success at the sealing moment). The fixture
    # carries the baseline line so the media rule is the ONLY possible failure
    # (review r2: without it group 9 failed first and the pin was vacuous),
    # and the assertion keys on the FAIL-line shape, not on rc alone.
    fx = Fx()
    (fx.d / "tests" / "shot.png").write_bytes(png)
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: noseal-media-nogreen\n- Baseline verified GREEN\n"
        "- iter 1 FAIL: criterion #1 | diagnosis: the media capture step never completed | changed: tests/shot.png\n"
        "- working-note: created (fixture)\n")
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out50 = r.stdout + r.stderr
    ok50 = r.returncode == 1 and "  - cited media evidence is not sealed" in out50
    rec("S50 G1 bootstrap + media at --final → still FAIL (completion always enforces)", ok50,
        f"rc={r.returncode} failline={('  - cited media evidence is not sealed' in out50)}")

    # S51 — the bootstrap window must not reach --final for the stale state
    # either (review r2 probe A: `--final` always enforces).
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "a.py").write_text("x = 1\n")
    fx.commit("code")
    run([sys.executable, str(SEAL)], fx.d)
    (fx.d / "app" / "a.py").write_text("x = 2\n")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: stale-final-nogreen\n- Baseline verified GREEN\n"
        "- iter 1 FAIL: criterion #1 | diagnosis: the freshness check never completed | changed: app/a.py\n"
        "- working-note: created (fixture)\n")
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out51 = r.stdout + r.stderr
    ok51 = r.returncode == 1 and "  - sealed evidence is STALE" in out51
    rec("S51 G1 bootstrap + stale seal at --final → FAIL STALE (completion always enforces)", ok51,
        f"rc={r.returncode} failline={('  - sealed evidence is STALE' in out51)}")

    # S52 — the green marker uses COV-1's `PASS\\b` grammar: a colon-less PASS
    # line must bring the seal obligation live (review r2 probe B).
    fx = Fx()
    (fx.d / "app").mkdir()
    (fx.d / "app" / "a.py").write_text("x = 1\n")
    fx.commit("code")
    run([sys.executable, str(SEAL)], fx.d)
    (fx.d / "app" / "a.py").write_text("x = 2\n")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: colonless-pass\n- Baseline verified GREEN\n"
        "- iter 1 PASS — smoke run (evidence: scaffold, 1/1)\n")
    r = fx.assert_run()
    out52 = r.stdout + r.stderr
    ok52 = r.returncode == 1 and "  - sealed evidence is STALE" in out52
    rec("S52 G1 colon-less `- iter 1 PASS` still arms the seal obligation", ok52,
        f"rc={r.returncode} failline={('  - sealed evidence is STALE' in out52)}")

    # ---- W18 batch 2/3: ratchet · claim-lint · wave-base · deletions · hint ----
    # S53 — G3 ratchet: an unrecorded >40 MiB blob still FAILS at --final
    # (S29 pins the same; kept as the ratchet's contrast arm).
    fx = Fx()
    fx.write("assets/big.bin", "0" * (41 * 1024 * 1024))
    fx.commit("large blob")
    run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], fx.d)  # re-anchor: the blob is history, not this wave
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out53 = r.stdout + r.stderr
    ok53 = r.returncode == 1 and "largest blob" in out53 and "record-debt" in out53
    rec("S53 G3 unrecorded 41 MiB blob at --final → FAIL naming --record-debt", ok53,
        f"rc={r.returncode} hint={('record-debt' in out53)}")

    # S54 — G3 ratchet: `--record-debt` records it once → the same blob is
    # WARN `held at baseline` and no longer FAILS (existing debt does not
    # block the next wave).
    r_rec = run([sys.executable, "tests/assert_artifacts.py", "--record-debt"], fx.d)
    fx.commit("record existing blob debt (shrink-only baseline)")  # the committed baseline is the ratchet's tamper anchor
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out54 = r.stdout + r.stderr
    ok54 = r_rec.returncode == 0 and r.returncode == 0 and "held at baseline" in out54
    rec("S54 G3 --record-debt → WARN `held at baseline`, exit 0", ok54,
        f"rec_rc={r_rec.returncode} rc={r.returncode} held={('held at baseline' in out54)} "
        f"fails={[l for l in out54.splitlines() if l.startswith('  - ')][:2]}")

    # S55 — G3 ratchet teeth: growth beyond the recorded value FAILS
    # (recorded edited smaller = the measurement grew; debt may shrink, never grow).
    import json as _json
    bl_p = fx.d / "tests" / "debt_baseline.json"
    if bl_p.exists():
        bl = _json.loads(bl_p.read_text())
        for k in bl:
            bl[k]["recorded"] = 1024
        bl_p.write_text(_json.dumps(bl))
        r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
        out55 = r.stdout + r.stderr
        ok55 = r.returncode == 1 and "GREW beyond" in out55
        det55 = f"rc={r.returncode} grew={('GREW beyond' in out55)}"
    else:
        ok55 = False
        det55 = "no debt_baseline.json (--record-debt missing)"
    rec("S55 G3 growth beyond recorded debt → FAIL (shrink-only ratchet)", ok55, det55)

    # S56 — G4: progress-state iter lines (PARTIAL/PENDING/POST-HOC) are not
    # claim-checked; a bare claim on a PASS line still is.
    fx = Fx()
    fx.write("tests/verification_log.md",
             "## Task: w18-g4\n- Baseline verified GREEN\n"
             "- iter 4 PARTIAL: verified the remaining cases\n"
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out56 = r.stdout + r.stderr
    ok56 = "claim without stated coverage" not in out56
    rec("S56 G4 `- iter 4 PARTIAL: verified …` (progress state) not flagged", ok56,
        f"rc={r.returncode} flagged={('claim without stated coverage' in out56)}")

    # S57 — G4: a bare claim on a PASS line (no coverage) still flags.
    fx = Fx()
    fx.write("tests/verification_log.md",
             "## Task: w18-g4b\n- Baseline verified GREEN\n"
             "- iter 1 PASS: verified the endpoint\n"
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out57 = r.stdout + r.stderr
    ok57 = r.returncode == 1 and "claim without stated coverage" in out57
    rec("S57 G4 `- iter 1 PASS: verified …` without coverage → flagged", ok57,
        f"rc={r.returncode} flagged={('claim without stated coverage' in out57)}")

    # S58 — G4 claim-ack channel: a reasoned suppression licenses the line; a
    # bare suppression (no reason) does not.
    fx = Fx()
    fx.write("tests/verification_log.md",
             "## Task: w18-g4c\n- Baseline verified GREEN\n"
             "- iter 1 PASS: verified the endpoint\n"
             '- claim-ack: line 3 "verified the endpoint" — oracle is the external acceptance suite, scope stated there\n' 
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out58 = r.stdout + r.stderr
    ok58a = "claim without stated coverage" not in out58
    fx.write("tests/verification_log.md",
             "## Task: w18-g4d\n- Baseline verified GREEN\n"
             "- iter 1 PASS: verified the endpoint\n"
             '- claim-ack: line 3 "verified the endpoint" —\n' 
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out58b = r.stdout + r.stderr
    ok58b = "claim without stated coverage" in out58b
    rec("S58 G4 `- claim-ack:` with reason suppresses; bare ack does not", ok58a and ok58b,
        f"reasoned={ok58a} bare={ok58b}")

    # S59 — G4 scope: the claim lint scans ONLY the current task block — a
    # historical block's bare claim is out of scope (W11 line-47 class).
    fx = Fx()
    fx.write("tests/verification_log.md",
             "## Task: old\n- iter 1 PASS: verified the old thing\n\n"
             "## Task: w18-g4e\n- Baseline verified GREEN\n"
             "- iter 1 PASS: all criteria (evidence: scaffold, 1/1)\n"
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out59 = r.stdout + r.stderr
    ok59 = "claim without stated coverage" not in out59
    rec("S59 G4 historical block's bare claim is out of scope (current block only)", ok59,
        f"rc={r.returncode} flagged={('claim without stated coverage' in out59)}")

    # S60 — G6: the task-level `- wave-base: <sha>` anchor decides the wave
    # sampling; without it a stale anchor makes C1 name the escape hatch.
    fx = Fx()
    fx.write("app/model.py", "class M:\n    pass\n")
    fx.commit("code before this task")
    fx.write("docs/plan.md", "doc-only task\n")
    fx.commit("doc task")
    fx.append_log("- wave-base: " + run(["git", "rev-parse", "HEAD~1"], fx.d).stdout.strip())
    fx.append_log("- class: DOC — doc-only wave (plan prose)")
    r = fx.assert_run()
    out60 = r.stdout + r.stderr
    ok60 = r.returncode == 0 and "MORE LENIENT" not in out60
    rec("S60 G6 `- wave-base:` task anchor → doc wave derives DOC (no C1 false positive)", ok60,
        f"rc={r.returncode} c1={('MORE LENIENT' in out60)}")

    fx2 = Fx()
    fx2.write("app/model.py", "class M:\n    pass\n")
    fx2.commit("code before this task")
    fx2.write("docs/plan.md", "doc-only task\n")
    fx2.commit("doc task")
    fx2.append_log("- class: DOC — doc-only wave (plan prose)")
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing"], fx2.d)
    out60b = r.stdout + r.stderr
    ok60b = r.returncode == 1 and "- wave-base:" in out60b
    rec("S60b G6 without `- wave-base:` the C1 failure names the escape hatch", ok60b,
        f"rc={r.returncode} hint={('- wave-base:' in out60b)}")

    # S61 — R3: a deletion-only wave is shrink, never wave-too-large.
    fx = Fx()
    for i in range(3000):
        fx.write(f"junk/f{i}.txt", "x")
    fx.commit("add junk")
    for i in range(3000):
        (fx.d / "junk" / f"{i}.txt" if False else fx.d / "junk" / f"f{i}.txt").unlink()
    run(["git", "add", "-u"], fx.d)
    run(["git", "commit", "-qm", "hygiene: drop junk"], fx.d)
    r = fx.assert_run()
    out61 = r.stdout + r.stderr
    ok61 = "wave too large" not in out61
    rec("S61 R3 pure-deletion wave never trips wave-too-large", ok61,
        f"rc={r.returncode} too_large={('wave too large' in out61)}")

    # S62 — T2: the _ignored failure carries the git-add -f hint (W12 guessed
    # 18 times; nested .gitignore files swallowed by ignore rules).
    fx = Fx()
    (fx.d / ".gitignore").write_text(".DS_Store\n__pycache__/\n*.pyc\n.venv/\nvenv/\ndist/\nbuild/\n.env\n")
    (fx.d / "frontend").mkdir()
    (fx.d / "frontend" / "package.json").write_text("{}\n")
    fx.commit("frontend manifest, no node_modules rule")
    r = fx.assert_run()
    out62 = r.stdout + r.stderr
    ok62 = r.returncode == 1 and "git add -f" in out62
    rec("S62 T2 _ignored failure carries the `git add -f` hint", ok62,
        f"rc={r.returncode} hint={('git add -f' in out62)}")

    # S63 — G5: a hand-typed sha (63 hex chars) warns; a real 64-hex does not.
    fx = Fx()
    fx.append_log("- rebase-map: " + "a" * 63)
    r = fx.assert_run()
    out63 = r.stdout + r.stderr
    ok63a = "suspected hand-typed sha" in out63
    fx = Fx()
    fx.append_log("- rebase-map: " + "a" * 64)
    r = fx.assert_run()
    ok63b = "suspected hand-typed sha" not in (r.stdout + r.stderr)
    rec("S63 G5 63-hex hand-typed sha WARNs; 64-hex is clean", ok63a and ok63b,
        f"short63={ok63a} ok64={ok63b}")

    # S64 — G5: under a cli/library profile the seal binds cited non-web
    # evidence (tests/**/*.log|json|md), and tampering invalidates it.
    import json as _j2
    fx = Fx()
    (fx.d / "tests" / "project_profile.json").write_text(_j2.dumps({"profile": "library"}))
    (fx.d / "tests" / "w18").mkdir()
    (fx.d / "tests" / "w18" / "run.log").write_text("step1 ok\nstep2 ok\n")
    (fx.d / "tests" / "verification_log.md").write_text(
        "## Task: g5-seal\n- Baseline verified GREEN\n"
        "- iter 1 PASS: CLI run (evidence: tests/w18/run.log, 2/2)\n"
        "- working-note: created (fixture)\n")
    r_seal = run([sys.executable, str(SEAL)], fx.d)
    man = _j2.loads((fx.d / "tests" / "evidence_manifest.json").read_text())
    ok64a = r_seal.returncode == 0 and "tests/w18/run.log" in man.get("files", {})
    r_chk = run([sys.executable, str(SEAL), "--check"], fx.d)
    ok64b = r_chk.returncode == 0
    (fx.d / "tests" / "w18" / "run.log").write_text("step1 ok\nstep2 TAMPERED\n")
    r_chk2 = run([sys.executable, str(SEAL), "--check"], fx.d)
    ok64c = r_chk2.returncode == 1
    rec("S64 G5 cli/library seal binds tests/*.log; tamper fails --check", ok64a and ok64b and ok64c,
        f"bound={ok64a} clean_check={ok64b} tamper={ok64c}")

    # S65 — G5: record_evidence.sh captures the sha (64 hex, machine-copied)
    # and the log stays clean under the hand-typed-sha lint.
    fx = Fx()
    (fx.d / "tests" / "w18").mkdir()
    (fx.d / "tests" / "w18" / "run.log").write_text("ok\n")
    r_rec = run(["bash", str(REPO / "scripts" / "record_evidence.sh"),
                 "--note", "final harness run", "--hash", "tests/w18/run.log"], fx.d)
    log_txt = (fx.d / "tests" / "verification_log.md").read_text()
    r = fx.assert_run()
    out65 = r.stdout + r.stderr
    ok65 = (r_rec.returncode == 0 and "- record:" in log_txt and "sha256=" in log_txt
            and "suspected hand-typed sha" not in out65)
    rec("S65 G5 record_evidence.sh captures machine sha (64 hex, lint-clean)", ok65,
        f"rec_rc={r_rec.returncode} line={('- record:' in log_txt)} lint_clean={('suspected hand-typed sha' not in out65)}")

    # S66 — G3 tamper anchor: hand-RAISING `recorded` above the committed
    # value fails (review A PoC: raised baseline neutralized the ratchet).
    fx = Fx()
    fx.write("assets/big.bin", "0" * (41 * 1024 * 1024))
    fx.commit("large blob")
    run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], fx.d)
    run([sys.executable, "tests/assert_artifacts.py", "--record-debt"], fx.d)
    fx.commit("record debt")
    bl = _json.loads((fx.d / "tests" / "debt_baseline.json").read_text())
    for k in bl:
        bl[k]["recorded"] = 10 * 1024 * 1024 * 1024
    (fx.d / "tests" / "debt_baseline.json").write_text(_json.dumps(bl))
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out66 = r.stdout + r.stderr
    ok66 = r.returncode == 1 and "RAISED above its committed value" in out66
    rec("S66 G3 hand-raised debt baseline → FAIL (committed anchor is the truth)", ok66,
        f"rc={r.returncode} raised={('RAISED above its committed value' in out66)}")

    # S67 — G3 residual (review A/B): raising `recorded` AND committing it
    # must still FAIL — the shrink-only ratchet holds across the file's git
    # history, not just against the latest commit.
    fx = Fx()
    fx.write("assets/big.bin", "0" * (41 * 1024 * 1024))
    fx.commit("large blob")
    run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], fx.d)
    run([sys.executable, "tests/assert_artifacts.py", "--record-debt"], fx.d)
    fx.commit("record debt")
    bl = _json.loads((fx.d / "tests" / "debt_baseline.json").read_text())
    for k in bl:
        bl[k]["recorded"] = 80 * 1024 * 1024
    (fx.d / "tests" / "debt_baseline.json").write_text(_json.dumps(bl))
    fx.commit("raise the baseline (the laundering move)")
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out67 = r.stdout + r.stderr
    ok67 = r.returncode == 1 and ("RAISED" in out67 or "history" in out67)
    rec("S67 G3 committed raise of `recorded` → FAIL (ratchet spans git history)", ok67,
        f"rc={r.returncode} caught={('RAISED' in out67 or 'history' in out67)}")

    # S68 — G4 residual: a claim-ack whose line ref drifted (points at a
    # non-claim line) suppresses nothing and is itself flagged stale.
    fx = Fx()
    fx.write("tests/verification_log.md",
             "## Task: ack-drift\n- Baseline verified GREEN\n"
             "- some ordinary progress note\n"
             '- claim-ack: line 3 "some ordinary progress note" — the oracle suite carries the scope statement\n' 
             "- iter 1 PASS: verified the endpoint\n"
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out68 = r.stdout + r.stderr
    ok68 = ("claim without stated coverage" in out68) and ("stale claim-ack" in out68)
    rec("S68 G4 drifted claim-ack suppresses nothing + flags stale (content binding)", ok68,
        f"rc={r.returncode} claim_flagged={('claim without stated coverage' in out68)} stale={('stale claim-ack' in out68)}")

    # S69 — G4 content binding: an ack quoting a DIFFERENT claim than the one
    # now on the referenced line must not license it (claim→claim retarget).
    fx = Fx()
    fx.write("tests/verification_log.md",
             "## Task: ack-rebind\n- Baseline verified GREEN\n"
             '- claim-ack: line 3 "verified alpha" — the scope statement lives in the oracle suite\n'
             "- iter 1 PASS: verified gamma\n"
             "- working-note: created (fixture)\n")
    r = fx.assert_run()
    out69 = r.stdout + r.stderr
    ok69 = ("claim without stated coverage" in out69) and ("stale claim-ack" in out69)
    rec("S69 G4 quote mismatch → no suppression + stale (retarget closed)", ok69,
        f"rc={r.returncode} flagged={('claim without stated coverage' in out69)} stale={('stale claim-ack' in out69)}")

    # S70 — G3 churn window: cosmetic commits after a raise must not evict the
    # low adoption anchor (the first revision is always in the min).
    fx = Fx()
    fx.write("assets/big.bin", "0" * (41 * 1024 * 1024))
    fx.commit("large blob")
    run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], fx.d)
    run([sys.executable, "tests/assert_artifacts.py", "--record-debt"], fx.d)
    fx.commit("record debt")
    bl = _json.loads((fx.d / "tests" / "debt_baseline.json").read_text())
    for k in bl:
        bl[k]["recorded"] = 80 * 1024 * 1024
    (fx.d / "tests" / "debt_baseline.json").write_text(_json.dumps(bl))
    fx.commit("raise the baseline")
    for i in range(55):
        bl = _json.loads((fx.d / "tests" / "debt_baseline.json").read_text())
        for k in bl:
            bl[k]["reason"] = f"churn {i}"
        (fx.d / "tests" / "debt_baseline.json").write_text(_json.dumps(bl))
        fx.commit(f"churn {i}")
    r = run([sys.executable, "tests/assert_artifacts.py", "--existing", "--final"], fx.d)
    out70 = r.stdout + r.stderr
    ok70 = r.returncode == 1 and ("RAISED" in out70 or "history" in out70)
    rec("S70 G3 55 churn commits cannot evict the adoption anchor (first rev pinned)", ok70,
        f"rc={r.returncode} caught={('RAISED' in out70 or 'history' in out70)}")

    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== {len(RESULTS) - len(fails)}/{len(RESULTS)} pass" +
          (f" — FAILED: {', '.join(fails)}" if fails else " ==="))
    return 1 if fails else 0


def test_assert_group_vectors():
    """pytest entry point (the file is also a direct-run harness)."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
