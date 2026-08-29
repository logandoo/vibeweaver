# fix_two_bucket.md

- type: fix
- status: ✅ Verified (2026-08-29)
- problem: Starter `two_bucket.py` stub (`pass`) for the Exercism "Two Bucket" exercise did nothing.
- solution: BFS from the filled-start state. `measure()` seeds `(cap_start, 0)` (count=1), generates the 6 successor states (fill/empty both, pour both via `min(source, cap_dest - dest)`), prunes the forbidden state (`(0, cap_two)` when start=="one", `(cap_one, 0)` when start=="two") and visited states (enqueue-time marking), returns `(actions, goal_bucket, other)` on first goal hit, raises `ValueError("No more moves!")` on exhaustion. two_bucket.py.
- verification: tests/verify_green.run.log — 11/11 canonical cases pass; tests/diff_sweep.run.log — 1152-input differential sweep vs independent reference BFS, 0 mismatches; `python3 -m py_compile` OK; A4.9 independent review APPROVE.
- avoided pitfall: do NOT gcd-pre-check impossibility — the canonical "not possible" cases must fail through BFS exhaustion so reachability (incl. forbidden-state pruning) is decided by the actual state space; keep the ValueError message non-empty (canonical test uses `r".+"`).
