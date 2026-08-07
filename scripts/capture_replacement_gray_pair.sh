#!/usr/bin/env bash
# Capture a replacement gray pair as pair4_left / pair4_right without mixing
# it into the earlier brown-shoe capture folder.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../vision/.venv/bin/python" "$SCRIPT_DIR/capture_real_shoes.py" \
  --target 75 \
  --output-dir "$SCRIPT_DIR/../real_shoes/replacement_gray_pair/raw" \
  "$@"
