---
name: Fix Login Timeout
description: session TTL mismatch between auth service and gateway
type: fix
date: 2026-08-19
status: ⏳
commit: a1b2c3d
---

# Fix Login Timeout

**Root Cause:** TTL 300s vs 3600s.
**Correct Fix:** aligned to 1800s.
