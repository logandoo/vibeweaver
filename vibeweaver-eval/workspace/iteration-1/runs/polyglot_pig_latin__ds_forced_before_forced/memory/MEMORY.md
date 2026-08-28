# Project Memory Index

## Project Context
- [Pig Latin exercise contract](project_pig_latin.md) — Exercism canonical spec; only pig_latin.py may be changed; no test files; graded by hidden canonical tests

## Fix Tracking
- ⏳ [Fix: Pig Latin translate](fix_pig_latin.md) — single-pass prefix scan; 23/23 canonical cases pass locally; awaiting hidden-test grade

## Key Dependencies & Conventions
- `pig_latin.py` exposes only `translate(text)` (hidden test imports only that name)
- Vowels = `aeiou`; `y` is a consonant at word start, a vowel elsewhere; `u` after `q` stays in the moved prefix
- workflow artifacts (tests/, script/, memory/) must not be mistaken for test files
