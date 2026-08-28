# Project Memory Index

## transpose (polyglot_transpose)

- ✅ Verified: `transpose(text)` transposes line-based text. Algorithm: split on `\n`, for each column index up to max row length build the output row from `rows[0..last]` where `last` is the final row having a char at that column; exhausted rows contribute a leading space (pad left), rows past `last` are omitted (no right-pad). This preserves real trailing spaces (e.g. `ei ` row) while omitting padding-only ones.
- ❌ Failed approach: naive "missing char → space then `.rstrip()`" strips real trailing input spaces (fails the mixed-line-length case `ei ` row).
- Validation: 12/12 hidden tests pass; inline 12/12 prompt-example checks pass.
