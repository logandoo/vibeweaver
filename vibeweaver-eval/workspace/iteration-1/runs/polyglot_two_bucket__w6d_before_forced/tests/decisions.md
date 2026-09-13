# Decisions (AUTO mode)

D-1 | trigger: COV-9 baseline commit | options: commit baseline in the shared
`vibeweaver-eval` repo vs capture a compile-check baseline without committing |
chosen: no commit | why: base instruction forbids committing unless explicitly
asked, and this run dir is nested in a shared eval repo where `git add -A`
would sweep unrelated modified run directories | revisit-if: user asks for a
commit or the exercise is extracted to its own repo.

D-2 | trigger: COV-5 verifier probe | options: model-native probe / mm-sensor /
direct read | chosen: direct read (non-web) | why: this skill install ships
only `SKILL.md`; `scripts/mm_probe.py` and `vision.py` are absent, and a pure
library has no UI/media to grade | revisit-if: multimodal tooling is installed.

D-3 | trigger: task says "do NOT create or modify any test files" | options:
write the test harness into the workspace vs keep it outside | chosen: keep
the harness at `/tmp/opencode/two_bucket_checks.py`, log output into
`tests/*.log` | why: honors the task constraint while preserving on-disk
evidence | revisit-if: the grader expects an in-repo test file.
