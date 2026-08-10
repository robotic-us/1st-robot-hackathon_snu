#!/usr/bin/env bash
# Launch the webcam tracker with the JetPack 6 / CUDA 12.6 environment.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/.jetson-venv/bin/python" "$SCRIPT_DIR/live_shoe_tracker.py" --device 0 "$@"
