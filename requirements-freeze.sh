#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="requirements.txt"
OUTPUT_FILE="requirements-freeze.txt"

# Empty output file
> "$OUTPUT_FILE"

while IFS= read -r line; do
  # Strip comments (everything after '#')
  line="${line%%#*}"
  # Trim whitespace
  line="$(echo "$line" | xargs)"

  # Skip empty lines
  [[ -z "$line" ]] && continue

  # Remove version specifiers (==, >=, <=, ~=, >, <, etc.)
  name="$(echo "$line" | sed 's/[<>=!~].*//')"

  # Remove extras: package[inmem] -> package
  name="$(echo "$name" | sed 's/\[.*\]//')"

  # Trim again
  name="$(echo "$name" | xargs)"

  # Skip if still empty
  [[ -z "$name" ]] && continue

  # Get installed version
  version=$(python -m pip show "$name" 2>/dev/null | awk '/^Version: /{print $2}')

  if [[ -n "$version" ]]; then
    echo "$name==$version" | tee -a "$OUTPUT_FILE"
  else
    echo "⚠️ $name is not installed (skipping)" >&2
  fi

done < "$INPUT_FILE"
