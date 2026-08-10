#!/usr/bin/env python3
"""Interactive webcam test for locating and identifying shoes on a static floor.

The detector compares each frame with a captured empty-floor reference.  It is
intended for testing camera placement and lighting, not as the final shoe
instance-segmentation system.

Controls
--------
R  capture the current image as the empty-floor reference
S  save raw image, annotated image, mask, and candidate JSON
A  identify the current candidates with the Kimi API (when --api is set)
Q / Esc  quit
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
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
    parser.add_argument("--threshold", type=int, default=28, help="Foreground difference threshold (0-255)")
    parser.add_argument("--background", type=Path, help="Load an empty-floor reference image")
    parser.add_argument("--calibration", type=Path, help="Calibration JSON from calibrate_floor.py")
    parser.add_argument("--model", type=Path, help="Ultralytics segmentation model (.pt); bypasses background subtraction")
    parser.add_argument("--confidence", type=float, default=0.45, help="Minimum model confidence")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/vision_captures"), help="Directory for saved tests"
    )
    parser.add_argument("--camera-height-cm", type=float, default=65.0, help="Recorded metadata only")
    parser.add_argument("--horizontal-fov-deg", type=float, default=55.0, help="Recorded metadata only")
    parser.add_argument(
        "--api",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable Kimi identification (default: enabled; use --no-api for offline-only)",
    )
    parser.add_argument("--api-model", default="kimi-k3", help="Kimi vision model used for shoe identity")
    parser.add_argument(
        "--api-base-url",
        default="https://api.moonshot.ai/v1",
        help="Kimi OpenAI-compatible API base URL",
    )
    parser.add_argument("--api-min-confidence", type=float, default=0.60, help="Reject API identities below this confidence")
    parser.add_argument("--api-max-candidates", type=int, default=4, help="Refuse unexpectedly large/costly API requests")
    parser.add_argument("--shoe-assets", type=Path, default=Path("shoe_assets.json"), help="Known-shoe manifest")
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("shoe_references"),
        help="Reference gallery; use one subdirectory per asset_id",
    )
    return parser.parse_args()


def foreground_mask(
    frame: np.ndarray, background: np.ndarray, threshold: int, roi: np.ndarray | None = None
) -> np.ndarray:
    """Return a clean binary mask of pixels that differ from the empty floor."""
    difference = cv2.absdiff(frame, background)
    gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    if roi is not None:
        roi_mask = np.zeros_like(mask)
        cv2.fillPoly(roi_mask, [roi.astype(np.int32)], 255)
        mask = cv2.bitwise_and(mask, roi_mask)
    return mask


def pixel_to_floor(point: tuple[float, float], homography: np.ndarray | None) -> list[float] | None:
    if homography is None:
        return None
    source = np.float32([[[point[0], point[1]]]])
    transformed = cv2.perspectiveTransform(source, homography)[0, 0]
    return [round(float(transformed[0]), 2), round(float(transformed[1]), 2)]


def find_candidates(
    mask: np.ndarray, min_area: float, homography: np.ndarray | None = None
) -> list[dict[str, object]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[dict[str, object]] = []
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
        perimeter = cv2.arcLength(contour, True)
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        solidity = area / hull_area if hull_area > 0 else 0.0
        floor_xy = pixel_to_floor((center_x, center_y), homography)
        box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
        candidates.append(
            {
                "shoe_id": None,
                "pair_id": None,
                "side": "unknown",
                "center_px": [round(center_x, 1), round(center_y, 1)],
                "floor_xy_cm": floor_xy,
                "orientation_deg": round(angle, 1),
                "toe_direction_deg": None,
                "area_px": round(area, 1),
                "size_px": [round(max(rect_width, rect_height), 1), round(min(rect_width, rect_height), 1)],
                "bbox_px": [box_x, box_y, box_width, box_height],
                "solidity": round(solidity, 3),
                "perimeter_px": round(perimeter, 1),
                "visible": True,
                "touching_or_merged": bool(solidity < 0.78),
                "pickup_candidate": bool(solidity >= 0.78),
                "confidence": None,
                "identity_confidence": None,
            }
        )
    return sorted(candidates, key=lambda candidate: float(candidate["area_px"]), reverse=True)


def find_model_candidates(
    frame: np.ndarray, model: object, confidence: float, homography: np.ndarray | None
) -> tuple[np.ndarray, list[dict[str, object]]]:
    result = model.predict(frame, conf=confidence, verbose=False)[0]  # type: ignore[attr-defined]
    combined = np.zeros(frame.shape[:2], dtype=np.uint8)
    candidates: list[dict[str, object]] = []
    if result.masks is None:
        return combined, candidates
    confidences = result.boxes.conf.detach().cpu().numpy() if result.boxes is not None else []
    for index, raw_mask in enumerate(result.masks.data.detach().cpu().numpy()):
        resized = cv2.resize(raw_mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
        binary = np.uint8(resized >= 0.5) * 255
        combined = cv2.bitwise_or(combined, binary)
        detected = find_candidates(binary, min_area=50.0, homography=homography)
        if not detected:
            continue
        candidate = detected[0]
        candidate["confidence"] = round(float(confidences[index]), 4) if index < len(confidences) else None
        candidate["touching_or_merged"] = False
        candidate["pickup_candidate"] = bool(candidate["confidence"] is not None and float(candidate["confidence"]) >= confidence)
        candidates.append(candidate)
    return combined, sorted(candidates, key=lambda candidate: float(candidate["confidence"] or 0.0), reverse=True)


def annotate(frame: np.ndarray, candidates: list[dict[str, object]]) -> np.ndarray:
    display = frame.copy()
    for index, candidate in enumerate(candidates, start=1):
        x, y = candidate["center_px"]  # type: ignore[misc]
        angle = float(candidate["orientation_deg"])
        center = (int(x), int(y))
        radians = math.radians(angle)
        endpoint = (int(x + 70 * math.cos(radians)), int(y + 70 * math.sin(radians)))
        cv2.circle(display, center, 5, (0, 255, 0), -1)
        cv2.arrowedLine(display, center, endpoint, (0, 255, 0), 2, tipLength=0.2)
        floor_xy = candidate.get("floor_xy_cm")
        metric = f" | {floor_xy[0]:.1f},{floor_xy[1]:.1f} cm" if floor_xy else ""
        merged = " | MERGED?" if candidate["touching_or_merged"] else ""
        identity = candidate.get("shoe_id") or "unidentified"
        confidence = candidate.get("identity_confidence") if candidate.get("shoe_id") else None
        score = f" {float(confidence):.0%}" if confidence is not None else ""
        cv2.putText(display, f"{index}: {identity}{score} | {angle:.0f} deg{metric}{merged}", (center[0] + 8, center[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.putText(display, f"Candidates: {len(candidates)}", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(display, "R: empty floor | A: API identify | S: save | Q/Esc: quit", (16, display.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    return display


def image_bytes_data_url(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    return f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"


def frame_crop_data_url(frame: np.ndarray, bbox: list[int], padding: int = 30) -> str:
    x, y, width, height = bbox
    x1, y1 = max(0, x - padding), max(0, y - padding)
    x2 = min(frame.shape[1], x + width + padding)
    y2 = min(frame.shape[0], y + height + padding)
    ok, encoded = cv2.imencode(".jpg", frame[y1:y2, x1:x2], [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Could not encode a candidate crop for the API.")
    return image_bytes_data_url(encoded.tobytes())


def load_shoe_catalog(manifest_path: Path, reference_dir: Path) -> tuple[dict[str, dict[str, object]], list[tuple[str, Path]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = {str(asset["asset_id"]): asset for asset in manifest["assets"]}
    references: list[tuple[str, Path]] = []
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    for asset_id, asset in catalog.items():
        gallery = reference_dir / asset_id
        paths = sorted(path for path in gallery.glob("*") if path.suffix.lower() in extensions) if gallery.is_dir() else []
        if not paths:
            fallback = manifest_path.parent / Path(str(asset["obj_path"])).parent / "3DModel.jpg"
            if fallback.is_file():
                paths = [fallback]
        references.extend((asset_id, path) for path in paths)
    missing = sorted(set(catalog) - {asset_id for asset_id, _ in references})
    if missing:
        raise RuntimeError(f"No reference image found for: {', '.join(missing)}")
    return catalog, references


def reference_data_url(path: Path) -> str:
    mime_types = {".png": "image/png", ".webp": "image/webp"}
    return image_bytes_data_url(path.read_bytes(), mime_types.get(path.suffix.lower(), "image/jpeg"))


def identify_candidates_with_api(
    frame: np.ndarray,
    candidates: list[dict[str, object]],
    catalog: dict[str, dict[str, object]],
    references: list[tuple[str, Path]],
    model: str,
    base_url: str,
    min_confidence: float,
    max_candidates: int,
) -> None:
    if not candidates:
        print("No candidates to identify.")
        return
    if len(candidates) > max_candidates:
        print(f"Refusing API request for {len(candidates)} candidates (limit: {max_candidates}). Adjust detection first.")
        return
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        print("MOONSHOT_API_KEY is not set; no API request was made.")
        return
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("Kimi API mode requires: .venv/bin/python -m pip install -r requirements-api.txt") from error

    labels = list(catalog) + ["unknown"]
    content: list[dict[str, object]] = [
        {
            "type": "text",
            "text": (
                "Match every candidate crop to exactly one labeled reference shoe. "
                "Use unknown when the crop is not a reliable match. Identity only: do not estimate position. "
                "Confidence must be from 0 to 1. Return one result for every candidate index."
            ),
        }
    ]
    for asset_id, path in references:
        content.append({"type": "text", "text": f"REFERENCE label={asset_id}, file={path.name}"})
        content.append({"type": "image_url", "image_url": {"url": reference_data_url(path)}})
    for index, candidate in enumerate(candidates, start=1):
        content.append({"type": "text", "text": f"CANDIDATE index={index}"})
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": frame_crop_data_url(frame, candidate["bbox_px"])},  # type: ignore[arg-type]
            }
        )

    result_schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "candidate_index": {"type": "integer"},
                        "shoe_id": {"type": "string", "enum": labels},
                        "confidence": {"type": "number"},
                        "reason": {"type": "string"},
                    },
                    "required": ["candidate_index", "shoe_id", "confidence", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }
    print(f"Identifying {len(candidates)} candidate(s) with {model}...")
    response = OpenAI(api_key=api_key, base_url=base_url).chat.completions.create(
        model=model,
        reasoning_effort="low",
        messages=[{"role": "user", "content": content}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "shoe_identification", "strict": True, "schema": result_schema},
        },
        max_completion_tokens=2048,
    )
    output_text = response.choices[0].message.content
    if not output_text:
        raise RuntimeError("Kimi returned no final answer.")
    parsed = json.loads(output_text)
    for candidate in candidates:
        candidate.update({"shoe_id": None, "pair_id": None, "side": "unknown", "identity_confidence": None})
    seen: set[int] = set()
    for result in parsed.get("results", []):
        index = result.get("candidate_index")
        if not isinstance(index, int) or not 1 <= index <= len(candidates) or index in seen:
            continue
        seen.add(index)
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
        shoe_id = str(result.get("shoe_id", "unknown"))
        candidate = candidates[index - 1]
        if shoe_id not in catalog or confidence < min_confidence:
            candidate.update({"shoe_id": None, "pair_id": None, "side": "unknown", "identity_confidence": confidence})
            print(f"  candidate {index}: unknown ({confidence:.0%}) - {result.get('reason', '')}")
            continue
        asset = catalog[shoe_id]
        candidate.update(
            {
                "shoe_id": shoe_id,
                "pair_id": asset["pair_id"],
                "side": asset["side"],
                "identity_confidence": confidence,
            }
        )
        print(f"  candidate {index}: {shoe_id} ({confidence:.0%}) - {result.get('reason', '')}")


def carry_api_identities(
    candidates: list[dict[str, object]], identified: list[dict[str, object]], max_distance_px: float = 80.0
) -> None:
    """Carry the last API result across nearby detections until A is pressed again."""
    available = set(range(len(identified)))
    for candidate in candidates:
        center = candidate["center_px"]
        best: tuple[float, int] | None = None
        for old_index in available:
            old_center = identified[old_index]["center_px"]
            distance = math.hypot(float(center[0]) - float(old_center[0]), float(center[1]) - float(old_center[1]))  # type: ignore[index]
            if distance <= max_distance_px and (best is None or distance < best[0]):
                best = (distance, old_index)
        if best is None:
            continue
        old = identified[best[1]]
        available.remove(best[1])
        candidate.update(
            {
                "shoe_id": old.get("shoe_id"),
                "pair_id": old.get("pair_id"),
                "side": old.get("side", "unknown"),
                "identity_confidence": old.get("identity_confidence"),
            }
        )


def save_capture(output_dir: Path, frame: np.ndarray, annotated: np.ndarray, mask: np.ndarray, candidates: list[dict[str, object]], args: argparse.Namespace, frame_id: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stem = output_dir / stamp
    cv2.imwrite(str(stem.with_name(f"{stamp}_raw.jpg")), frame)
    cv2.imwrite(str(stem.with_name(f"{stamp}_annotated.jpg")), annotated)
    cv2.imwrite(str(stem.with_name(f"{stamp}_mask.png")), mask)
    record = {
        "schema_version": 1,
        "frame_id": frame_id,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "camera": {"index": args.camera, "height_cm": args.camera_height_cm, "horizontal_fov_deg": args.horizontal_fov_deg},
        "frame_size_px": [int(frame.shape[1]), int(frame.shape[0])],
        "candidates": candidates,
    }
    stem.with_name(f"{stamp}_candidates.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved capture set: {stem}")


def main() -> None:
    args = parse_args()
    shoe_catalog: dict[str, dict[str, object]] = {}
    shoe_references: list[tuple[str, Path]] = []
    if args.api:
        shoe_catalog, shoe_references = load_shoe_catalog(args.shoe_assets, args.reference_dir)
        print(f"Kimi identity enabled: {len(shoe_references)} reference image(s), model {args.api_model}")
    model = None
    if args.model:
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise SystemExit("Model inference requires: python3 -m pip install -r requirements-ml.txt") from error
        model = YOLO(str(args.model))
    homography: np.ndarray | None = None
    roi: np.ndarray | None = None
    if args.calibration:
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
        homography = np.asarray(calibration["homography_px_to_floor_cm"], dtype=np.float64)
        roi = np.asarray(calibration.get("roi_px"), dtype=np.float32) if calibration.get("roi_px") else None
    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera}. Try --camera 1 (or another index).")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    background: np.ndarray | None = cv2.imread(str(args.background)) if args.background else None
    if args.background and background is None:
        raise RuntimeError(f"Could not read background image: {args.background}")
    frame_id = 0
    identified_candidates: list[dict[str, object]] = []
    if model is None:
        print("Camera opened. Clear the floor and press R to capture the empty-floor reference.")
    else:
        print(f"Camera opened with segmentation model: {args.model}")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera returned no frame.")
            frame_id += 1
            if background is not None and background.shape != frame.shape:
                raise RuntimeError("Background image size does not match the camera frame size.")

            if model is not None:
                mask, candidates = find_model_candidates(frame, model, args.confidence, homography)
                carry_api_identities(candidates, identified_candidates)
                if identified_candidates:
                    identified_candidates = [dict(candidate) for candidate in candidates if candidate.get("shoe_id")]
                annotated = annotate(frame, candidates)
            elif background is None:
                mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                annotated = frame.copy()
                cv2.putText(annotated, "Clear floor, then press R to set reference", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
                candidates: list[dict[str, object]] = []
            else:
                mask = foreground_mask(frame, background, args.threshold, roi)
                candidates = find_candidates(mask, args.min_area, homography)
                carry_api_identities(candidates, identified_candidates)
                if identified_candidates:
                    identified_candidates = [dict(candidate) for candidate in candidates if candidate.get("shoe_id")]
                annotated = annotate(frame, candidates)

            cv2.imshow("Shoe vision test", annotated)
            cv2.imshow("Foreground mask", mask)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key in (ord("r"), ord("R")):
                background = frame.copy()
                print("Empty-floor reference captured.")
            if key in (ord("a"), ord("A")):
                if not args.api:
                    print("API identity is disabled. Restart with --api to enable it.")
                elif model is None and background is None:
                    print("Capture an empty-floor reference first (R).")
                else:
                    try:
                        identify_candidates_with_api(
                            frame,
                            candidates,
                            shoe_catalog,
                            shoe_references,
                            args.api_model,
                            args.api_base_url,
                            args.api_min_confidence,
                            args.api_max_candidates,
                        )
                        identified_candidates = [dict(candidate) for candidate in candidates]
                        cv2.imshow("Shoe vision test", annotate(frame, candidates))
                    except Exception as error:
                        print(f"API identification failed: {error}")
            if key in (ord("s"), ord("S")):
                if model is None and background is None:
                    print("Capture an empty-floor reference first (R).")
                else:
                    save_capture(args.output_dir, frame, annotated, mask, candidates, args, frame_id)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
