# Decisions

- D-1 | trigger: canonical test seeds `random` and expects reset-after-reseed to yield a DIFFERENT name | options: (a) global used-names set so re-seed collision forces regeneration; (b) rely on randomness only | chosen: (a) persistent `_used_names` class set, reset does NOT release old name | why: guarantees uniqueness among existing robots AND satisfies the seeded-reset test deterministically | revisit-if: name space exhaustion (676,000 combos) — not a practical concern here.
