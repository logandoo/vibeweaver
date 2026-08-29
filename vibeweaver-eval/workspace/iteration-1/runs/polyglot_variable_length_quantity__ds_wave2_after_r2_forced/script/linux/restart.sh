#!/usr/bin/env bash
set -e
bash "$(dirname "$0")/stop.sh"
bash "$(dirname "$0")/start.sh"
