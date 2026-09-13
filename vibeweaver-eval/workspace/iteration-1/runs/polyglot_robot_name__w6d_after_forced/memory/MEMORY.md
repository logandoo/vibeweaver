# Project Memory — robot_name

## Project
Single-file Exercism `robot-name` exercise. Deliverable: `robot_name.py` (`Robot` class).
Python 3.9.6. No build/service lifecycle, no `script/`.

## ✅ Verified
- `Robot.name` is lazy (generated on first access), format `[A-Z]{2}\d{3}`.
- `Robot.used_names` is a class-level registry; names are NEVER removed, so a
  reset robot cannot re-draw its previous name — required by the canonical
  seeded `test_reset_name` (reseed + reset must yield a different name).
- `reset()` only wipes `self._name`; next `name` access regenerates uniquely.

## ⛔ Forbidden
- Do not seed `random` inside the module (canonical test controls the seed).
- Do not discard names from `used_names` on reset (breaks seeded reset test).
