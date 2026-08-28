> cap=5  stall=3×
1. `transpose("")` returns `""`.
2. Single-row input `"A1"` returns `"A\n1"` (columns become rows).
3. Single-column input `"A\n1"` returns `"A1"` (rows become columns).
4. Equal-length matrix transposes exactly (rows↔columns), e.g. `"ABC\n123"` → `"A1\nB2\nC3"`.
5. Ragged rows: shorter rows are left-padded with spaces and not right-padded, e.g. `"ABC\nDE"` → `"AD\nBE\nC"` and `"AB\nDEF"` → `"AD\nBE\n F"`.
6. Real trailing spaces in the input are preserved in the output (e.g. the `ei ` row of the mixed-line-length case); only padding produced by exhausted rows is omitted.
7. All 12 cases in the authoritative hidden suite `transpose_test.py` pass (Ran 12 tests ... OK).
