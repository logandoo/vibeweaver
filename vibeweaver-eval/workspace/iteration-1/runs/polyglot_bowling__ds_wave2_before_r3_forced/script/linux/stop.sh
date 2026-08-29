#!/usr/bin/env bash
# stop.sh — kills only the PID recorded by start.sh; never a pattern-kill
# (HOST-SAFETY: on shared hosts, pkill patterns kill unrelated processes).
cd "$(dirname "$0")/../.."
if [ -f .pid ]; then
  kill "$(cat .pid)" 2>/dev/null || true
  rm -f .pid
  echo "stopped"
else
  echo "no .pid file — nothing to stop"
fi
