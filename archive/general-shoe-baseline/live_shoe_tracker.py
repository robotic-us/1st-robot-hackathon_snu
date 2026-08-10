#!/usr/bin/env python3
"""Show live shoe detections with persistent tracker IDs from a webcam.

Example:
    python3 live_shoe_tracker.py
    python3 live_shoe_tracker.py --camera 0 --confidence 0.25 --width 1280 --height 720

Controls: Q/Esc quit, Space pause/resume, S save an annotated frame.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

try:
    import cv2
    from ultralytics import YOLO
except ImportError as error:
    missing = error.name or "a required package"
    raise SystemExit(
        f"Missing dependency: {missing}. Run this in the same Python environment used for training."
    ) from error


DEFAULT_MODEL = Path(__file__).parent / "training/general_shoes_yolo26s_baseline/weights/best.pt"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="YOLO .pt weights")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV webcam index (default: 0)")
    parser.add_argument("--width", type=int, default=1280, help="Requested webcam width")
    parser.add_argument("--height", type=int, default=720, help="Requested webcam height")
    parser.add_argument("--confidence", type=float, default=0.25, help="Detection confidence threshold")
    parser.add_argument("--iou", type=float, default=0.50, help="NMS IoU threshold")
    parser.add_argument(
        "--device",
        default="cpu",
        help="YOLO device, e.g. cpu or 0 (default: cpu; use 0 only with a compatible CUDA setup)",
    )
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Ultralytics tracker configuration")
    parser.add_argument("--save-dir", type=Path, default=Path("live_captures"), help="Folder for S key captures")
    return parser.parse_args()


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    # V4L2 is the most reliable backend for direct Linux webcams; fall back if unavailable.
    camera = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not camera.isOpened():
        camera = cv2.VideoCapture(index)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera {index}. Try --camera 1 or check /dev/video*.")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return camera


def draw_status(frame, fps: float, detections: int, paused: bool) -> None:
    status = f"FPS: {fps:.1f}   shoes: {detections}"
    if paused:
        status += "   PAUSED"
    cv2.rectangle(frame, (8, 8), (385, 46), (20, 20, 20), -1)
    cv2.putText(frame, status, (16, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (80, 255, 80), 2)
    cv2.putText(
        frame,
        "Q/Esc: quit | Space: pause | S: save frame",
        (16, frame.shape[0] - 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )


def main() -> None:
    args = arguments()
    if not 0 < args.confidence <= 1 or not 0 < args.iou <= 1:
        raise SystemExit("--confidence and --iou must be between 0 and 1.")
    if not args.model.is_file():
        raise SystemExit(f"Model not found: {args.model}")

    model = YOLO(args.model)
    camera = open_camera(args.camera, args.width, args.height)
    window = "Live shoe tracker"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    print("Camera open. Press Q or Esc in the video window to quit.")

    paused = False
    annotated = None
    last_count = 0
    fps = 0.0
    previous = time.perf_counter()
    try:
        while True:
            if not paused:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Could not read a frame from the webcam.")

                # persist=True retains ByteTrack identities between consecutive frames.
                result = model.track(
                    frame,
                    persist=True,
                    tracker=args.tracker,
                    conf=args.confidence,
                    iou=args.iou,
                    device=args.device,
                    classes=[0],
                    verbose=False,
                )[0]
                annotated = result.plot(labels=True, conf=True, boxes=True)
                now = time.perf_counter()
                instant_fps = 1.0 / max(now - previous, 1e-6)
                fps = instant_fps if fps == 0 else 0.85 * fps + 0.15 * instant_fps
                previous = now
                last_count = 0 if result.boxes is None else len(result.boxes)

            if annotated is not None:
                display = annotated.copy()
                draw_status(display, fps, last_count, paused=paused)
                cv2.imshow(window, display)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord(" "):
                paused = not paused
            if key == ord("s") and annotated is not None:
                args.save_dir.mkdir(parents=True, exist_ok=True)
                destination = args.save_dir / f"shoe-track-{datetime.now():%Y%m%d-%H%M%S}.jpg"
                if cv2.imwrite(str(destination), display):
                    print(f"Saved {destination}")
                else:
                    print(f"Could not save {destination}")
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
