#!/usr/bin/env bash
set -euo pipefail
"$(dirname "$0")/stop.sh" || true
"$(dirname "$0")/start.sh"
