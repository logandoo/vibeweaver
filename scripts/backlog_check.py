#!/usr/bin/env python3
"""backlog_check.py — C8 outer-loop ledger gate.

Two checks over tests/backlog.json (the machine-checkable stop condition):
  1. schema: valid JSON, top-level userStories list, each item carrying
     id / title / priority / passes (acceptanceCriteria + dependsOn optional).
  2. evidence binding: every item with passes:true must be named by at
     least one line in tests/verification_log.md or tests/progress.txt —
     a pass flag without an executed-test record is COV-1 fraud at the
     backlog level (a flip without evidence is the outer-loop failure mode).

W25 multi-agent (PLAN Task 6, §MA7): a `passes:true` item may instead carry
a TRANSACTIONAL CLAIM marker — a line in tests/verification_log.md (or a
string in the item's `claims` list) matching
    `- claim: task=<id> run=<run-<32hex>> attempt=<attempt-<32hex>> epoch=<int>`
bound to that item's id. A claim marker additionally requires:
    * a live lease (optional --leases JSON {attempt_id: expiry_epoch_seconds};
      an absent file = legacy mode, no lease check; a missing entry or an
      expired expiry blocks the claim),
    * no pending outbox entry for the item (optional --outbox JSON list of
      {subject, status}; pending -> the item cannot claim passes).

Usage: python3 backlog_check.py [project-root] [--leases PATH] [--outbox PATH]
       [--control-db PATH]
Exit 0 = clean (or no backlog.json — the check is inert outside C8).
Exit 1 = violations, named on stdout.
"""
import argparse
import json
import pathlib
import re
import sqlite3
import sys
import time

REQUIRED = ("id", "title", "priority", "passes")
# W25 transactional claim marker (Consistency Hub id grammar: uuid4-hex ids;
# lease epochs start at 1 — epoch=0 is malformed and must never license a pass)
CLAIM_RE = re.compile(
    r"^\s*-\s*claim:\s*task=(?P<task>[A-Za-z0-9._-]{1,64})"
    r"\s+run=(?P<run>run-[0-9a-f]{32})"
    r"\s+attempt=(?P<attempt>attempt-[0-9a-f]{32})"
    r"\s+epoch=(?P<epoch>[1-9]\d*)\s*$")


def _claim_markers(text):
    out = []
    for line in text.splitlines():
        m = CLAIM_RE.match(line)
        if m:
            out.append(m.groupdict())
    return out


def _load_json_map(path, what):
    """Return (value, error) — a missing file is legacy mode (None, None)."""
    p = pathlib.Path(path)
    if not p.is_file():
        return None, None
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as e:
        return None, f"FAIL {path}: unreadable {what} JSON — {e}"


def _load_run_control():
    """Defensive sibling import of scripts/run_control.py (the control plane
    owning the attempts/leases schema). Absence never crashes the gate — the
    claim probe below degrades to read-only SQL over the same schema."""
    here = pathlib.Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import run_control  # noqa: F401 — sibling control-plane module
        return run_control
    except Exception:  # noqa: BLE001 — fail-soft import, fail-closed checks
        return None


def _control_plane_claim_reasons(db_path, claim):
    """Named failure reasons when a claim marker does not correspond to a
    REAL run_control attempt (the `attempts`/`leases` tables): the attempt
    must exist, carry the marker's task, and record lease_epoch >= the
    marker's epoch (a claim cannot assert an epoch the plane never granted)."""
    if not pathlib.Path(db_path).is_file():
        return [f"control db {db_path} missing/unreadable — cannot verify the "
                f"claim (fail-closed)"]
    try:
        con = sqlite3.connect(str(db_path))
        try:
            row = con.execute(
                "SELECT task_id, lease_epoch FROM attempts WHERE attempt_id=?",
                (claim["attempt"],)).fetchone()
        finally:
            con.close()
    except sqlite3.Error as e:
        return [f"control db {db_path} unreadable ({e}) — cannot verify the "
                f"claim (fail-closed)"]
    if row is None:
        return [f"claim attempt not registered in control plane (attempt="
                f"{claim['attempt']} has no attempts row in {db_path})"]
    if row[0] != claim["task"]:
        return [f"claim attempt not registered in control plane (attempt="
                f"{claim['attempt']} is registered for task {row[0]!r}; the "
                f"marker claims task {claim['task']!r})"]
    if int(row[1]) < int(claim["epoch"]):
        return [f"claim epoch below lease epoch (marker epoch={claim['epoch']} "
                f"exceeds the recorded lease_epoch={row[1]} for attempt="
                f"{claim['attempt']} — a claim cannot assert an epoch the "
                f"control plane never granted)"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="C8 outer-loop ledger gate")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: cwd)")
    ap.add_argument("--leases", default="",
                    help="JSON mapping attempt_id -> lease expiry epoch seconds "
                         "(absent file = legacy mode: no lease check)")
    ap.add_argument("--outbox", default="",
                    help="JSON list of {subject, status} outbox records "
                         "(pending entries block passes:true)")
    ap.add_argument("--control-db", default="",
                    help="W25: run_control.py control-plane SQLite DB — when "
                         "given, every claim marker must correspond to a REAL "
                         "registered attempt (task matches, recorded "
                         "lease_epoch >= marker epoch); legacy text-pattern "
                         "mode stays when absent")
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    backlog = root / "tests" / "backlog.json"
    if not backlog.is_file():
        print("backlog_check.py: no tests/backlog.json — inert (exit 0)")
        return 0

    fails = []
    try:
        data = json.loads(backlog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL tests/backlog.json: not valid JSON — {e}")
        return 1

    if not isinstance(data, dict):
        print("FAIL tests/backlog.json: top-level value must be an object with `userStories`")
        return 1

    items = data.get("userStories")
    if not isinstance(items, list):
        print("FAIL tests/backlog.json: top-level `userStories` list missing")
        return 1

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            fails.append(f"userStories[{i}]: not an object")
            continue
        for key in REQUIRED:
            if key not in item:
                fails.append(f"userStories[{i}] ({item.get('id', '?')}): missing required key `{key}`")
        if "passes" in item and not isinstance(item["passes"], bool):
            fails.append(f"userStories[{i}] ({item.get('id', '?')}): `passes` must be a boolean")

    # --- W25 lease / outbox inputs (absent file = legacy mode) -------------
    leases, err = _load_json_map(args.leases, "lease") if args.leases else (None, None)
    if err:
        print(err)
        return 1
    if leases is not None and not isinstance(leases, dict):
        print(f"FAIL {args.leases}: lease JSON must map attempt_id -> expiry epoch seconds")
        return 1
    outbox, err = _load_json_map(args.outbox, "outbox") if args.outbox else (None, None)
    if err:
        print(err)
        return 1
    if outbox is not None and not isinstance(outbox, list):
        print(f"FAIL {args.outbox}: outbox JSON must be a list of {{subject, status}} records")
        return 1

    # claim markers: tests/verification_log.md lines + per-item `claims` lists
    vlog = root / "tests" / "verification_log.md"
    log_markers = _claim_markers(
        vlog.read_text(encoding="utf-8", errors="replace") if vlog.is_file() else "")

    passed_ids = [str(it.get("id")) for it in items if isinstance(it, dict) and it.get("passes") is True and it.get("id")]
    if passed_ids:
        evidence = ""
        for name in ("verification_log.md", "progress.txt"):
            p = root / "tests" / name
            if p.is_file():
                evidence += p.read_text(encoding="utf-8", errors="replace") + "\n"
        # C3e (P1, 2026-10-15): a mere ID mention is NOT evidence — the
        # line must carry EXECUTION proof: a command marker AND its exit 0
        # ("- TODO: US-3 not started" must never mark US-3 done).
        exec_ok = re.compile(r"(?:exit(?:\s*code)?|rc)\s*[:=]?\s*0\b|(?:→|->)\s*0\b", re.I)
        cmd_mark = re.compile(r"(?:\$\s|command\s*[:=]|cmd\s*[:=]|\bran\b|\bexecuted\b|\brun\b)", re.I)
        for item in items:
            if not (isinstance(item, dict) and item.get("passes") is True and item.get("id")):
                continue
            pid = str(item.get("id"))
            hit = False
            for line in evidence.splitlines():
                if not re.search(rf"^\s*-.*\b{re.escape(pid)}\b", line, re.M):
                    continue
                if exec_ok.search(line) and cmd_mark.search(line):
                    hit = True
                    break
            # W25: transactional claim markers bound to THIS item's id also
            # license passes:true — with their own lease/outbox conditions.
            markers = [m for m in log_markers if m["task"] == pid]
            for claim in item.get("claims") or []:
                if not isinstance(claim, str):
                    continue
                text = claim.strip()
                if not text.startswith("-"):
                    text = "- " + text
                m = CLAIM_RE.match(text)
                if m and m.group("task") == pid:
                    markers.append(m.groupdict())
            if not hit and not markers:
                fails.append(
                    f"{pid}: passes:true but no line in tests/verification_log.md or "
                    f"tests/progress.txt carries EXECUTION evidence for it (a command "
                    f"marker AND its exit 0) — a mention or TODO is not a test run "
                    f"(C3e / COV-1)")
                continue
            for m in markers:
                if args.control_db:
                    # H10: a claim marker must bind to REAL control-plane
                    # state — a fabricated claim (unknown attempt, foreign
                    # task, or an epoch the plane never granted) fails the
                    # item with a named reason. run_control is imported
                    # defensively (sys.path sibling) before the probe.
                    _load_run_control()
                    for reason in _control_plane_claim_reasons(args.control_db, m):
                        fails.append(f"{pid}: {reason}")
                if leases is not None:
                    exp = leases.get(m["attempt"])
                    if exp is None:
                        fails.append(
                            f"{pid}: claim marker attempt={m['attempt']} has no lease record in "
                            f"{args.leases} — a transactional claim needs a live lease "
                            f"(missing entry = lease not established)")
                    else:
                        try:
                            exp_f = float(exp)
                        except (TypeError, ValueError):
                            fails.append(
                                f"{pid}: claim marker attempt={m['attempt']} lease expiry is not "
                                f"epoch seconds ({exp!r}) — repair {args.leases} (fail-closed)")
                            continue
                        if time.time() >= exp_f:
                            fails.append(
                                f"{pid}: claim marker attempt={m['attempt']} lease expired at "
                                f"{int(exp_f)} (epoch {m['epoch']}) — an expired lease cannot "
                                f"claim passes (expiry is not stop, §MA4; create a new attempt)")
                if outbox is not None:
                    pending = [e for e in outbox
                               if isinstance(e, dict)
                               and str(e.get("subject")) == pid
                               and str(e.get("status", "")).lower() == "pending"]
                    if pending:
                        fails.append(
                            f"{pid}: {len(pending)} pending outbox entr"
                            f"{'y' if len(pending) == 1 else 'ies'} for this item — publication "
                            f"incomplete; passes:true cannot be claimed until the outbox is "
                            f"reconciled (§MA7 transactional outbox)")

    if fails:
        print(f"backlog_check.py: {len(fails)} violation(s):")
        for f in fails:
            print("  FAIL " + f)
        return 1
    done = sum(1 for it in items if isinstance(it, dict) and it.get("passes") is True)
    print(f"backlog_check.py: clean — {done}/{len(items)} items passing, all evidence-bound (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
