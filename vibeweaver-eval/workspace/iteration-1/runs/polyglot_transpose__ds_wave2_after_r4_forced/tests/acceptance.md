> cap=5  stall=3×

# transpose exercise — acceptance criteria

1. `transpose("")` returns `""` (empty string).
2. `transpose("A1")` returns `"A\n1"` (two characters in a row → column).
3. `transpose("A\n1")` returns `"A1"` (two characters in a column → row).
4. `transpose("ABC\n123")` returns `"A1\nB2\nC3"` (simple square transpose).
5. `transpose("Single line.")` returns one character per line, preserving the interior space as its own line (`"S\ni\nn\ng\nl\ne\n \nl\ni\nn\ne\n."`).
6. First line longer than second: `transpose("The fourth line.\nThe fifth line.")` matches the canonical expected output (real spaces preserved, no trailing padding).
7. Second line longer than first: `transpose("The first line.\nThe second line.")` matches canonical expected output (pad spaces appear on the left of output rows).
8. Mixed line lengths: `transpose("The longest line.\nA long line.\nA longer line.\nA line.")` matches canonical expected output (real trailing spaces in input are preserved in the output).
9. Square: `transpose("HEART\nEMBER\nABUSE\nRESIN\nTREND")` returns the same text.
10. Rectangle: `transpose("FRACTURE\nOUTLINED\nBLOOMING\nSEPTETTE")` matches canonical expected output.
11. Triangle: `transpose("T\nEE\nAAA\nSSSS\nEEEEE\nRRRRRR")` matches canonical expected output (left-padded rows).
12. Jagged triangle: `transpose("11\n2\n3333\n444\n555555\n66666")` matches canonical expected output.
13. Prompt matrix examples: `transpose("ABC\nDEF") == "AD\nBE\nCF"`, `transpose("ABC\nDE") == "AD\nBE\nC"`, `transpose("AB\nDEF") == "AD\nBE\n F"`.
14. No module-level side effects, import-safe, runs without syntax/runtime errors on all of the above.
