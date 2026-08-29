# Project Memory — polyglot_pig_latin

## Task identity
- Repo task: Exercism "pig-latin" — implement `translate(text)` in `pig_latin.py`.
- Graded by `harness/grade_polyglot.py`: copies workdir, injects canonical hidden
  test `pig_latin_test.py`, runs `python3 -m pytest -q pig_latin_test.py`.
- Hard constraint: do NOT create or modify test files inside the workdir.

## Key files
- [pig_latin.py](pig_latin.py) — the only solution file; stub replaced this task.
- [tests/verification_log.md](tests/verification_log.md) — iteration/baseline evidence.
- [tests/decisions.md](tests/decisions.md) — ADRs (split-point algorithm, qu/y handling).
- [tests/acceptance.md](tests/acceptance.md) — C1–C8 criteria (all PASS at iter 2).

## Topic files
- [pig_latin_implementation.md](pig_latin_implementation.md) — algorithm, rules, verification, caveats.

## Open items
- None. Task completed GREEN (22/22 canonical + 0/22 vector failures).
