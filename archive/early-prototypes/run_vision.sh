#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Missing .venv. Run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-api.txt" >&2
    exit 1
fi

if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
    if [[ -t 0 ]]; then
        read -rsp "Kimi API key: " MOONSHOT_API_KEY
        echo
        export MOONSHOT_API_KEY
    else
        echo "MOONSHOT_API_KEY is not set, and this command has no interactive terminal for a secure prompt." >&2
        echo "Open a terminal, export MOONSHOT_API_KEY, then run ./run_vision.sh again." >&2
        exit 1
    fi
fi

exec .venv/bin/python vision_shoe_test.py "$@"
