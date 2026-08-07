#!/usr/bin/env python3
"""Export four-pass manual annotations into a stratified YOLO pose dataset."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil

import cv2


CLASS_ID = {
    "pair1_right": 0, "pair1_left": 1, "pair2_right": 2,
    "pair2_left": 3, "pair3_right": 4, "pair3_left": 5,
    "pair4_right": 6, "pair4_left": 7,
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=Path("real_shoes/raw"))
    parser.add_argument("--annotations", type=Path, default=Path("real_shoes/manual_labels/annotations"))
    parser.add_argument("--output", type=Path, default=Path("real_shoes/pose_dataset"))
    parser.add_argument("--val-every", type=int, default=5, help="Every Nth image per class goes to validation")
    return parser.parse_args()


def yolo_line(annotation: dict, class_id: int, width: int, height: int) -> str:
    try:
        x1, y1, x2, y2 = (float(value) for value in annotation["box"])
        heel_x, heel_y = (float(value) for value in annotation["heel"])
        toe_x, toe_y = (float(value) for value in annotation["toe"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("missing or invalid box/heel/toe") from error
    if not 0 <= x1 < x2 <= width - 1 or not 0 <= y1 < y2 <= height - 1:
        raise ValueError("bounding box is outside the image")
    for x, y in ((heel_x, heel_y), (toe_x, toe_y)):
        if not 0 <= x <= width - 1 or not 0 <= y <= height - 1:
            raise ValueError("keypoint is outside the image")
    return (
        f"{class_id} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
        f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f} "
        f"{heel_x / width:.6f} {heel_y / height:.6f} 2 {toe_x / width:.6f} {toe_y / height:.6f} 2\n"
    )


def copy_image(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def main() -> None:
    args = arguments()
    if args.val_every < 2:
        raise SystemExit("--val-every must be at least 2.")
    totals = {"train": 0, "val": 0}
    for shoe, class_id in CLASS_ID.items():
        photos = sorted(path for path in (args.images / shoe).glob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if not photos:
            raise SystemExit(f"No source images for {shoe}")
        for position, photo in enumerate(photos):
            annotation_file = args.annotations / shoe / f"{photo.stem}.json"
            if not annotation_file.exists():
                raise SystemExit(f"Missing annotation: {annotation_file}")
            image = cv2.imread(str(photo))
            if image is None:
                raise SystemExit(f"Unreadable image: {photo}")
            height, width = image.shape[:2]
            annotation = json.loads(annotation_file.read_text(encoding="utf-8"))
            try:
                label = yolo_line(annotation, class_id, width, height)
            except ValueError as error:
                raise SystemExit(f"Invalid annotation in {annotation_file}: {error}") from error
            split = "val" if position % args.val_every == 0 else "train"
            stem = f"{shoe}__{photo.stem}"
            copy_image(photo, args.output / "images" / split / f"{stem}{photo.suffix.lower()}")
            label_path = args.output / "labels" / split / f"{stem}.txt"
            label_path.parent.mkdir(parents=True, exist_ok=True)
            label_path.write_text(label, encoding="utf-8")
            totals[split] += 1
    (args.output / "data.yaml").write_text(
        "path: " + str(args.output.resolve()) + "\n"
        "train: images/train\nval: images/val\n"
        "kpt_shape: [2, 3]\nflip_idx: [0, 1]\n"
        "names:\n"
        "  0: pair1_right\n  1: pair1_left\n  2: pair2_right\n"
        "  3: pair2_left\n  4: pair3_right\n  5: pair3_left\n"
        "  6: pair4_right\n  7: pair4_left\n",
        encoding="utf-8",
    )
    print(f"Prepared {totals['train']} train and {totals['val']} validation images in {args.output}")


if __name__ == "__main__":
    main()
