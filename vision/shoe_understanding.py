"""Gemini-backed semantic shoe understanding for the live YOLO tracker.

YOLO remains responsible for fast local detection and ByteTrack identity.  This
module is deliberately a slower, optional second stage: it describes a stable
shoe crop and compares several stable crops for likely left/right pairs.  Its
output is advisory; callers must apply their own calibration and pickup-safety
checks before commanding any hardware.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

import cv2
import numpy as np


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
POINT_NAMES = ("toe", "heel", "opening_center", "hook_target")


def _point_schema() -> dict[str, Any]:
    return {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}


SHOE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "shoe_type": {"type": "string", "enum": ["sneaker", "slipper", "sandal", "boot", "unknown"]},
        "appearance_id": {"type": "string", "description": "Short visual description; do not invent a brand."},
        "side": {"type": "string", "enum": ["left", "right", "unknown"]},
        "toe": _point_schema(),
        "heel": _point_schema(),
        "opening_center": _point_schema(),
        "hook_target": _point_schema(),
        "opening_visible": {"type": "boolean"},
        "shoe_upright": {"type": "boolean"},
        "pickup_safe": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": [
        "shoe_type", "appearance_id", "side", "toe", "heel", "opening_center", "hook_target",
        "opening_visible", "shoe_upright", "pickup_safe", "confidence",
    ],
}


PAIR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pairs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "track_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
                    "confidence": {"type": "number"},
                },
                "required": ["track_ids", "confidence"],
            },
        }
    },
    "required": ["pairs"],
}


def _gemini_request(parts: list[dict[str, Any]], schema: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema},
    }
    request = urllib.request.Request(
        f"{GEMINI_API_URL}/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Gemini API HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:300]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Gemini API connection error: {error.reason}") from error
    try:
        return json.loads(reply["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Gemini returned no usable JSON response.") from error


def _image_part(image: np.ndarray) -> dict[str, Any]:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Could not encode image for Gemini.")
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(encoded.tobytes()).decode("ascii")}}


def _normalised_point(value: Any, name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, (int, float)) for item in value):
        raise RuntimeError(f"Gemini returned invalid {name} point.")
    return [max(0.0, min(1000.0, float(item))) for item in value]


def analyse_shoe(crop: np.ndarray, api_key: str, model: str) -> dict[str, Any]:
    """Return semantic labels and normalised landmarks for one overhead shoe crop."""
    prompt = (
        "This is one shoe seen from directly overhead. Identify its type (sneaker, slipper, sandal, boot, or unknown) "
        "and whether it is a left or right shoe. Locate toe, heel, the centre of the usable opening, and a conservative "
        "hook target inside that opening. A sneaker hook target is near the tongue/collar opening; an open-back slipper "
        "target is near its rear entrance. Coordinates are normalised in this crop: [0,0] is top-left and [1000,1000] is "
        "bottom-right. Set pickup_safe=false if the opening is hidden, shoe is upside down, overlapping, or a hook target "
        "cannot be determined reliably. Use unknown rather than guessing."
    )
    answer = _gemini_request([{"text": prompt}, _image_part(crop)], SHOE_SCHEMA, api_key, model)
    for name in POINT_NAMES:
        answer[name] = _normalised_point(answer.get(name), name)
    if answer.get("shoe_type") not in {"sneaker", "slipper", "sandal", "boot", "unknown"}:
        raise RuntimeError("Gemini returned an invalid shoe type.")
    if answer.get("side") not in {"left", "right", "unknown"}:
        raise RuntimeError("Gemini returned an invalid left/right label.")
    answer["confidence"] = max(0.0, min(1.0, float(answer.get("confidence", 0))))
    for name in ("opening_visible", "shoe_upright", "pickup_safe"):
        if not isinstance(answer.get(name), bool):
            raise RuntimeError(f"Gemini returned invalid {name}.")
    answer["appearance_id"] = str(answer.get("appearance_id", "unknown"))[:100]
    return answer


def make_contact_sheet(crops: dict[int, np.ndarray], cell_size: int = 240) -> np.ndarray:
    """Create a labelled image so Gemini can compare several shoes in one request."""
    if len(crops) < 2:
        raise ValueError("Pair analysis needs at least two shoe crops.")
    columns = 2
    rows = (len(crops) + columns - 1) // columns
    sheet = np.full((rows * cell_size, columns * cell_size, 3), 30, dtype=np.uint8)
    for index, (track_id, crop) in enumerate(sorted(crops.items())):
        scale = min((cell_size - 32) / crop.shape[1], (cell_size - 48) / crop.shape[0])
        resized = cv2.resize(crop, (max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale))))
        x = (index % columns) * cell_size + (cell_size - resized.shape[1]) // 2
        y = (index // columns) * cell_size + 30 + (cell_size - 30 - resized.shape[0]) // 2
        sheet[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
        cv2.putText(sheet, f"TRACK {track_id}", ((index % columns) * cell_size + 8, (index // columns) * cell_size + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return sheet


def analyse_pairs(crops: dict[int, np.ndarray], api_key: str, model: str) -> list[dict[str, Any]]:
    """Return only high-level pair hypotheses for labelled track crops."""
    track_ids = sorted(crops)
    prompt = (
        "This contact sheet contains separate overhead shoe crops labelled TRACK <id>. Determine which two tracks are a "
        "physical left/right pair. Match material, colour, silhouette, sole, laces and complementary left/right geometry. "
        f"Only use these IDs: {track_ids}. Return a pair only when you have clear evidence; do not pair two left shoes or "
        "two right shoes. A track may remain unmatched."
    )
    answer = _gemini_request([{"text": prompt}, _image_part(make_contact_sheet(crops))], PAIR_SCHEMA, api_key, model)
    pairs: list[dict[str, Any]] = []
    used: set[int] = set()
    for pair in answer.get("pairs", []):
        ids = pair.get("track_ids") if isinstance(pair, dict) else None
        if not isinstance(ids, list) or len(ids) != 2 or not all(isinstance(item, int) for item in ids):
            continue
        first, second = ids
        if first == second or first not in crops or second not in crops or first in used or second in used:
            continue
        confidence = max(0.0, min(1.0, float(pair.get("confidence", 0))))
        pairs.append({"track_ids": [first, second], "confidence": confidence})
        used.update((first, second))
    return pairs


def draw_understanding(frame: np.ndarray, result: dict[str, Any]) -> None:
    """Draw a validated, image-coordinate semantic result from ``analyse_shoe``."""
    toe = tuple(round(value) for value in result["toe"])
    heel = tuple(round(value) for value in result["heel"])
    target = tuple(round(value) for value in result["hook_target"])
    safe = result["pickup_safe"] and result["opening_visible"] and result["shoe_upright"]
    color = (0, 255, 0) if safe else (0, 165, 255)
    cv2.arrowedLine(frame, heel, toe, color, 3, tipLength=0.18)
    cv2.circle(frame, target, 7, (255, 0, 255) if safe else (0, 0, 255), -1)
    label = f"{result['shoe_type']} {result['side']} | hook {'OK' if safe else 'CHECK'} {result['confidence']:.2f}"
    cv2.putText(frame, label, (target[0] + 8, target[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
