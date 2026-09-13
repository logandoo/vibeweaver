> cap=5  stall=3×

1. `transpose(text)` transposes a rectangular matrix (rows become columns) exactly.
2. Ragged input follows the spec: real spaces are preserved, trailing padding is dropped.
3. All canonical Exercism `transpose` cases pass (incl. mixed line length, triangle, jagged triangle).
4. Both prompt.md worked examples (`ABC/DE` and `AB/DEF`) match exactly.
5. `python3 -m py_compile transpose.py` exits 0 and the function never raises on canonical inputs.
