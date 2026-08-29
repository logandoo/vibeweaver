# Project Memory Index

## Fix Tracking
- ⏳ [Fix: VLQ encode/decode implementation](fix_variable_length_quantity.md) — Implemented canonical VLQ encoding/decoding with 32-bit restriction (2026-08-29)

## Key Dependencies & Conventions
- Pure-Python standard-library module `variable_length_quantity.py` exposing `encode(numbers)` and `decode(bytes_)` (Exercism-style exercise)
- Exercise contract: inputs restricted to 32-bit unsigned integers (encode raises ValueError for out-of-range); decode raises ValueError("incomplete sequence") when the byte stream ends on a continuation byte
- Grading: hidden test `variable_length_quantity_test.py` (26 tests) run via `python3 -m pytest -q` (see workspace-iteration-1 tasks/.../task.json)
