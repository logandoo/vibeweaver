#!/usr/bin/env python3
"""resource_allocator.py — per-attempt namespaced resource allocation (W25 Task 3).

Single-host reference implementation of the multi-agent resource boundary
(docs/PLAN_w25_multi_agent.md Task 3 / MULTI_AGENT.md §MA9): every resource a
running attempt consumes is centrally registered in a SQLite registry so that
concurrent attempts never collide and cleanup is auditable.

Registered kinds: port, procgroup, tempdir, db_name, browser_profile,
credential_ref, exclusive. The `allocations` row IS the reservation:
  * UNIQUE(attempt_id, kind, name) makes every allocate_* idempotent —
    a repeat call returns the existing value instead of double-allocating;
  * a partial UNIQUE index on (name) WHERE state='held' makes scarce
    singletons (kind='exclusive') globally single-holder: a second take
    raises ResourceConflict until the holder's reclaim releases it;
  * state machine per row: held -> reclaimed | quarantined. Quarantined
    rows are frozen for human review: reclaim refuses to touch them.

Ports come from the centrally reserved range 20000-40999 (lowest free port
that is not 'held' by any attempt and passes a real socket bind test —
never random). Procgroups spawn via subprocess.Popen(start_new_session=True)
and record the pgid leader's ps(1) start time so reclaim can refuse to kill
a PID that was recycled by an unrelated process ("skipped-pid-reuse").
Credential refs are opaque names only — no secret VALUE is ever accepted,
stored, or written anywhere.

Lease fencing: every allocate_* runs an epoch check first (the injected
`epoch_check` callable, or the built-in `leases` table which rejects any
epoch older than the newest recorded for that attempt with StaleEpochError).
All writes are transactional (BEGIN IMMEDIATE).
"""
import argparse
import hashlib
import json
import os
import re
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

try:  # sibling control-plane module (Task 2) owns the canonical exception
    from run_control import StaleEpochError
except Exception:  # noqa: BLE001 — defensive: run_control may not exist yet
    class StaleEpochError(RuntimeError):
        pass


class ResourceConflict(RuntimeError):
    pass


PORT_MIN = 20000
PORT_MAX = 40999
KILL_GRACE = 0.5  # seconds between SIGTERM and SIGKILL on reclaim

ATTEMPT_RE = re.compile(r"^attempt-([0-9a-f]{32})$")
NAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
# H7 (R17): secret-shaped names are refused — a credential VALUE has nowhere
# to go, and a token-shaped NAME is a credential leak by another route.
CRED_NAME_MAX = 64
_HEX_TOKEN_RE = re.compile(r"[0-9a-fA-F]{32,}")
_B64ISH_RE = re.compile(r"[A-Za-z0-9+/=]{20,}")
_ALNUM_RE = re.compile(r"[A-Za-z0-9]+")
_SEP_CHARS = "._-"


def _credential_name_is_secret_shaped(name) -> bool:
    """True when a credential-ref NAME looks like credential material:
    obvious key/token patterns (hex >= 32, base64ish >= 20) or a high-entropy
    token shape (length >= 20, NO separator chars (._-), mixed [A-Za-z0-9])."""
    if _HEX_TOKEN_RE.fullmatch(name):
        return True
    if _B64ISH_RE.fullmatch(name):
        return True
    return (len(name) >= 20 and not any(c in name for c in _SEP_CHARS)
            and _ALNUM_RE.fullmatch(name) is not None)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS allocations (
    attempt_id TEXT NOT NULL,
    lease_epoch INTEGER NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'held',
    created REAL NOT NULL,
    extra TEXT,
    UNIQUE(attempt_id, kind, name)
);
CREATE UNIQUE INDEX IF NOT EXISTS alloc_held_name
    ON allocations(name) WHERE state = 'held';
CREATE TABLE IF NOT EXISTS leases (
    attempt_id TEXT PRIMARY KEY,
    lease_epoch INTEGER NOT NULL
);
"""


def _ps_lstart(pid):
    """ps(1) start-time string for pid: None = cannot verify, '' = process gone."""
    try:
        r = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)],
                           capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001 — verification failure must fail closed
        return None
    return r.stdout.strip()


def _proc_gone(pid):
    """True when pid is absent or a zombie (a zombie is already dead)."""
    try:
        r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                           capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001
        return False
    out = r.stdout.strip()
    return out == "" or out.startswith("Z")


def _signal_group(pgid, sig):
    """Best-effort group signal. EPERM/ESRCH on dead or zombie-only groups
    (a macOS quirk) are tolerated: the verdict comes from _proc_gone, not
    from the syscall return."""
    try:
        os.killpg(pgid, sig)
    except OSError:
        pass


def _kill_group(pid, pgid):
    """SIGTERM the process group, SIGKILL after a short grace, reap if ours.
    Returns 'gone' (never existed), 'killed' (verifiably dead) or
    'kill-unconfirmed' (still alive — caller must NOT mark it reclaimed)."""
    if _proc_gone(pid):
        return "gone"
    _signal_group(pgid, signal.SIGTERM)
    deadline = time.time() + KILL_GRACE
    while time.time() < deadline and not _proc_gone(pid):
        time.sleep(0.05)
    if not _proc_gone(pid):
        _signal_group(pgid, signal.SIGKILL)
        deadline = time.time() + KILL_GRACE
        while time.time() < deadline and not _proc_gone(pid):
            time.sleep(0.05)
    try:  # best effort: only succeeds when the leader is our own child
        os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, PermissionError, OSError):
        pass
    return "killed" if _proc_gone(pid) else "kill-unconfirmed"


class _Txn:
    """BEGIN IMMEDIATE ... COMMIT / ROLLBACK around a write block."""

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.execute("BEGIN IMMEDIATE")
        return self.db

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.db.execute("COMMIT")
        else:
            self.db.execute("ROLLBACK")
        return False


class ResourceAllocator:
    def __init__(self, db_path, *, epoch_check=None):
        self.db_path = str(db_path)
        self.epoch_check = epoch_check
        self._db = sqlite3.connect(self.db_path, isolation_level=None)
        self._db.executescript(_SCHEMA)

    # -- fencing -----------------------------------------------------------

    def _check_epoch(self, attempt_id, lease_epoch):
        """Reject allocations from stale leases. Runs before any allocation."""
        if not isinstance(lease_epoch, int) or lease_epoch < 1:
            raise ValueError(f"lease_epoch must be an int >= 1, got {lease_epoch!r}")
        if self.epoch_check is not None:
            self.epoch_check(attempt_id, lease_epoch)  # any raise rejects
            return
        with _Txn(self._db) as db:
            row = db.execute("SELECT lease_epoch FROM leases WHERE attempt_id=?",
                             (attempt_id,)).fetchone()
            if row is not None and lease_epoch < row[0]:
                raise StaleEpochError(
                    f"{attempt_id}: lease_epoch {lease_epoch} older than recorded {row[0]}")
            if row is None:
                db.execute("INSERT INTO leases(attempt_id, lease_epoch) VALUES (?,?)",
                           (attempt_id, lease_epoch))
            elif lease_epoch > row[0]:
                db.execute("UPDATE leases SET lease_epoch=? WHERE attempt_id=?",
                           (lease_epoch, attempt_id))

    # -- row helpers (callers hold the transaction) ------------------------

    @staticmethod
    def _attempt8(attempt_id):
        m = ATTEMPT_RE.match(attempt_id)
        if not m:
            raise ValueError(f"bad attempt_id {attempt_id!r}: expected attempt-<32hex>")
        return m.group(1)[:8]

    @staticmethod
    def _extra_dict(raw):
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _hold_row(self, db, attempt_id, lease_epoch, kind, name, value, extra):
        """Register (or re-hold) one allocation row; returns the held value."""
        now = time.time()
        extra_json = json.dumps(extra, sort_keys=True) if extra is not None else None
        row = db.execute(
            "SELECT value, state FROM allocations WHERE attempt_id=? AND kind=? AND name=?",
            (attempt_id, kind, name)).fetchone()
        if row is not None and row[1] == "held":
            return row[0]  # idempotent: the existing value wins
        if row is not None and row[1] == "quarantined":
            raise ResourceConflict(
                f"{kind}:{name} is quarantined for {attempt_id}; awaiting human review")
        if row is None:
            try:
                db.execute(
                    "INSERT INTO allocations(attempt_id, lease_epoch, kind, name, value,"
                    " state, created, extra) VALUES (?,?,?,?,?,'held',?,?)",
                    (attempt_id, lease_epoch, kind, name, value, now, extra_json))
            except sqlite3.IntegrityError as exc:
                raise ResourceConflict(f"{kind}:{name} already held: {exc}") from exc
        else:  # re-hold a released record in place (keeps UNIQUE satisfied)
            db.execute(
                "UPDATE allocations SET lease_epoch=?, value=?, state='held', created=?, extra=?"
                " WHERE attempt_id=? AND kind=? AND name=?",
                (lease_epoch, value, now, extra_json, attempt_id, kind, name))
        return value

    # -- allocators --------------------------------------------------------

    def allocate_port(self, attempt_id: str, lease_epoch: int) -> int:
        self._check_epoch(attempt_id, lease_epoch)
        # H8 (port TOCTOU): candidate pick + bind test + DB reserve all run in
        # this ONE BEGIN IMMEDIATE transaction — a port that fails to bind is
        # never reserved (the socket binds with SO_REUSEADDR off, verifies,
        # closes, and only then the row is inserted).
        with _Txn(self._db) as db:
            row = db.execute(
                "SELECT value FROM allocations WHERE attempt_id=? AND kind='port' AND state='held'",
                (attempt_id,)).fetchone()
            if row is not None:
                return int(row[0])  # idempotent
            taken = {r[0] for r in db.execute(
                "SELECT name FROM allocations WHERE kind='port' AND state IN ('held','quarantined')")}
            for port in range(PORT_MIN, PORT_MAX + 1):
                name = str(port)
                if name in taken:
                    continue
                if not _bindable(port):
                    continue
                self._hold_row(db, attempt_id, lease_epoch, "port", name, name, None)
                return port
        raise ResourceConflict(f"no free port in {PORT_MIN}-{PORT_MAX}")

    def allocate_procgroup(self, attempt_id: str, lease_epoch: int,
                           argv: list, cwd=None) -> dict:
        self._check_epoch(attempt_id, lease_epoch)
        argv = [str(a) for a in argv]
        if not argv:
            raise ValueError("argv must be non-empty")
        digest = hashlib.sha256(" ".join(argv).encode("utf-8")).hexdigest()
        name = f"pg-{attempt_id}-{digest[:16]}"
        with _Txn(self._db) as db:
            row = db.execute(
                "SELECT value, state, extra FROM allocations"
                " WHERE attempt_id=? AND kind='procgroup' AND name=?",
                (attempt_id, name)).fetchone()
            if row is not None and row[1] == "held":
                extra = self._extra_dict(row[2])  # idempotent: no respawn
                return {k: extra[k] for k in ("pid", "pgid", "started_at", "argv_digest")
                        if k in extra}
            if row is not None and row[1] == "quarantined":
                raise ResourceConflict(
                    f"procgroup:{name} is quarantined for {attempt_id}; awaiting human review")
            proc = subprocess.Popen(argv, cwd=cwd, start_new_session=True)
            pid = proc.pid
            try:
                pgid = os.getpgid(pid)
            except OSError:
                pgid = pid
            info = {"pid": pid, "pgid": pgid, "started_at": time.time(),
                    "argv_digest": digest}
            extra = dict(info)
            extra["lstart"] = _ps_lstart(pid) or ""  # PID-reuse evidence
            try:
                self._hold_row(db, attempt_id, lease_epoch, "procgroup", name,
                               str(pid), extra)
            except ResourceConflict:
                _kill_group(pid, pgid)  # never leak a fresh spawn
                raise
            return info

    def allocate_tempdir(self, attempt_id: str, lease_epoch: int) -> str:
        self._check_epoch(attempt_id, lease_epoch)
        with _Txn(self._db) as db:
            row = db.execute(
                "SELECT value FROM allocations WHERE attempt_id=? AND kind='tempdir'"
                " AND state='held'", (attempt_id,)).fetchone()
            if row is not None:
                return row[0]  # idempotent
            path = tempfile.mkdtemp(prefix="vw-alloc-")
            self._hold_row(db, attempt_id, lease_epoch, "tempdir", path, path, None)
            return path

    def allocate_db_name(self, attempt_id: str, lease_epoch: int) -> str:
        self._check_epoch(attempt_id, lease_epoch)
        attempt8 = self._attempt8(attempt_id)
        run8 = hashlib.sha256(f"run:{attempt_id}".encode("utf-8")).hexdigest()[:8]
        value = f"vw_{run8}_{attempt8}"
        with _Txn(self._db) as db:
            self._hold_row(db, attempt_id, lease_epoch, "db_name", value, value, None)
            return value

    def allocate_browser_profile(self, attempt_id: str, lease_epoch: int) -> str:
        self._check_epoch(attempt_id, lease_epoch)
        attempt8 = self._attempt8(attempt_id)
        value = f"vw-profile-{attempt8}"
        with _Txn(self._db) as db:
            self._hold_row(db, attempt_id, lease_epoch, "browser_profile", value, value, None)
            return value

    def allocate_credential_ref(self, attempt_id: str, lease_epoch: int, name: str) -> str:
        # Deliberately accepts ONLY a name — a secret VALUE has nowhere to go.
        # H7 (R17): the name itself must not be credential material (a
        # token-shaped name is a secret leak by another route) and is capped.
        if not isinstance(name, str) or len(name) > CRED_NAME_MAX:
            raise ValueError(
                f"credential ref name must be a str of at most {CRED_NAME_MAX}"
                f" chars (got {len(name) if isinstance(name, str) else type(name).__name__})")
        if _credential_name_is_secret_shaped(name):
            raise ValueError(
                "credential ref name looks like credential material (secret-"
                "shaped token) — pass a NAME (e.g. 'github-token'), never a "
                "credential VALUE or token-shaped string")
        self._check_epoch(attempt_id, lease_epoch)
        attempt8 = self._attempt8(attempt_id)
        sanitized = NAME_SAFE_RE.sub("-", name).strip("-") or "name"
        ref = f"cred://vw/{attempt8}/{sanitized}"
        with _Txn(self._db) as db:
            self._hold_row(db, attempt_id, lease_epoch, "credential_ref", ref, ref, None)
            return ref

    def allocate_exclusive(self, resource_name: str, attempt_id: str,
                           lease_epoch: int) -> str:
        self._check_epoch(attempt_id, lease_epoch)
        with _Txn(self._db) as db:
            own = db.execute(
                "SELECT state FROM allocations WHERE attempt_id=? AND kind='exclusive'"
                " AND name=?", (attempt_id, resource_name)).fetchone()
            if own is not None and own[0] == "held":
                return resource_name  # idempotent: the existing hold wins
            # The partial UNIQUE(name) WHERE state='held' index does NOT cover
            # 'quarantined' rows — reject held OR quarantined takes of the same
            # singleton explicitly (transactionally) so quarantine is never a
            # double-take bypass.
            clash = db.execute(
                "SELECT attempt_id, state FROM allocations"
                " WHERE kind='exclusive' AND name=? AND state IN ('held','quarantined')"
                " LIMIT 1", (resource_name,)).fetchone()
            if clash is not None:
                raise ResourceConflict(
                    f"exclusive:{resource_name} is {clash[1]} by {clash[0]};"
                    f" awaiting release/human review")
            self._hold_row(db, attempt_id, lease_epoch, "exclusive",
                           resource_name, resource_name, None)
            return resource_name

    def allocate_quota(self, attempt_id: str, lease_epoch: int, name: str,
                       limit) -> dict:
        """Register a named resource quota (CPU-seconds, bytes, …) for an
        attempt (§MA9 resource ownership). Idempotent per (attempt, name);
        the stored row is kind='quota' with value {"limit", "used"}."""
        self._check_epoch(attempt_id, lease_epoch)
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit <= 0:
            raise ValueError(f"quota limit must be a positive number, got: {limit!r}")
        with _Txn(self._db) as db:
            row = db.execute(
                "SELECT value FROM allocations WHERE attempt_id=? AND kind='quota'"
                " AND name=?", (attempt_id, name)).fetchone()
            if row is not None:
                return json.loads(row[0])
            payload = {"limit": limit, "used": 0}
            self._hold_row(db, attempt_id, lease_epoch, "quota", name,
                           json.dumps(payload), None)
            return payload

    def charge_quota(self, attempt_id: str, lease_epoch: int, name: str,
                     amount) -> bool:
        """Charge usage against a quota. Returns False WITHOUT applying the
        charge when it would exceed the limit (fail-closed, never overdrafts).
        Raises KeyError when no held quota exists for the name."""
        self._check_epoch(attempt_id, lease_epoch)
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError(f"quota charge must be a non-negative number, got: {amount!r}")
        with _Txn(self._db) as db:
            row = db.execute(
                "SELECT value FROM allocations WHERE attempt_id=? AND kind='quota'"
                " AND name=? AND state='held'", (attempt_id, name)).fetchone()
            if row is None:
                raise KeyError(f"no held quota {name!r} for {attempt_id}")
            payload = json.loads(row[0])
            if payload["used"] + amount > payload["limit"]:
                return False
            payload["used"] += amount
            db.execute(
                "UPDATE allocations SET value=? WHERE attempt_id=? AND kind='quota'"
                " AND name=?", (json.dumps(payload), attempt_id, name))
            return True

    def quota(self, attempt_id: str, name: str):
        """Current {"limit", "used"} for a quota, or None when unregistered."""
        with _Txn(self._db) as db:
            row = db.execute(
                "SELECT value FROM allocations WHERE attempt_id=? AND kind='quota'"
                " AND name=?", (attempt_id, name)).fetchone()
        return json.loads(row[0]) if row is not None else None

    # -- lifecycle ---------------------------------------------------------

    def reclaim(self, attempt_id: str, lease_epoch=None) -> dict:
        """Reclaim every held row of an attempt (fail-closed per row).

        lease_epoch is an optional write fence: when supplied, a stale epoch
        raises StaleEpochError before anything is touched. A tempdir that
        cannot be removed stays state='held' and is listed under "skipped"
        with reason "rmtree-failed:<err>" — a row is never marked reclaimed
        while its directory still exists.
        """
        if lease_epoch is not None:
            self._check_epoch(attempt_id, lease_epoch)  # stale epoch -> StaleEpochError
        summary = {"reclaimed": [], "skipped": []}
        with _Txn(self._db) as db:
            rows = db.execute(
                "SELECT kind, name, value, state, extra FROM allocations"
                " WHERE attempt_id=? ORDER BY created, kind, name", (attempt_id,)).fetchall()
            for kind, name, value, state, extra_raw in rows:
                extra = self._extra_dict(extra_raw)
                if state == "quarantined":
                    reason = "quarantined"
                    if extra.get("quarantine_reason"):
                        reason = f"quarantined: {extra['quarantine_reason']}"
                    summary["skipped"].append(
                        {"kind": kind, "name": name, "value": value, "reason": reason})
                    continue  # frozen until human review
                if state != "held":
                    continue
                if kind == "procgroup":
                    entry = self._reclaim_procgroup(db, name, value, extra)
                    (summary["reclaimed"] if entry[0] else summary["skipped"]).append(entry[1])
                elif kind == "tempdir":
                    try:
                        self._rm_tree(value)
                    except OSError as err:
                        if os.path.isdir(value):
                            # Fail closed: the directory still exists — keep the
                            # row held and record why removal failed.
                            summary["skipped"].append(
                                {"kind": kind, "name": name, "value": value,
                                 "reason": f"rmtree-failed:{err}"})
                            continue
                    db.execute("UPDATE allocations SET state='reclaimed'"
                               " WHERE attempt_id=? AND kind=? AND name=?",
                               (attempt_id, kind, name))
                    summary["reclaimed"].append(
                        {"kind": kind, "name": name, "value": value, "action": "rmtree"})
                else:
                    db.execute("UPDATE allocations SET state='reclaimed'"
                               " WHERE attempt_id=? AND kind=? AND name=?",
                               (attempt_id, kind, name))
                    summary["reclaimed"].append(
                        {"kind": kind, "name": name, "value": value, "action": "released"})
        return summary

    def _reclaim_procgroup(self, db, name, value, extra):
        """Kill a recorded process group — only when the pgid leader provably
        is still the same process (PID-reuse guard). Returns (kept, entry)."""
        entry_base = {"kind": "procgroup", "name": name, "value": value}
        pid, pgid = extra.get("pid"), extra.get("pgid")
        rec_lstart = extra.get("lstart")
        if not isinstance(pid, int) or not isinstance(pgid, int):
            extra["reclaim"] = "skipped-bad-record"
            self._mark_procgroup(db, name, extra, held=True)
            return False, {**entry_base, "reason": "skipped-bad-record"}
        current = _ps_lstart(pid)
        if rec_lstart is None or pgid != pid or current is None:
            # Missing/mismatched evidence or non-leader pgid: never kill.
            extra["reclaim"] = "skipped-pid-reuse"
            self._mark_procgroup(db, name, extra, held=True)
            return False, {**entry_base, "reason": "skipped-pid-reuse"}
        if current == "":
            # The recorded process already exited; nothing to kill.
            extra["reclaim"] = "gone"
            self._mark_procgroup(db, name, extra, held=False)
            return True, {**entry_base, "action": "gone"}
        if current != rec_lstart:
            extra["reclaim"] = "skipped-pid-reuse"
            self._mark_procgroup(db, name, extra, held=True)
            return False, {**entry_base, "reason": "skipped-pid-reuse"}
        action = _kill_group(pid, pgid)
        if action == "kill-unconfirmed":  # still alive: fail closed, keep held
            extra["reclaim"] = "skipped-kill-failed"
            self._mark_procgroup(db, name, extra, held=True)
            return False, {**entry_base, "reason": "skipped-kill-failed"}
        extra["reclaim"] = action
        self._mark_procgroup(db, name, extra, held=False)
        return True, {**entry_base, "action": action}

    @staticmethod
    def _mark_procgroup(db, name, extra, *, held):
        state = "held" if held else "reclaimed"
        db.execute("UPDATE allocations SET state=?, extra=? WHERE kind='procgroup' AND name=?",
                   (state, json.dumps(extra, sort_keys=True), name))

    @staticmethod
    def _rm_tree(path):
        import shutil  # local import: only reclaim needs it
        # Fail closed: errors propagate to reclaim() so a still-existing
        # directory is never silently dropped (no ignore_errors).
        shutil.rmtree(path)

    def quarantine(self, attempt_id: str, reason: str) -> None:
        with _Txn(self._db) as db:
            rows = db.execute(
                "SELECT kind, name, extra FROM allocations"
                " WHERE attempt_id=? AND state='held'", (attempt_id,)).fetchall()
            for kind, name, extra_raw in rows:
                extra = self._extra_dict(extra_raw)
                extra["quarantine_reason"] = reason
                db.execute(
                    "UPDATE allocations SET state='quarantined', extra=?"
                    " WHERE attempt_id=? AND kind=? AND name=? AND state='held'",
                    (json.dumps(extra, sort_keys=True), attempt_id, kind, name))

    def list_allocations(self, attempt_id: str) -> list:
        rows = self._db.execute(
            "SELECT attempt_id, lease_epoch, kind, name, value, state, created, extra"
            " FROM allocations WHERE attempt_id=? ORDER BY created, kind, name",
            (attempt_id,)).fetchall()
        out = []
        for attempt_id_, lease_epoch, kind, name, value, state, created, extra_raw in rows:
            out.append({"attempt_id": attempt_id_, "lease_epoch": lease_epoch,
                        "kind": kind, "name": name, "value": value, "state": state,
                        "created": created, "extra": self._extra_dict(extra_raw)})
        return out


def _bindable(port):
    """True when 127.0.0.1:port really binds right now (SO_REUSEADDR off —
    an occupied/TIME_WAIT port must never look bindable)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="W25 per-attempt resource allocator (registry CLI)")
    ap.add_argument("--db", required=True, help="path to the allocator sqlite registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "reclaim"):
        p = sub.add_parser(name)
        p.add_argument("--attempt", required=True)
    pq = sub.add_parser("quarantine")
    pq.add_argument("--attempt", required=True)
    pq.add_argument("--reason", default="manual")
    args = ap.parse_args(argv)
    alloc = ResourceAllocator(args.db)
    if args.cmd == "list":
        print(json.dumps(alloc.list_allocations(args.attempt), indent=2, sort_keys=True))
    elif args.cmd == "reclaim":
        print(json.dumps(alloc.reclaim(args.attempt), indent=2, sort_keys=True))
    else:
        alloc.quarantine(args.attempt, args.reason)
        print(json.dumps(alloc.list_allocations(args.attempt), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
