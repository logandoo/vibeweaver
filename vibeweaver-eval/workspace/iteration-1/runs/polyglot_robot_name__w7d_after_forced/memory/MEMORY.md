# Project Memory — robot_name

## Project
Single-file Exercism `robot-name` exercise. Deliverable: `robot_name.py` (`Robot` class).
Python 3.9.6. No build/service lifecycle, so no `script/` directory (COV-2 = na).

## ✅ Verified
- `Robot.name` is lazy (generated on first access); format `[A-Z]{2}\d{3}`.
- `Robot.used_names` is a class-level registry. Names are NEVER removed, so a
  reset robot cannot re-draw its previous name — required by the canonical
  seeded `test_reset_name` (reseed + reset must yield a different name).
- `reset()` only wipes `self._name`; the next `name` access regenerates uniquely.
- Hidden suite `robot_name_test.py` passes 4/4; 5000-robot uniqueness stress passes.

## ⏳ Deferred minors (from A4.9 review, not test-visible)
- Namespace exhaustion: after all 676,000 names are cumulatively issued (resets
  included), `_generate_name`'s `while True` never terminates. Fine for the
  contract; revisit if the exercise is scaled to exhaust the namespace.
- `used_names` grows unbounded (names of reset/GC'd robots are retained by design).
- `candidate not in used_names` / `used_names.add` is not atomic; a multi-threaded
  caller could race. Add a lock only if concurrency is ever required.

## ⛔ Forbidden
- Do not seed `random` inside the module (the canonical test controls the seed).
- Do not discard names from `used_names` on reset (breaks the seeded reset test).
