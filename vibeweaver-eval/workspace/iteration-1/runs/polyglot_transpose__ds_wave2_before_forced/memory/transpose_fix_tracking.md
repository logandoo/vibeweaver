# Transpose algorithm — verified

Type: reference · Status: ✅ Verified · 2026-08-29

## Problem

Transpose a multi-line text so rows become columns, per the Exercism Transpose
exercise. Non-rectangular inputs: pad with spaces, keep every input character.

## Validated approach (passes all 12 official canonical cases)

1. Split text on `'\n'` into lines.
2. For each column index `col` in `range(max(line lengths))`:
   - Build `column = ''.join(line[col] if col < len(line) else ' ' for line in lines)`
     (left-aligned column; padding spaces for too-short lines).
   - Trim only the *trailing padding* spaces (the last line index `last` with
     `len(lines[last]) > col` defines the kept prefix `column[:last+1]`).
3. Join output rows with `'\n'`.

Key subtlety: real spaces in the input are preserved, only *padding* spaces from
too-short bottom lines are trimmed. E.g. `"The fourth line.\nThe fifth line."`
row 9 is `"h "` (real trailing space, kept); `"11\n2\n3333\n444\n555555\n66666"`
column 5 is `"    5 "` (padding, trimmed to `"    5"`).

## Rejected approaches

- Plain `.rstrip()` per row — strips real trailing spaces too; fails canonical
  cases 6 (`"h "`) and 8 (`"ei "`). ❌
- Right-aligning input — fails simple rectangular transpose (`"ABC\nDEF"`).
  ❌

## Failure recorded

- `import transpose` in a smoke script binds the module, not the function →
  `TypeError: 'module' object is not callable`. Use `from transpose import transpose`. ❌ (see MEMORY.md index)

## Evidence

- 12/12 official canonical tests pass (tests/verification_run_iter1.log).
- 3 prompt.md examples pass.
- Lifecycle scripts script/linux/{start,stop,restart}.sh green (pidfile pattern).

## A4.9 independent review (2026-08-29)

Verdict: READY (Critical: none · Important: none). Review also independently
re-ran all 12 canonical cases and 20,000 randomized inputs (zero input chars
dropped, no right-padding). Findings adjudicated:

- Minor 1 (start.sh records subshell PID, pidfile decorative): ruled accepted,
  no action — library-only project, no long-running service; matches sibling-run
  convention. pidfile pattern kept for stop.sh safety (targeted kill, no pkill).
- Minor 2 (stop.sh no numeric/ownership validation of pidfile): ruled accepted,
  no action — sandbox-only, `|| true` already suppresses; would require ownership
  check in a shared-host service project (not applicable here).
- Minor 3 (no docstring/comment for subtle trailing-space rule): ruled deferred —
  skill covenant forbids comments unless asked; rule documented here + in
  acceptance.md criteria 6/12 instead.
- Minor 4 (test-suite source not pinned on disk): ruled accepted by design — task
  forbids creating test files in the workspace; canonical-data.json URL pinned in
  tests/acceptance.md.
- Minor 5 (assert_artifacts.py is a copied artifact checker): ruled accepted —
  mandated by skill §A4.4.1 (copy canonical, never retype).
