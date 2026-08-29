# task: transpose

type: project
date: 2026-08-29

## Requirement (prompt.md)
Transpose an input text: rows become columns. Ragged rows: pad LEFT with spaces, never pad RIGHT.
All input characters must survive in the output; real trailing spaces in a column are kept as the
right-most characters of the output row.

## Verification target
Hidden suite: tasks/polyglot_transpose/hidden_tests/transpose_test.py (12 cases, exercism canonical).
Grading command: `python3 -m pytest -q`. Contract: `from transpose import transpose; transpose(text)`.

## Result
All 12 hidden tests + 4 prompt-spec examples pass (iter 1). No stalls, no cap hits.
