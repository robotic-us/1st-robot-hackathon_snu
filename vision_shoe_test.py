#!/usr/bin/env python3
"""Interactive webcam baseline for detecting shoes on a static floor.

The detector compares each frame with a captured empty-floor reference.  It is
intended for testing camera placement and lighting, not as the final shoe
instance-segmentation system.

Controls
--------
R  capture the current image as the empty-floor reference
S  save raw image, annotated image, mask, and candidate JSON
Q / Esc  quit
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError as error:
    missing_package = error.name or "a required package"
    raise SystemExit(
        f"Missing Python dependency: {missing_package}. "
        "In WSL, create a project virtual environment and install dependencies with: "
        "python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
    ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index (default: 0)")
    parser.add_argument("--width", type=int, default=1280, help="Requested capture width")
    parser.add_argument("--height", type=int, default=720, help="Requested capture height")
    parser.add_argument(
        "--min-area", type=float, default=1200, help="Minimum foreground contour area in pixels"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/vision_captures"), help="Directory for saved tests"
    )
    parser.add_argument("--camera-height-cm", type=float, default=65.0, help="Recorded metadata only")
    parser.add_argument("--horizontal-fov-deg", type=float, default=55.0, help="Recorded metadata only")
    return parser.parse_args()


def foreground_mask(frame: np.ndarray, background: np.ndarray) -> np.ndarray:
    """Return a clean binary mask of pixels that differ from the empty floor."""
    difference = cv2.absdiff(frame, background)
    gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(gray, 28, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)


def find_candidates(mask: np.ndarray, min_area: float) -> list[dict[str, float | list[float]]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[dict[str, float | list[float]]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        (center_x, center_y), (rect_width, rect_height), angle = cv2.minAreaRect(contour)
        # OpenCV's angle is tied to its chosen rectangle side.  Normalize the
        # major-axis direction to [0, 180), where 0 is horizontal.
        if rect_width < rect_height:
            angle += 90.0
        angle %= 180.0
        candidates.append(
            {
                "center_px": [round(center_x, 1), round(center_y, 1)],
                "orientation_deg": round(angle, 1),
                "area_px": round(area, 1),
                "size_px": [round(max(rect_width, rect_height), 1), round(min(rect_width, rect_height), 1)],
            }
        )
    return sorted(candidates, key=lambda candidate: float(candidate["area_px"]), reverse=True)


def annotate(frame: np.ndarray, mask: np.ndarray, candidates: list[dict[str, float | list[float]]]) -> np.ndarray:
    display = frame.copy()
    for index, candidate in enumerate(candidates, start=1):
        x, y = candidate["center_px"]  # type: ignore[misc]
        angle = float(candidate["orientation_deg"])
        center = (int(x), int(y))
        radians = math.radians(angle)
        endpoint = (int(x + 70 * math.cos(radians)), int(y + 70 * math.sin(radians)))
        cv2.circle(display, center, 5, (0, 255, 0), -1)
        cv2.arrowedLine(display, center, endpoint, (0, 255, 0), 2, tipLength=0.2)
        cv2.putText(display, f"candidate {index}: {angle:.0f} deg", (center[0] + 8, center[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.putText(display, f"Candidates: {len(candidates)}", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(display, "R: set empty floor | S: save test | Q/Esc: quit", (16, display.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    return display


def save_capture(output_dir: Path, frame: np.ndarray, annotated: np.ndarray, mask: np.ndarray, candidates: list[dict[str, float | list[float]]], args: argparse.Namespace) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stem = output_dir / stamp
    cv2.imwrite(str(stem.with_name(f"{stamp}_raw.jpg")), frame)
    cv2.imwrite(str(stem.with_name(f"{stamp}_annotated.jpg")), annotated)
    cv2.imwrite(str(stem.with_name(f"{stamp}_mask.png")), mask)
    record = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "camera": {"index": args.camera, "height_cm": args.camera_height_cm, "horizontal_fov_deg": args.horizontal_fov_deg},
        "frame_size_px": [int(frame.shape[1]), int(frame.shape[0])],
        "candidates": candidates,
    }
    stem.with_name(f"{stamp}_candidates.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved capture set: {stem}")


def main() -> None:
    args = parse_args()
    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera}. Try --camera 1 (or another index).")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    background: np.ndarray | None = None
    print("Camera opened. Clear the floor and press R to capture the empty-floor reference.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera returned no frame.")

            if background is None:
                mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                annotated = frame.copy()
                cv2.putText(annotated, "Clear floor, then press R to set reference", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
                candidates: list[dict[str, float | list[float]]] = []
            else:
                mask = foreground_mask(frame, background)
                candidates = find_candidates(mask, args.min_area)
                annotated = annotate(frame, mask, candidates)

            cv2.imshow("Shoe vision test", annotated)
            cv2.imshow("Foreground mask", mask)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key in (ord("r"), ord("R")):
                background = frame.copy()
                print("Empty-floor reference captured.")
            if key in (ord("s"), ord("S")):
                if background is None:
                    print("Capture an empty-floor reference first (R).")
                else:
                    save_capture(args.output_dir, frame, annotated, mask, candidates, args)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
