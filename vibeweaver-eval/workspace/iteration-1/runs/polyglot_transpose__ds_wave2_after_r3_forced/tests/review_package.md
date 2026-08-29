# A4.9 Review Package — transpose exercise

Task: implement `transpose(text)` (Exercism transpose kata) in `transpose.py`.

Wave: `git diff 8020354..HEAD` (commit 65141e6; baseline `d1dc499 backup: before changes`).

## Files in wave (15)
- transpose.py — the only code change (stub `pass` → implementation).
- tests/{acceptance,verification_log,decisions}.md, tests/{hidden_run,worked_examples,restart_run,assert_run}.log, tests/assert_artifacts.py — verification evidence/artifacts.
- memory/{MEMORY.md, transpose.md} — session memory.
- script/linux/{start,stop,restart}.sh — pure-library lifecycle wrappers (no service).
- run.log — harness transcript.

## transpose.py (final)
```python
def transpose(text):
    rows = text.split("\n")
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    out = []
    for column in range(width):
        line = "".join(
            row[column] if column < len(row) else " " for row in rows
        )
        while line and line[-1] == " " and len(rows[len(line) - 1]) <= column:
            line = line[:-1]
        out.append(line)
    return "\n".join(out)
```

## Spec (prompt.md rules)
- Rows become columns; ragged rows: pad missing cells with spaces (left-pad), never pad right.
- All input characters must survive in the output; trailing output spaces that are real input characters (bottom-most rows) must be kept.
- Example: `"AB\nDEF"` → `"AD\nBE\n F"`; `"ABC\nDE"` → `"AD\nBE\nC"`.
- Critical canonical case: `"The fourth line.\nThe fifth line."` must produce row `"h "` (real trailing space kept) and final row `"."`.

## Verification evidence
- `tests/hidden_run.log`: `12 passed in 0.03s` (canonical 12-test suite, exit 0).
- `tests/worked_examples.log`: all 10 prompt/edge cases pass (incl. `"ABC "` → `"A\nB\nC\n "`, `"ABC\nAB"` → `"AA\nBB\nC"`).
- `tests/restart_run.log`: `bash script/linux/restart.sh` → smoke check OK.

## Verdict contract for reviewer
Report: **Strengths** · **Critical / Important / Minor** — dimension-tagged
(Bugs/Security/Compliance), Minor ≤5 itemized with file:line + why ·
**Assessment** (approved / changes-required). Read-only: do NOT edit files.
