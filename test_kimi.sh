#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Missing .venv. Run the project setup first." >&2
    exit 1
fi

if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
    if [[ ! -t 0 ]]; then
        echo "Run ./test_kimi.sh from a normal interactive terminal." >&2
        exit 1
    fi
    read -rsp "Kimi API key: " MOONSHOT_API_KEY
    echo
    export MOONSHOT_API_KEY
fi

exec .venv/bin/python test_kimi_api.py
