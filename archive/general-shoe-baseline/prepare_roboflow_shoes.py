#!/usr/bin/env python3
"""Clean the downloaded Roboflow shoe archive into a leakage-safe YOLO dataset."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from collections import Counter
from pathlib import Path


def source_id(filename: str) -> str:
    """Return Roboflow's pre-augmentation source identifier."""
    return filename.split(".rf.", 1)[0]


def destination_split(identifier: str) -> str:
    """Assign all variants of one source to a deterministic 70/20/10 split."""
    bucket = int(hashlib.sha256(identifier.encode()).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 90:
        return "val"
    return "test"


def clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def to_box(line: str) -> str | None:
    """Merge either a YOLO box or polygon annotation into class 0 (`shoe`)."""
    fields = line.split()
    if len(fields) < 5:
        return None

    try:
        values = [float(value) for value in fields[1:]]
    except ValueError:
        return None

    if len(values) == 4:
        x_center, y_center, width, height = values
        x_min = x_center - width / 2
        x_max = x_center + width / 2
        y_min = y_center - height / 2
        y_max = y_center + height / 2
    elif len(values) >= 6 and len(values) % 2 == 0:
        xs = values[0::2]
        ys = values[1::2]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
    else:
        return None

    x_min, x_max = clamp(x_min), clamp(x_max)
    y_min, y_max = clamp(y_min), clamp(y_max)
    width, height = x_max - x_min, y_max - y_min
    if width <= 0 or height <= 0:
        return None

    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    return f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def prepare(archive: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing directory: {output}")

    counts: Counter[str] = Counter()
    skipped = 0
    output.mkdir(parents=True)

    with zipfile.ZipFile(archive) as source:
        entries = {entry.filename: entry for entry in source.infolist()}
        images = [
            entry
            for entry in source.infolist()
            if entry.filename.startswith(("train/images/", "valid/images/", "test/images/"))
            and not entry.is_dir()
        ]

        for image in images:
            name = Path(image.filename).name
            split = destination_split(source_id(name))
            image_output = output / "images" / split / name
            label_output = output / "labels" / split / f"{Path(name).stem}.txt"
            image_output.parent.mkdir(parents=True, exist_ok=True)
            label_output.parent.mkdir(parents=True, exist_ok=True)

            with source.open(image) as input_file, image_output.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)

            original_split = image.filename.split("/", 1)[0]
            original_label = f"{original_split}/labels/{Path(name).stem}.txt"
            converted: list[str] = []
            if original_label in entries:
                text = source.read(original_label).decode("utf-8", errors="replace")
                for line in text.splitlines():
                    box = to_box(line)
                    if box is None:
                        skipped += 1
                    else:
                        converted.append(box)
            label_output.write_text("\n".join(converted) + ("\n" if converted else ""))
            counts[f"{split}_images"] += 1
            counts[f"{split}_boxes"] += len(converted)

    (output / "data.yaml").write_text(
        "path: /workspace/datasets/general_shoes\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n\n"
        "names:\n"
        "  0: shoe\n"
    )
    (output / "README.md").write_text(
        "# General shoes dataset\n\n"
        "Source: Roboflow Universe, Shoe Detection v2\n\n"
        "License: CC BY 4.0\n\n"
        "Source URL: https://universe.roboflow.com/robotics-lo9nk/shoe-detection-lmpo9/dataset/2\n\n"
        "Preparation: merged both source classes into `shoe`, converted polygon labels to "
        "bounding boxes, and reassigned splits by pre-augmentation source ID to prevent "
        "source-image leakage across train, validation, and test.\n"
    )

    print(f"Created {output}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    print(f"skipped_annotations: {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.archive.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
