#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server/daemon).
# Nothing to stop — pid-file kill pattern (APPENDIX §A6) applies only to
# services started by start.sh; here start.sh runs a foreground smoke check.
echo "stop: no service running (pure library, no daemon) — OK"
