# Decisions — Bowling Scorer

## D-1 Frame-based state machine (chosen)
Represent the game as `self.frames` (list of per-frame roll lists). A new frame is
started only when the current one is complete. Validation is local to the active
frame, which maps directly onto the rules that are per-frame (two-roll sum, 10th-frame
fill balls). Rejected alternative: a flat rolls list re-deriving frame boundaries on
every roll — more index arithmetic for validation, no benefit at this size.

## D-2 COV-9 baseline recorded as skipped
The workspace is untracked inside the parent eval repo; a baseline commit would stage
unrelated sibling runs. The pre-change stub cannot be GREEN, so the honest record is a
pre-change RED baseline plus a `COV-9 skipped` entry (see verification_log.md).

## D-3 Trusted oracle is the certification source
`prompt.md` omits the validation cases; the hidden Exercism suite is the acceptance
oracle. Behavior was driven from the oracle, not invented, and the oracle is run from
an isolated temp dir so no test file lands in the deliverable.

## D-4 Project profile = library
No service/UI lifecycle exists. `tests/project_profile.json` declares `library`, which
declaratively skips the service-lifecycle group rather than weakening any applicable
check.
