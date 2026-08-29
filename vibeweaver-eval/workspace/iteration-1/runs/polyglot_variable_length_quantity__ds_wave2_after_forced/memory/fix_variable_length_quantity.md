# fix: multi-value encode ordering (variable_length_quantity.py)

## Symptom
`encode([0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000])` produced value
groups in reverse order (2 hidden canonical tests failed: two_multi_byte,
many_multi_byte). Single-value cases passed.

## Diagnosis
`encoded.insert(0, number % 0x80 + 0x80)` prepended each higher-order chunk at
the front of the GLOBAL output list. After finishing number k, the chunks for
number k+1 were inserted before all of number k's chunks, reversing value order.

## Fix
Collect each number's chunks in a local `chunks` list (insert at index 0 within
that list), then `encoded.extend(chunks)` for each input number.

## Lesson
When assembling per-item groups, scope the `insert(0, …)` buffer to the item,
not the accumulator. Verified via canonical suite 26/26 + differential
roundtrip checks (tests/canonical_suite.log, tests/differential_check.log).
