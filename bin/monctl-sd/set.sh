#!/usr/bin/env bash
set -euo pipefail

monitor="${1:-}"
input="${2:-}"

if [[ -z "$monitor" || -z "$input" ]]; then
  echo "Usage: set.sh <monitor> <input>" >&2
  exit 2
fi

monctl set "$monitor" "$input"
