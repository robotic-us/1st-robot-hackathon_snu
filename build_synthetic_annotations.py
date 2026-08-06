#!/usr/bin/env python3
"""Convert synthetic instance masks and metadata into JSON and YOLO polygons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Dataset directory made by generate_synthetic_shoes.py")
    parser.add_argument("--min-area", type=float, default=100.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    annotation_dir = args.dataset / "annotations"
    label_dir = args.dataset / "labels"
    annotation_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    for metadata_path in sorted((args.dataset / "metadata").glob("*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        mask_path = args.dataset / "instance_masks" / f"{metadata_path.stem}.png"
        mask_image = cv2.imread(str(mask_path), cv2.IMREAD_COLOR)
        if mask_image is None:
            raise RuntimeError(f"Missing instance mask: {mask_path}")
        height, width = mask_image.shape[:2]
        output_instances = []
        yolo_lines = []
        for instance in metadata["instances"]:
            rgb = np.asarray(instance["mask_rgb"], dtype=np.int16)
            bgr = rgb[::-1]
            distance = np.max(np.abs(mask_image.astype(np.int16) - bgr), axis=2)
            binary = np.uint8(distance <= 12) * 255
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = [contour for contour in contours if cv2.contourArea(contour) >= args.min_area]
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)
            moments = cv2.moments(contour)
            center = [moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]]
            x, y, w, h = cv2.boundingRect(contour)
            epsilon = 0.003 * cv2.arcLength(contour, True)
            polygon = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
            normalized = [[round(float(px) / width, 6), round(float(py) / height, 6)] for px, py in polygon]
            enriched = dict(instance)
            enriched.update(
                {
                    "center_px": [round(center[0], 2), round(center[1], 2)],
                    "bbox_xywh_px": [int(x), int(y), int(w), int(h)],
                    "area_px": round(cv2.contourArea(contour), 1),
                    "segmentation_px": polygon.tolist(),
                }
            )
            output_instances.append(enriched)
            coordinates = " ".join(f"{px:.6f} {py:.6f}" for px, py in normalized)
            yolo_lines.append(f"0 {coordinates}")

        annotation = {
            "schema_version": 1,
            "image": f"images/{metadata_path.stem}.png",
            "image_size_px": [width, height],
            "instances": output_instances,
        }
        (annotation_dir / metadata_path.name).write_text(json.dumps(annotation, indent=2), encoding="utf-8")
        (label_dir / f"{metadata_path.stem}.txt").write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
    print(f"Built annotations in {annotation_dir} and {label_dir}")


if __name__ == "__main__":
    main()
