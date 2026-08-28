#!/bin/sh
# No long-running service is started by this project (pure library module),
# so there is nothing to stop. Never use pattern-kill (host safety).
echo "stop.sh: no service running (pure library module); nothing to stop"
