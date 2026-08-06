#!/usr/bin/env python3
"""Capture one camera frame and ask Kimi K3 to draw shoe bounding boxes."""

from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime
from pathlib import Path

import cv2


BASE_URL = "https://api.moonshot.ai/v1"
MODEL = "kimi-k3"


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


def frame_data_url(frame) -> str:
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Could not encode the camera frame.")
    payload = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


def ask_kimi_for_shoes(frame, api_key: str) -> list[dict[str, object]]:
    try:
        from openai import OpenAI
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
                        "side": {"type": "string", "enum": ["left", "right", "unknown"]},
                        "confidence": {"type": "number"},
                        "x_min": {"type": "integer"},
                        "y_min": {"type": "integer"},
                        "x_max": {"type": "integer"},
                        "y_max": {"type": "integer"},
                    },
                    "required": ["label", "side", "confidence", "x_min", "y_min", "x_max", "y_max"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["shoes"],
        "additionalProperties": False,
    }
    prompt = (
        "Detect every visible physical shoe in this image. Return one item per shoe and no other objects. "
        "Draw a tight bounding box using integer coordinates normalized from 0 to 1000 across the FULL image: "
        "x increases left-to-right and y increases top-to-bottom. Use 0 for the left/top edge and 1000 for "
        "the right/bottom edge. Describe each shoe briefly in label. If left versus right cannot be seen, use unknown. "
        "If there are no shoes, return an empty shoes array."
    )
    response = OpenAI(api_key=api_key, base_url=BASE_URL).chat.completions.create(
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
        max_completion_tokens=2048,
    )
    output = response.choices[0].message.content
    if not output:
        raise RuntimeError("Kimi returned no final answer.")
    parsed = json.loads(output)
    return parsed.get("shoes", [])


def normalized_box_to_pixels(shoe: dict[str, object], width: int, height: int) -> tuple[int, int, int, int]:
    values = [float(shoe[name]) for name in ("x_min", "y_min", "x_max", "y_max")]
    x1 = round(max(0.0, min(1000.0, values[0])) * width / 1000.0)
    y1 = round(max(0.0, min(1000.0, values[1])) * height / 1000.0)
    x2 = round(max(0.0, min(1000.0, values[2])) * width / 1000.0)
    y2 = round(max(0.0, min(1000.0, values[3])) * height / 1000.0)
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def annotate(frame, shoes: list[dict[str, object]]):
    result = frame.copy()
    height, width = result.shape[:2]
    for index, shoe in enumerate(shoes, start=1):
        x1, y1, x2, y2 = normalized_box_to_pixels(shoe, width, height)
        confidence = max(0.0, min(1.0, float(shoe.get("confidence", 0.0))))
        label = f"{index}: {shoe.get('label', 'shoe')} | {shoe.get('side', 'unknown')} | {confidence:.0%}"
        cv2.rectangle(result, (x1, y1), (x2, y2), (0, 255, 0), 3)
        text_y = max(24, y1 - 8)
        cv2.putText(result, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        shoe["box_px"] = [x1, y1, x2, y2]
    return result


def save_result(output_dir: Path, frame, annotated, shoes: list[dict[str, object]]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = output_dir / f"{stamp}_raw.jpg"
    annotated_path = output_dir / f"{stamp}_boxed.jpg"
    json_path = output_dir / f"{stamp}_shoes.json"
    cv2.imwrite(str(raw_path), frame)
    cv2.imwrite(str(annotated_path), annotated)
    json_path.write_text(json.dumps({"model": MODEL, "shoes": shoes}, indent=2), encoding="utf-8")
    return annotated_path, json_path


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        raise SystemExit("MOONSHOT_API_KEY is not set. Start this program with ./shoe_photo.sh")
    frame = capture_one_frame(args.camera, args.width, args.height)
    if frame is None:
        print("Cancelled.")
        return
    print("Picture captured. Asking Kimi to locate shoes...")
    shoes = ask_kimi_for_shoes(frame, api_key)
    annotated = annotate(frame, shoes)
    annotated_path, json_path = save_result(args.output_dir, frame, annotated, shoes)
    print(f"Kimi found {len(shoes)} shoe(s).")
    print(f"Boxed image: {annotated_path}")
    print(f"JSON result: {json_path}")
    cv2.imshow("Kimi shoe result - press any key", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
