#!/usr/bin/env python3
"""Show live shoe detections with persistent tracker IDs from a webcam.

Example:
    python3 live_shoe_tracker.py
    python3 live_shoe_tracker.py --camera 0 --confidence 0.25 --width 1280 --height 720

Controls: Q/Esc quit, Space pause/resume, S save an annotated frame, G ask Gemini.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from kimi_understanding import analyse_scene as analyse_kimi_scene
from shoe_understanding import analyse_pairs, analyse_scene as analyse_gemini_scene, analyse_shoe, draw_understanding

try:
    import cv2
    from ultralytics import YOLO
except ImportError as error:
    missing = error.name or "a required package"
    raise SystemExit(
        f"Missing dependency: {missing}. Run this in the same Python environment used for training."
    ) from error


DEFAULT_MODEL = Path(__file__).parent / "models/shoe-detector.pt"

# Kept blank deliberately. Supply KIMI_API_KEY through the environment or
# --kimi-key so credentials never live in this shared source file.
KIMI_API_KEY = ""
KIMI_API_URL = "https://api.moonshot.ai/v1/chat/completions"

# Kept blank deliberately. Supply GEMINI_API_KEY through the environment or
# --gemini-key so credentials never live in this shared source file.
GEMINI_API_KEY = ""
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="YOLO .pt weights")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV webcam index (default: 0)")
    parser.add_argument("--width", type=int, default=1280, help="Requested webcam width")
    parser.add_argument("--height", type=int, default=720, help="Requested webcam height")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO inference size (default: 640)")
    parser.add_argument("--confidence", type=float, default=0.25, help="Detection confidence threshold")
    parser.add_argument("--iou", type=float, default=0.50, help="NMS IoU threshold")
    parser.add_argument(
        "--class-aware-nms",
        action="store_true",
        help="Keep overlapping predictions from different YOLO classes (normally disabled for generic shoe boxes)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="YOLO device, e.g. cpu or 0 (default: cpu; use 0 only with a compatible CUDA setup)",
    )
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Ultralytics tracker configuration")
    parser.add_argument("--save-dir", type=Path, default=Path("live_captures"), help="Folder for S key captures")
    kimi_mode = parser.add_mutually_exclusive_group()
    kimi_mode.add_argument("--kimi-orientation", action="store_true", help="Ask Kimi once for each new stable shoe track")
    kimi_mode.add_argument("--kimi-understanding", action="store_true", help="Ask Kimi for left/right and likely pair hypotheses")
    parser.add_argument("--kimi-key", default="", help="Kimi API key (overrides KIMI_API_KEY and the script placeholder)")
    parser.add_argument("--kimi-model", default="kimi-k3", help="Kimi multimodal model name")
    parser.add_argument("--kimi-stable-frames", type=int, default=8, help="Frames before asking Kimi (default: 8)")
    parser.add_argument("--kimi-pair-visible-seconds", type=float, default=2.5,
                        help="Continuous two-shoe visibility required before Kimi pair check (default: 2.5)")
    parser.add_argument("--kimi-min-confidence", type=float, default=0.70, help="Ignore Kimi side labels below this confidence (default: 0.70)")
    gemini_mode = parser.add_mutually_exclusive_group()
    gemini_mode.add_argument("--gemini-orientation", action="store_true", help="Ask Gemini once for each new stable shoe track")
    gemini_mode.add_argument("--gemini-understanding", action="store_true", help="Press G to ask Gemini for joint left/right and pair hypotheses")
    parser.add_argument("--gemini-key", default="", help="Gemini API key (overrides GEMINI_API_KEY and the script placeholder)")
    parser.add_argument("--gemini-model", default="gemini-3.5-flash", help="Gemini multimodal model name")
    parser.add_argument("--gemini-stable-frames", type=int, default=8, help="Frames before asking Gemini (default: 8)")
    parser.add_argument("--gemini-pair-visible-seconds", type=float, default=2.5,
                        help="Continuous two-shoe visibility required before Gemini pair check (default: 2.5)")
    parser.add_argument("--gemini-min-confidence", type=float, default=0.70, help="Ignore Gemini results below this confidence (default: 0.70)")
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
        "Q/Esc: quit | Space: pause | S: save | G: ask Gemini",
        (16, frame.shape[0] - 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )


def robot_bearing_degrees(point_x: float, point_y: float, frame_width: int, frame_height: int) -> float:
    """Return a point's bearing from the robot at the bottom-center of the image.

    The camera's image y-axis points down.  This convention makes straight up
    (away from the robot) 0 degrees, the left side positive, and the right
    side negative.  A shoe below the robot origin can therefore return an
    angle outside -90 to +90 degrees.
    """
    robot_x = frame_width / 2.0
    robot_y = float(frame_height)
    return math.degrees(math.atan2(robot_x - point_x, robot_y - point_y))


def draw_robot_bearings(frame, result) -> None:
    """Overlay per-shoe bearings and the robot's image-space origin."""
    height, width = frame.shape[:2]
    robot_origin = (width // 2, height - 1)
    cv2.circle(frame, robot_origin, 7, (0, 0, 255), -1)
    cv2.putText(
        frame,
        "ROBOT (0 deg)",
        (max(8, robot_origin[0] - 75), height - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 0, 255),
        2,
    )

    if result.boxes is None or len(result.boxes) == 0:
        return

    boxes = result.boxes.xyxy.cpu().tolist()
    track_ids = result.boxes.id
    ids = track_ids.int().cpu().tolist() if track_ids is not None else [None] * len(boxes)

    for box, track_id in zip(boxes, ids):
        x1, y1, x2, y2 = box
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        bearing = robot_bearing_degrees(center_x, center_y, width, height)

        # The line shows the camera-space polar direction used for the label.
        cv2.line(frame, robot_origin, (round(center_x), round(center_y)), (0, 230, 255), 1)
        identifier = f"ID {track_id} " if track_id is not None else ""
        label = f"{identifier}{bearing:+.1f} deg"
        label_y = max(22, round(y1) - 12)
        cv2.putText(
            frame,
            label,
            (round(x1), label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (0, 230, 255),
            2,
        )


def kimi_orientation(crop, api_key: str, model: str) -> dict:
    """Ask Kimi for toe/heel points in a single shoe crop, returning normalized points."""
    ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Could not encode shoe crop for Kimi.")
    image_url = "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
    prompt = (
        "This image contains one shoe, viewed from above. Locate its toe and heel. "
        "Return JSON only, with no markdown: "
        '{"toe":[x,y],"heel":[x,y],"confidence":0.0}. '
        "x and y must be integers from 0 to 1000, normalized within this crop "
        "(0,0 is top-left; 1000,1000 is bottom-right). If uncertain, set confidence below 0.5."
    )
    payload = {
        "model": model,
        # kimi-k2.5 currently accepts only temperature=1.
        "temperature": 1,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}],
    }
    request = urllib.request.Request(
        KIMI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Kimi API HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:300]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Kimi API connection error: {error.reason}") from error

    content = reply["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    answer = json.loads(content)
    for name in ("toe", "heel"):
        point = answer.get(name)
        if not isinstance(point, list) or len(point) != 2 or not all(isinstance(value, (int, float)) for value in point):
            raise RuntimeError(f"Kimi returned invalid {name} point.")
        answer[name] = [max(0, min(1000, float(value))) for value in point]
    answer["confidence"] = float(answer.get("confidence", 0))
    return answer


def draw_kimi_orientation(frame, orientation: dict) -> None:
    """Draw Kimi's cached toe-to-heel line in image coordinates."""
    toe = tuple(round(value) for value in orientation["toe"])
    heel = tuple(round(value) for value in orientation["heel"])
    confidence = orientation["confidence"]
    color = (0, 255, 0) if confidence >= 0.7 else (0, 165, 255)
    cv2.arrowedLine(frame, heel, toe, color, 3, tipLength=0.18)
    cv2.putText(frame, f"Kimi toe {confidence:.2f}", (toe[0] + 6, toe[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


def gemini_orientation(crop, api_key: str, model: str) -> dict:
    """Ask Gemini for shoe landmarks in a single crop, returning normalized points."""
    ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Could not encode shoe crop for Gemini.")
    image_data = base64.b64encode(encoded.tobytes()).decode("ascii")
    prompt = (
        "This image contains one upright sneaker, viewed from directly above. Locate its toe, heel, and tongue. "
        "The toe is the front tip, the heel is the rear end, and the tongue is the center of the opening/upper flap "
        "where a hook could approach. Do not confuse the tongue with a lace. "
        "Coordinates are normalized within this crop: (0,0) is top-left and (1000,1000) bottom-right. "
        "If uncertain, use a confidence below 0.5."
    )
    point_schema = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
    schema = {
        "type": "object",
        "properties": {
            "toe": point_schema,
            "heel": point_schema,
            "tongue": point_schema,
            "confidence": {"type": "number", "description": "Overall landmark confidence from 0 to 1."},
        },
        "required": ["toe", "heel", "tongue", "confidence"],
    }
    payload = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": image_data}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema},
    }
    request = urllib.request.Request(
        f"{GEMINI_API_URL}/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Gemini API HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:300]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Gemini API connection error: {error.reason}") from error

    answer = json.loads(reply["candidates"][0]["content"]["parts"][0]["text"])
    for name in ("toe", "heel", "tongue"):
        point = answer.get(name)
        if not isinstance(point, list) or len(point) != 2 or not all(isinstance(value, (int, float)) for value in point):
            raise RuntimeError(f"Gemini returned invalid {name} point.")
        answer[name] = [max(0, min(1000, float(value))) for value in point]
    answer["confidence"] = max(0, min(1, float(answer["confidence"])))
    return answer


def draw_gemini_orientation(frame, orientation: dict) -> None:
    """Draw Gemini's cached heel-to-toe axis and tongue hook target."""
    toe = tuple(round(value) for value in orientation["toe"])
    heel = tuple(round(value) for value in orientation["heel"])
    tongue = tuple(round(value) for value in orientation["tongue"])
    confidence = orientation["confidence"]
    # Match the robot bearing convention: up is 0°, left is positive.
    rotation = math.degrees(math.atan2(heel[0] - toe[0], heel[1] - toe[1]))
    cv2.arrowedLine(frame, heel, toe, (0, 255, 0), 3, tipLength=0.18)
    cv2.circle(frame, tongue, 7, (255, 0, 255), -1)
    cv2.putText(frame, f"shoe {rotation:+.1f} deg", (toe[0] + 6, toe[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, f"HOOK: tongue ({confidence:.2f})", (tongue[0] + 8, tongue[1] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 0, 255), 2)


def main() -> None:
    args = arguments()
    if not 0 < args.confidence <= 1 or not 0 < args.iou <= 1:
        raise SystemExit("--confidence and --iou must be between 0 and 1.")
    if (not 0 <= args.gemini_min_confidence <= 1 or not 0 <= args.kimi_min_confidence <= 1
            or args.kimi_pair_visible_seconds < 0 or args.gemini_pair_visible_seconds < 0):
        raise SystemExit("--gemini-min-confidence and --kimi-min-confidence must be between 0 and 1.")
    if not args.model.is_file():
        raise SystemExit(f"Model not found: {args.model}")
    kimi_key = args.kimi_key or os.environ.get("KIMI_API_KEY") or KIMI_API_KEY
    if (args.kimi_orientation or args.kimi_understanding) and not kimi_key:
        raise SystemExit("Kimi mode needs an API key. Set KIMI_API_KEY or pass --kimi-key.")
    gemini_key = args.gemini_key or os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if (args.gemini_orientation or args.gemini_understanding) and not gemini_key:
        raise SystemExit("Gemini mode needs an API key. Set GEMINI_API_KEY or pass --gemini-key.")

    model = YOLO(args.model)
    camera = open_camera(args.camera, args.width, args.height)
    window = "Live shoe tracker"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    print(f"Kimi joint pair mode: {'ON' if args.kimi_understanding else 'OFF'}", flush=True)
    print(f"Gemini joint pair mode: {'ON' if args.gemini_understanding else 'OFF'}", flush=True)
    print("Camera open. Press Q or Esc in the video window to quit.", flush=True)

    paused = False
    annotated = None
    last_count = 0
    fps = 0.0
    previous = time.perf_counter()
    track_frames: dict[int, int] = {}
    pending_kimi: dict[int, Future] = {}
    kimi_results: dict[int, dict] = {}
    kimi_understanding_results: dict[int, dict] = {}
    pending_kimi_scene: Future | None = None
    kimi_scene_signature: tuple[int, ...] = ()
    kimi_pair_results: list[dict] = []
    kimi_last_visible_count = -1
    kimi_pair_visible = False
    kimi_two_visible_since: float | None = None
    gemini_last_visible_count = -1
    gemini_pair_visible = False
    gemini_two_visible_since: float | None = None
    pending_gemini_scene: Future | None = None
    gemini_scene_results: dict[int, dict] = {}
    gemini_scene_pairs: list[dict] = []
    gemini_manual_requested = False
    pending_gemini: dict[int, Future] = {}
    gemini_results: dict[int, dict] = {}
    gemini_finished: set[int] = set()
    understanding_results: dict[int, dict] = {}
    understanding_finished: set[int] = set()
    understanding_crops: dict[int, object] = {}
    pending_understanding: dict[int, Future] = {}
    pending_pairing: Future | None = None
    pair_signature: tuple[int, ...] = ()
    pair_results: list[dict] = []
    track_centers: dict[int, tuple[int, int]] = {}
    executor = ThreadPoolExecutor(max_workers=1) if (args.kimi_orientation or args.kimi_understanding or args.gemini_orientation or args.gemini_understanding) else None
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
                    imgsz=args.imgsz,
                    device=args.device,
                    # Our pose model has four identity classes, but the live
                    # detector intentionally treats them all as one generic
                    # shoe. Suppress overlapping left/right class guesses so
                    # one physical shoe cannot produce two boxes.
                    agnostic_nms=not args.class_aware_nms,
                    verbose=False,
                )[0]
                if args.kimi_understanding:
                    visible_count = 0 if result.boxes is None else len(result.boxes)
                    if visible_count != kimi_last_visible_count:
                        print(f"Kimi trigger: {visible_count} shoe box(es) visible.", flush=True)
                        kimi_last_visible_count = visible_count
                    if visible_count < 2:
                        # Seeing a new two-shoe scene later should make a new
                        # request even if ByteTrack reuses the same IDs.
                        kimi_pair_visible = False
                        kimi_two_visible_since = None
                    elif kimi_two_visible_since is None:
                        kimi_two_visible_since = time.perf_counter()
                        print(f"Kimi: two-shoe timer started ({args.kimi_pair_visible_seconds:.1f}s).", flush=True)
                # The model's identity classes are intentionally not shown:
                # Kimi handles left/right only when at least two shoes appear.
                annotated = result.plot(labels=False, conf=False, boxes=True)
                draw_robot_bearings(annotated, result)
                if result.boxes is not None:
                    display_ids = (
                        result.boxes.id.int().cpu().tolist()
                        if result.boxes.id is not None
                        else list(range(1, len(result.boxes) + 1))
                    )
                    for box, track_id in zip(result.boxes.xyxy.cpu().tolist(), display_ids):
                        x1, y1, _, _ = (round(value) for value in box)
                        cv2.putText(annotated, f"shoe {track_id}", (x1 + 4, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

                if args.kimi_orientation and result.boxes is not None and result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().tolist()
                    ids = result.boxes.id.int().cpu().tolist()
                    for box, track_id in zip(boxes, ids):
                        track_frames[track_id] = track_frames.get(track_id, 0) + 1
                        if track_id in kimi_results or track_id in pending_kimi or track_frames[track_id] < args.kimi_stable_frames:
                            continue
                        x1, y1, x2, y2 = (round(value) for value in box)
                        padding = max(12, round(max(x2 - x1, y2 - y1) * 0.12))
                        left, top = max(0, x1 - padding), max(0, y1 - padding)
                        right, bottom = min(frame.shape[1], x2 + padding), min(frame.shape[0], y2 + padding)
                        crop = frame[top:bottom, left:right].copy()
                        if crop.size:
                            pending_kimi[track_id] = executor.submit(kimi_orientation, crop, kimi_key, args.kimi_model)
                            pending_kimi[track_id].crop_origin = (left, top)  # type: ignore[attr-defined]
                            pending_kimi[track_id].crop_size = (right - left, bottom - top)  # type: ignore[attr-defined]
                            print(f"Kimi: evaluating orientation for track ID {track_id}...")

                    for track_id, future in list(pending_kimi.items()):
                        if not future.done():
                            continue
                        del pending_kimi[track_id]
                        try:
                            answer = future.result()
                            left, top = future.crop_origin  # type: ignore[attr-defined]
                            crop_width, crop_height = future.crop_size  # type: ignore[attr-defined]
                            for name in ("toe", "heel"):
                                answer[name] = (left + answer[name][0] * crop_width / 1000, top + answer[name][1] * crop_height / 1000)
                            kimi_results[track_id] = answer
                            print(f"Kimi: track ID {track_id} orientation ready (confidence {answer['confidence']:.2f}).")
                        except Exception as error:
                            print(f"Kimi: track ID {track_id} failed: {error}")

                    for track_id, orientation in kimi_results.items():
                        draw_kimi_orientation(annotated, orientation)

                if args.kimi_understanding and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().tolist()
                    ids = (
                        result.boxes.id.int().cpu().tolist()
                        if result.boxes.id is not None
                        else list(range(1, len(boxes) + 1))
                    )
                    current_crops: dict[int, object] = {}
                    track_centers = {}
                    for box, track_id in zip(boxes, ids):
                        x1, y1, x2, y2 = (round(value) for value in box)
                        track_centers[track_id] = ((x1 + x2) // 2, (y1 + y2) // 2)
                        padding = max(12, round(max(x2 - x1, y2 - y1) * 0.12))
                        left, top = max(0, x1 - padding), max(0, y1 - padding)
                        right, bottom = min(frame.shape[1], x2 + padding), min(frame.shape[0], y2 + padding)
                        crop = frame[top:bottom, left:right].copy()
                        if crop.size:
                            current_crops[track_id] = crop

                    # One joint request starts as soon as any two tracked shoes
                    # are visible; this lets Kimi use their complementary shape.
                    visible_ids = tuple(sorted(current_crops)[:6])
                    visible_for = 0.0 if kimi_two_visible_since is None else time.perf_counter() - kimi_two_visible_since
                    if pending_kimi_scene is None and len(visible_ids) >= 2 and visible_for >= args.kimi_pair_visible_seconds and not kimi_pair_visible:
                        crops = {track_id: current_crops[track_id] for track_id in visible_ids}
                        print(f"Kimi: SUBMITTING joint left/right + pair request for track IDs {list(visible_ids)}...", flush=True)
                        pending_kimi_scene = executor.submit(analyse_kimi_scene, crops, kimi_key, args.kimi_model)
                        pending_kimi_scene.signature = visible_ids  # type: ignore[attr-defined]
                        kimi_pair_visible = True
                    if pending_kimi_scene is not None and pending_kimi_scene.done():
                        try:
                            answer = pending_kimi_scene.result()
                            kimi_understanding_results = answer["sides"]
                            kimi_pair_results = answer["pairs"]
                            kimi_scene_signature = pending_kimi_scene.signature  # type: ignore[attr-defined]
                            print(f"Kimi: response sides={kimi_understanding_results}, pairs={kimi_pair_results or 'none'}")
                        except Exception as error:
                            print(f"Kimi: joint left/right and pair check failed: {error}")
                            # Do not repeatedly spend requests on the same
                            # unavailable model/API error. A new attempt occurs
                            # only after the visible shoe count drops below two.
                            kimi_pair_visible = True
                        pending_kimi_scene = None

                    if len(visible_ids) >= 2 and pending_kimi_scene is None and not kimi_pair_visible:
                        remaining = max(0.0, args.kimi_pair_visible_seconds - visible_for)
                        cv2.putText(annotated, f"KIMI WAITING {remaining:.1f}s", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                    elif pending_kimi_scene is not None:
                        cv2.putText(annotated, "KIMI CHECKING LEFT/RIGHT + PAIR...", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

                    for track_id, understanding in kimi_understanding_results.items():
                        if track_id not in track_centers:
                            continue
                        accepted = understanding["side"] != "unknown" and understanding["confidence"] >= args.kimi_min_confidence
                        color = (0, 255, 0) if accepted else (0, 165, 255)
                        x, y = track_centers[track_id]
                        cv2.putText(annotated, f"Kimi {understanding['side']} {understanding['confidence']:.2f}", (x + 8, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    for pair in kimi_pair_results:
                        first, second = pair["track_ids"]
                        if first not in track_centers or second not in track_centers:
                            continue
                        cv2.line(annotated, track_centers[first], track_centers[second], (255, 255, 0), 2)
                        midpoint = ((track_centers[first][0] + track_centers[second][0]) // 2, (track_centers[first][1] + track_centers[second][1]) // 2)
                        cv2.putText(annotated, f"KIMI PAIR {first}<->{second} {pair['confidence']:.2f}", midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 0), 2)

                if args.gemini_orientation and result.boxes is not None and result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().tolist()
                    ids = result.boxes.id.int().cpu().tolist()
                    for box, track_id in zip(boxes, ids):
                        track_frames[track_id] = track_frames.get(track_id, 0) + 1
                        if track_id in gemini_finished or track_id in pending_gemini or track_frames[track_id] < args.gemini_stable_frames:
                            continue
                        x1, y1, x2, y2 = (round(value) for value in box)
                        padding = max(12, round(max(x2 - x1, y2 - y1) * 0.12))
                        left, top = max(0, x1 - padding), max(0, y1 - padding)
                        right, bottom = min(frame.shape[1], x2 + padding), min(frame.shape[0], y2 + padding)
                        crop = frame[top:bottom, left:right].copy()
                        if crop.size:
                            pending_gemini[track_id] = executor.submit(gemini_orientation, crop, gemini_key, args.gemini_model)
                            pending_gemini[track_id].crop_origin = (left, top)  # type: ignore[attr-defined]
                            pending_gemini[track_id].crop_size = (right - left, bottom - top)  # type: ignore[attr-defined]
                            print(f"Gemini: evaluating orientation for track ID {track_id}...")

                    for track_id, future in list(pending_gemini.items()):
                        if not future.done():
                            continue
                        del pending_gemini[track_id]
                        try:
                            answer = future.result()
                            gemini_finished.add(track_id)
                            left, top = future.crop_origin  # type: ignore[attr-defined]
                            crop_width, crop_height = future.crop_size  # type: ignore[attr-defined]
                            for name in ("toe", "heel", "tongue"):
                                answer[name] = (left + answer[name][0] * crop_width / 1000, top + answer[name][1] * crop_height / 1000)
                            if answer["confidence"] < args.gemini_min_confidence:
                                print(f"Gemini: track ID {track_id} ignored (confidence {answer['confidence']:.2f} < {args.gemini_min_confidence:.2f}).")
                                continue
                            gemini_results[track_id] = answer
                            print(f"Gemini: track ID {track_id} orientation ready (confidence {answer['confidence']:.2f}).")
                        except Exception as error:
                            gemini_finished.add(track_id)
                            print(f"Gemini: track ID {track_id} failed: {error}")

                    for track_id, orientation in gemini_results.items():
                        draw_gemini_orientation(annotated, orientation)

                if args.gemini_understanding and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().tolist()
                    ids = (result.boxes.id.int().cpu().tolist() if result.boxes.id is not None
                           else list(range(1, len(boxes) + 1)))
                    current_crops: dict[int, object] = {}
                    track_centers = {}
                    for box, track_id in zip(boxes, ids):
                        x1, y1, x2, y2 = (round(value) for value in box)
                        track_centers[track_id] = ((x1 + x2) // 2, (y1 + y2) // 2)
                        padding = max(12, round(max(x2 - x1, y2 - y1) * 0.12))
                        left, top = max(0, x1 - padding), max(0, y1 - padding)
                        right, bottom = min(frame.shape[1], x2 + padding), min(frame.shape[0], y2 + padding)
                        crop = frame[top:bottom, left:right].copy()
                        if crop.size:
                            current_crops[track_id] = crop

                    visible_count = len(current_crops)
                    if visible_count != gemini_last_visible_count:
                        print(f"Gemini trigger: {visible_count} shoe box(es) visible.", flush=True)
                        gemini_last_visible_count = visible_count
                    if visible_count < 2:
                        gemini_two_visible_since = None
                    elif gemini_two_visible_since is None:
                        gemini_two_visible_since = time.perf_counter()

                    visible_ids = tuple(sorted(current_crops)[:6])
                    visible_for = 0.0 if gemini_two_visible_since is None else time.perf_counter() - gemini_two_visible_since
                    if pending_gemini_scene is None and len(visible_ids) >= 2 and gemini_manual_requested:
                        crops = {track_id: current_crops[track_id] for track_id in visible_ids}
                        print(f"Gemini: SUBMITTING joint left/right + pair request for track IDs {list(visible_ids)}...", flush=True)
                        pending_gemini_scene = executor.submit(analyse_gemini_scene, crops, gemini_key, args.gemini_model)
                        gemini_pair_visible = True
                        gemini_manual_requested = False
                    if pending_gemini_scene is not None and pending_gemini_scene.done():
                        try:
                            answer = pending_gemini_scene.result()
                            gemini_scene_results = answer["sides"]
                            gemini_scene_pairs = answer["pairs"]
                            print(f"Gemini: response sides={gemini_scene_results}, pairs={gemini_scene_pairs or 'none'}", flush=True)
                        except Exception as error:
                            print(f"Gemini: joint left/right and pair check failed: {error}", flush=True)
                        pending_gemini_scene = None

                    if len(visible_ids) >= 2 and pending_gemini_scene is None:
                        cv2.putText(annotated, "PRESS G: GEMINI LEFT/RIGHT + PAIR", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                    elif pending_gemini_scene is not None:
                        cv2.putText(annotated, "GEMINI CHECKING LEFT/RIGHT + PAIR...", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                    for track_id, understanding in gemini_scene_results.items():
                        if track_id not in track_centers:
                            continue
                        accepted = understanding["side"] != "unknown" and understanding["confidence"] >= args.gemini_min_confidence
                        color = (0, 255, 0) if accepted else (0, 165, 255)
                        x, y = track_centers[track_id]
                        cv2.putText(annotated, f"Gemini {understanding['side']} {understanding['confidence']:.2f}", (x + 8, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    for pair in gemini_scene_pairs:
                        first, second = pair["track_ids"]
                        if first not in track_centers or second not in track_centers:
                            continue
                        cv2.line(annotated, track_centers[first], track_centers[second], (255, 255, 0), 2)
                        midpoint = ((track_centers[first][0] + track_centers[second][0]) // 2, (track_centers[first][1] + track_centers[second][1]) // 2)
                        cv2.putText(annotated, f"GEMINI PAIR {first}<->{second} {pair['confidence']:.2f}", midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 0), 2)

                if False and args.gemini_understanding and result.boxes is not None and result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().tolist()
                    ids = result.boxes.id.int().cpu().tolist()
                    for box, track_id in zip(boxes, ids):
                        track_frames[track_id] = track_frames.get(track_id, 0) + 1
                        x1, y1, x2, y2 = (round(value) for value in box)
                        track_centers[track_id] = ((x1 + x2) // 2, (y1 + y2) // 2)
                        if track_id in understanding_finished or track_id in pending_understanding or track_frames[track_id] < args.gemini_stable_frames:
                            continue
                        padding = max(12, round(max(x2 - x1, y2 - y1) * 0.12))
                        left, top = max(0, x1 - padding), max(0, y1 - padding)
                        right, bottom = min(frame.shape[1], x2 + padding), min(frame.shape[0], y2 + padding)
                        crop = frame[top:bottom, left:right].copy()
                        if crop.size:
                            pending_understanding[track_id] = executor.submit(analyse_shoe, crop, gemini_key, args.gemini_model)
                            pending_understanding[track_id].crop_origin = (left, top)  # type: ignore[attr-defined]
                            pending_understanding[track_id].crop_size = (right - left, bottom - top)  # type: ignore[attr-defined]
                            pending_understanding[track_id].crop = crop  # type: ignore[attr-defined]
                            print(f"Gemini: understanding track ID {track_id}...")

                    for track_id, future in list(pending_understanding.items()):
                        if not future.done():
                            continue
                        del pending_understanding[track_id]
                        understanding_finished.add(track_id)
                        try:
                            answer = future.result()
                            left, top = future.crop_origin  # type: ignore[attr-defined]
                            crop_width, crop_height = future.crop_size  # type: ignore[attr-defined]
                            for name in ("toe", "heel", "opening_center", "hook_target"):
                                answer[name] = (left + answer[name][0] * crop_width / 1000, top + answer[name][1] * crop_height / 1000)
                            understanding_results[track_id] = answer
                            understanding_crops[track_id] = future.crop  # type: ignore[attr-defined]
                            print(
                                f"Gemini: ID {track_id} is {answer['side']} {answer['shoe_type']} "
                                f"(pickup {'candidate' if answer['pickup_safe'] else 'not safe'}, {answer['confidence']:.2f})."
                            )
                        except Exception as error:
                            print(f"Gemini: understanding ID {track_id} failed: {error}")

                    # Pairing is an occasional contact-sheet comparison, not a per-frame API call.
                    visible_ids = tuple(sorted(track_id for track_id in understanding_results if track_id in track_centers))
                    comparison_ids = visible_ids[:6]
                    if pending_pairing is None and len(comparison_ids) >= 2 and comparison_ids != pair_signature:
                        crops = {track_id: understanding_crops[track_id] for track_id in comparison_ids}
                        pending_pairing = executor.submit(analyse_pairs, crops, gemini_key, args.gemini_model)
                        pending_pairing.signature = tuple(crops)  # type: ignore[attr-defined]
                        print(f"Gemini: comparing likely pairs among track IDs {list(crops)}...")
                    if pending_pairing is not None and pending_pairing.done():
                        try:
                            pair_results = pending_pairing.result()
                            pair_signature = pending_pairing.signature  # type: ignore[attr-defined]
                            print(f"Gemini: pair hypotheses: {pair_results or 'none'}")
                        except Exception as error:
                            print(f"Gemini: pair comparison failed: {error}")
                        pending_pairing = None

                    for track_id, understanding in understanding_results.items():
                        if track_id in track_centers:
                            draw_understanding(annotated, understanding)
                    for pair in pair_results:
                        first, second = pair["track_ids"]
                        if first not in track_centers or second not in track_centers:
                            continue
                        cv2.line(annotated, track_centers[first], track_centers[second], (255, 255, 0), 2)
                        midpoint = ((track_centers[first][0] + track_centers[second][0]) // 2, (track_centers[first][1] + track_centers[second][1]) // 2)
                        cv2.putText(annotated, f"PAIR {first}<->{second} {pair['confidence']:.2f}", midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 0), 2)
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
            if key in (ord("g"), ord("G")):
                if not args.gemini_understanding:
                    print("Gemini is off. Restart with --gemini-understanding to use G.", flush=True)
                elif last_count < 2:
                    print("Gemini needs at least two visible shoe boxes before G can submit a pair check.", flush=True)
                elif pending_gemini_scene is not None:
                    print("Gemini request is already running.", flush=True)
                else:
                    gemini_manual_requested = True
                    print("Gemini: G pressed; submitting the current two-shoe scene...", flush=True)
    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
