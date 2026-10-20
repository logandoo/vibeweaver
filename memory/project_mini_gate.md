---
name: Mini checker gate
description: vibeweaver-mini ships its own plugin because the full gate keys on tests/verification_log.md; activation, oracle guard, tests, review lessons
type: project
date: 2026-10-20
---

# Mini checker gate

**Why a separate plugin.** The full gate/auditor activate on
`tests/verification_log.md`. The mini kit's contract is the checker's literal
`ALL CHECKS PASS`, so the full pair is inert there. `vibeweaver-mini-gate.js`
runs `vw_check.py` (or the mini `script/check.sh` when `vw_check.py` is absent)
after every write/edit: red throws the repair packet, green appends the
checker's own output. It also challenges an idle completion claim, budget
2/session, no reset.

**What the reviews forced (5 rounds, 2026-10-20).**

- Root = the session project only. No ancestor walk: a nested `vw_check.py`
  must never capture a full project. `tests/verification_log.md` at the root is
  the full-skill precedence marker.
- The oracle is read-only: block `write`/`edit` to `vw_check.py`,
  `script/check.sh`, `script(s)/vw_check.py`, `.vw_test_hashes.json`,
  `.vw_loop_state.json`, and `tests/verification_log.md`; case-fold on
  darwin/win32. Bash redirections are a heuristic (tee, fd redirects, `>&file`,
  `.vw*` globs), not a security boundary.
- Pass predicate is a line-anchored `ALL CHECKS PASS`; exit 0 without the line
  is red. Missing/silent checker and timeouts fail closed.
- Gate-observed runs set `VW_CHECK_NO_STATE=1`: they keep a `seen` marker but
  do not consume the model's cap/stall budget. A pass resets `runs`/`same_fail`
  while preserving `seen`.
- Assistant text requires a known assistant `messageID`; parts arriving before
  `message.updated` are buffered, user text is never a claim. Idle consumes the
  turn's text; the plugin prompt is not re-read.
- The checker hashes nested pytest config (`conftest.py`, `pytest.ini`,
  `tox.ini`, `setup.cfg`, pytest `pyproject.toml`), npm `package.json` and the
  node default test layouts (`test.*`, `*_test.*`, `.mts/.cts`), plus nested
  JS runner configs; `PYTHONDONTWRITEBYTECODE=1` avoids stale-bytecode greens.
- v2 idle needs `ctx.session.prompt`; the shipped v2 context may lack it, so
  the write gate is the v2 guard. Windows requires `vw_check.py`; the
  `script/check.sh` fallback needs bash.

**Verification.** `node tests/mini_gate_test.mjs` 61/61 (v1+v2, oracle guard,
missing/silent checker, timeout, idle/budget, real pytest fail→pass, nested
conftest, npm layouts, installers) · `verify_skill.py` 10/10 · unittest 56/56.

**How to apply.** Keep the mini plugin separate from the full gate; protect the
oracle before running it; hash every test-discovery input the runner uses; do
not let observation runs consume the loop budget; document shell/v2 limits
instead of overclaiming.
