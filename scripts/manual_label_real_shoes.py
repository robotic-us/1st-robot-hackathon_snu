#!/usr/bin/env python3
"""Manually label real shoe photos for YOLO pose training.

Run from /home/phorce/comp:
    vision/.venv/bin/python scripts/manual_label_real_shoes.py

Use four passes: ``--pass box``, then ``heel``, then ``toe``, then ``review``.
Controls: B draw box, H click heel, T click toe, S save and next, R reset,
N/P next/previous, Q/Esc quit. Class is taken from the source folder name.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import cv2


CLASS_ID = {
    "pair1_right": 0,
    "pair1_left": 1,
    "pair2_right": 2,
    "pair2_left": 3,
}
CLASS_ID.update({"pair3_right": 4, "pair3_left": 5})
CLASS_ID.update({"pair4_right": 6, "pair4_left": 7})


@dataclass
class Annotation:
    box: tuple[int, int, int, int] | None = None
    heel: tuple[int, int] | None = None
    toe: tuple[int, int] | None = None


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("real_shoes/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("real_shoes/manual_labels"))
    parser.add_argument("--max-width", type=int, default=1280)
    parser.add_argument("--max-height", type=int, default=850)
    parser.add_argument("--pass", dest="phase", choices=("box", "heel", "toe", "review"), default="box")
    parser.add_argument("--include-complete", action="store_true", help="Include images already complete for this pass")
    return parser.parse_args()


def images(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"} and path.parent.name in CLASS_ID)


def label_path(output: Path, image: Path) -> Path:
    return output / "labels" / image.parent.name / f"{image.stem}.txt"


def annotation_path(output: Path, image: Path) -> Path:
    return output / "annotations" / image.parent.name / f"{image.stem}.json"


def load_annotation(output: Path, image: Path) -> Annotation:
    path = annotation_path(output, image)
    if not path.exists():
        return Annotation()
    data = json.loads(path.read_text(encoding="utf-8"))
    return Annotation(
        box=tuple(data["box"]) if data.get("box") else None,
        heel=tuple(data["heel"]) if data.get("heel") else None,
        toe=tuple(data["toe"]) if data.get("toe") else None,
    )


def save_annotation(output: Path, image: Path, annotation: Annotation) -> None:
    path = annotation_path(output, image)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"box": annotation.box, "heel": annotation.heel, "toe": annotation.toe}, indent=2), encoding="utf-8")


def complete_for_phase(output: Path, image: Path, phase: str) -> bool:
    annotation = load_annotation(output, image)
    if phase == "box":
        return annotation.box is not None
    if phase == "heel":
        return annotation.heel is not None
    if phase == "toe":
        return annotation.toe is not None
    return label_path(output, image).exists()


def display_scale(shape: tuple[int, ...], max_width: int, max_height: int) -> float:
    height, width = shape[:2]
    return min(1.0, max_width / width, max_height / height)


def yolo_line(annotation: Annotation, class_id: int, width: int, height: int) -> str:
    assert annotation.box and annotation.heel and annotation.toe
    x1, y1, x2, y2 = annotation.box
    heel_x, heel_y = annotation.heel
    toe_x, toe_y = annotation.toe
    return (
        f"{class_id} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
        f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f} "
        f"{heel_x / width:.6f} {heel_y / height:.6f} 2 {toe_x / width:.6f} {toe_y / height:.6f} 2\n"
    )


def draw(frame, annotation: Annotation, mode: str, image: Path, index: int, total: int, scale: float):
    canvas = frame.copy()
    if annotation.box:
        x1, y1, x2, y2 = annotation.box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 255), 3)
    if annotation.heel:
        cv2.circle(canvas, annotation.heel, 8, (255, 0, 0), -1)
        cv2.putText(canvas, "HEEL", (annotation.heel[0] + 10, annotation.heel[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
    if annotation.toe:
        cv2.circle(canvas, annotation.toe, 8, (0, 0, 255), -1)
        cv2.putText(canvas, "TOE", (annotation.toe[0] + 10, annotation.toe[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    if annotation.heel and annotation.toe:
        cv2.arrowedLine(canvas, annotation.heel, annotation.toe, (0, 255, 0), 3, tipLength=0.06)
    cv2.rectangle(canvas, (0, 0), (min(canvas.shape[1], 1000), 82), (20, 20, 20), -1)
    cv2.putText(canvas, f"{index + 1}/{total}  {image.parent.name}  |  MODE: {mode}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 255, 80), 2)
    cv2.putText(canvas, "B box | H heel | T toe | S save+next | R reset | N/P browse | Q quit", (12, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
    return cv2.resize(canvas, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1 else canvas


def main() -> None:
    args = arguments()
    paths = images(args.input_dir)
    if not args.include_complete:
        paths = [path for path in paths if not complete_for_phase(args.output_dir, path, args.phase)]
    if not paths:
        raise SystemExit("No unlabelled images found.")
    index, annotation, mode, dragging = 0, Annotation(), args.phase.upper() if args.phase != "review" else "BOX", False
    drag_start: tuple[int, int] | None = None
    window = "Manual shoe pose labeller"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    def load(current: int):
        frame = cv2.imread(str(paths[current]))
        if frame is None:
            raise RuntimeError(f"Could not read {paths[current]}")
        return frame, display_scale(frame.shape, args.max_width, args.max_height)

    frame, scale = load(index)
    annotation = load_annotation(args.output_dir, paths[index])

    def mouse(event, x, y, _flags, _param):
        nonlocal annotation, dragging, drag_start
        px, py = round(x / scale), round(y / scale)
        px = max(0, min(px, frame.shape[1] - 1))
        py = max(0, min(py, frame.shape[0] - 1))
        if mode == "BOX":
            if event == cv2.EVENT_LBUTTONDOWN:
                dragging, drag_start = True, (px, py)
            elif event == cv2.EVENT_LBUTTONUP and dragging and drag_start:
                x1, y1 = drag_start
                annotation.box = (min(x1, px), min(y1, py), max(x1, px), max(y1, py))
                dragging, drag_start = False, None
        elif event == cv2.EVENT_LBUTTONDOWN and mode == "HEEL":
            annotation.heel = (px, py)
        elif event == cv2.EVENT_LBUTTONDOWN and mode == "TOE":
            annotation.toe = (px, py)

    cv2.setMouseCallback(window, mouse)
    while True:
        cv2.imshow(window, draw(frame, annotation, mode, paths[index], index, len(paths), scale))
        key = cv2.waitKey(16) & 0xFF
        if key in (27, ord("q")):
            break
        if key == ord("b"):
            mode = "BOX"
        elif key == ord("h"):
            mode = "HEEL"
        elif key == ord("t"):
            mode = "TOE"
        elif key == ord("r"):
            if args.phase == "box":
                annotation.box = None
            elif args.phase == "heel":
                annotation.heel = None
            elif args.phase == "toe":
                annotation.toe = None
            else:
                annotation = Annotation()
        elif key == ord("s"):
            requirement = {"box": annotation.box, "heel": annotation.heel, "toe": annotation.toe}.get(args.phase)
            if args.phase != "review" and not requirement:
                print(f"Add the {args.phase} annotation before saving.")
                continue
            if args.phase == "review" and not (annotation.box and annotation.heel and annotation.toe):
                print("Review requires a box, heel, and toe. Return to the incomplete pass first.")
                continue
            save_annotation(args.output_dir, paths[index], annotation)
            if args.phase == "review":
                destination = label_path(args.output_dir, paths[index])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(yolo_line(annotation, CLASS_ID[paths[index].parent.name], frame.shape[1], frame.shape[0]), encoding="utf-8")
                print(f"Saved final YOLO label {destination}")
            else:
                print(f"Saved {args.phase} annotation for {paths[index].name}")
            if index == len(paths) - 1:
                print("All shown images are labelled.")
                break
            index += 1
            frame, scale, annotation, mode = *load(index), load_annotation(args.output_dir, paths[index]), args.phase.upper() if args.phase != "review" else "BOX"
        elif key == ord("n") and index < len(paths) - 1:
            index += 1
            frame, scale, annotation, mode = *load(index), load_annotation(args.output_dir, paths[index]), args.phase.upper() if args.phase != "review" else "BOX"
        elif key == ord("p") and index > 0:
            index -= 1
            frame, scale, annotation, mode = *load(index), load_annotation(args.output_dir, paths[index]), args.phase.upper() if args.phase != "review" else "BOX"
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
