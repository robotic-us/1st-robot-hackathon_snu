#!/usr/bin/env python3
"""Create a pixel-to-floor homography from four clicked workspace corners."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError as error:
    raise SystemExit("Install dependencies with: python3 -m pip install -r requirements.txt") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Overhead image showing the empty work area")
    parser.add_argument("--width-cm", type=float, required=True, help="Work-area width")
    parser.add_argument("--height-cm", type=float, required=True, help="Work-area height")
    parser.add_argument("--output", type=Path, default=Path("floor_calibration.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit(f"Could not read image: {args.image}")

    points: list[list[float]] = []
    display = image.copy()

    def on_mouse(event: int, x: int, y: int, _flags: int, _data: object) -> None:
        if event != cv2.EVENT_LBUTTONDOWN or len(points) >= 4:
            return
        points.append([float(x), float(y)])
        cv2.circle(display, (x, y), 6, (0, 255, 0), -1)
        cv2.putText(display, str(len(points)), (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    window = "Click TL, TR, BR, BL | R reset | Enter save | Esc cancel"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)
    while True:
        cv2.imshow(window, display)
        key = cv2.waitKey(20) & 0xFF
        if key == 27:
            cv2.destroyAllWindows()
            raise SystemExit("Calibration cancelled")
        if key in (ord("r"), ord("R")):
            points.clear()
            display = image.copy()
        if key in (10, 13) and len(points) == 4:
            break
    cv2.destroyAllWindows()

    floor_points = [[0.0, 0.0], [args.width_cm, 0.0], [args.width_cm, args.height_cm], [0.0, args.height_cm]]
    matrix = cv2.getPerspectiveTransform(np.float32(points), np.float32(floor_points))
    record = {
        "schema_version": 1,
        "image_size_px": [int(image.shape[1]), int(image.shape[0])],
        "image_points_px": points,
        "floor_points_cm": floor_points,
        "homography_px_to_floor_cm": matrix.tolist(),
        "roi_px": points,
    }
    args.output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved calibration: {args.output}")


if __name__ == "__main__":
    main()
