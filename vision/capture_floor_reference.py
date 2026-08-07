#!/usr/bin/env python3
"""Save one clean, full-resolution overhead photo of the empty floor.

Press S or Space to save; Q or Esc to quit.
"""

import argparse
from pathlib import Path

import cv2


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--camera", type=int, default=0)
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--output", type=Path, default=Path("floor_reference.jpg"))
args = parser.parse_args()

camera = cv2.VideoCapture(args.camera, cv2.CAP_V4L2)
if not camera.isOpened():
    camera = cv2.VideoCapture(args.camera)
if not camera.isOpened():
    raise SystemExit(f"Could not open camera {args.camera}.")
camera.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

for _ in range(30):  # Let exposure and white balance settle.
    camera.read()

try:
    while True:
        ok, frame = camera.read()
        if not ok:
            raise SystemExit("Camera returned no frame.")
        preview = frame.copy()
        cv2.putText(preview, "Clear floor | S/Space save | Q/Esc quit", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Floor reference", preview)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        if key in (ord("s"), ord(" ")):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if cv2.imwrite(str(args.output), frame, [cv2.IMWRITE_JPEG_QUALITY, 100]):
                print(f"Saved {args.output.resolve()}")
                break
finally:
    camera.release()
    cv2.destroyAllWindows()
