# Trust model (vibeweaver, W0)

**TCB (trusted computing base):** the installed skill payload, the two
opencode plugins, and `tests/assert_artifacts.py` pinned by
`scripts/assert_artifacts.sha256`. A host that can rewrite these files is
outside the model.

| Threat | Control | Residual | Test |
|---|---|---|---|
| Lazy forgery (3-line fake checker) | checker pin (sha256) + release manifest | an agent that can rewrite the gate/checker **or the installed pin/canonical dir** (same user writable) — outside TCB | `tests/gate_trust/run.sh` |
| Rule forgery (loosen acceptance, delete FAIL, edit profile/debt) | `scripts/evidence_lock.py`; protected evidence is gated | a root process can edit `.evidence.lock` | `tests/gate_trust/evidence_integrity/run.sh` |
| Fake media evidence | magic bytes + size in evidence lock | a crafted real-format image with wrong content | `evidence_integrity/run.sh` (1-byte PNG) |
| Secret exfiltration via state | redact before write; 5 MB cap; 14-day retention; `.vibeweaver/` ignored | leaked credentials need rotation (history is not cleaned by `.gitignore`) | `tests/test_state_sanitize.py` · `tests/state_bounds_test.mjs` |
| Malicious project (symlink/path traversal) | `realpath` + first-segment anchoring | OS-level symlink race | `tests/plugin_compat_test.mjs` T37 |
| Prompt injection in fetched content | COV-11 (data, not instructions) | model persuasion | contract review; no fixture yet |
| Supply-chain release replacement | signed manifest / GitHub attestation; `install.sh` verifies | signing key or CI compromise | `.github/workflows/release.yml` |
| Multi-tenant activation | project-root marker (`tests/verification_log.md`) | host misconfiguration | gate hook tests |
| Subagent bootstrap leakage | child-session keys + full-contract dedupe | real host subagent input shape unprobed (adapter gap) | `tests/bootstrap_test.mjs` (mock shapes) |
| Destructive command (`git add -A`, `rm -rf`) | **not in P0** (Task 7.5, pre-write guard) | execution-level damage | deferred to W1 |

## Scope notes

- `install.sh` verifies `release/MANIFEST.json` before copying. A missing
  manifest in the release layout is a hard failure; `--no-verify` is for the
  dev tree only.
- `sha256sum -c` detects corruption, not replacement. Use a digest from an
  independent channel, or the signed manifest/attestation.
- Runtime state (`.vibeweaver/audit-state.json`) is host-local; the session
  transcript retention policy remains a host concern (D-003: fail-open must be
  labelled `UNVERIFIED`).
