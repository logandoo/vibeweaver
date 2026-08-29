> cap=5  stall=3×

# Transpose — Acceptance Criteria

Derived from prompt.md + the hidden Exercism transpose suite (`tasks/polyglot_transpose/hidden_tests/transpose_test.py`, canonical 12 tests).

1. Empty string transposes to the empty string.
2. Two characters in a single row (`"A1"`) become two single-character rows (`"A\n1"`).
3. Two characters in a column (`"A\n1"`) become one two-character row (`"A1"`).
4. A simple 2×3 rectangle (`"ABC\n123"`) transposes to `"A1\nB2\nC3"`.
5. A single line transposes to one character per line, preserving embedded spaces (`"Single line."` → 12 single-char lines including a `" "` line).
6. First line longer than second (`"The fourth line.\nThe fifth line."`): the shorter row is padded on the left, and the real trailing space of the bottom row survives as a trailing space in its output row (`"h "`), matching the canonical expected output exactly.
7. Second line longer than first (`"The first line.\nThe second line."`): short-row padding appears at the left of output rows (`" l"`), matching canonical expected output exactly.
8. Mixed/ragged line lengths (4 rows) transpose with correct interleaved left-padding, matching the canonical expected output.
9. Square matrix transposes to itself.
10. Rectangle (4×8) transposes to the canonical 8×4 output.
11. Triangle (6 rows of increasing length) transposes to the canonical left-padded output.
12. Jagged triangle (ragged rows of interleaved lengths) transposes to the canonical output including interior padding cells (`"1 3456"`, `"  3 56"`).
13. All input characters appear in the transposed output (no data loss) and no padding spaces are appended to the right of any output row.
14. Module imports as `from transpose import transpose`; implementation lives in `transpose.py` only; no test files created or modified in the workspace.
