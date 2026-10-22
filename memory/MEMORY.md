# Project Memory Index

## Project Context
- [Mini checker gate](project_mini_gate.md) — why mini needs its own plugin; activation, oracle guard, review lessons (2026-10-20)
- W0 trust floor (2026-10-22, ✅ verified dev+repo) — signed-manifest path, checker pin, evidence lock, bootstrap pointer, state redaction; evidence in `tests/w0/`
- Release topology (2026-10-22, ✅) — dev tree is source; payload = `vibeweaver/`; tags `w18`/`w18.1` immutable; `w18.2.4` is the W0 release (w18.2..w18.2.3 superseded)
- Trust boundaries (2026-10-22, ✅) — `docs/TRUST_MODEL.md`: lazy forgery vs hostile root, TCB, residual risks
- Compatibility (2026-10-22, ⏳) — opencode v1/v2 only; other hosts are adapters (D-002), not equal-semantics

## Feedback
- Claims need a reproducer (2026-10-22, ✅) — every count/effect claim binds command + platform + evidence path; `check_doc_counts.py` enforced
- Sync is a controlled list (2026-10-22, ✅) — harness, checker pin, gate fixtures and release scripts ship with the payload; `tests/sync_skill.py` fails closed

## References
- [Release verification](../docs/RELEASE.md) — manifest, `sha256sum -c`, cosign, `gh attestation verify`
