#!/usr/bin/env python3
"""Live camera -> one of ten taught PHORCE shoe motions.

Default mode is camera-only: it shows boxes, toe/heel points, and the matching
situation without connecting to the arm.  With ``--execute``, a situation must
remain unchanged for five seconds, then Space must be double-tapped to play
its verified full motion. Q/Esc quits.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Optional

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "vision"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from ultralytics import YOLO  # noqa: E402

from motion_map import SITUATIONS, Situation  # noqa: E402
from live_shoe_tracker import open_camera  # noqa: E402


# This is the real-photo pose model.  ``vision/models/shoe-detector.pt`` is
# detection-only, so it can draw boxes but cannot supply heel/toe landmarks.
DEFAULT_MODEL = PROJECT.parent / "runs" / "pose" / "runs" / "shoe_pose_real_only_baseline" / "weights" / "best.pt"


def angle_difference(first: float, second: float) -> float:
    """Smallest signed difference between two angles, in degrees."""
    return (first - second + 180.0) % 360.0 - 180.0


def shoe_angle(heel: tuple[float, float], toe: tuple[float, float]) -> float:
    """Heel -> toe angle: up is 0°, camera-left is positive."""
    return math.degrees(math.atan2(heel[0] - toe[0], heel[1] - toe[1]))


def origin_bearing(point: tuple[float, float], width: int, height: int) -> float:
    """Bearing from the camera's bottom-centre origin: up=0°, left=positive."""
    return math.degrees(math.atan2(width / 2.0 - point[0], height - point[1]))


def match_situation(
    center: tuple[float, float], angle_deg: float
) -> Optional[Situation]:
    """Return the single configured position/rotation situation, if any."""
    matches: list[tuple[float, Situation]] = []
    for situation in SITUATIONS:
        if situation.center_px is None:
            continue
        distance = math.dist(center, situation.center_px)
        angle_error = abs(angle_difference(angle_deg, situation.angle_deg))
        if distance <= situation.position_tolerance_px and angle_error <= situation.angle_tolerance_deg:
            # Prefer the closest valid situation if tolerance areas overlap.
            matches.append((distance + angle_error, situation))
    return min(matches, default=(0.0, None), key=lambda item: item[0])[1]


def draw_situations(frame) -> None:
    """Show configured target centres and expected toe direction."""
    for index, situation in enumerate(SITUATIONS, start=1):
        if situation.center_px is None:
            continue
        x, y = situation.center_px
        radius = round(situation.position_tolerance_px)
        cv2.circle(frame, (x, y), radius, (100, 100, 100), 1)
        radians = math.radians(situation.angle_deg)
        tip = (round(x - math.sin(radians) * radius), round(y - math.cos(radians) * radius))
        cv2.arrowedLine(frame, (x, y), tip, (100, 100, 100), 2, tipLength=0.20)
        cv2.putText(frame, str(index), (x - 8, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def text_line(image, text: str, row: int, color=(225, 225, 225), scale: float = 0.48) -> None:
    """Draw one fixed-width-ish line in the telemetry panel."""
    cv2.putText(image, text, (14, 30 + row * 24), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def telemetry_panel(
    height: int,
    frame_no: int,
    fps: float,
    detection_count: int,
    shoes: list[dict],
    candidate: Optional[Situation],
    lock_elapsed: float,
    lock_seconds: float,
    samples: deque[str],
) -> object:
    """Create a small scrolling numerical console to the right of the feed."""
    panel = np.full((height, 540, 3), (18, 18, 18), dtype=np.uint8)
    cv2.rectangle(panel, (0, 0), (539, 48), (42, 42, 42), -1)
    cv2.putText(panel, "LIVE VISION TELEMETRY", (14, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (70, 220, 255), 2, cv2.LINE_AA)
    text_line(panel, f"frame        {frame_no:06d}", 2)
    text_line(panel, f"inference fps {fps:5.1f}", 3, (120, 255, 120))
    text_line(panel, f"shoes seen   {detection_count}", 4)
    text_line(panel, "origin       bottom-centre of camera image", 5, (0, 230, 255))
    if candidate is None:
        state = "WAIT: exactly one shoe needed to arm motion" if detection_count != 1 else "situation: no configured match"
        text_line(panel, state, 6, (0, 180, 255))
    else:
        text_line(panel, f"situation: {candidate.name}  lock={min(lock_elapsed, lock_seconds):.1f}/{lock_seconds:.1f}s", 6, (70, 255, 255))
    row = 8
    for index, shoe in enumerate(shoes, start=1):
        if row + 4 > 18:
            text_line(panel, f"+ {len(shoes) - index + 1} more shoes (see overlay)", row, (0, 180, 255))
            break
        box = shoe["box"]
        center = shoe["center"]
        text_line(panel, f"SHOE {index}  track={shoe['track_id'] if shoe['track_id'] is not None else '--'}  conf={shoe['confidence']:.3f}", row, (70, 220, 255))
        text_line(panel, f"  box ({box[0]:.0f},{box[1]:.0f})->({box[2]:.0f},{box[3]:.0f})  centre=({center[0]:.1f},{center[1]:.1f})", row + 1)
        if shoe["heel"] is None:
            text_line(panel, "  heel/toe: no valid landmarks", row + 2, (0, 180, 255))
            row += 4
            continue
        heel, toe = shoe["heel"], shoe["toe"]
        text_line(panel, f"  heel=({heel[0]:.1f},{heel[1]:.1f})  toe=({toe[0]:.1f},{toe[1]:.1f})", row + 2)
        text_line(panel, f"  heading={shoe['angle']:+.1f} deg  origin bearing={shoe['bearing']:+.1f} deg", row + 3, (70, 255, 70))
        text_line(panel, f"  radial alignment (heading - bearing) = {shoe['alignment']:+.1f} deg", row + 4, (255, 220, 70))
        row += 6
    divider_y = min(height - 175, 520)
    cv2.line(panel, (12, divider_y), (528, divider_y), (70, 70, 70), 1)
    cv2.putText(panel, "RECENT SAMPLES", (14, divider_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1, cv2.LINE_AA)
    for row, sample in enumerate(samples):
        y = divider_y + 49 + row * 18
        if y > height - 10:
            break
        cv2.putText(panel, sample, (14, y), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (205, 205, 205), 1, cv2.LINE_AA)
    return panel


class PhorceRunner:
    """The deliberately tiny real-robot part: one verified slot per request."""

    def __init__(self) -> None:
        import phorce

        self.connection = phorce.connect()
        self.robot = self.connection.__enter__()

    def play(self, motion_id: int) -> bool:
        if not 1 <= motion_id <= 50:
            raise ValueError(f"Invalid PHORCE motion ID {motion_id}; expected 1..50.")
        status = self.robot.status()
        if getattr(status, "estop_active", True):
            raise RuntimeError("Robot reports an E-stop or unknown unsafe status.")
        return bool(self.robot.play(motion_id).ok)

    def close(self) -> None:
        self.connection.__exit__(None, None, None)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--device", default="cpu", help="Ultralytics device, e.g. cpu or 0 when the installed Torch/CUDA stack is compatible.")
    parser.add_argument("--lock-seconds", type=float, default=5.0, help="Continuous matching time required before execution can be armed.")
    parser.add_argument("--double-tap-window", type=float, default=0.5, help="Maximum seconds between the two Space presses.")
    parser.add_argument("--execute", action="store_true", help="Enable double-Space to run mapped PHORCE motions.")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    if not args.model.is_file():
        raise SystemExit(f"Model not found: {args.model}")
    if args.lock_seconds <= 0 or args.double_tap_window <= 0:
        raise SystemExit("--lock-seconds and --double-tap-window must be positive.")

    model = YOLO(args.model)
    camera = open_camera(args.camera, args.width, args.height)
    robot = PhorceRunner() if args.execute else None
    executor = ThreadPoolExecutor(max_workers=1) if robot else None
    motion: Optional[Future] = None
    stable_name: Optional[str] = None
    stable_since: Optional[float] = None
    last_ready: Optional[Situation] = None
    last_space_at: Optional[float] = None
    samples: deque[str] = deque(maxlen=12)
    frame_no = 0
    last_frame_at = time.perf_counter()
    last_sample_at = 0.0
    window = "Shoe valet control"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    print("Camera ready. Lock a situation for 5 seconds, then double-tap Space to play it in --execute mode. Q/Esc quits.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Could not read a camera frame.")
            result = model.track(
                frame, persist=True, conf=args.confidence, imgsz=args.imgsz,
                device=args.device, agnostic_nms=True, verbose=False,
            )[0]
            display = result.plot(labels=False, conf=False, boxes=True)
            draw_situations(display)
            frame_no += 1
            detection_count = 0 if result.boxes is None else len(result.boxes)

            # One shoe only: the arm has one pickup path and cannot safely
            # choose between multiple simultaneous shoes.
            candidate: Optional[Situation] = None
            shoes: list[dict] = []
            image_height, image_width = display.shape[:2]
            origin = (image_width // 2, image_height - 1)
            cv2.circle(display, origin, 7, (0, 230, 255), -1)
            cv2.putText(display, "CAMERA ORIGIN / 0 deg", (max(8, origin[0] - 115), image_height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 2, cv2.LINE_AA)
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().tolist()
                confidences = result.boxes.conf.cpu().tolist()
                track_ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(boxes)
                keypoints = result.keypoints.xy.cpu().tolist() if result.keypoints is not None else [None] * len(boxes)
                for index, (box, confidence, track_id, points) in enumerate(zip(boxes, confidences, track_ids, keypoints), start=1):
                    center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                    bearing = origin_bearing(center, image_width, image_height)
                    shoe = {"box": box, "confidence": float(confidence), "track_id": track_id, "center": center,
                            "heel": None, "toe": None, "angle": None, "bearing": bearing, "alignment": None}
                    # Thin yellow line = the shoe centre's bearing from the camera origin.
                    cv2.line(display, origin, tuple(map(round, center)), (0, 230, 255), 1, cv2.LINE_AA)
                    cv2.putText(display, f"SHOE {index}  bearing {bearing:+.1f}", (round(box[0]), max(20, round(box[1]) - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 230, 255), 2, cv2.LINE_AA)
                    if points is not None and len(points) >= 2:
                        heel, toe = tuple(points[0]), tuple(points[1])  # dataset order: heel, toe
                        if heel != (0.0, 0.0) and toe != (0.0, 0.0):
                            angle = shoe_angle(heel, toe)
                            alignment = angle_difference(angle, bearing)
                            shoe.update(heel=heel, toe=toe, angle=angle, alignment=alignment)
                            cv2.arrowedLine(display, tuple(map(round, heel)), tuple(map(round, toe)), (0, 255, 0), 3, tipLength=0.18)
                            for label, point, color in (("HEEL", heel, (255, 180, 0)), ("TOE", toe, (0, 255, 0))):
                                px, py = map(round, point)
                                cv2.circle(display, (px, py), 6, color, -1)
                                cv2.putText(display, label, (px + 9, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
                            cv2.putText(display, f"alignment {alignment:+.1f} deg", (round(box[0]), min(image_height - 20, round(box[3]) + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 220, 70), 2, cv2.LINE_AA)
                    shoes.append(shoe)

            # Visualize every shoe above, but only arm a physical action for
            # the unambiguous one-shoe case.
            if len(shoes) == 1 and shoes[0]["angle"] is not None:
                candidate = match_situation(shoes[0]["center"], shoes[0]["angle"])

            now = time.perf_counter()
            if candidate is not None and candidate.name == stable_name:
                assert stable_since is not None
            elif candidate is not None:
                stable_name, stable_since = candidate.name, now
            else:
                stable_name, stable_since = None, None
            lock_elapsed = 0.0 if stable_since is None else now - stable_since
            last_ready = candidate if lock_elapsed >= args.lock_seconds else None

            if last_ready is not None:
                message = f"LOCKED: {last_ready.name}  slot={last_ready.motion_id}  double-tap SPACE"
                color = (0, 255, 0) if last_ready.motion_id else (0, 165, 255)
            elif candidate is not None:
                message = f"LOCKING {candidate.name}: {max(0.0, args.lock_seconds - lock_elapsed):.1f}s remaining"
                color = (0, 255, 255)
            elif result.boxes is not None and len(result.boxes) > 1:
                message, color = "WAIT: show exactly one shoe", (0, 165, 255)
            else:
                message, color = "WAIT: place shoe in a configured situation", (0, 165, 255)
            cv2.rectangle(display, (8, 8), (850, 52), (20, 20, 20), -1)
            cv2.putText(display, message, (16, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            if motion is not None and motion.done():
                try:
                    print("PHORCE motion completed." if motion.result() else "PHORCE motion failed.")
                except Exception as error:
                    print(f"PHORCE motion blocked: {error}")
                motion = None
            if motion is not None:
                cv2.putText(display, "PHORCE MOTION RUNNING", (16, 116), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

            now = time.perf_counter()
            fps = 1.0 / max(now - last_frame_at, 0.001)
            last_frame_at = now
            if now - last_sample_at >= 0.25:
                if not shoes:
                    samples.appendleft(f"{frame_no:06d}  shoes={detection_count}  waiting")
                else:
                    sample = shoes[0]
                    heading = "--" if sample["angle"] is None else f"{sample['angle']:+5.1f}"
                    samples.appendleft(f"{frame_no:06d}  n={detection_count}  x={sample['center'][0]:5.0f} y={sample['center'][1]:5.0f}  a={heading}")
                last_sample_at = now
            panel = telemetry_panel(
                display.shape[0], frame_no, fps, detection_count, shoes,
                candidate, lock_elapsed, args.lock_seconds, samples,
            )
            cv2.imshow(window, cv2.hconcat([display, panel]))
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                if motion is None:
                    break
                print("A PHORCE motion is still running. Keep monitoring; use the physical E-stop if unsafe.")
            if key == ord(" "):
                if not args.execute:
                    print("Dry-run mode: restart with --execute after verifying all motions.")
                elif motion is not None:
                    print("A PHORCE motion is already running.")
                elif last_ready is None or last_ready.motion_id is None:
                    print("No five-second locked situation with a verified motion ID is ready.")
                    last_space_at = None
                elif last_space_at is not None and now - last_space_at <= args.double_tap_window:
                    print(f"PHORCE: playing {last_ready.name}, slot {last_ready.motion_id}.")
                    motion = executor.submit(robot.play, last_ready.motion_id)
                    last_space_at = None
                else:
                    last_space_at = now
                    print(f"{last_ready.name} locked. Press Space again within {args.double_tap_window:.1f}s to execute.")
    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=False)
        if robot is not None:
            robot.close()
        camera.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
