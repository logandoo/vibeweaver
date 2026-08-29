#!/usr/bin/env bash
set -e
if [ -f .vlq.pid ]; then
  kill "$(cat .vlq.pid)" 2>/dev/null || true
  rm -f .vlq.pid
fi
echo "VLQ library task: no long-running service; nothing to stop"
