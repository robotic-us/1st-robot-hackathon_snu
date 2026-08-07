#!/usr/bin/env bash
# Run the tracker with this project's JetPack 6 / CUDA 12.6 environment.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/live_shoe_tracker.py" --device 0 "$@"
