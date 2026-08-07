#!/usr/bin/env bash
# Run the tracker with this project's JetPack 6 / CUDA 12.6 environment.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# This launcher deliberately reads API keys only from exported environment
# variables. That keeps credentials out of source files and command history.
# It also supplies the current real-only pose model unless --model is given.
has_model=false
for tracker_arg in "$@"; do
  if [[ "$tracker_arg" == "--model" ]]; then
    has_model=true
    break
  fi
done

default_args=()
if [[ "$has_model" == false ]]; then
  default_args=(--model /home/phorce/runs/pose/runs/shoe_pose_real_only_baseline/weights/best.pt)
fi

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/live_shoe_tracker.py" --device 0 "${default_args[@]}" "$@"
