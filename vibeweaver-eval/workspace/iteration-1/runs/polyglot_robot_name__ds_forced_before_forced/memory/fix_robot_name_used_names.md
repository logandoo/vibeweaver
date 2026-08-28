---
title: robot-name uniqueness approach
type: fix
trust: verified
date: 2026-08-29
---

# robot-name: used-names set must keep names forever

## Symptom
Hidden `test_reset_name` re-seeds `random`, then does `reset()` + re-ask; the
regenerated name must differ from the pre-reset one.

## Root cause insight
With the RNG re-seeded, a fresh generation would reproduce the exact same
name — unless the old name is still tracked. Keeping every generated name in
a class-level `used_names` set (never removing on `reset()`) forces the
regeneration loop to skip the old candidate and emit a different, unique name.

## Fix (validated)
`Robot.used_names = set()` (class attr) + lazy `name` property; `_generate_unique_name()`
loops `random.choices` candidates until not-in-set, then adds and returns.
`reset()` only sets `self._name = None`.

## Status
✅ Verified — hidden test `robot_name_test.py` 4/4 pass (grader command);
robustness run 6/6 PASS (`tests/verification_run.log`).

## Independent review (A4.9) — verdict PASS
Critical/Important: none.
Minor findings + rulings:
- `used_names` never releases names consumed by `reset()` (unbounded growth).
  Ruling: ACCEPT — spec-compliant; keep-forever is required by the re-seed
  test; population is finite (676,000) so growth is bounded in any realistic
  run.
- `_generate_unique_name` while-loop would spin if all 676k names were
  exhausted. Ruling: ACCEPT — theoretical only, outside tested scope;
  exhaustive namespace collision is not reachable by the acceptance tests.
