#!/usr/bin/env bash
set -euo pipefail

preset="${1:-}"
if [[ -z "$preset" ]]; then
  echo "Usage: apply.sh <preset>" >&2
  exit 2
fi

monctl preset "$preset"
#notify-send "MonCtl" "Applied preset: $preset" || true

