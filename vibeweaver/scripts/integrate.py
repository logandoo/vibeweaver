#!/usr/bin/env python3
"""integrate.py — immutable-candidate integration queue for multi-agent runs.

W25 Task 4 (see docs/PLAN_w25_multi_agent.md). A single-host reference
implementation of the immutable-candidate flow:

  1. enqueue        — freeze source_head_sha / target_base_sha (40-hex only;
                      branch names are rejected). The frozen SHAs never change
                      when branches move later.
  2. build_candidate — materialize a detached worktree at the frozen
                      target_base_sha, then cherry-pick every earlier queue item
                      (FIFO) plus the current one on top. Conflicts abort the
                      pick and yield NO candidate (the worktree is left clean).
  3. integration_gate — run real test commands bound to the candidate SHA.
                      Coverage honesty: ok=True never hides unverified
                      (empty/placeholder) review ids.
  4. publish        — CAS ref update via `git update-ref <ref> <new> <old>`.
                      If the target moved, raise TargetChangedError, mark the
                      candidate stale and requeue the item.
  5. record_sha_map / reconcile_shas — map candidate -> final commit/tree SHAs
                      and report published items missing their mapping.
  6. invalidate_on_target_change — when the target ref advances, stale
                      queued/gated items are invalidated as a batch.
  7. cleanup_precheck — evidence gate: published + sha_map + ok gate + no
                      pending integration outbox entries.

State machine (queue.state): queued | building | gated | published | stale |
invalidated. Transitions: enqueue -> queued; build_candidate -> building
(conflict -> queued); integration_gate ok -> gated; publish ok -> published
(CAS failure -> queued, candidate row -> stale); invalidate_on_target_change ->
invalidated. FIFO build picks include every non-dead item (queued/building/
gated/published) at or before the current row; stale/invalidated items are
never replayed into a candidate.

SQLite tables: queue, candidates, gate_results, sha_map, publications.
Optional `control` duck-types ControlPlane.outbox_put/outbox_pending: publish /
candidate transitions emit ("integration", {"queue_id","candidate_sha","event"},
f"integration:{queue_id}:{event}").

CLI: python3 scripts/integrate.py status|reconcile|cleanup-precheck --db PATH
Python 3.9+ stdlib only.
"""
import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
QUEUE_STATES = ("queued", "building", "gated", "published", "stale", "invalidated")
# FIFO build picks: dead items (stale/invalidated) are never replayed.
PICKABLE_STATES = ("queued", "building", "gated", "published")
INVALIDATABLE_STATES = ("queued", "gated")
REVIEW_PLACEHOLDERS = {"todo", "tbd", "none", "null", "n/a", "na",
                       "unknown", "unverified", "fill-me"}


class TargetChangedError(RuntimeError):
    """CAS publish failed because the target ref moved away from expected_old_sha."""


def _is_sha(value):
    return isinstance(value, str) and SHA_RE.match(value) is not None


def _is_placeholder_review(review_id):
    s = (review_id or "").strip() if isinstance(review_id, str) else ""
    if not s or "placeholder" in s.lower():
        return True
    return s.lower() in REVIEW_PLACEHOLDERS


class IntegrationQueue:
    """Immutable-candidate integration queue backed by SQLite."""

    def __init__(self, db_path, control=None):
        # control: object with outbox_put(record_type, payload, idempotency_key) -> int,
        # or None. When a publish/candidate transition happens, emit outbox records
        # via control if present:
        #   control.outbox_put("integration", {"queue_id":..., "candidate_sha":..., "event":...},
        #                      f"integration:{queue_id}:{event}")
        self.db_path = str(db_path)
        self.control = control
        self.target_ref = "refs/heads/main"
        self._init_schema()

    # ------------------------------------------------------------- plumbing

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS queue (
                    id TEXT PRIMARY KEY,
                    source_head_sha TEXT NOT NULL,
                    target_base_sha TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    deps_json TEXT NOT NULL,
                    spec_hash TEXT NOT NULL,
                    bundle_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS candidates (
                    queue_id TEXT PRIMARY KEY,
                    integration_run_id TEXT NOT NULL,
                    candidate_sha TEXT,
                    tree_sha TEXT,
                    manifest_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    stale_reason TEXT
                );
                CREATE TABLE IF NOT EXISTS gate_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id TEXT NOT NULL,
                    candidate_sha TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    results_json TEXT NOT NULL,
                    covered_json TEXT NOT NULL,
                    unverified_json TEXT NOT NULL,
                    created INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sha_map (
                    queue_id TEXT PRIMARY KEY,
                    candidate_sha TEXT NOT NULL,
                    final_commit_sha TEXT NOT NULL,
                    final_tree_sha TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id TEXT NOT NULL,
                    candidate_sha TEXT NOT NULL,
                    expected_old_sha TEXT NOT NULL,
                    target_ref TEXT NOT NULL,
                    created INTEGER NOT NULL
                );
                """
            )

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row(self, queue_id):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM queue WHERE id=?", (queue_id,)).fetchall()
        if not rows:
            raise ValueError(f"unknown queue_id: {queue_id}")
        return rows[0]

    def _set_state(self, queue_id, state):
        with self._connect() as conn:
            conn.execute("UPDATE queue SET state=? WHERE id=?", (state, queue_id))

    def _candidate_row(self, queue_id):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM candidates WHERE queue_id=?", (queue_id,)).fetchall()
        return rows[-1] if rows else None

    def _emit(self, queue_id, candidate_sha, event):
        if self.control is None:
            return
        self.control.outbox_put(
            "integration",
            {"queue_id": queue_id, "candidate_sha": candidate_sha, "event": event},
            f"integration:{queue_id}:{event}")

    @staticmethod
    def _git(cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True)

    # --------------------------------------------------------------- queue

    def enqueue(self, source_head_sha: str, target_base_sha: str, run_id: str, attempt_id: str,
                deps: list[str], spec_hash: str, bundle_hash: str) -> str:
        """Freeze a queue item. SHAs must be 40-hex (branch names raise ValueError)."""
        for name, value in (("source_head_sha", source_head_sha),
                            ("target_base_sha", target_base_sha)):
            if not _is_sha(value):
                raise ValueError(f"{name} must be a 40-hex SHA, got: {value!r}")
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise ValueError("deps must be a list of str")
        for name, value in (("run_id", run_id), ("attempt_id", attempt_id),
                            ("spec_hash", spec_hash), ("bundle_hash", bundle_hash)):
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a str")
        queue_id = "q-" + uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO queue (id, source_head_sha, target_base_sha, run_id,"
                " attempt_id, deps_json, spec_hash, bundle_hash, state, created)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (queue_id, source_head_sha, target_base_sha, run_id, attempt_id,
                 json.dumps(deps), spec_hash, bundle_hash, "queued", time.time_ns()))
        return queue_id

    # ---------------------------------------------------------------- build

    def build_candidate(self, repo_path: str, queue_id: str, integration_run_id: str, workdir: str) -> dict:
        """Build an immutable candidate on target_base_sha + every prior FIFO item.

        Materializes a detached worktree at the frozen target_base_sha and
        cherry-picks each pickable item up to and including this one, in FIFO
        order. On any cherry-pick conflict the pick is aborted and no candidate
        is produced (worktree left clean).
        """
        row = self._row(queue_id)
        if not isinstance(integration_run_id, str) or not integration_run_id:
            raise ValueError("integration_run_id must be a non-empty str")
        self._set_state(queue_id, "building")
        workdir = Path(workdir)
        workdir.parent.mkdir(parents=True, exist_ok=True)
        wt = self._git(repo_path, "worktree", "add", "--detach",
                       str(workdir), row["target_base_sha"])
        if wt.returncode != 0:
            self._set_state(queue_id, "queued")
            raise RuntimeError(f"worktree add failed: {wt.stderr.strip()}")

        with self._connect() as conn:
            picks = [r["source_head_sha"] for r in conn.execute(
                "SELECT * FROM queue WHERE state IN (%s) AND"
                " rowid <= (SELECT rowid FROM queue WHERE id=?)"
                " ORDER BY rowid" % ",".join("?" * len(PICKABLE_STATES)),
                (*PICKABLE_STATES, queue_id)).fetchall()]
            picks.append(row["source_head_sha"])  # current item last in FIFO order
            picks = list(dict.fromkeys(picks))  # dedupe while keeping order

        for sha in picks:
            cp = self._git(workdir, "cherry-pick", sha)
            if cp.returncode != 0:
                out = cp.stderr + cp.stdout
                if "now empty" in out or "empty cherry-pick" in out:
                    # Nothing to replay (e.g. an --allow-empty source commit or a
                    # change already present): no-op, keep going, no candidate loss.
                    self._git(workdir, "cherry-pick", "--abort")
                    continue
                self._git(workdir, "cherry-pick", "--abort")
                self._set_state(queue_id, "queued")
                return {"queue_id": queue_id, "candidate_sha": None,
                        "tree_sha": None, "conflicts": [sha]}
        candidate_sha = self._git(workdir, "rev-parse", "HEAD").stdout.strip()
        tree_sha = self._git(workdir, "rev-parse", "HEAD^{tree}").stdout.strip()
        manifest = {"queue_id": queue_id, "integration_run_id": integration_run_id,
                    "candidate_sha": candidate_sha, "tree_sha": tree_sha,
                    "target_base_sha": row["target_base_sha"], "picked": picks}
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO candidates (queue_id, integration_run_id,"
                " candidate_sha, tree_sha, manifest_json, state, stale_reason)"
                " VALUES (?,?,?,?,?,?,?)",
                (queue_id, integration_run_id, candidate_sha, tree_sha,
                 json.dumps(manifest), "built", None))
        self._emit(queue_id, candidate_sha, "built")
        return {"queue_id": queue_id, "candidate_sha": candidate_sha,
                "tree_sha": tree_sha, "conflicts": [],
                "integration_run_id": integration_run_id}

    # ----------------------------------------------------------------- gate

    def integration_gate(self, repo_path: str, queue_id: str, candidate_sha: str,
                         test_commands: list[list[str]], review_ids: list[str]) -> dict:
        """Run test commands bound to the queue's current candidate SHA.

        Returns {"ok", "results", "covered", "unverified", "candidate_sha"}.
        ok=True never hides unverified entries: every empty/placeholder review id
        is listed in "unverified" with a reason regardless of ok.
        """
        if not _is_sha(candidate_sha):
            raise ValueError(f"candidate_sha must be a 40-hex SHA, got: {candidate_sha!r}")
        current = self._candidate_row(queue_id)
        if current is None or current["candidate_sha"] != candidate_sha:
            raise ValueError(
                f"candidate_sha {candidate_sha} is not the queue's current candidate")
        if current["state"] == "stale":
            raise ValueError(
                f"candidate {candidate_sha} is stale (target changed) — rebuild "
                "the candidate before gating (invalidation propagation)")
        with self._connect() as conn:
            qrow = conn.execute("SELECT state FROM queue WHERE id=?",
                                (queue_id,)).fetchone()
        if qrow is not None and qrow["state"] in ("stale", "invalidated"):
            raise ValueError(
                f"queue {queue_id} is {qrow['state']} — its old green is void; "
                "rebuild and re-gate on the current target")
        results = []
        for cmd in test_commands:
            try:
                r = subprocess.run(cmd, cwd=repo_path, capture_output=True, timeout=120)
                out = r.stdout.decode("utf-8", "replace")
                err = r.stderr.decode("utf-8", "replace")
                rc = r.returncode
            except subprocess.TimeoutExpired:
                out, err, rc = "", "timeout after 120s", -1
            results.append({"cmd": list(cmd), "rc": rc,
                            "stdout_tail": out[-2000:], "stderr_tail": err[-2000:],
                            "candidate_sha": candidate_sha})
        covered = [r["cmd"] for r in results if r["rc"] == 0]
        unverified = [{"review_id": rid,
                       "reason": f"review {rid!r} is empty or placeholder — "
                                 f"coverage unverified"}
                      for rid in review_ids if _is_placeholder_review(rid)]
        ok = all(r["rc"] == 0 for r in results)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO gate_results (queue_id, candidate_sha, ok, results_json,"
                " covered_json, unverified_json, created) VALUES (?,?,?,?,?,?,?)",
                (queue_id, candidate_sha, 1 if ok else 0,
                 json.dumps(results), json.dumps(covered), json.dumps(unverified),
                 time.time_ns()))
        if ok:
            self._set_state(queue_id, "gated")
        return {"ok": ok, "results": results, "covered": covered,
                "unverified": unverified, "candidate_sha": candidate_sha}

    # -------------------------------------------------------------- publish

    def publish(self, repo_path: str, queue_id: str, candidate_sha: str, expected_old_sha: str) -> dict:
        """CAS publish: git update-ref <target_ref> candidate expected_old.

        Target moved -> TargetChangedError, candidate row marked stale,
        outbox event "target-changed", queue item returns to "queued".
        """
        self._row(queue_id)
        for name, value in (("candidate_sha", candidate_sha),
                            ("expected_old_sha", expected_old_sha)):
            if not _is_sha(value):
                raise ValueError(f"{name} must be a 40-hex SHA, got: {value!r}")
        ref = self.target_ref
        r = self._git(repo_path, "update-ref", ref, candidate_sha, expected_old_sha)
        if r.returncode != 0:
            cur = self._git(repo_path, "rev-parse", "--verify", ref + "^{commit}")
            if cur.returncode == 0 and cur.stdout.strip() != expected_old_sha:
                with self._connect() as conn:
                    conn.execute(
                        "UPDATE candidates SET state='stale',"
                        " stale_reason=? WHERE queue_id=?",
                        (f"target-changed: {ref} moved away from {expected_old_sha}",
                         queue_id))
                self._set_state(queue_id, "queued")
                self._emit(queue_id, candidate_sha, "target-changed")
                raise TargetChangedError(
                    f"{ref} moved: expected {expected_old_sha}, "
                    f"found {cur.stdout.strip()}")
            raise RuntimeError(f"update-ref failed: {r.stderr.strip()}")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO publications (queue_id, candidate_sha, expected_old_sha,"
                " target_ref, created) VALUES (?,?,?,?,?)",
                (queue_id, candidate_sha, expected_old_sha, ref, time.time_ns()))
        self._set_state(queue_id, "published")
        self._emit(queue_id, candidate_sha, "published")
        return {"queue_id": queue_id, "candidate_sha": candidate_sha,
                "target_ref": ref, "expected_old_sha": expected_old_sha,
                "published": True}

    # --------------------------------------------------------- SHA mapping

    def record_sha_map(self, queue_id: str, candidate_sha: str, final_commit_sha: str, final_tree_sha: str) -> None:
        for name, value in (("candidate_sha", candidate_sha),
                            ("final_commit_sha", final_commit_sha),
                            ("final_tree_sha", final_tree_sha)):
            if not _is_sha(value):
                raise ValueError(f"{name} must be a 40-hex SHA, got: {value!r}")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sha_map (queue_id, candidate_sha,"
                " final_commit_sha, final_tree_sha) VALUES (?,?,?,?)",
                (queue_id, candidate_sha, final_commit_sha, final_tree_sha))

    def reconcile_shas(self) -> list[dict]:
        """Pure-DB diff report: published queue items missing their sha_map row."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT q.id FROM queue q WHERE q.state='published'"
                " AND NOT EXISTS (SELECT 1 FROM sha_map m WHERE m.queue_id = q.id)"
                " ORDER BY q.rowid").fetchall()
        return [{"queue_id": r["id"],
                 "issue": "published queue has no sha_map row"} for r in rows]

    # -------------------------------------------------------- invalidation

    def invalidate_on_target_change(self, repo_path: str, target_ref: str) -> int:
        """Batch-invalidate queued/gated items whose frozen base no longer matches
        the target ref. Candidate rows go stale; an outbox notice is emitted."""
        cur = self._git(repo_path, "rev-parse", "--verify", target_ref + "^{commit}")
        if cur.returncode != 0:
            raise RuntimeError(f"cannot read {target_ref}: {cur.stderr.strip()}")
        current = cur.stdout.strip()
        count = 0
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM queue WHERE state IN (%s) ORDER BY rowid"
                % ",".join("?" * len(INVALIDATABLE_STATES)),
                INVALIDATABLE_STATES).fetchall()
        for row in rows:
            if row["target_base_sha"] == current:
                continue
            cand = self._candidate_row(row["id"])
            with self._connect() as conn:
                conn.execute(
                    "UPDATE candidates SET state='stale', stale_reason=? WHERE queue_id=?",
                    (f"target-changed: {target_ref} is {current}, "
                     f"base {row['target_base_sha']}", row["id"]))
            self._set_state(row["id"], "invalidated")
            self._emit(row["id"],
                       cand["candidate_sha"] if cand else None, "invalidated")
            count += 1
        return count

    # ------------------------------------------------------------- cleanup

    def cleanup_precheck(self, queue_id: str) -> tuple[bool, list[str]]:
        """(ok, reasons): True only when published + sha_map present + ok gate bound
        to the current candidate + no pending "integration" outbox entries."""
        row = self._row(queue_id)
        reasons = []
        if row["state"] != "published":
            reasons.append(f"queue state is {row['state']!r}, not 'published'")
        with self._connect() as conn:
            maps = conn.execute(
                "SELECT * FROM sha_map WHERE queue_id=?", (queue_id,)).fetchall()
            gates = conn.execute(
                "SELECT * FROM gate_results WHERE queue_id=? ORDER BY id",
                (queue_id,)).fetchall()
        if not maps:
            reasons.append("no sha_map row")
        cand = self._candidate_row(queue_id)
        current_sha = cand["candidate_sha"] if cand else None
        gate_ok = any(g["ok"] == 1 and g["candidate_sha"] == current_sha for g in gates)
        if not gates:
            reasons.append("no gate_results row")
        elif not gate_ok:
            reasons.append("no ok gate_results row bound to the current candidate")
        pending = getattr(self.control, "outbox_pending", None)
        if self.control is not None and callable(pending):
            n = len([i for i in pending()
                     if isinstance(i, dict) and i.get("record_type") == "integration"])
            if n:
                reasons.append(f"{n} pending integration outbox entries")
        return (not reasons), reasons

    # ----------------------------------------------------------------- CLI

    def cli_status(self) -> list[dict]:
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM queue ORDER BY rowid").fetchall()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="W25 immutable-candidate integration queue")
    ap.add_argument("--db", required=True, help="SQLite queue database path")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="dump queue rows as JSON")
    sub.add_parser("reconcile", help="report published items missing sha_map")
    cp = sub.add_parser("cleanup-precheck", help="evidence gate before cleanup")
    cp.add_argument("--queue-id", required=True)
    args = ap.parse_args(argv)
    q = IntegrationQueue(args.db)
    try:
        if args.cmd == "status":
            print(json.dumps(q.cli_status(), indent=2))
            return 0
        if args.cmd == "reconcile":
            print(json.dumps(q.reconcile_shas(), indent=2))
            return 0
        ok, reasons = q.cleanup_precheck(args.queue_id)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({"ok": ok, "reasons": reasons}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
