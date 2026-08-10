#!/usr/bin/env python3
"""Live camera -> the 0° angle-selected PHORCE shoe motion sequence.

Default mode is camera-only: it shows boxes, toe/heel points, and the matching
situation without connecting to the arm.  With ``--execute``, a situation must
remain unchanged for five seconds, then Space must be double-tapped to play
its verified four-part motion sequence. Q/Esc quits.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import deque
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
DEFAULT_MODEL = PROJECT / "artifacts" / "models" / "shoe-pose-real-only-baseline.pt"
CALIBRATION_FILE = Path(__file__).with_name("camera_floor_calibration.json")
FLOOR_WIDTH_CM = 50.0
FLOOR_HEIGHT_CM = 80.0


def angle_difference(first: float, second: float) -> float:
    """Smallest signed difference between two angles, in degrees."""
    return (first - second + 180.0) % 360.0 - 180.0


def shoe_angle(heel: tuple[float, float], toe: tuple[float, float]) -> float:
    """Heel -> toe angle: up is 0°, camera-left is positive."""
    return math.degrees(math.atan2(heel[0] - toe[0], heel[1] - toe[1]))


def average_angle(first: float, second: float) -> float:
    """Circular mean of two headings, in the controller's degree convention."""
    radians = math.atan2(
        math.sin(math.radians(first)) + math.sin(math.radians(second)),
        math.cos(math.radians(first)) + math.cos(math.radians(second)),
    )
    return math.degrees(radians)


def origin_bearing(point: tuple[float, float], width: int, height: int) -> float:
    """Bearing from the camera's bottom-centre origin: up=0°, left=positive."""
    return math.degrees(math.atan2(width / 2.0 - point[0], height - point[1]))


class FloorCalibration:
    """Perspective map between camera pixels and the physical cardboard floor."""

    def __init__(self, corners_px: list[tuple[float, float]]) -> None:
        self.corners_px = corners_px
        source = np.array(corners_px, dtype=np.float32)
        floor = np.array([(0, 0), (FLOOR_WIDTH_CM, 0), (FLOOR_WIDTH_CM, FLOOR_HEIGHT_CM), (0, FLOOR_HEIGHT_CM)], dtype=np.float32)
        self.to_floor = cv2.getPerspectiveTransform(source, floor)
        self.to_camera = cv2.getPerspectiveTransform(floor, source)

    def cm(self, point_px: tuple[float, float]) -> tuple[float, float]:
        point = cv2.perspectiveTransform(np.array([[point_px]], dtype=np.float32), self.to_floor)[0, 0]
        return float(point[0]), float(point[1])

    def px(self, point_cm: tuple[float, float]) -> tuple[int, int]:
        point = cv2.perspectiveTransform(np.array([[point_cm]], dtype=np.float32), self.to_camera)[0, 0]
        return round(float(point[0])), round(float(point[1]))

    @classmethod
    def load(cls, path: Path) -> Optional["FloorCalibration"]:
        if not path.is_file():
            return None
        try:
            values = json.loads(path.read_text(encoding="utf-8"))["camera_corners_px_tl_tr_br_bl"]
            if len(values) != 4:
                raise ValueError("expected four corners")
            return cls([tuple(map(float, point)) for point in values])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            print(f"Ignoring invalid camera calibration {path}: {error}")
            return None

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "floor_width_cm": FLOOR_WIDTH_CM,
            "floor_height_cm": FLOOR_HEIGHT_CM,
            "camera_corners_px_tl_tr_br_bl": self.corners_px,
        }, indent=2) + "\n", encoding="utf-8")


def match_situation(angle_deg: float) -> Optional[Situation]:
    """Return the configured angle band containing ``angle_deg``.

    The physical location is intentionally ignored: the shoe nearest the
    camera centre is the controlled shoe, and its angle is the only input.
    """
    matches: list[tuple[float, Situation]] = []
    for situation in SITUATIONS:
        angle_error = abs(angle_difference(angle_deg, situation.angle_deg))
        if angle_error <= situation.angle_tolerance_deg:
            # Prefer the closest band if tolerances ever overlap.
            matches.append((angle_error, situation))
    return min(matches, default=(0.0, None), key=lambda item: item[0])[1]


def draw_situations(frame, calibration: Optional[FloorCalibration]) -> None:
    """Show configured target centres and expected toe direction."""
    for index, situation in enumerate(SITUATIONS, start=1):
        if situation.center_cm is None or calibration is None:
            continue
        x, y = calibration.px(situation.center_cm)
        tolerance_edge = calibration.px((situation.center_cm[0] + situation.position_tolerance_cm, situation.center_cm[1]))
        radius = max(5, round(math.dist((x, y), tolerance_edge)))
        radians = math.radians(situation.angle_deg)
        tip = calibration.px((
            situation.center_cm[0] - math.sin(radians) * situation.position_tolerance_cm,
            situation.center_cm[1] - math.cos(radians) * situation.position_tolerance_cm,
        ))
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
    calibrated: bool,
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
    text_line(panel, "1 shoe or 2 aligned shoes; heading: 0 deg +/-18", 5, (0, 230, 255))
    if candidate is None:
        state = "WAIT: shoe(s) need a 0 deg +/-18 angle" if detection_count else "WAIT: no shoe detected"
        text_line(panel, state, 6, (0, 180, 255))
    else:
        text_line(panel, f"situation: {candidate.name}  lock={min(lock_elapsed, lock_seconds):.1f}/{lock_seconds:.1f}s", 6, (70, 255, 255))
    row = 8
    unit = "cm" if calibrated else "px"
    for index, shoe in enumerate(shoes, start=1):
        if row + 4 > 18:
            text_line(panel, f"+ {len(shoes) - index + 1} more shoes (see overlay)", row, (0, 180, 255))
            break
        box = shoe["box"]
        center = shoe["center"]
        text_line(panel, f"SHOE {index}  track={shoe['track_id'] if shoe['track_id'] is not None else '--'}  conf={shoe['confidence']:.3f}", row, (70, 220, 255))
        text_line(panel, f"  centre=({center[0]:.1f}, {center[1]:.1f}) {unit}  box=({box[2]-box[0]:.0f} x {box[3]-box[1]:.0f}) px", row + 1)
        if shoe["heel"] is None:
            text_line(panel, "  heel/toe: no valid landmarks", row + 2, (0, 180, 255))
            row += 4
            continue
        heel, toe = shoe["heel"], shoe["toe"]
        text_line(panel, f"  heel=({heel[0]:.1f},{heel[1]:.1f})  toe=({toe[0]:.1f},{toe[1]:.1f}) {unit}  length={math.dist(heel, toe):.1f} {unit}", row + 2)
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
    """Run the verified four-slot request synchronously on the robot."""

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

    def play_sequence(self, motion_ids: tuple[int, int, int, int]) -> bool:
        """Play all four verified steps without yielding control to the UI."""
        if len(motion_ids) != 4:
            raise ValueError("The situation requires exactly four PHORCE motion IDs.")
        for index, motion_id in enumerate(motion_ids):
            if not self.play(motion_id):
                return False
            if index < len(motion_ids) - 1:
                time.sleep(1.0)
        return True

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
    parser.add_argument("--pair-alignment-tolerance", type=float, default=18.0, help="Maximum heading difference, in degrees, between the two required shoes.")
    parser.add_argument("--double-tap-window", type=float, default=0.5, help="Maximum seconds between the two Space presses.")
    parser.add_argument("--execute", action="store_true", help="Enable double-Space to run mapped PHORCE motions.")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    if not args.model.is_file():
        raise SystemExit(f"Model not found: {args.model}")
    if args.lock_seconds <= 0 or args.double_tap_window <= 0 or args.pair_alignment_tolerance <= 0:
        raise SystemExit("--lock-seconds, --double-tap-window, and --pair-alignment-tolerance must be positive.")

    model = YOLO(args.model)
    camera = open_camera(args.camera, args.width, args.height)
    robot = PhorceRunner() if args.execute else None
    stable_name: Optional[str] = None
    stable_since: Optional[float] = None
    last_ready: Optional[Situation] = None
    last_space_at: Optional[float] = None
    pending_situation: Optional[Situation] = None
    samples: deque[str] = deque(maxlen=12)
    frame_no = 0
    last_frame_at = time.perf_counter()
    last_sample_at = 0.0
    window = "Shoe valet control"
    calibration = FloorCalibration.load(CALIBRATION_FILE)
    calibrating = False
    calibration_points: list[tuple[int, int]] = []
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    def on_click(event: int, x: int, y: int, _flags: int, _userdata) -> None:
        nonlocal calibration, calibrating
        if event != cv2.EVENT_LBUTTONDOWN or not calibrating:
            return
        calibration_points.append((x, y))
        if len(calibration_points) == 4:
            calibration = FloorCalibration([(float(px), float(py)) for px, py in calibration_points])
            calibration.save(CALIBRATION_FILE)
            calibrating = False
            print(f"Floor calibration saved to {CALIBRATION_FILE}. Coordinates are now centimetres.")

    cv2.setMouseCallback(window, on_click)
    print("Camera ready. Show one shoe, or two aligned shoes at 0 deg (+/-18); lock for 5 seconds, then double-tap Space to play slots 11, 12, 13, 16 in --execute mode. Q/Esc quits.")

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
            draw_situations(display, calibration)
            frame_no += 1
            detection_count = 0 if result.boxes is None else len(result.boxes)

            # Exactly two similarly aligned shoes form the input. Their shared
            # heading, not their positions, selects the angle situation.
            candidate: Optional[Situation] = None
            shoes: list[dict] = []
            image_height, image_width = display.shape[:2]
            origin_cm = (FLOOR_WIDTH_CM / 2.0, FLOOR_HEIGHT_CM)
            origin = calibration.px(origin_cm) if calibration is not None else (image_width // 2, image_height - 1)
            cv2.circle(display, origin, 7, (0, 230, 255), -1)
            cv2.putText(display, "FLOOR ORIGIN / 0 deg", (max(8, origin[0] - 105), image_height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 2, cv2.LINE_AA)
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().tolist()
                confidences = result.boxes.conf.cpu().tolist()
                track_ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(boxes)
                keypoints = result.keypoints.xy.cpu().tolist() if result.keypoints is not None else [None] * len(boxes)
                for index, (box, confidence, track_id, points) in enumerate(zip(boxes, confidences, track_ids, keypoints), start=1):
                    center_px = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                    center = calibration.cm(center_px) if calibration is not None else center_px
                    bearing = origin_bearing(center, FLOOR_WIDTH_CM, FLOOR_HEIGHT_CM) if calibration is not None else origin_bearing(center, image_width, image_height)
                    shoe = {"box": box, "confidence": float(confidence), "track_id": track_id, "center": center,
                            "heel": None, "toe": None, "angle": None, "bearing": bearing, "alignment": None}
                    # Thin yellow line = the shoe centre's bearing from the camera origin.
                    cv2.line(display, origin, tuple(map(round, center_px)), (0, 230, 255), 1, cv2.LINE_AA)
                    cv2.putText(display, f"SHOE {index}  bearing {bearing:+.1f}", (round(box[0]), max(20, round(box[1]) - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 230, 255), 2, cv2.LINE_AA)
                    if points is not None and len(points) >= 2:
                        heel_px, toe_px = tuple(points[0]), tuple(points[1])  # dataset order: heel, toe
                        if heel_px != (0.0, 0.0) and toe_px != (0.0, 0.0):
                            heel = calibration.cm(heel_px) if calibration is not None else heel_px
                            toe = calibration.cm(toe_px) if calibration is not None else toe_px
                            angle = shoe_angle(heel, toe)
                            alignment = angle_difference(angle, bearing)
                            shoe.update(heel=heel, toe=toe, angle=angle, alignment=alignment)
                            cv2.arrowedLine(display, tuple(map(round, heel_px)), tuple(map(round, toe_px)), (0, 255, 0), 3, tipLength=0.18)
                            for label, point, color in (("HEEL", heel_px, (255, 180, 0)), ("TOE", toe_px, (0, 255, 0))):
                                px, py = map(round, point)
                                cv2.circle(display, (px, py), 6, color, -1)
                                cv2.putText(display, label, (px + 9, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
                            cv2.putText(display, f"alignment {alignment:+.1f} deg", (round(box[0]), min(image_height - 20, round(box[3]) + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 220, 70), 2, cv2.LINE_AA)
                    shoes.append(shoe)

            pair_angle_error: Optional[float] = None
            selected_angle: Optional[float] = None
            if len(shoes) == 1 and shoes[0]["angle"] is not None and not calibrating:
                selected_angle = shoes[0]["angle"]
            elif len(shoes) == 2 and all(shoe["angle"] is not None for shoe in shoes) and not calibrating:
                pair_angle_error = abs(angle_difference(shoes[0]["angle"], shoes[1]["angle"]))
                if pair_angle_error <= args.pair_alignment_tolerance:
                    selected_angle = average_angle(shoes[0]["angle"], shoes[1]["angle"])
            if selected_angle is not None:
                candidate = match_situation(selected_angle)
                for shoe in shoes:
                    box = shoe["box"]
                    cv2.rectangle(display, (round(box[0]), round(box[1])), (round(box[2]), round(box[3])), (255, 80, 255), 3)
                label = "SINGLE HEADING" if len(shoes) == 1 else "PAIR HEADING"
                cv2.putText(display, f"{label} {selected_angle:+.1f} deg", (16, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 80, 255), 2, cv2.LINE_AA)

            now = time.perf_counter()
            if candidate is not None and candidate.name == stable_name:
                assert stable_since is not None
            elif candidate is not None:
                stable_name, stable_since = candidate.name, now
            else:
                stable_name, stable_since = None, None
            lock_elapsed = 0.0 if stable_since is None else now - stable_since
            last_ready = candidate if lock_elapsed >= args.lock_seconds else None
            if last_space_at is not None and now - last_space_at > args.double_tap_window:
                last_space_at, pending_situation = None, None

            if calibrating:
                message, color = f"CALIBRATION: click floor corner {len(calibration_points) + 1}/4 (TL, TR, BR, BL)", (0, 230, 255)
                for point in calibration_points:
                    cv2.circle(display, point, 7, color, -1)
                if len(calibration_points) > 1:
                    cv2.polylines(display, [np.array(calibration_points, dtype=np.int32)], False, color, 2)
            elif last_space_at is not None and pending_situation is not None:
                remaining = max(0.0, args.double_tap_window - (now - last_space_at))
                message = f"CONFIRM {pending_situation.name}: press SPACE again ({remaining:.1f}s)"
                color = (255, 80, 255)
            elif last_ready is not None:
                slots = "unverified" if last_ready.motion_ids is None else "/".join(map(str, last_ready.motion_ids))
                message = f"PREVIEW: {last_ready.name}  slots={slots}  double-tap SPACE"
                color = (0, 255, 0) if last_ready.motion_ids else (0, 165, 255)
            elif candidate is not None:
                remaining = max(0.0, args.lock_seconds - lock_elapsed)
                message = f"COUNTDOWN: {candidate.name} will be selected in {remaining:.1f}s"
                color = (0, 255, 255)
            elif len(shoes) not in (1, 2):
                message, color = f"WAIT: show one or two shoes ({len(shoes)} detected)", (0, 165, 255)
            elif selected_angle is not None:
                message, color = "WAIT: heading must be 0 deg (+/-18 deg)", (0, 165, 255)
            elif pair_angle_error is None:
                message, color = "WAIT: detected shoe(s) need valid heel/toe angles", (0, 165, 255)
            elif pair_angle_error > args.pair_alignment_tolerance:
                message = f"WAIT: align the two shoes ({pair_angle_error:.1f} deg apart; max {args.pair_alignment_tolerance:.0f} deg)"
                color = (0, 165, 255)
            else:
                message, color = "WAIT: aligned pair must be 0 deg (+/-18 deg)", (0, 165, 255)
            cv2.rectangle(display, (8, 8), (850, 52), (20, 20, 20), -1)
            cv2.putText(display, message, (16, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            if candidate is not None and last_ready is None:
                progress = min(1.0, lock_elapsed / args.lock_seconds)
                cv2.rectangle(display, (16, 61), (516, 78), (40, 40, 40), -1)
                cv2.rectangle(display, (16, 61), (16 + round(500 * progress), 78), color, -1)
            if candidate is not None:
                preview = f"NEXT SITUATION: {candidate.name}"
                cv2.rectangle(display, (8, image_height - 51), (550, image_height - 8), (20, 20, 20), -1)
                cv2.putText(display, preview, (16, image_height - 21), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 80, 255), 2, cv2.LINE_AA)

            now = time.perf_counter()
            fps = 1.0 / max(now - last_frame_at, 0.001)
            last_frame_at = now
            if now - last_sample_at >= 0.25:
                if not shoes:
                    samples.appendleft(f"{frame_no:06d}  shoes={detection_count}  waiting")
                else:
                    sample = shoes[0]
                    heading = "--" if sample["angle"] is None else f"{sample['angle']:+5.1f}"
                    unit = "cm" if calibration is not None else "px"
                    samples.appendleft(f"{frame_no:06d}  n={detection_count}  x={sample['center'][0]:5.1f} y={sample['center'][1]:5.1f} {unit}  a={heading}")
                last_sample_at = now
            panel = telemetry_panel(
                display.shape[0], frame_no, fps, detection_count, shoes, calibration is not None,
                candidate, lock_elapsed, args.lock_seconds, samples,
            )
            cv2.imshow(window, cv2.hconcat([display, panel]))
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("c"), ord("C")):
                calibrating = True
                calibration_points.clear()
                stable_name, stable_since, last_ready = None, None, None
                last_space_at, pending_situation = None, None
                print("Calibration: click cardboard-floor corners in order TL, TR, BR, BL.")
            if key in (ord("q"), 27):
                break
            if key == ord(" "):
                if last_ready is None:
                    print("No five-second locked situation is ready.")
                    last_space_at, pending_situation = None, None
                elif last_space_at is not None and now - last_space_at <= args.double_tap_window:
                    if pending_situation is not None and pending_situation.name == last_ready.name:
                        if not args.execute:
                            print(f"Dry-run: selected {last_ready.name}; no robot motion is sent.")
                        elif last_ready.motion_ids is None:
                            print(f"{last_ready.name} is selected, but has no verified four-motion sequence.")
                        else:
                            print(f"PHORCE: running {last_ready.name}, slots {last_ready.motion_ids}; UI input is paused until all steps finish.")
                            cv2.rectangle(display, (8, 82), (850, 130), (20, 20, 20), -1)
                            cv2.putText(display, "PHORCE SEQUENCE RUNNING - INPUT PAUSED", (16, 116), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 255), 2)
                            cv2.imshow(window, cv2.hconcat([display, panel]))
                            cv2.waitKey(1)
                            try:
                                print("PHORCE sequence completed." if robot.play_sequence(last_ready.motion_ids) else "PHORCE sequence failed.")
                            except Exception as error:
                                print(f"PHORCE sequence blocked: {error}")
                    else:
                        print("Situation changed before confirmation; double-tap Space again.")
                    last_space_at, pending_situation = None, None
                else:
                    last_space_at = now
                    pending_situation = last_ready
                    print(f"Previewing {last_ready.name}. Press Space again within {args.double_tap_window:.1f}s to confirm.")
    finally:
        if robot is not None:
            robot.close()
        camera.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
