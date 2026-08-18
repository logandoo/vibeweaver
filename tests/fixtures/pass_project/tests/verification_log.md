## Task: login timeout repair | 2026-08-19
- Baseline verified GREEN
- iter 1 FAIL: criterion #1 (session expires at 5 min) | diagnosis: auth-service TTL 300s mismatches gateway 3600s | changed: backend/app/auth/config.py
- iter 2 FAIL: criterion #2 (no fresh session after expiry) | diagnosis: refresh endpoint never called when 401 returned | changed: frontend/src/services/api.ts
- iter 3 PASS: all criteria (evidence: tests/shot.png, 3/3)

```
RED evidence (iter 1, pasted watched failure):
AssertionError: expected status_code 401, got 200 — ttl verified path mismatch
```

- endpoint sweep: all 3 auth endpoints re-tested, coverage 3/3, trace tests/workflows/flow.trace.log
