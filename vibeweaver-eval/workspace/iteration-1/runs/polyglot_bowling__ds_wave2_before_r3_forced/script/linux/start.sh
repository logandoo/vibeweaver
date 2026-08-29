#!/usr/bin/env bash
# start.sh — this exercise is a pure-Python logic module with no long-running
# service; this entry point runs a one-shot smoke run of bowling.py and
# records its PID to .pid (COV-2 / APPENDIX A6 pattern).
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p logs
nohup python3 -c "from bowling import BowlingGame; g=BowlingGame(); [g.roll(r) for r in [10]*12]; assert g.score()==300; print('bowling smoke ok: perfect game = 300')" > logs/smoke.log 2>&1 &
echo $! > .pid
echo "started (pid $(cat .pid)) — see logs/smoke.log"
