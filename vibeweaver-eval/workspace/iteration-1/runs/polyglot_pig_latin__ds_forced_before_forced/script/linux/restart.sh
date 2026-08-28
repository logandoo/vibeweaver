#!/bin/sh
# No service lifecycle: restart = re-run the start smoke check.
set -eu
"$(dirname "$0")/start.sh"
echo "restart.sh: complete (smoke check re-run)"
