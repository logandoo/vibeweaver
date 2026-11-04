#!/usr/bin/env python3
"""run_control.py — single-host SQLite control plane for multi-agent runs (W25 Task 2).

Reference implementation of the MULTI_AGENT.md §MA1/§MA4 contracts:
RunContext identity, atomic claim, lease + epoch fencing, CAS state
transitions, fenced latches, an idempotent outbox, an append-only event log,
a single fenced queue leader, and the seven cleanup preconditions
(`can_clean`, MULTI_AGENT.md §MA4).

Storage rules (fail-closed):
  * SQLite (stdlib) with WAL mode, PRAGMA synchronous=FULL, and every write
    inside a BEGIN IMMEDIATE transaction.
  * Every shared write is fenced by (attempt_id, lease_epoch). A stale epoch
    is rejected with StaleEpochError — the ONLY stale-epoch rejection point.
    Expiry alone is never sufficient for takeover or cleanup: the old attempt
    must be explicitly expire()d AND isolate()d first (§MA2 "expiry is not
    stop").
  * `<state_root>/run_context.json` is written atomically (unique tmp +
    fsync + rename); a persistence failure aborts the claim transaction —
    it never succeeds silently.

Usage: python3 scripts/run_control.py init|claim|status|reconcile --db PATH [args]
All CLI results are JSON on stdout; errors are {"ok": false, "error": ...}.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

SCHEMA_ID = "vibeweaver-run-context/1"
SCHEMA_VERSION = 1
LEASE_TTL_SECONDS = 1800

RUN_ID_RE = re.compile(r"^run-[0-9a-f]{32}$")
ATTEMPT_ID_RE = re.compile(r"^attempt-[0-9a-f]{32}$")
WAVE_ID_RE = re.compile(r"^wave-[0-9a-f]{32}$")
TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

MAIN_STATES = ["pending", "leased", "running", "verifying", "ready",
               "integrating", "merged", "published", "cleaned"]
BYPASS_STATES = ["paused", "blocked", "expired", "quarantined", "stopping", "aborted"]
ALL_STATES = MAIN_STATES + BYPASS_STATES

# Work that is finished (or dead) — never blocked on, never force-expired.
TERMINAL_STATES = {"merged", "published", "cleaned", "aborted"}

# VALID_TRANSITIONS: the main path in order, plus paused<->running,
# running->blocked, blocked->running, any->expired (used by expire()),
# any->quarantined, running->stopping->aborted. Defined explicitly here.
VALID_TRANSITIONS: dict = {}
for _a, _b in zip(MAIN_STATES, MAIN_STATES[1:]):
    VALID_TRANSITIONS.setdefault(_a, set()).add(_b)
for _a, _b in (("running", "paused"), ("paused", "running"),
               ("running", "blocked"), ("blocked", "running"),
               ("running", "stopping"), ("stopping", "aborted")):
    VALID_TRANSITIONS.setdefault(_a, set()).add(_b)
for _s in ALL_STATES:
    VALID_TRANSITIONS.setdefault(_s, set()).update({"expired", "quarantined"})


class StaleEpochError(RuntimeError):
    """A write carrying a stale lease_epoch — rejected at the storage side."""


class ContextValidationError(ValueError):
    """A RunContext payload is forged or malformed (bad schema/fields/ids)."""


class InvalidTransition(ValueError):
    """State transition not present in VALID_TRANSITIONS."""


class LeaseConflict(RuntimeError):
    """The task lease is held (or the takeover preconditions are not met)."""


@dataclass
class RunContext:
    """Run identity handed to every participant of one attempt (Hub §MA1)."""

    repo_id: str
    task_id: str
    run_id: str
    attempt_id: str
    wave_id: str
    session_id: str
    lease_epoch: int
    worktree_root: str
    artifact_root: str
    state_root: str
    base_sha: str
    spec_hash: str
    skill_version: str
    checker_digest: str

    def to_json(self) -> str:
        body = asdict(self)
        body["schema"] = SCHEMA_ID
        return json.dumps(body, sort_keys=True)

    @classmethod
    def from_json(cls, src) -> "RunContext":
        """Parse + validate a RunContext; raise ContextValidationError on any forgery."""
        if isinstance(src, str):
            try:
                obj = json.loads(src)
            except json.JSONDecodeError as e:
                raise ContextValidationError(f"not valid JSON: {e}")
        elif isinstance(src, dict):
            obj = src
        else:
            raise ContextValidationError(f"unsupported source type {type(src).__name__}")
        if not isinstance(obj, dict):
            raise ContextValidationError("RunContext payload must be a JSON object")
        if obj.get("schema") != SCHEMA_ID:
            raise ContextValidationError(
                f"schema id mismatch: expected {SCHEMA_ID!r}, got {obj.get('schema')!r}")
        names = [f for f in cls.__dataclass_fields__]
        missing = [n for n in names if n not in obj]
        if missing:
            raise ContextValidationError(f"missing field(s): {', '.join(missing)}")
        for n in names:
            if n == "lease_epoch":
                continue
            if not isinstance(obj[n], str):
                raise ContextValidationError(f"field {n} must be a str")
        epoch = obj["lease_epoch"]
        if type(epoch) is not int or epoch < 1:
            raise ContextValidationError("lease_epoch must be an int >= 1")
        for n, rx in (("run_id", RUN_ID_RE), ("attempt_id", ATTEMPT_ID_RE),
                      ("wave_id", WAVE_ID_RE)):
            if rx.match(obj[n]) is None:
                raise ContextValidationError(f"field {n} has bad id format: {obj[n]!r}")
        if TASK_ID_RE.match(obj["task_id"]) is None:
            raise ContextValidationError(f"field task_id has bad format: {obj['task_id']!r}")
        return cls(**{n: obj[n] for n in names})


def _atomic_write_json(path: Path, obj) -> None:
    """Unique tmp + fsync + rename. Raises on failure — never silent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{os.getpid()}.{time.time_ns()}.{uuid.uuid4().hex[:8]}.tmp"
    data = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    # Best-effort directory fsync so the rename itself is durable; the file
    # content (fsync) and the rename have already failed closed above.
    try:
        fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


class ControlPlane:
    """SQLite-backed control plane. All writes: BEGIN IMMEDIATE + epoch fence."""

    def __init__(self, db_path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._init_schema()

    # -- infrastructure ----------------------------------------------------

    def _init_schema(self) -> None:
        c = self._conn
        c.execute("CREATE TABLE IF NOT EXISTS schema_meta ("
                  " key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS runs ("
                  " run_id TEXT PRIMARY KEY, task_id TEXT NOT NULL,"
                  " repo_id TEXT NOT NULL, wave_id TEXT NOT NULL,"
                  " state TEXT NOT NULL DEFAULT 'pending', final_ref TEXT,"
                  " created REAL NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS attempts ("
                  " attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,"
                  " task_id TEXT NOT NULL, repo_id TEXT NOT NULL,"
                  " session_id TEXT NOT NULL, lease_epoch INTEGER NOT NULL,"
                  " worktree_root TEXT NOT NULL, artifact_root TEXT NOT NULL,"
                  " state_root TEXT NOT NULL, base_sha TEXT NOT NULL,"
                  " spec_hash TEXT NOT NULL, skill_version TEXT NOT NULL,"
                  " checker_digest TEXT NOT NULL,"
                  " state TEXT NOT NULL DEFAULT 'pending',"
                  " lease_expired INTEGER NOT NULL DEFAULT 0,"
                  " isolated INTEGER NOT NULL DEFAULT 0,"
                  " handed_off INTEGER NOT NULL DEFAULT 0,"
                  " evidence_archived INTEGER NOT NULL DEFAULT 0,"
                  " untracked_included INTEGER NOT NULL DEFAULT 0,"
                  " effects_reconciled INTEGER NOT NULL DEFAULT 0,"
                  " retention_satisfied INTEGER NOT NULL DEFAULT 0,"
                  " open_children INTEGER NOT NULL DEFAULT 0,"
                  " created REAL NOT NULL)")
        c.execute("CREATE INDEX IF NOT EXISTS attempts_task_epoch"
                  " ON attempts(task_id, lease_epoch)")
        c.execute("CREATE TABLE IF NOT EXISTS leases ("
                  " task_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL,"
                  " lease_epoch INTEGER NOT NULL, expires_at REAL NOT NULL,"
                  " expired INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS session_runs ("
                  " session_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,"
                  " attempt_id TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS latches ("
                  " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                  " attempt_id TEXT NOT NULL, lease_epoch INTEGER NOT NULL,"
                  " run_id TEXT NOT NULL, session_id TEXT NOT NULL,"
                  " key TEXT NOT NULL, bad_json TEXT NOT NULL,"
                  " ts REAL NOT NULL, released INTEGER NOT NULL DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS outbox ("
                  " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                  " record_type TEXT NOT NULL, payload_json TEXT NOT NULL,"
                  " idempotency_key TEXT NOT NULL UNIQUE,"
                  " status TEXT NOT NULL DEFAULT 'pending',"
                  " created REAL NOT NULL, done_ts REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS events ("
                  " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                  " attempt_id TEXT NOT NULL, lease_epoch INTEGER NOT NULL,"
                  " kind TEXT NOT NULL, detail TEXT NOT NULL, ts REAL NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS queue_leaders ("
                  " name TEXT PRIMARY KEY, attempt_id TEXT NOT NULL,"
                  " lease_epoch INTEGER NOT NULL, acquired_ts REAL NOT NULL)")
        c.execute("INSERT OR IGNORE INTO schema_meta(key, value) VALUES (?, ?)",
                  ("schema_version", str(SCHEMA_VERSION)))

    def _write(self, fn):
        """Run fn(cur) inside BEGIN IMMEDIATE; commit or roll back."""
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            out = fn(cur)
        except BaseException:
            self._conn.rollback()
            raise
        self._conn.commit()
        return out

    def _assert_epoch(self, cur, attempt_id, lease_epoch) -> None:
        """Storage-side fence: reject writes from stale epochs (or unknown attempts)."""
        row = cur.execute("SELECT task_id, lease_epoch FROM attempts WHERE attempt_id=?",
                          (attempt_id,)).fetchone()
        if row is None:
            raise StaleEpochError(f"unknown attempt {attempt_id}")
        if row["lease_epoch"] != lease_epoch:
            raise StaleEpochError(
                f"attempt {attempt_id} carries epoch {row['lease_epoch']}, "
                f"write carries {lease_epoch}")
        mx = cur.execute("SELECT MAX(lease_epoch) AS m FROM attempts WHERE task_id=?",
                         (row["task_id"],)).fetchone()["m"]
        if mx is not None and lease_epoch < mx:
            raise StaleEpochError(
                f"stale epoch {lease_epoch} for task {row['task_id']} (current {mx})")

    def _fence(self, cur, attempt_id, lease_epoch) -> None:
        """Optional write fence for the shared-write entry points: when both
        attempt_id and lease_epoch are supplied, run _assert_epoch first (a
        stale epoch raises StaleEpochError). Supplying only one of the pair is
        a fencing mistake and fails closed."""
        if (attempt_id is None) != (lease_epoch is None):
            raise ValueError(
                "attempt_id and lease_epoch must be supplied together (fenced write)")
        if attempt_id is not None:
            self._assert_epoch(cur, attempt_id, lease_epoch)

    def _attempt_row(self, cur, attempt_id):
        row = cur.execute("SELECT * FROM attempts WHERE attempt_id=?",
                          (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown attempt {attempt_id}")
        return row

    def _next_epoch(self, cur, task_id) -> int:
        mx = cur.execute("SELECT MAX(lease_epoch) AS m FROM attempts WHERE task_id=?",
                         (task_id,)).fetchone()["m"]
        return (mx or 0) + 1

    def _refresh_run_state(self, cur, run_id) -> None:
        row = cur.execute("SELECT state FROM attempts WHERE run_id=?"
                          " ORDER BY lease_epoch DESC LIMIT 1", (run_id,)).fetchone()
        if row is not None:
            cur.execute("UPDATE runs SET state=? WHERE run_id=?", (row["state"], run_id))

    def _new_run(self, cur, task_id, repo_id, now) -> tuple:
        run_id = "run-" + uuid.uuid4().hex
        wave_id = "wave-" + uuid.uuid4().hex
        cur.execute("INSERT INTO runs(run_id, task_id, repo_id, wave_id, state, created)"
                    " VALUES (?,?,?,?,?,?)",
                    (run_id, task_id, repo_id, wave_id, "pending", now))
        return run_id, wave_id

    def _insert_attempt(self, cur, ctx, now) -> None:
        cur.execute(
            "INSERT INTO attempts(attempt_id, run_id, task_id, repo_id, session_id,"
            " lease_epoch, worktree_root, artifact_root, state_root, base_sha,"
            " spec_hash, skill_version, checker_digest, state, created)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ctx.attempt_id, ctx.run_id, ctx.task_id, ctx.repo_id, ctx.session_id,
             ctx.lease_epoch, ctx.worktree_root, ctx.artifact_root, ctx.state_root,
             ctx.base_sha, ctx.spec_hash, ctx.skill_version, ctx.checker_digest,
             "pending", now))

    def _upsert_lease(self, cur, task_id, attempt_id, lease_epoch, now) -> None:
        cur.execute("INSERT INTO leases(task_id, attempt_id, lease_epoch, expires_at,"
                    " expired, updated) VALUES (?,?,?,?,0,?)"
                    " ON CONFLICT(task_id) DO UPDATE SET"
                    " attempt_id=excluded.attempt_id, lease_epoch=excluded.lease_epoch,"
                    " expires_at=excluded.expires_at, expired=0, updated=excluded.updated",
                    (task_id, attempt_id, lease_epoch,
                     now + LEASE_TTL_SECONDS, now))

    def _event(self, cur, attempt_id, lease_epoch, kind, detail, now) -> int:
        cur.execute("INSERT INTO events(attempt_id, lease_epoch, kind, detail, ts)"
                    " VALUES (?,?,?,?,?)", (attempt_id, lease_epoch, kind, detail, now))
        return cur.lastrowid

    def _supersede(self, cur, task_id, now) -> None:
        """Force-expire every non-terminal prior attempt of the task (takeover step)."""
        cur.execute(
            "UPDATE attempts SET lease_expired=1 WHERE task_id=? AND state NOT IN"
            " ('merged','published','cleaned','aborted')", (task_id,))
        cur.execute(
            "UPDATE attempts SET state='expired' WHERE task_id=? AND state NOT IN"
            " ('merged','published','cleaned','aborted')", (task_id,))
        cur.execute("UPDATE leases SET expired=1, updated=? WHERE task_id=?", (now, task_id))

    def _lease_active(self, cur, task_id, now):
        row = cur.execute("SELECT * FROM leases WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            return None
        if row["expired"] == 0 and row["expires_at"] > now:
            return row
        return row

    # -- claim / takeover / lease ------------------------------------------

    def claim(self, task_id, repo_id, session_id, worktree_root, artifact_root,
              state_root, base_sha, spec_hash, skill_version, checker_digest,
              *, takeover=False) -> RunContext:
        """Atomic claim of a task. lease_epoch = previous max epoch + 1 (starts at 1).

        Raises LeaseConflict when the task has an unexpired active lease and
        takeover=False. With takeover=True the SAME §MA4 precondition as
        takeover() applies: every non-terminal prior attempt must already be
        expire()d AND isolate()d — a LIVE lease is never force-superseded
        (expiry is not stop); otherwise LeaseConflict. Met preconditions are
        then superseded (same order as takeover(): supersede BEFORE insert).
        """
        if TASK_ID_RE.match(task_id) is None:
            raise ContextValidationError(f"bad task_id format: {task_id!r}")

        def _tx(cur):
            now = time.time()
            if takeover:
                priors = cur.execute(
                    "SELECT attempt_id, lease_expired, isolated FROM attempts"
                    " WHERE task_id=? AND state NOT IN"
                    " ('merged','published','cleaned','aborted')"
                    " ORDER BY lease_epoch", (task_id,)).fetchall()
                for p in priors:
                    if p["lease_expired"] != 1 or p["isolated"] != 1:
                        raise LeaseConflict(
                            f"claim(takeover=True) denied: attempt {p['attempt_id']}"
                            f" is not yet expire()d + isolate()d"
                            f" (lease_expired={p['lease_expired']},"
                            f" isolated={p['isolated']})")
                if priors:
                    self._supersede(cur, task_id, now)
            else:
                lease = self._lease_active(cur, task_id, now)
                if lease is not None and lease["expired"] == 0 and lease["expires_at"] > now:
                    raise LeaseConflict(
                        f"task {task_id} has an unexpired lease held by"
                        f" attempt {lease['attempt_id']} (epoch {lease['lease_epoch']})")
            epoch = self._next_epoch(cur, task_id)
            run_id, wave_id = self._new_run(cur, task_id, repo_id, now)
            ctx = RunContext(
                repo_id=repo_id, task_id=task_id, run_id=run_id,
                attempt_id="attempt-" + uuid.uuid4().hex, wave_id=wave_id,
                session_id=session_id, lease_epoch=epoch,
                worktree_root=worktree_root, artifact_root=artifact_root,
                state_root=state_root, base_sha=base_sha, spec_hash=spec_hash,
                skill_version=skill_version, checker_digest=checker_digest)
            self._insert_attempt(cur, ctx, now)
            self._upsert_lease(cur, task_id, ctx.attempt_id, epoch, now)
            self._event(cur, ctx.attempt_id, epoch,
                        "claim-takeover" if takeover else "claim",
                        f"task={task_id} run={run_id}", now)
            # Fail-closed persistence: a broken state_root aborts the claim.
            _atomic_write_json(Path(state_root) / "run_context.json",
                               json.loads(ctx.to_json()))
            return ctx

        return self._write(_tx)

    def takeover(self, task_id, repo_id, session_id, worktree_root, artifact_root,
                 state_root, base_sha, spec_hash, skill_version, checker_digest,
                 reason: str) -> RunContext:
        """Supersede an expired AND isolated attempt with a new attempt (higher epoch).

        Precondition per MULTI_AGENT.md §MA4: every non-terminal prior attempt
        must have been expire()d AND isolate()d — TTL alone is never enough.
        The old attempts are force-set to state 'expired'; the takeover writes
        an event. The run (run_id/wave_id) is reused; only the attempt is new.
        """
        if TASK_ID_RE.match(task_id) is None:
            raise ContextValidationError(f"bad task_id format: {task_id!r}")

        def _tx(cur):
            now = time.time()
            priors = cur.execute(
                "SELECT attempt_id, state, lease_expired, isolated FROM attempts"
                " WHERE task_id=? AND state NOT IN ('merged','published','cleaned','aborted')"
                " ORDER BY lease_epoch", (task_id,)).fetchall()
            for p in priors:
                if p["lease_expired"] != 1 or p["isolated"] != 1:
                    raise LeaseConflict(
                        f"takeover denied: attempt {p['attempt_id']} is not yet"
                        f" expire()d + isolate()d (lease_expired={p['lease_expired']},"
                        f" isolated={p['isolated']})")
            epoch = self._next_epoch(cur, task_id)
            run = cur.execute("SELECT run_id, wave_id FROM runs WHERE task_id=?"
                              " ORDER BY created DESC LIMIT 1", (task_id,)).fetchone()
            if run is None:
                run_id, wave_id = self._new_run(cur, task_id, repo_id, now)
            else:
                run_id, wave_id = run["run_id"], run["wave_id"]
            ctx = RunContext(
                repo_id=repo_id, task_id=task_id, run_id=run_id,
                attempt_id="attempt-" + uuid.uuid4().hex, wave_id=wave_id,
                session_id=session_id, lease_epoch=epoch,
                worktree_root=worktree_root, artifact_root=artifact_root,
                state_root=state_root, base_sha=base_sha, spec_hash=spec_hash,
                skill_version=skill_version, checker_digest=checker_digest)
            # Supersede the OLD attempts BEFORE inserting the fresh one (same
            # order claim() uses): _supersede force-expires every non-terminal
            # row of the task, so running it after the insert would mark the
            # brand-new attempt 'expired' and kill it before it ever started.
            self._supersede(cur, task_id, now)
            self._insert_attempt(cur, ctx, now)
            self._upsert_lease(cur, task_id, ctx.attempt_id, epoch, now)
            self._event(cur, ctx.attempt_id, epoch,
                        "takeover", f"reason={reason} new_attempt={ctx.attempt_id}", now)
            self._refresh_run_state(cur, run_id)
            _atomic_write_json(Path(state_root) / "run_context.json",
                               json.loads(ctx.to_json()))
            return ctx

        return self._write(_tx)

    def isolate(self, attempt_id) -> None:
        """Mark an attempt isolated (a can_clean + takeover precondition)."""
        def _tx(cur):
            self._attempt_row(cur, attempt_id)
            cur.execute("UPDATE attempts SET isolated=1 WHERE attempt_id=?", (attempt_id,))
        self._write(_tx)

    def expire(self, attempt_id) -> None:
        """Mark the lease expired (scheduling stops) and the attempt 'expired'."""
        def _tx(cur):
            row = self._attempt_row(cur, attempt_id)
            now = time.time()
            cur.execute("UPDATE attempts SET lease_expired=1, state='expired'"
                        " WHERE attempt_id=?", (attempt_id,))
            cur.execute("UPDATE leases SET expired=1, updated=? WHERE task_id=? AND attempt_id=?",
                        (now, row["task_id"], attempt_id))
            self._refresh_run_state(cur, row["run_id"])
        self._write(_tx)

    def heartbeat(self, attempt_id, lease_epoch) -> bool:
        """Renew the lease TTL. False only for an unknown attempt.

        A stale lease_epoch raises StaleEpochError. Heartbeat only extends the
        lease TTL timestamp; it never clears the `expired` flag, so a lease the
        supervisor explicitly expire()d does NOT come back to life — renewal
        never resurrects that decision.
        """
        def _tx(cur):
            row = cur.execute("SELECT task_id FROM attempts WHERE attempt_id=?",
                              (attempt_id,)).fetchone()
            if row is None:
                return False
            self._assert_epoch(cur, attempt_id, lease_epoch)
            now = time.time()
            cur.execute("UPDATE leases SET expires_at=?, updated=? WHERE task_id=?",
                        (now + LEASE_TTL_SECONDS, now, row["task_id"]))
            return True
        return self._write(_tx)

    # -- state machine -----------------------------------------------------

    def transition(self, attempt_id, lease_epoch, to_state) -> str:
        """CAS state transition fenced by lease_epoch; returns the new state."""
        if to_state not in ALL_STATES:
            raise InvalidTransition(f"unknown state {to_state!r}")

        def _tx(cur):
            self._assert_epoch(cur, attempt_id, lease_epoch)
            row = self._attempt_row(cur, attempt_id)
            cur_state = row["state"]
            if to_state not in VALID_TRANSITIONS.get(cur_state, set()):
                raise InvalidTransition(
                    f"{cur_state} -> {to_state} is not a valid transition")
            cur.execute("UPDATE attempts SET state=? WHERE attempt_id=?",
                        (to_state, attempt_id))
            self._refresh_run_state(cur, row["run_id"])
            return to_state
        return self._write(_tx)

    def state(self, attempt_id) -> str:
        cur = self._conn.cursor()
        row = cur.execute("SELECT state FROM attempts WHERE attempt_id=?",
                          (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown attempt {attempt_id}")
        return row["state"]

    # -- session mapping ---------------------------------------------------

    def set_session_run(self, session_id, run_id, attempt_id, *, lease_epoch=None) -> None:
        """Map session -> run/attempt. Pass lease_epoch to fence the write with
        the row's attempt_id (stale epoch -> StaleEpochError)."""
        def _tx(cur):
            if lease_epoch is not None:
                self._assert_epoch(cur, attempt_id, lease_epoch)
            cur.execute("INSERT INTO session_runs(session_id, run_id, attempt_id)"
                        " VALUES (?,?,?)"
                        " ON CONFLICT(session_id) DO UPDATE SET"
                        " run_id=excluded.run_id, attempt_id=excluded.attempt_id",
                        (session_id, run_id, attempt_id))
        self._write(_tx)

    def session_run(self, session_id):
        cur = self._conn.cursor()
        row = cur.execute("SELECT run_id, attempt_id FROM session_runs WHERE session_id=?",
                          (session_id,)).fetchone()
        return (row["run_id"], row["attempt_id"]) if row is not None else None

    # -- latches -----------------------------------------------------------

    def latch_set(self, attempt_id, lease_epoch, key, bad: dict) -> None:
        def _tx(cur):
            self._assert_epoch(cur, attempt_id, lease_epoch)
            row = self._attempt_row(cur, attempt_id)
            cur.execute("INSERT INTO latches(attempt_id, lease_epoch, run_id,"
                        " session_id, key, bad_json, ts) VALUES (?,?,?,?,?,?,?)",
                        (attempt_id, lease_epoch, row["run_id"], row["session_id"],
                         key, json.dumps(bad, sort_keys=True), time.time()))
        self._write(_tx)

    def latch_get(self, run_id):
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM latches WHERE run_id=? AND released=0"
                          " ORDER BY ts DESC, id DESC LIMIT 1", (run_id,)).fetchone()
        if row is None:
            return None
        return {"sessionID": row["session_id"], "runID": row["run_id"],
                "attemptID": row["attempt_id"], "ts": row["ts"],
                "bad": json.loads(row["bad_json"])}

    def latch_release(self, attempt_id, lease_epoch, key) -> bool:
        """Release a latch. Only the owning attempt+epoch — or a NEWER epoch of
        the same task — may release; another task's attempt gets False."""
        def _tx(cur):
            latch = cur.execute("SELECT * FROM latches WHERE key=? AND released=0"
                                " ORDER BY ts DESC, id DESC LIMIT 1", (key,)).fetchone()
            if latch is None:
                return False
            self._assert_epoch(cur, attempt_id, lease_epoch)
            caller = self._attempt_row(cur, attempt_id)
            if latch["attempt_id"] == attempt_id and latch["lease_epoch"] == lease_epoch:
                cur.execute("UPDATE latches SET released=1 WHERE id=?", (latch["id"],))
                return True
            owner = cur.execute("SELECT task_id FROM attempts WHERE attempt_id=?",
                                (latch["attempt_id"],)).fetchone()
            if (owner is not None and owner["task_id"] == caller["task_id"]
                    and lease_epoch > latch["lease_epoch"]):
                cur.execute("UPDATE latches SET released=1 WHERE id=?", (latch["id"],))
                return True
            return False
        return self._write(_tx)

    # -- outbox ------------------------------------------------------------

    def outbox_put(self, record_type, payload: dict, idempotency_key,
                   *, attempt_id=None, lease_epoch=None) -> int:
        """Insert an outbox record; a duplicate idempotency_key returns the
        existing row id without inserting (Hub: <type>:<subject>:<intent>).
        Optional (attempt_id, lease_epoch) fence the write (stale epoch ->
        StaleEpochError); unfenced calls stay backward compatible."""
        def _tx(cur):
            self._fence(cur, attempt_id, lease_epoch)
            row = cur.execute("SELECT id FROM outbox WHERE idempotency_key=?",
                              (idempotency_key,)).fetchone()
            if row is not None:
                return row["id"]
            cur.execute("INSERT INTO outbox(record_type, payload_json, idempotency_key,"
                        " status, created) VALUES (?,?,?,?,?)",
                        (record_type, json.dumps(payload, sort_keys=True),
                         idempotency_key, "pending", time.time()))
            return cur.lastrowid
        return self._write(_tx)

    def outbox_pending(self) -> list:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM outbox WHERE status='pending' ORDER BY id").fetchall()
        return [{"id": r["id"], "record_type": r["record_type"],
                 "payload": json.loads(r["payload_json"]),
                 "idempotency_key": r["idempotency_key"], "status": r["status"]}
                for r in rows]

    def outbox_mark_done(self, item_id, *, attempt_id=None, lease_epoch=None) -> None:
        """Mark an outbox record published. Optional (attempt_id, lease_epoch)
        fence the write (stale epoch -> StaleEpochError)."""
        def _tx(cur):
            self._fence(cur, attempt_id, lease_epoch)
            cur.execute("UPDATE outbox SET status='done', done_ts=? WHERE id=?",
                        (time.time(), item_id))
        self._write(_tx)

    # -- reconcile ---------------------------------------------------------

    def reconcile(self, git_refs: dict = None) -> list:
        """Return discrepancy records {"kind", "detail"}:
        'outbox-pending'      — merged/published runs whose outbox entries pend;
        'ref-mismatch'        — runs whose recorded final ref != git_refs[run_id];
        'expired-not-isolated'— attempts marked expired but never isolated.
        """
        cur = self._conn.cursor()
        now = time.time()
        recs = []
        done_runs = cur.execute("SELECT run_id, state FROM runs"
                                " WHERE state IN ('merged','published')").fetchall()
        for run in done_runs:
            pend = cur.execute("SELECT id, idempotency_key FROM outbox"
                               " WHERE status='pending'").fetchall()
            hits = [p for p in pend
                    if json.loads(cur.execute(
                        "SELECT payload_json FROM outbox WHERE id=?", (p["id"],)
                    ).fetchone()["payload_json"]).get("run_id") == run["run_id"]]
            if hits:
                keys = ", ".join(p["idempotency_key"] for p in hits)
                recs.append({"kind": "outbox-pending",
                             "detail": f"run {run['run_id']} state={run['state']}"
                                       f" still has pending outbox: {keys}"})
        if git_refs:
            for run_id, sha in git_refs.items():
                run = cur.execute("SELECT run_id, final_ref FROM runs WHERE run_id=?",
                                  (run_id,)).fetchone()
                if run is None:
                    continue
                if run["final_ref"] != sha:
                    recs.append({"kind": "ref-mismatch",
                                 "detail": f"run {run_id} recorded final ref"
                                           f" {run['final_ref']!r} != git {sha!r}"})
        stale = cur.execute("SELECT attempt_id, state FROM attempts"
                            " WHERE (lease_expired=1 OR state='expired') AND isolated=0"
                            " ORDER BY created").fetchall()
        for a in stale:
            recs.append({"kind": "expired-not-isolated",
                         "detail": f"attempt {a['attempt_id']} state={a['state']}"
                                   f" is marked expired but not isolated"})
        _ = now
        return recs

    def record_final_ref(self, run_id, sha, *, attempt_id=None, lease_epoch=None) -> None:
        """Record the final ref/sha a run published (consumed by reconcile).
        Optional (attempt_id, lease_epoch) fence the write (stale epoch ->
        StaleEpochError)."""
        def _tx(cur):
            self._fence(cur, attempt_id, lease_epoch)
            row = cur.execute("SELECT run_id FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(f"unknown run {run_id}")
            cur.execute("UPDATE runs SET final_ref=? WHERE run_id=?", (sha, run_id))
        self._write(_tx)

    # -- events / leadership -----------------------------------------------

    def event(self, attempt_id, lease_epoch, kind, detail) -> int:
        """Append-only event; fenced (a stale epoch raises StaleEpochError)."""
        def _tx(cur):
            self._assert_epoch(cur, attempt_id, lease_epoch)
            return self._event(cur, attempt_id, lease_epoch, kind, detail, time.time())
        return self._write(_tx)

    def _leader_holder_live(self, cur, row) -> bool:
        att = cur.execute("SELECT task_id, lease_epoch FROM attempts WHERE attempt_id=?",
                          (row["attempt_id"],)).fetchone()
        if att is None or att["lease_epoch"] != row["lease_epoch"]:
            return False
        mx = cur.execute("SELECT MAX(lease_epoch) AS m FROM attempts WHERE task_id=?",
                         (att["task_id"],)).fetchone()["m"]
        if mx != row["lease_epoch"]:
            return False
        lease = cur.execute("SELECT expires_at, expired FROM leases WHERE task_id=?",
                            (att["task_id"],)).fetchone()
        return (lease is not None and lease["expired"] == 0
                and lease["expires_at"] > time.time())

    def acquire_leader(self, name, attempt_id, lease_epoch) -> bool:
        """Single fenced leader lease. A stale-epoch caller cannot acquire
        (StaleEpochError); acquiring from a live holder returns False."""
        def _tx(cur):
            self._assert_epoch(cur, attempt_id, lease_epoch)
            now = time.time()
            row = cur.execute("SELECT * FROM queue_leaders WHERE name=?", (name,)).fetchone()
            if row is None:
                cur.execute("INSERT INTO queue_leaders(name, attempt_id, lease_epoch,"
                            " acquired_ts) VALUES (?,?,?,?)",
                            (name, attempt_id, lease_epoch, now))
                return True
            if row["attempt_id"] == attempt_id and row["lease_epoch"] == lease_epoch:
                cur.execute("UPDATE queue_leaders SET acquired_ts=? WHERE name=?",
                            (now, name))
                return True
            if self._leader_holder_live(cur, row):
                return False
            cur.execute("UPDATE queue_leaders SET attempt_id=?, lease_epoch=?, acquired_ts=?"
                        " WHERE name=?", (attempt_id, lease_epoch, now, name))
            return True
        return self._write(_tx)

    # -- cleanup preconditions (MULTI_AGENT.md §MA4 — all seven) ------------

    def mark_handed_off(self, attempt_id, *, lease_epoch=None) -> None:
        self._flag(attempt_id, "handed_off", lease_epoch=lease_epoch)

    def mark_evidence_archived(self, attempt_id, *, lease_epoch=None) -> None:
        self._flag(attempt_id, "evidence_archived", lease_epoch=lease_epoch)

    def mark_untracked_included(self, attempt_id, *, lease_epoch=None) -> None:
        self._flag(attempt_id, "untracked_included", lease_epoch=lease_epoch)

    def mark_effects_reconciled(self, attempt_id, *, lease_epoch=None) -> None:
        self._flag(attempt_id, "effects_reconciled", lease_epoch=lease_epoch)

    def mark_retention_satisfied(self, attempt_id, *, lease_epoch=None) -> None:
        self._flag(attempt_id, "retention_satisfied", lease_epoch=lease_epoch)

    def _flag(self, attempt_id, column, *, lease_epoch=None) -> None:
        """Set a cleanup-precondition flag. Optional lease_epoch fences the
        write against the row's attempt_id (stale epoch -> StaleEpochError)."""
        def _tx(cur):
            if lease_epoch is not None:
                self._assert_epoch(cur, attempt_id, lease_epoch)
            self._attempt_row(cur, attempt_id)
            cur.execute(f"UPDATE attempts SET {column}=1 WHERE attempt_id=?",
                        (attempt_id,))
        self._write(_tx)

    def add_child(self, attempt_id, *, lease_epoch=None) -> int:
        """Register a supervised child process; returns the open-child count.
        Optional lease_epoch fences the write (stale epoch -> StaleEpochError)."""
        def _tx(cur):
            if lease_epoch is not None:
                self._assert_epoch(cur, attempt_id, lease_epoch)
            self._attempt_row(cur, attempt_id)
            cur.execute("UPDATE attempts SET open_children=open_children+1"
                        " WHERE attempt_id=?", (attempt_id,))
            return cur.execute("SELECT open_children AS n FROM attempts WHERE attempt_id=?",
                               (attempt_id,)).fetchone()["n"]
        return self._write(_tx)

    def finish_child(self, attempt_id, *, lease_epoch=None) -> int:
        """A supervised child exited; returns the open-child count (floored at 0).
        Optional lease_epoch fences the write (stale epoch -> StaleEpochError)."""
        def _tx(cur):
            if lease_epoch is not None:
                self._assert_epoch(cur, attempt_id, lease_epoch)
            self._attempt_row(cur, attempt_id)
            cur.execute("UPDATE attempts SET open_children=CASE WHEN open_children>0"
                        " THEN open_children-1 ELSE 0 END WHERE attempt_id=?",
                        (attempt_id,))
            return cur.execute("SELECT open_children AS n FROM attempts WHERE attempt_id=?",
                               (attempt_id,)).fetchone()["n"]
        return self._write(_tx)

    def can_clean(self, attempt_id):
        """All seven §MA4 cleanup preconditions. Returns (ok, missing-reasons)."""
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM attempts WHERE attempt_id=?",
                          (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown attempt {attempt_id}")
        reasons = []
        if row["handed_off"] != 1:
            reasons.append("code not handed off (mark_handed_off not set)")
        if row["evidence_archived"] != 1:
            reasons.append("evidence not archived / read back (mark_evidence_archived not set)")
        if row["untracked_included"] != 1:
            reasons.append("untracked evidence not included (mark_untracked_included not set)")
        if row["effects_reconciled"] != 1:
            reasons.append("external side effects not reconciled (mark_effects_reconciled not set)")
        if row["open_children"] > 0:
            reasons.append(f"{row['open_children']} open child process(es) (finish_child pending)")
        if row["isolated"] != 1:
            reasons.append("attempt not isolated (isolate not called)")
        if row["retention_satisfied"] != 1:
            reasons.append("retention/approval not satisfied (mark_retention_satisfied not set)")
        # §MA4: 'cleaned' is unreachable while publication is incomplete — a
        # pending outbox record for THIS run blocks cleanup until it is done.
        # Unattributable 'integration' rows (no run_id in the payload) also
        # block: an orphaned publication cannot be proven complete (fail-closed).
        pend = cur.execute("SELECT record_type, payload_json FROM outbox"
                           " WHERE status='pending'").fetchall()
        for p in pend:
            try:
                payload = json.loads(p["payload_json"])
            except ValueError:
                payload = {}
            if isinstance(payload, dict) and payload.get("run_id") == row["run_id"]:
                reasons.append("outbox publication incomplete")
                break
            if p["record_type"] == "integration" and not (isinstance(payload, dict) and payload.get("run_id")):
                reasons.append("outbox publication incomplete (unattributed integration record)")
                break
        return (not reasons, reasons)


# -- CLI --------------------------------------------------------------------

def _cli_claim(args) -> dict:
    cp = ControlPlane(args.db)
    ctx = cp.claim(args.task_id, args.repo_id, args.session_id, args.worktree_root,
                   args.artifact_root, args.state_root, args.base_sha, args.spec_hash,
                   args.skill_version, args.checker_digest, takeover=args.takeover)
    return {"ok": True, "run_context": json.loads(ctx.to_json())}


def _cli_status(args) -> dict:
    cp = ControlPlane(args.db)
    con = cp._conn
    where, params = "", ()
    if args.task_id:
        where, params = " WHERE task_id=?", (args.task_id,)
    runs = [dict(r) for r in con.execute("SELECT * FROM runs" + where, params).fetchall()]
    attempts = [dict(r) for r in con.execute(
        "SELECT attempt_id, run_id, task_id, session_id, lease_epoch, state,"
        " lease_expired, isolated, open_children, created FROM attempts"
        + where + " ORDER BY created", params).fetchall()]
    leases = [dict(r) for r in con.execute("SELECT * FROM leases" + where, params).fetchall()]
    return {"ok": True, "runs": runs, "attempts": attempts, "leases": leases}


def _cli_reconcile(args) -> dict:
    cp = ControlPlane(args.db)
    git_refs = None
    if args.git_refs:
        git_refs = json.loads(args.git_refs)
        if not isinstance(git_refs, dict):
            raise ValueError("--git-refs must be a JSON object {run_id: sha}")
    return {"ok": True, "discrepancies": cp.reconcile(git_refs)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_control.py", description="Multi-agent run control plane (W25).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create/upgrade the control-plane DB")
    p_init.add_argument("--db", required=True)

    p_claim = sub.add_parser("claim", help="atomically claim a task")
    p_claim.add_argument("--db", required=True)
    for name in ("task-id", "repo-id", "session-id", "worktree-root", "artifact-root",
                 "state-root", "base-sha", "spec-hash", "skill-version", "checker-digest"):
        p_claim.add_argument("--" + name, required=True)
    p_claim.add_argument("--takeover", action="store_true")

    p_status = sub.add_parser("status", help="dump runs/attempts/leases")
    p_status.add_argument("--db", required=True)
    p_status.add_argument("--task-id")

    p_rec = sub.add_parser("reconcile", help="report discrepancies")
    p_rec.add_argument("--db", required=True)
    p_rec.add_argument("--git-refs", help='JSON object {"run-id": "sha"}')

    args = parser.parse_args(argv)
    handlers = {"init": lambda a: {"ok": True, "db": str(a.db),
                                   "schema_version": SCHEMA_VERSION},
                "claim": _cli_claim, "status": _cli_status, "reconcile": _cli_reconcile}
    try:
        out = handlers[args.cmd](args)
    except BaseException as e:
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
