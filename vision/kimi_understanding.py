"""Kimi-backed left/right and pair checks for stable local shoe tracks."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

import cv2
import numpy as np

from shoe_understanding import make_contact_sheet


KIMI_API_URL = "https://api.moonshot.ai/v1/chat/completions"


def _image_message(image: np.ndarray) -> dict[str, Any]:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Could not encode image for Kimi.")
    return {
        "type": "image_url",
        "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")},
    }


def _request(prompt: str, image: np.ndarray, api_key: str, model: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "temperature": 1,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, _image_message(image)]}],
    }
    request = urllib.request.Request(
        KIMI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        # K3 can spend noticeable time reasoning over a multi-image scene.
        with urllib.request.urlopen(request, timeout=60) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Kimi API HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:300]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Kimi API connection error: {error.reason}") from error
    try:
        content = reply["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Kimi returned no usable JSON response.") from error


def analyse_side(crop: np.ndarray, api_key: str, model: str) -> dict[str, Any]:
    """Classify side only; local YOLO remains the source for toe/heel points."""
    answer = _request(
        "This crop contains exactly one shoe seen from directly above. Determine whether it is a physical left shoe, "
        "right shoe, or unknown. Use the visible upper, toe shape, laces, sole and opening; do not infer from where it "
        "appears in the image. Return only JSON: {\"side\":\"left|right|unknown\",\"appearance_id\":\"short visual description\",\"confidence\":0.0}. "
        "Use unknown when the view is ambiguous.",
        crop, api_key, model,
    )
    if answer.get("side") not in {"left", "right", "unknown"}:
        raise RuntimeError("Kimi returned an invalid left/right label.")
    return {
        "side": answer["side"],
        "appearance_id": str(answer.get("appearance_id", "unknown"))[:100],
        "confidence": max(0.0, min(1.0, float(answer.get("confidence", 0)))),
    }


def analyse_pairs(crops: dict[int, np.ndarray], api_key: str, model: str) -> list[dict[str, Any]]:
    """Return high-confidence complementary left/right pairs from labelled crops."""
    track_ids = sorted(crops)
    answer = _request(
        "This contact sheet contains separate overhead shoe crops labelled TRACK <id>. Identify physical left/right pairs "
        "by matching material, colour, silhouette, laces, sole, and complementary geometry. Only use these IDs: "
        f"{track_ids}. Do not pair two left shoes or two right shoes. Return only JSON: "
        "{\"pairs\":[{\"track_ids\":[integer,integer],\"confidence\":0.0}]}. Return an empty list when uncertain.",
        make_contact_sheet(crops), api_key, model,
    )
    pairs: list[dict[str, Any]] = []
    used: set[int] = set()
    for pair in answer.get("pairs", []):
        ids = pair.get("track_ids") if isinstance(pair, dict) else None
        if not isinstance(ids, list) or len(ids) != 2 or not all(isinstance(item, int) for item in ids):
            continue
        first, second = ids
        if first == second or first not in crops or second not in crops or first in used or second in used:
            continue
        pairs.append({"track_ids": [first, second], "confidence": max(0.0, min(1.0, float(pair.get("confidence", 0))))})
        used.update((first, second))
    return pairs


def analyse_scene(crops: dict[int, np.ndarray], api_key: str, model: str) -> dict[str, Any]:
    """Jointly classify sides and pair hypotheses from two or more tracks."""
    track_ids = sorted(crops)
    answer = _request(
        "This contact sheet contains separate overhead shoe crops labelled TRACK <id>. For every shown track, identify "
        "whether it is a physical left shoe, right shoe, or unknown. Then identify physical left/right pairs by matching "
        "material, colour, silhouette, laces, sole, and complementary geometry. Only use these IDs: "
        f"{track_ids}. Do not pair two left shoes or two right shoes. Return only JSON: "
        "{\"sides\":[{\"track_id\":integer,\"side\":\"left|right|unknown\",\"confidence\":0.0}],"
        "\"pairs\":[{\"track_ids\":[integer,integer],\"confidence\":0.0}]}. Use unknown or an empty pairs list when uncertain.",
        make_contact_sheet(crops), api_key, model,
    )
    sides: dict[int, dict[str, Any]] = {}
    for item in answer.get("sides", []):
        if not isinstance(item, dict) or item.get("track_id") not in crops or item.get("side") not in {"left", "right", "unknown"}:
            continue
        track_id = item["track_id"]
        sides[track_id] = {
            "side": item["side"],
            "confidence": max(0.0, min(1.0, float(item.get("confidence", 0)))),
        }
    pairs: list[dict[str, Any]] = []
    used: set[int] = set()
    for pair in answer.get("pairs", []):
        ids = pair.get("track_ids") if isinstance(pair, dict) else None
        if not isinstance(ids, list) or len(ids) != 2 or not all(isinstance(item, int) for item in ids):
            continue
        first, second = ids
        if first == second or first not in crops or second not in crops or first in used or second in used:
            continue
        pairs.append({"track_ids": [first, second], "confidence": max(0.0, min(1.0, float(pair.get("confidence", 0))))})
        used.update((first, second))
    return {"sides": sides, "pairs": pairs}
