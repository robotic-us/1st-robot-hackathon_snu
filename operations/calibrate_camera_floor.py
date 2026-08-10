#!/usr/bin/env python3
"""Calibrate the fixed camera against the 50 x 80 cm cardboard floor.

Click the floor corners in this order: top-left, top-right, bottom-right,
bottom-left. The second window becomes a rectified, top-down 50 x 80 cm view
with a 10 cm grid and a red 30 cm shoe-length ruler.

Keys: R reset corners | S save calibration JSON | Q/Esc quit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


FLOOR_WIDTH_CM = 50.0
FLOOR_HEIGHT_CM = 80.0
PIXELS_PER_CM = 10  # the rectified preview is 500 x 800 pixels
SHOE_LENGTH_CM = 30.0


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("camera_floor_calibration.json"),
        help="Where S saves the four camera points and physical floor dimensions.",
    )
    return parser.parse_args()


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    camera = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not camera.isOpened():
        camera = cv2.VideoCapture(index)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera {index}. Try --camera 1.")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return camera


def draw_camera_guides(image: np.ndarray, corners: list[tuple[int, int]]) -> None:
    labels = ("1 TL", "2 TR", "3 BR", "4 BL")
    for index, point in enumerate(corners):
        cv2.circle(image, point, 7, (0, 255, 255), -1)
        cv2.putText(image, labels[index], (point[0] + 9, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
    if len(corners) > 1:
        cv2.polylines(image, [np.array(corners, dtype=np.int32)], False, (0, 255, 255), 2, cv2.LINE_AA)
    if len(corners) == 4:
        cv2.polylines(image, [np.array(corners, dtype=np.int32)], True, (0, 255, 255), 2, cv2.LINE_AA)
        status = "Floor locked: check the rectified 10 cm grid, then press S to save"
    else:
        status = f"Click cardboard-floor corner {len(corners) + 1}/4: {labels[len(corners)]}"
    cv2.rectangle(image, (8, 8), (850, 50), (20, 20, 20), -1)
    cv2.putText(image, status, (16, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(image, "R: reset   S: save   Q/Esc: quit", (16, image.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2, cv2.LINE_AA)


def rectified_floor(frame: np.ndarray, corners: list[tuple[int, int]]) -> np.ndarray:
    """Warp four camera points into a 500 x 800 px floor, i.e. 10 px/cm."""
    width = round(FLOOR_WIDTH_CM * PIXELS_PER_CM)
    height = round(FLOOR_HEIGHT_CM * PIXELS_PER_CM)
    source = np.array(corners, dtype=np.float32)
    destination = np.array([(0, 0), (width - 1, 0), (width - 1, height - 1), (0, height - 1)], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, destination)
    floor = cv2.warpPerspective(frame, matrix, (width, height))

    # Grid is physical centimetres after the perspective correction.
    for cm in range(0, int(FLOOR_WIDTH_CM) + 1, 10):
        x = round(cm * PIXELS_PER_CM)
        cv2.line(floor, (x, 0), (x, height - 1), (120, 120, 120), 1)
        cv2.putText(floor, f"{cm} cm", (min(x + 4, width - 55), 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    for cm in range(0, int(FLOOR_HEIGHT_CM) + 1, 10):
        y = round(cm * PIXELS_PER_CM)
        cv2.line(floor, (0, y), (width - 1, y), (120, 120, 120), 1)
        cv2.putText(floor, f"{cm} cm", (5, min(y + 16, height - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    ruler_pixels = round(SHOE_LENGTH_CM * PIXELS_PER_CM)
    start = (width // 2 - ruler_pixels // 2, height // 2)
    end = (start[0] + ruler_pixels, start[1])
    cv2.arrowedLine(floor, start, end, (0, 0, 255), 3, tipLength=0.035)
    cv2.putText(floor, "30 cm shoe reference", (start[0], start[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 255), 2, cv2.LINE_AA)
    return floor


def main() -> int:
    args = arguments()
    corners: list[tuple[int, int]] = []
    camera = open_camera(args.camera, args.width, args.height)
    camera_window, floor_window = "Camera: click cardboard floor corners", "Rectified 50 x 80 cm floor"
    cv2.namedWindow(camera_window, cv2.WINDOW_NORMAL)
    cv2.namedWindow(floor_window, cv2.WINDOW_NORMAL)

    def on_click(event: int, x: int, y: int, _flags: int, _userdata) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(corners) < 4:
            corners.append((x, y))

    cv2.setMouseCallback(camera_window, on_click)
    print("Camera calibration ready. Click floor corners TL, TR, BR, BL. R resets; S saves; Q quits.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Could not read a camera frame.")
            camera_view = frame.copy()
            draw_camera_guides(camera_view, corners)
            cv2.imshow(camera_window, camera_view)
            if len(corners) == 4:
                cv2.imshow(floor_window, rectified_floor(frame, corners))
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                corners.clear()
                cv2.destroyWindow(floor_window)
                cv2.namedWindow(floor_window, cv2.WINDOW_NORMAL)
            if key == ord("s"):
                if len(corners) != 4:
                    print("Need all four floor corners before saving.")
                    continue
                payload = {
                    "floor_width_cm": FLOOR_WIDTH_CM,
                    "floor_height_cm": FLOOR_HEIGHT_CM,
                    "rectified_pixels_per_cm": PIXELS_PER_CM,
                    "camera_corners_px_tl_tr_br_bl": corners,
                }
                args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                print(f"Saved camera floor calibration to {args.output}")
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
