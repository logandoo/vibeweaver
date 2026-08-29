# Verification Log

## Task: implement Bowling in `bowling.py` (Modify-Existing, backend-only pure library)

- Baseline verified GREEN — stub `bowling.py` compiles (`python3 -m py_compile` exit 0) and `BowlingGame()` constructs (`roll`/`score` bound methods present; no behavior implemented, as expected for a stub). No build/service/UI runtime exists in this exercise workspace, so there is no build/start step to baseline-test (COV-9 baseline entry recorded).
- COV-9 baseline commit made, scoped to this run dir only: `44a8187 backup: before changes` (`git add -A .` from the run directory — no unrelated harness changes staged).

### Verifier probe (COV-5)
- Backend-only pure-library task → no UI/media to capture; §A4.7 test loop applies (no browser-rendered output exists). `mm_probe.py` is not deployed in this skill install (only SKILL.md) and there is no media to probe — no `vision.py` (mm-sensor) either. → **Verifier: direct-read (non-web)** — evidence = executed-check run log (`tests/verification_run.log`) + canonical-suite + differential-check exit codes, cross-checked against `bowling.py` source.

### TDD RED evidence (A4.8 — run against the stub BEFORE implementation)
- Spec-derived verification (runner kept outside the workspace at `/var/folders/.../T/opencode/bowling_verify.py`; no test files written into the workspace per the harness "no test files" constraint) against the stub produced the expected failure:
  - `score()` returned `None` for every game; no errors raised for invalid rolls
  - SUMMARY: 1/23 passed, 22 failed (criterion 1 = imports/constructs PASS; all behavior + error criteria FAIL)

### Loop iterations
- iter 1 FAIL: criteria #4 (strike-alone / strike-double-count / consecutive-strikes) and #8 (two-rolls-in-frame > 10) — diagnosis: two distinct causes — (a) my runner's test DATA used 20-roll games after early strikes, but the canonical game completes on roll 19 (or 17 for 10,10,10,5,3) so the trailing roll is correctly rejected as `IndexError: Cannot roll after the game is over` (test-data bug, fixed to canonical 19/17-roll sequences); (b) a REAL code bug in `bowling.py`: `_current_frame_state` advanced its walk past a 1-roll in-progress non-strike frame, so the second-roll frame-over-10 validation was skipped (`roll(5); roll(6)` appended 6). changed: `bowling.py` (walker now stops at an incomplete frame — `elif i + 1 < len(self.rolls)` / `break`).
- iter 2 PASS: criteria #1–#8 — 29/29 executed checks in `tests/verification_run.log` PASS (open frames 0 & 90; spare bonus 10 & 16 & consecutive 31; strike bonus 10 & 26 & consecutive 81; last-two-strikes 31; 10th spare 17 & 20; 10th strike 18 & 20 & 30; perfect 300; error contracts: negative / >10 / frame-over-10 / bonus-over-10-after-non-strike / bonus-cannot-be-strike-after-non-strike / second-bonus>10 all raise, roll-after-game-over & roll-after-fill & score-before-complete & score-with-10th-bonus-pending all raise). Changed: `bowling.py` (stub → full implementation).
- **Cross-check A (canonical Exercism suite):** the official `exercism/python` `bowling_test.py` run from a temp dir against the final `bowling.py` → **31/31 OK** (`python3 -m unittest bowling_test_canonical`).
- **Cross-check B (randomized differential):** 5000 randomly generated complete valid games scored by `BowlingGame.score()` vs an independent frame-based reference scorer → **0 mismatches** (`tests/` evidence via run log below).

## FRESH run on final tree
- `python3 -m py_compile bowling.py` → exit 0 (no syntax errors).
- `bash script/linux/start.sh` (compile + smoke check on final tree) → OK.
- Runner re-run on final tree (no commits after last test): 29/29 PASS, 0 failed; canonical suite 31/31; differential 5000/5000.

## A4.9 independent review
- Review package written to `tests/review_package.md`; independent READ-ONLY reviewer dispatched (subagent).
- Verdict: **PASS** — no Critical, no Important. Reviewer's independent re-tests (200k random deep trials with illegal pins, 30k valid games, exhaustive legal-prefix depth-5) all matched a reference implementation. 3 style/perf Minors recorded to `memory/MEMORY.md` (not fixed: leave validated code untouched).
- No post-review code changes → no re-run needed (reviewed against the exact final tree).
