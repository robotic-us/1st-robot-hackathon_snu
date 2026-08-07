#!/usr/bin/env python3
"""Create reviewable YOLO-pose labels for one-shoe photos using Gemini.

The API supplies a first pass only. Review every image in the generated
``review/`` folder before using the labels for training.

Example:
    export GEMINI_API_KEY='...'
    vision/.venv/bin/python scripts/label_real_shoes_gemini.py --limit 10
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import cv2


CLASS_ID = {
    "pair1_right": 0,
    "pair1_left": 1,
    "pair2_right": 2,
    "pair2_left": 3,
    "pair3_right": 4,
    "pair3_left": 5,
}

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "found": {"type": "BOOLEAN"},
        "confidence": {"type": "NUMBER"},
        "bbox": {
            "type": "OBJECT",
            "properties": {key: {"type": "NUMBER"} for key in ("x1", "y1", "x2", "y2")},
            "required": ["x1", "y1", "x2", "y2"],
        },
        "heel": {
            "type": "OBJECT",
            "properties": {key: {"type": "NUMBER"} for key in ("x", "y")},
            "required": ["x", "y"],
        },
        "toe": {
            "type": "OBJECT",
            "properties": {key: {"type": "NUMBER"} for key in ("x", "y")},
            "required": ["x", "y"],
        },
    },
    "required": ["found", "confidence", "bbox", "heel", "toe"],
}

PROMPT = """This is a fixed overhead photograph containing one shoe on a cardboard backdrop.
Annotate the visible shoe precisely. Return pixel coordinates in the ORIGINAL image coordinate system:
origin is top-left; x increases right; y increases down. bbox must tightly surround the entire visible shoe.
heel is the center of the rear-most end of the shoe; toe is the center of its front-most tip.
If the shoe cannot be identified confidently, set found false. Do not identify laces, the tongue, or shadows as toe/heel.
"""


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("real_shoes/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("real_shoes/gemini_first_pass"))
    parser.add_argument("--model", default="gemini-3.6-flash")
    parser.add_argument("--limit", type=int, default=0, help="Maximum new images to label (0 = all)")
    parser.add_argument("--delay", type=float, default=0.35, help="Seconds between requests")
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--overwrite", action="store_true", help="Reprocess images with existing labels")
    return parser.parse_args()


def image_paths(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"})


def request_annotation(image: Path, api_key: str, model: str) -> dict:
    mime_type = mimetypes.guess_type(image.name)[0] or "image/jpeg"
    body = {
        "contents": [{"parts": [
            {"text": PROMPT},
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image.read_bytes()).decode("ascii")}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA},
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.load(response)
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def point(data: dict, name: str, width: int, height: int) -> tuple[float, float]:
    value = data[name]
    return max(0.0, min(float(value["x"]), width - 1.0)), max(0.0, min(float(value["y"]), height - 1.0))


def yolo_label(data: dict, class_id: int, width: int, height: int) -> str:
    x1 = max(0.0, min(float(data["bbox"]["x1"]), width - 1.0))
    y1 = max(0.0, min(float(data["bbox"]["y1"]), height - 1.0))
    x2 = max(0.0, min(float(data["bbox"]["x2"]), width - 1.0))
    y2 = max(0.0, min(float(data["bbox"]["y2"]), height - 1.0))
    if x2 <= x1 or y2 <= y1:
        raise ValueError("invalid bounding box")
    heel_x, heel_y = point(data, "heel", width, height)
    toe_x, toe_y = point(data, "toe", width, height)
    return (
        f"{class_id} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
        f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f} "
        f"{heel_x / width:.6f} {heel_y / height:.6f} 2 {toe_x / width:.6f} {toe_y / height:.6f} 2\n"
    )


def draw_review(image: Path, data: dict, destination: Path) -> None:
    frame = cv2.imread(str(image))
    if frame is None:
        raise ValueError("OpenCV could not read image")
    height, width = frame.shape[:2]
    x1 = round(max(0.0, min(float(data["bbox"]["x1"]), width - 1.0)))
    y1 = round(max(0.0, min(float(data["bbox"]["y1"]), height - 1.0)))
    x2 = round(max(0.0, min(float(data["bbox"]["x2"]), width - 1.0)))
    y2 = round(max(0.0, min(float(data["bbox"]["y2"]), height - 1.0)))
    heel = tuple(round(value) for value in point(data, "heel", width, height))
    toe = tuple(round(value) for value in point(data, "toe", width, height))
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
    cv2.arrowedLine(frame, heel, toe, (0, 255, 0), 3, tipLength=0.08)
    cv2.circle(frame, heel, 6, (255, 0, 0), -1)
    cv2.circle(frame, toe, 6, (0, 0, 255), -1)
    cv2.putText(frame, f"heel -> toe | Gemini {float(data['confidence']):.2f}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), frame)


def main() -> None:
    args = arguments()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY in your terminal; never put it in this script.")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative.")
    images = image_paths(args.input_dir)
    if not images:
        raise SystemExit(f"No images found under {args.input_dir}")
    processed = skipped = failed = 0
    for image in images:
        shoe = image.parent.name
        if shoe not in CLASS_ID:
            print(f"Skipping {image}: parent folder is not a known class.")
            skipped += 1
            continue
        label = args.output_dir / "labels" / shoe / f"{image.stem}.txt"
        review = args.output_dir / "review" / shoe / f"{image.stem}.jpg"
        record = args.output_dir / "responses" / shoe / f"{image.stem}.json"
        if label.exists() and not args.overwrite:
            skipped += 1
            continue
        if args.limit and processed >= args.limit:
            break
        try:
            data = request_annotation(image, api_key, args.model)
            frame = cv2.imread(str(image))
            if frame is None:
                raise ValueError("OpenCV could not read image")
            height, width = frame.shape[:2]
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps(data, indent=2), encoding="utf-8")
            if not data["found"] or float(data["confidence"]) < args.min_confidence:
                print(f"Needs manual label: {image} (found={data['found']}, confidence={data['confidence']})")
                failed += 1
            else:
                label.parent.mkdir(parents=True, exist_ok=True)
                label.write_text(yolo_label(data, CLASS_ID[shoe], width, height), encoding="utf-8")
                draw_review(image, data, review)
                processed += 1
                print(f"Labelled {processed}: {image}")
        except (KeyError, ValueError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as error:
            print(f"Failed {image}: {error}")
            failed += 1
        time.sleep(args.delay)
    print(f"Done. labelled={processed}, skipped={skipped}, needs-review-or-failed={failed}")


if __name__ == "__main__":
    main()
