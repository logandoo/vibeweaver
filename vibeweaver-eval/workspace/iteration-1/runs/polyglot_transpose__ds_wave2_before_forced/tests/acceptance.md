> cap=5  stall=3×

Acceptance criteria for the Transpose exercise (canonical data from
https://github.com/exercism/problem-specifications/blob/main/exercises/transpose/canonical-data.json).

1. `transpose("")` returns `""` (empty string).
2. `transpose("A1")` returns `"A\n1"` (two characters in a row).
3. `transpose("A\n1")` returns `"A1"` (two characters in a column).
4. `transpose("ABC\n123")` returns `"A1\nB2\nC3"` (simple rectangular transpose).
5. `transpose("Single line.")` returns one character per line: `"S\ni\nn\ng\nl\ne\n \nl\ni\nn\ne\n."`.
6. `transpose("The fourth line.\nThe fifth line.")` returns the canonical 16-row result ending in `"."` (trailing padding trimmed, real spaces kept — includes row `"h "`).
7. `transpose("The first line.\nThe second line.")` returns the canonical 16-row result ending in `" ."`.
8. `transpose("The longest line.\nA long line.\nA longer line.\nA line.")` returns the canonical 17-row result (rows `"ei "`, `" .n"`, `"n"`, `"e"`, `"."`).
9. `transpose("HEART\nEMBER\nABUSE\nRESIN\nTREND")` returns the identical square (identity).
10. `transpose("FRACTURE\nOUTLINED\nBLOOMING\nSEPTETTE")` returns `"FOBS\nRULE\nATOP\nCLOT\nTIME\nUNIT\nRENT\nEDGE"`.
11. `transpose("T\nEE\nAAA\nSSSS\nEEEEE\nRRRRRR")` returns the canonical triangle (`"TEASER\n EASER\n  ASER\n   SER\n    ER\n     R"`).
12. `transpose("11\n2\n3333\n444\n555555\n66666")` returns `"123456\n1 3456\n  3456\n  3 56\n    56\n    5"` (jagged triangle: trailing padding trimmed, interior padding kept).
