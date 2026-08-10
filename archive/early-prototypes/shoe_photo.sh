#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Missing .venv. Run the project setup first." >&2
    exit 1
fi

if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
    if [[ ! -t 0 ]]; then
        echo "Run ./shoe_photo.sh from a normal interactive terminal." >&2
        exit 1
    fi
    read -rsp "Kimi API key: " MOONSHOT_API_KEY
    echo
    if [[ -z "$MOONSHOT_API_KEY" ]]; then
        echo "No API key entered." >&2
        exit 1
    fi
    export MOONSHOT_API_KEY
fi

exec .venv/bin/python webcam_kimi_shoe_detector.py "$@"
