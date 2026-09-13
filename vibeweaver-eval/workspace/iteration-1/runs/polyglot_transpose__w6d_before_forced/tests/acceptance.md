> cap=5  stall=3×

1. Empty input `""` returns `""`.
2. A single row transposes each character to its own output row, preserving interior spaces (e.g. `"A1"` → `"A\n1"`, `"Single line."` keeps the `" "` row).
3. A single column transposes to one output row (`"A\n1"` → `"A1"`).
4. Equal-length rows transpose correctly (square and rectangle).
5. When the first row is longer, right-side padding is dropped while genuine trailing input spaces are kept (`"ABC\nDE"` → `"AD\nBE\nC"`; `"The fourth line.\nThe fifth line."` includes the row `"h "`).
6. When a later row is longer, the missing top-row character appears as a leading space in the output row (`"AB\nDEF"` → `"AD\nBE\n F"`).
7. Jagged/triangle inputs preserve every non-newline input character with no added right padding (`triangle`, `jagged_triangle`).
8. Hidden canonical suite passes 12/12 and `python3 -m py_compile transpose.py` exits 0.
