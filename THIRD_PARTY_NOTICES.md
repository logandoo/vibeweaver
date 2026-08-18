# Third-Party Materials

This repository is MIT-licensed (see [LICENSE](LICENSE)). The third-party materials
below are used under their own terms; they are not relicensed merely by appearing
in this repository.

## J-Space Cognition Suite V3.6 — Apache License 2.0

- Source: <https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6>
- Author: Tiger3807861189 (<https://space.bilibili.com/3494375382321675>)
- License: Apache License 2.0 — full text at [`licenses/Apache-2.0.txt`](licenses/Apache-2.0.txt)

What we took, sorted by how much we took:

### Verbatim code (license obligations attach)

- **`vibeweaver/scripts/assert_artifacts.py`, group 13 — the `CLAIM` regex**
  (the English + Chinese claim-word list) is copied unchanged from
  `j-space/scripts/jspace.py` (`ship` mode). The file carries a prominent
  notice in its header comment.

### Modified code (derivative portions, license obligations attach)

- **The `COVERAGE` regex and the `claim_without_coverage` detection logic** in the
  same file are derived from the same source with modifications: scoped to
  `tests/verification_log.md`, added iter/baseline structured-line exemptions,
  Python standard library only, reworded messages.

### Ideas and protocols (not copyrightable; attribution is courtesy)

Re-expressed in our own words in `SKILL.md` and `TESTING_PROTOCOLS.md`:
the untrusted-content asymmetry rule (COV-11 / §2 Step 0.4), stall
parameterization, differential testing against an independent reference,
dual-path reconciliation, the write-once consistency hub (C3), post-gap
re-entry (§3.3), and the mechanized stall observation in
`vibeweaver/vibeweaver-gate.js`. The single-entry + on-demand-module layout
discipline was also informed by that project's architecture.

For the code portions above, the upstream Apache-2.0 terms apply: keep the
notices, ship the license text, and state modifications. If you redistribute
those portions, carry this file (or equivalent attribution) with them.
