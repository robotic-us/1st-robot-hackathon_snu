#!/usr/bin/env python3
"""Minimal Kimi K3 API connection test."""

from __future__ import annotations

import getpass
import os
import sys

try:
    from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI
except ImportError as error:
    raise SystemExit(
        "Missing API client. Run: .venv/bin/python -m pip install -r requirements-api.txt"
    ) from error


BASE_URL = "https://api.moonshot.ai/v1"
MODEL = "kimi-k3"


def main() -> None:
    api_key = os.environ.get("MOONSHOT_API_KEY", "")
    if not api_key and sys.stdin.isatty():
        api_key = getpass.getpass("Kimi API key: ")
    elif not api_key:
        raise SystemExit(
            "MOONSHOT_API_KEY is not set and no interactive terminal is available. "
            "Run this test from a normal terminal."
        )
    if not api_key.strip():
        raise SystemExit("No API key was entered.")

    print(f"Calling {MODEL} at {BASE_URL} ...")
    try:
        response = OpenAI(api_key=api_key, base_url=BASE_URL).chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "This is an API connection test. Reply with exactly: KIMI_API_OK",
                }
            ],
            reasoning_effort="low",
            max_completion_tokens=256,
        )
    except AuthenticationError as error:
        raise SystemExit(f"Authentication failed: {error.message}") from error
    except APIStatusError as error:
        raise SystemExit(f"Kimi returned HTTP {error.status_code}: {error.message}") from error
    except APIConnectionError as error:
        raise SystemExit(f"Could not connect to Kimi: {error}") from error
    except Exception as error:
        raise SystemExit(f"API test failed: {type(error).__name__}: {error}") from error

    answer = response.choices[0].message.content
    print(f"Response: {answer!r}")
    if answer and "KIMI_API_OK" in answer:
        print("SUCCESS: the Kimi API key, endpoint, and model are working.")
        return
    print("CONNECTED: Kimi answered, but the response was not the requested test phrase.")


if __name__ == "__main__":
    main()
