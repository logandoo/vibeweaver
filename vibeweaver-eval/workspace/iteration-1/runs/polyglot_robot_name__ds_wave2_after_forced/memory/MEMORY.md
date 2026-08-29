# MEMORY.md — project memory index

Project: polyglot exercise workspace — `robot_name.py` (Exercism-style "Robot Name" kata).
Mode: Modify-Existing (starter stub `class Robot: def __init__(self): pass`).

## User / constraints
- Harness constraint: "Do NOT create or modify any test files" — verification runner stays OUTSIDE the workspace (inline `python3 - <<EOF`); only log evidence lands in `tests/`.
- Graded by hidden tests run against `robot_name.py`; interface must be `Robot()` → `.name` attribute, `reset()` method.
- Run directory is untracked inside the parent repo; baseline commit was scoped to this dir (`dba13f7 backup: before changes`), final commit scoped likewise (Commit column = short hash).

## Topics
- [robot_name.md](robot_name.md) — spec + chosen approach for the Robot Name exercise (✅ Verified)

## Verified / Failed / Forbidden
- ✅ Verified: class-level `_used_names` set + `random.choices` retry-until-unique is the canonical, spec-satisfying approach for this kata; 7/7 acceptance criteria pass + extended sweeps (3000-robot uniqueness, 200 sequential resets) in `tests/verification_run.log`.
- ❌ Failed: (none yet)
- ⛔ Forbidden: writing any collectable test file into the workspace; sequential/counter names (violates "names must be random"); raw build/lifecycle commands bypassing `script/`.
