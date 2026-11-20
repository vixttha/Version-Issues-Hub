#!/usr/bin/env bash
set -euo pipefail

output="$1/path with spaces.txt"
printf '%s\n' 'launcher-output' > "$output"
if [[ "$(cat "$output")" != 'launcher-output' ]]; then
    printf '%s\n' 'unexpected bytes at quoted output path' >&2
    exit 1
fi
