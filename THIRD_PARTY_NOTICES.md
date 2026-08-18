# Third-Party Materials

This repository is MIT-licensed (see [LICENSE](LICENSE)). The third-party materials
below are used under their own terms; they are not relicensed merely by appearing
in this repository.

## J-Space Cognition Suite V3.6 — Apache License 2.0

- Source: <https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6>
- Author: Tiger3807861189 (<https://space.bilibili.com/3494375382321675>)
- License: Apache License 2.0 — <https://www.apache.org/licenses/LICENSE-2.0>

Adapted materials in this repository:

1. **`vibeweaver/scripts/assert_artifacts.py`, group 13 (claim-without-coverage lint).**
   The claim/coverage detection machinery (CLAIM/COVERAGE regex approach,
   markdown-structure exemption, fenced-block handling) is ported and adapted from
   `j-space/scripts/jspace.py` (`ship` mode). Modifications by the vibeweaver authors:
   scoped to `tests/verification_log.md`, iter/baseline structured-line exemptions,
   Python standard library only, different message wording. A prominent modification
   notice is carried in the file's header comment.

2. **Protocol mechanisms** adapted (re-expressed, not copied) into `SKILL.md` and
   `TESTING_PROTOCOLS.md`: untrusted-content asymmetry rule (COV-11 / §2 Step 0.4),
   stall parameterization, differential testing against an independent reference,
   dual-path reconciliation, the write-once consistency hub (C3), post-gap re-entry
   (§3.3), and the mechanized stall observation in `vibeweaver/vibeweaver-gate.js`.

Ideas and protocols are restated here; where code was ported, the upstream
Apache-2.0 terms govern that portion. If you redistribute the adapted portions,
carry this notice (or an equivalent attribution) with them.
