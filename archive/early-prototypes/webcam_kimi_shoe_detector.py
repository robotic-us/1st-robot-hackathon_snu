#!/usr/bin/env python3
"""Detect shoes, pairs, left/right sides, and toe direction in one webcam frame."""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path

import cv2


BASE_URL = "https://api.moonshot.ai/v1"
MODEL = "kimi-k3"
PAIR_COLORS = [
    (0, 220, 0),      # green
    (0, 165, 255),    # orange
    (255, 100, 0),    # blue
    (255, 0, 255),    # magenta
    (0, 255, 255),    # yellow
    (255, 255, 0),    # cyan
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--output-dir", type=Path, default=Path("data/kimi_shoe_photos"))
    return parser.parse_args()


def capture_one_frame(camera_index: int, width: int, height: int):
    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera {camera_index}.")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    print("Camera ready. Press Space or Enter to take one picture; Q/Esc cancels.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera returned no frame.")
            preview = frame.copy()
            cv2.putText(
                preview,
                "SPACE/Enter: capture one photo | Q: cancel",
                (16, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            cv2.imshow("Kimi shoe photo", preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                return None
            if key in (ord(" "), 10, 13):
                return frame.copy()
    finally:
        camera.release()
        cv2.destroyAllWindows()


def frame_jpeg_bytes(frame) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Could not encode the camera frame.")
    return encoded.tobytes()


def frame_data_url(frame) -> str:
    payload = base64.b64encode(frame_jpeg_bytes(frame)).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


def parse_shoe_response(
    output: str,
    parsed_response: object = None,
    finish_reason: object = None,
) -> list[dict[str, object]]:
    """Read a structured model response, tolerating a trailing JSON comma."""
    if isinstance(parsed_response, dict):
        shoes = parsed_response.get("shoes", [])
        if isinstance(shoes, list):
            return shoes
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as error:
        # Some model responses may contain a trailing comma despite JSON mode.
        repaired_output = re.sub(r",\s*([}\]])", r"\1", output)
        try:
            parsed = json.loads(repaired_output)
        except json.JSONDecodeError as repaired_error:
            if str(finish_reason).upper().endswith(("MAX_TOKENS", "LENGTH")):
                raise RuntimeError(
                    "Kimi ran out of output tokens before completing its response."
                ) from repaired_error
            raise RuntimeError(
                "Kimi returned malformed structured output. Please capture the frame again."
            ) from repaired_error
    shoes = parsed.get("shoes", [])
    if not isinstance(shoes, list):
        raise RuntimeError("Kimi's response did not contain a shoes list.")
    return shoes


def ask_kimi_for_shoes(frame, api_key: str) -> list[dict[str, object]]:
    try:
        from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI
    except ImportError as error:
        raise RuntimeError("Run: .venv/bin/python -m pip install -r requirements-api.txt") from error

    shoe_schema = {
        "type": "object",
        "properties": {
            "shoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "pair_id": {"type": "string"},
                        "side": {"type": "string", "enum": ["left", "right", "unknown"]},
                        "side_confidence": {"type": "number"},
                        "confidence": {"type": "number"},
                        "x_min": {"type": "integer"},
                        "y_min": {"type": "integer"},
                        "x_max": {"type": "integer"},
                        "y_max": {"type": "integer"},
                        "toe_x": {"type": "integer"},
                        "toe_y": {"type": "integer"},
                        "heel_x": {"type": "integer"},
                        "heel_y": {"type": "integer"},
                    },
                    "required": [
                        "label", "pair_id", "side", "side_confidence", "confidence",
                        "x_min", "y_min", "x_max", "y_max", "toe_x", "toe_y", "heel_x", "heel_y",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["shoes"],
        "additionalProperties": False,
    }
    prompt = (
        "Detect every visible physical shoe in this image. Return one item per shoe and no other objects. "
        "Group shoes that visually belong to the same left/right pair using the same pair_id. Use concise, "
        "frame-local IDs such as pair_1, pair_2; use a unique pair_id for an unpaired shoe. Determine whether "
        "each shoe is left or right from its shape, and use unknown only when that cannot be determined. "
        "Draw a tight bounding box using integer coordinates normalized from 0 to 1000 across the FULL image: "
        "x increases left-to-right and y increases top-to-bottom. Use 0 for the left/top edge and 1000 for "
        "the right/bottom edge. Also give the center of the toe and heel in the same normalized coordinates; "
        "they must identify the shoe's long axis. Describe each shoe briefly in label. "
        "If there are no shoes, return an empty shoes array."
    )
    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            reasoning_effort="low",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": frame_data_url(frame)}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "shoe_boxes", "strict": True, "schema": shoe_schema},
            },
            max_completion_tokens=8192,
        )
    except AuthenticationError:
        raise RuntimeError("Kimi rejected the API key. Enter a valid Moonshot API key.") from None
    except APIConnectionError:
        raise RuntimeError("Could not connect to the Kimi API. Check the internet connection.") from None
    except APIStatusError as error:
        raise RuntimeError(f"Kimi API request failed ({error.status_code}): {error.message}") from None
    output = response.choices[0].message.content
    if not output:
        raise RuntimeError("Kimi returned no final answer.")
    return parse_shoe_response(output, finish_reason=response.choices[0].finish_reason)


def normalized_box_to_pixels(shoe: dict[str, object], width: int, height: int) -> tuple[int, int, int, int]:
    values = [float(shoe[name]) for name in ("x_min", "y_min", "x_max", "y_max")]
    x1 = round(max(0.0, min(1000.0, values[0])) * width / 1000.0)
    y1 = round(max(0.0, min(1000.0, values[1])) * height / 1000.0)
    x2 = round(max(0.0, min(1000.0, values[2])) * width / 1000.0)
    y2 = round(max(0.0, min(1000.0, values[3])) * height / 1000.0)
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def normalized_point_to_pixels(x: object, y: object, width: int, height: int) -> tuple[int, int]:
    """Convert a normalized Kimi point to a pixel point within the image."""
    point_x = round(max(0.0, min(1000.0, float(x))) * width / 1000.0)
    point_y = round(max(0.0, min(1000.0, float(y))) * height / 1000.0)
    return point_x, point_y


def shoe_angle_degrees(toe_px: tuple[int, int], heel_px: tuple[int, int]) -> float | None:
    """Return heel-to-toe direction in image coordinates: right=0°, down=90°."""
    dx = toe_px[0] - heel_px[0]
    dy = toe_px[1] - heel_px[1]
    if dx == 0 and dy == 0:
        return None
    return round(math.degrees(math.atan2(dy, dx)) % 360.0, 1)


def pair_colors(shoes: list[dict[str, object]]) -> dict[str, tuple[int, int, int]]:
    """Give each frame-local pair ID a distinct, repeatable box color."""
    colors: dict[str, tuple[int, int, int]] = {}
    for shoe in shoes:
        pair_id = str(shoe.get("pair_id", "unpaired"))
        if pair_id not in colors:
            colors[pair_id] = PAIR_COLORS[len(colors) % len(PAIR_COLORS)]
    return colors


def annotate(frame, shoes: list[dict[str, object]]):
    result = frame.copy()
    height, width = result.shape[:2]
    colors = pair_colors(shoes)
    for index, shoe in enumerate(shoes, start=1):
        x1, y1, x2, y2 = normalized_box_to_pixels(shoe, width, height)
        confidence = max(0.0, min(1.0, float(shoe.get("confidence", 0.0))))
        side_confidence = max(0.0, min(1.0, float(shoe.get("side_confidence", 0.0))))
        pair_id = str(shoe.get("pair_id", "unpaired"))
        color = colors[pair_id]
        toe_px = normalized_point_to_pixels(shoe["toe_x"], shoe["toe_y"], width, height)
        heel_px = normalized_point_to_pixels(shoe["heel_x"], shoe["heel_y"], width, height)
        angle_deg = shoe_angle_degrees(toe_px, heel_px)
        angle_label = "angle unknown" if angle_deg is None else f"{angle_deg:.1f} deg"
        label = f"{pair_id} | {shoe.get('side', 'unknown')} ({side_confidence:.0%}) | {angle_label}"
        cv2.rectangle(result, (x1, y1), (x2, y2), color, 3)
        cv2.arrowedLine(result, heel_px, toe_px, color, 3, tipLength=0.18)
        text_y = max(24, y1 - 8)
        cv2.putText(result, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        shoe["box_px"] = [x1, y1, x2, y2]
        shoe["toe_px"] = list(toe_px)
        shoe["heel_px"] = list(heel_px)
        shoe["angle_deg"] = angle_deg
    return result


def save_result(output_dir: Path, frame, annotated) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = output_dir / f"{stamp}_raw.jpg"
    annotated_path = output_dir / f"{stamp}_boxed.jpg"
    cv2.imwrite(str(raw_path), frame)
    cv2.imwrite(str(annotated_path), annotated)
    return annotated_path


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        raise SystemExit("MOONSHOT_API_KEY is not set. Start this program with ./shoe_photo.sh")
    frame = capture_one_frame(args.camera, args.width, args.height)
    if frame is None:
        print("Cancelled.")
        return
    print("Picture captured. Asking Kimi to locate shoes, pairs, sides, and direction...")
    try:
        shoes = ask_kimi_for_shoes(frame, api_key)
    except RuntimeError as error:
        raise SystemExit(f"Error: {error}") from None
    annotated = annotate(frame, shoes)
    annotated_path = save_result(args.output_dir, frame, annotated)
    print(f"Kimi found {len(shoes)} shoe(s) in {len(pair_colors(shoes))} visual pair group(s).")
    print(f"Boxed image: {annotated_path}")
    cv2.imshow("Kimi shoe result - press any key", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
