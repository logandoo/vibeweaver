> cap=5  stall=3×

# Acceptance Criteria — transpose(text)

1. `transpose("")` returns `""` (empty input → empty output).
2. `transpose("A1")` returns `"A\n1"` (two characters in a row become two rows).
3. `transpose("A\n1")` returns `"A1"` (two characters in a column become one row).
4. `transpose("ABC\n123")` returns `"A1\nB2\nC3"` (simple 2x3 matrix).
5. `transpose("Single line.")` returns each character on its own row (`"S\ni\nn\ng\nl\ne\n \nl\ni\nn\ne\n."`).
6. First line longer than second line: `"The fourth line.\nThe fifth line."` matches canonical output, including preserving real trailing spaces (`"  "`, `"h "`).
7. Second line longer than first line: `"The first line.\nThe second line."` matches canonical output (`"l "`, `" ."`).
8. Mixed line length: `"The longest line.\nA long line.\nA longer line.\nA line."` matches canonical output (`"h   "`, `"ei "`, `" .n"`, `"l e"` — real trailing spaces preserved, padding stripped).
9. Square matrix: `"HEART\nEMBER\nABUSE\nRESIN\nTREND"` returns the same 5x5 grid.
10. Rectangle matrix: `"FRACTURE\nOUTLINED\nBLOOMING\nSEPTETTE"` matches canonical output.
11. Triangle (monotonically increasing lengths): `"T\nEE\nAAA\nSSSS\nEEEEE\nRRRRRR"` matches canonical output with left padding.
12. Jagged triangle: `"11\n2\n3333\n444\n555555\n66666"` matches canonical output (`"1 3456"`, `"  3 56"`, `"    5"`).
13. No syntax or runtime errors; function signature `transpose(text)` kept as given.
