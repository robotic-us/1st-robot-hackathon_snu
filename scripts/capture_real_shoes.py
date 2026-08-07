#!/usr/bin/env python3
"""Capture consistently named real-world shoe photos from a fixed camera.

Example:
    ../vision/.venv/bin/python scripts/capture_real_shoes.py --shoe pair1_right

Controls: S/Space capture, A toggle automatic capture, 1-8 select shoe,
N/P change pose index, Q/Esc quit.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time

import cv2


SHOES = (
    "pair1_right",
    "pair1_left",
    "pair2_right",
    "pair2_left",
    "pair3_right",
    "pair3_left",
    "pair4_right",
    "pair4_left",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default: 0)")
    parser.add_argument("--width", type=int, default=1280, help="Requested capture width")
    parser.add_argument("--height", type=int, default=720, help="Requested capture height")
    parser.add_argument("--shoe", choices=SHOES, default=SHOES[0], help="Starting shoe")
    parser.add_argument("--target", type=int, default=50, help="Photos to capture for each shoe")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="Seconds between automatic saves after pressing A (default: 1.5)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("real_shoes/raw"),
        help="Dataset folder, relative to the current directory",
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


def next_index(folder: Path) -> int:
    indices = []
    for image in folder.glob("*.jpg"):
        try:
            indices.append(int(image.stem.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    return max(indices, default=0) + 1


def image_count(folder: Path) -> int:
    return sum(1 for image in folder.glob("*.jpg") if image.is_file())


def main() -> None:
    args = arguments()
    if args.target < 1:
        raise SystemExit("--target must be at least 1.")
    if args.interval < 0:
        raise SystemExit("--interval cannot be negative.")
    selected = SHOES.index(args.shoe)
    indices = {}
    counts = {}
    for shoe in SHOES:
        folder = args.output_dir / shoe
        folder.mkdir(parents=True, exist_ok=True)
        indices[shoe] = next_index(folder)
        counts[shoe] = image_count(folder)

    camera = open_camera(args.camera, args.width, args.height)
    window = "Real shoe capture"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    # --interval only configures the timer. Capturing always begins in manual
    # mode so opening the program can never immediately save unwanted frames.
    automatic = False
    last_saved = time.monotonic()
    print("Capture ready in MANUAL mode. S/Space: save | A: automatic | 1-8: shoe | N/P: index | Q/Esc: quit")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera returned no frame.")
            shoe = SHOES[selected]
            index = indices[shoe]
            saved = counts[shoe]
            display = frame.copy()
            mode = f"AUTO {args.interval:.1f}s" if automatic else "MANUAL"
            status = f"{shoe}  |  {saved}/{args.target} saved  |  {mode}"
            cv2.rectangle(display, (8, 8), (650, 84), (20, 20, 20), -1)
            cv2.putText(display, status, (18, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (80, 255, 80), 2)
            cv2.putText(display, "S/Space save | A auto | 1-8 shoe | N/P index | Q/Esc quit", (18, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.imshow(window, display)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            should_save = key in (ord("s"), ord(" "))
            if automatic and counts[shoe] < args.target and time.monotonic() - last_saved >= args.interval:
                should_save = True
            if should_save:
                destination = args.output_dir / shoe / f"{shoe}_{index:03d}.jpg"
                if cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    print(f"Saved {destination}")
                    indices[shoe] += 1
                    counts[shoe] += 1
                    last_saved = time.monotonic()
            elif ord("1") <= key <= ord(str(len(SHOES))):
                selected = key - ord("1")
                last_saved = time.monotonic()
            elif key == ord("a"):
                automatic = not automatic
                last_saved = time.monotonic()
                print(f"Automatic capture {'enabled' if automatic else 'disabled'}.")
            elif key == ord("n"):
                indices[shoe] += 1
            elif key == ord("p"):
                indices[shoe] = max(1, indices[shoe] - 1)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
