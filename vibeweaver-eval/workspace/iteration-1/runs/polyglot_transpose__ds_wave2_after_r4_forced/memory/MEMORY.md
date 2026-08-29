# MEMORY.md — transpose exercise (polyglot run)

Index of project memory. Load priority: ⛔ Forbidden → ❌ Failed → ✅ Verified → ⏳ Unverified.

## Topics
- [fix_transpose_algorithm.md](fix_transpose_algorithm.md) — ✅ transpose algorithm + verified edge semantics (real trailing spaces preserved, left-pad/right-drop).
- [project_reference.md](project_reference.md) — ✅ harness constraints + canonical reference (exercism `transpose`), approach comparison.

## Verified (✅)
- Position-aware pad-marker algorithm is correct: 21/21 checks pass (12 canonical Exercism cases + 3 prompt examples + 6 edge cases), exit 0 — verified 2026-08-29.
- Real input spaces (including trailing) are preserved; only padding positions are dropped/converted — this is the key non-obvious rule (`test_mixed_line_length` `"h   "` row).

## Unverified (⏳)
- Whether the hidden grader includes any case with a trailing empty row after the final newline (`"abc\n"`): implementation treats the trailing newline as a row terminator (drops it), matching the canonical reference's `splitlines()` behavior — verified against canonical test suite; not graded locally.

## Forbidden (⛔)
- Do not create/modify grader test files (user constraint); do not add sentinel characters that could collide with real input (underscore approach rejected for collision risk).
