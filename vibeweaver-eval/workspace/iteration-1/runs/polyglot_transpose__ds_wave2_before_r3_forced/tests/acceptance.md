> cap=5  stall=3×
1. transpose("") returns "".
2. transpose("A1") returns "A\n1".
3. transpose("A\n1") returns "A1".
4. transpose("ABC\n123") returns "A1\nB2\nC3".
5. A single-line input becomes one output row per character.
6. When the first line is longer, missing bottom rows are not padded to the right.
7. When the second line is longer, missing top rows are padded to the left with spaces.
8. Mixed-length input preserves real trailing spaces in output rows (they are input characters) while stripping right-side padding for missing bottom rows.
9. Square and rectangle matrices transpose row↔column symmetrically.
10. Triangle and jagged-triangle inputs pad to the left correctly.
11. Every character of the input appears in the transposed output (no data loss).
