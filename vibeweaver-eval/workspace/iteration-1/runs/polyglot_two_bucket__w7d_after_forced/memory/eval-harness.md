---
type: reference
topic: eval-harness
trust: verified
---

# Eval Harness

- Deliverable is a single module (`two_bucket.py`); hidden oracle is copied in
  and run with `unittest` from an isolated dir so no test file lands here.
- `python3 tests/assert_artifacts.py --existing --profile library` gates the
  evidence artifacts.
