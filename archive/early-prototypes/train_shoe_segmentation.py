#!/usr/bin/env python3
"""Prepare a synthetic YOLO segmentation split and train a lightweight model."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError as error:
    raise SystemExit("Install ML dependencies with: python3 -m pip install -r requirements-ml.txt") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Synthetic dataset root")
    parser.add_argument("--base-model", default="yolo11n-seg.pt")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--device", default=None, help="Examples: 0, cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = args.dataset.resolve()
    images = sorted((dataset / "images").glob("*.png"))
    if len(images) < 20:
        raise SystemExit("Render and annotate at least 20 images before training.")
    missing = [image for image in images if not (dataset / "labels" / f"{image.stem}.txt").exists()]
    if missing:
        raise SystemExit(f"Missing labels for {len(missing)} images; run build_synthetic_annotations.py")
    rng = random.Random(args.seed)
    rng.shuffle(images)
    validation_count = max(1, round(len(images) * args.validation_fraction))
    validation, train = images[:validation_count], images[validation_count:]
    train_file, validation_file = dataset / "train.txt", dataset / "val.txt"
    train_file.write_text("\n".join(str(path) for path in train) + "\n", encoding="utf-8")
    validation_file.write_text("\n".join(str(path) for path in validation) + "\n", encoding="utf-8")
    data_yaml = dataset / "data.yaml"
    data_yaml.write_text(
        f"path: {dataset}\ntrain: {train_file}\nval: {validation_file}\nnames:\n  0: shoe\n",
        encoding="utf-8",
    )
    model = YOLO(args.base_model)
    options = {
        "data": str(data_yaml),
        "epochs": args.epochs,
        "imgsz": args.image_size,
        "batch": args.batch,
        "seed": args.seed,
        "project": str(dataset / "runs"),
        "name": "shoe_segmentation",
    }
    if args.device is not None:
        options["device"] = args.device
    model.train(**options)


if __name__ == "__main__":
    main()
