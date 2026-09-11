#!/usr/bin/env bash
# Fetch the study inputs from the Internet Archive collection and verify them.
# Usage: inputs/fetch.sh            (from the repository root)
set -euo pipefail
cd "$(dirname "$0")/kirkshooting"
BASE="https://archive.org/download/kirkshooting"
for f in 2.MOV 2.mp4 16.mp4 7.mp4; do
  if [ ! -f "$f" ]; then
    echo "fetching $f"
    curl -L --fail -o "$f" "$BASE/$f"
  fi
done
shasum -a 256 -c SHA256SUMS
