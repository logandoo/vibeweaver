# Auto Decisions (AUTO mode)

D-1 | trigger: approach choice for VLQ codec | options: (A) shift-accumulate over 7-bit groups big-endian; (B) bytearray + mask assembly | chosen: A | why: fewer allocations, standard MIDI VLQ algorithm, directly matches the prompt's worked examples | revisit-if: input domain expands to signed/streaming values

D-2 | trigger: tests/assert_artifacts.py unavailable (skill scripts/ dir absent) | options: (A) hand-write the canonical assertion script from memory; (B) skip artifact-assertion script | chosen: B | why: user requirement forbids creating test files; the skill's canonical script is not present to copy | revisit-if: skill scripts/ becomes available
