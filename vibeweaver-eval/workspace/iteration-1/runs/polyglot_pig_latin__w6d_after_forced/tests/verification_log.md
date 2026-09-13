# Verification Log — pig_latin

- Baseline (COV-9): `python3 -c "import pig_latin; print(repr(pig_latin.translate('apple')))"` → `None` (stub non-functional). Baseline has 1 expected pre-existing failure (the stub); implementing the function is the task. No `script/` directory exists (single-file library) → lifecycle scripts N/A. Proceed.
- iter 1 PASS: criteria #1-#6 | evidence: `/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/opencode/pig_latin_verify.py` executed → `20/20 passed`, exit=0; `python3 -m py_compile pig_latin.py` → OK; `ast.parse` → OK. All prompt examples (Rules 1-4) plus multi-word case pass.
