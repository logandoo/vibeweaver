# FCV report — vibeweaver-mini-gate (2026-10-20)

**Why FCV.** Lane L + a new dual-compat plugin: the maker is the same model
that wrote the code, so an independent fresh-context check is required.

**Method.** Five review rounds, each in a fresh subagent with the diff package
and no write access:

1. Two independent adversarial reviewers over the feature commit.
2. One scoped re-review over the first fix round.
3. One scoped re-review over the case/nested-config round.
4. One ship-check over the npm/state/hint round.
5. One final ship-check over the node-layout/redirect round.

Findings were adjudicated: every Critical/Important was fixed with a covering
test; Minors were deferred to `memory/project_mini_gate.md` (bash is a denylist
not a sandbox; `find -delete` / inline interpreters are outside the hook;
Windows `.bat` is exercised by the CI matrix, not locally; v2 idle requires
`ctx.session.prompt`).

**Final result (fresh run on the delivered tree).**

- `node tests/mini_gate_test.mjs` → 61/61
- `python3 verify_skill.py` → 10 checks OK
- `python3 -m unittest discover -s tests` → 56 tests OK
- `node tests/plugin_compat_test.mjs --allow-known` → 69/71 (E3/G9 known)
- `node vibeweaver/scripts/audit_selftest.mjs` → 568/0 (1 skipped)
- `node vibeweaver/scripts/mutation_sweep.mjs` → 44/0
- `assert_artifacts.py --profile library --existing --final` → 18/18

**Residual risk.** The shell guard is a heuristic over `write`/`edit` and common
redirects; it is not a sandbox. The v2 idle challenge is inert on hosts without
`ctx.session.prompt` (the write gate still runs). Both are documented rather
than overclaimed.
