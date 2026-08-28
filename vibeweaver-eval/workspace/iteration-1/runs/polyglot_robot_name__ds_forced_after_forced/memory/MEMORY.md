# MEMORY.md — project memory index

Project: polyglot exercise workspace — `robot_name.py` (Exercism-style "Robot Name" kata).
Mode: Modify-Existing (starter stub `class Robot: def __init__(self): pass`).

## User / constraints
- Harness constraint: "Do NOT create or modify any test files" — verification runner stays OUTSIDE the workspace; only log evidence lands in `tests/`.
- Graded by hidden tests run against `robot_name.py`; interface must be `Robot()` → `.name` attribute, `reset()` method.
- Run directory is untracked inside the parent repo → no git baseline/feature commits (Commit column = N/A).

## Topics
- [robot_name.md](robot_name.md) — spec + chosen approach for the Robot Name exercise (✅ Verified)

## Verified / Failed / Forbidden
- ✅ Verified: class-level `_used_names` set + `random.choices` retry-until-unique is the canonical, spec-satisfying approach for this kata.
- ❌ Failed: (none yet)
- ⛔ Forbidden: writing any collectable test file into the workspace; sequential/counter names (violates "names must be random"); raw build/lifecycle commands bypassing `script/`.
