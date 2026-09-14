# Verification Log — polyglot_bowling (w7d_before_forced)

> cap=5  stall=3×   (COV-7 bound; verifier: direct read (non-web))

## Baseline (COV-9, Modify-Existing)
- `python3 -c "ast.parse(bowling.py)"` on the starter stub → `baseline stub syntax OK`.
- Baseline verdict: GREEN (stub parses; no tests/scripts exist in workspace).
- COV-9 ADR D-2: skipped `git add -A && git commit "backup: before changes"` because the
  workspace is untracked inside the parent `vibeweaver-repo`; a repo-wide `git add -A`
  would stage unrelated sibling eval runs. Stub baseline is trivially green anyway.

## Iterations
- iter 1 PASS: criteria #1-#7 | diagnosis: n/a (first implementation correct) | changed: bowling.py
  Evidence (inline harness, `python3 - <<'EOF'`, 2026-09-14):
  ```
  PASS: all gutter balls (20x0): got=0 expected=0
  PASS: all open frames 9+0 (20x9/0): got=90 expected=90
  PASS: one spare then 3: 5,5,3 + rest 0: got=16 expected=16
  PASS: one strike then 3,4: 10,3,4 + rest 0: got=24 expected=24
  PASS: prompt example X | 5/ | 9 0: got=48 expected=48
  PASS: all spares 5/ (21 rolls): got=150 expected=150
  PASS: perfect game 12 strikes: got=300 expected=300
  PASS: tenth frame strike + spare fill: ...X 1/: got=20 expected=20
  PASS: tenth frame three strikes: ...XXX: got=30 expected=30
  RESULT: 9/9 assertions passed
  two-strike lookahead: got 51 expected 51
  ```
- `python3 -m py_compile bowling.py` → exit 0 (no syntax errors).
