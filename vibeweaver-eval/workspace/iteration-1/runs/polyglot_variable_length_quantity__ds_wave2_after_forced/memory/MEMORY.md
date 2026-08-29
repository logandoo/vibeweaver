# Vibeweaver Memory — polyglot_variable_length_quantity

Project memory store (A6.1). Read at task start; appended on completion.

## Task context
- Benchmark task: `polyglot_variable_length_quantity` (run `polyglot_variable_length_quantity__ds_wave2_after_forced`)
- Verifier: direct read (non-web), COV-5 preset (library task, no UI/HTTP)
- Key facts: 32-bit unsigned VLQ encode/decode; grader = canonical Exercism hidden suite
  (`python3 -m pytest -q`); `decode` must raise `ValueError("incomplete sequence")`
  for truncation, including the `[0x80]` zero-residue case; empty inputs are valid.

## Topic files
- [fix_variable_length_quantity.md](fix_variable_length_quantity.md)

## Environment notes
- Companion docs (R1 TESTING_PROTOCOLS.md, R1b COMPLETION_GATE.md) live in the skill
  install dir; the eval config copy ships SKILL.md only.
- Shared git repo at the workspace root: commit strictly via pathspec scoped to this run dir.
