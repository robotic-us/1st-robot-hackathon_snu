#!/usr/bin/env bash
# Run the live shoe-valet controller in the project's Jetson CUDA 12.6 env.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

exec "$PROJECT_DIR/vision/.venv/bin/python" "$PROJECT_DIR/operations/shoe_valet.py" --device 0 "$@"
