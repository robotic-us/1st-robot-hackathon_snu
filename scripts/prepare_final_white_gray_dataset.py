"""Combine the 1,000 synthetic images with labelled real white/gray images.

Target classes match the Blender generator exactly:
0 gray_left, 1 gray_right, 2 white_left, 3 white_right.
"""
import argparse
import os
import shutil
from pathlib import Path


ROOT = Path("/home/phorce/comp")
SYNTHETIC = ROOT / "generated/white_gray_pose_1000"
WHITE_IMAGES = ROOT / "real_shoes/pose_dataset/images"
WHITE_LABELS = ROOT / "real_shoes/pose_dataset/labels"
GRAY_IMAGES = ROOT / "real_shoes/replacement_gray_pair/raw"
GRAY_LABELS = ROOT / "real_shoes/replacement_gray_pair/manual_labels/labels"

# source name, original label class, target class
REAL_SOURCES = (
    ("white_right", WHITE_IMAGES, WHITE_LABELS, "pair1_right", 0, 3),
    ("white_left", WHITE_IMAGES, WHITE_LABELS, "pair1_left", 1, 2),
    ("gray_right", GRAY_IMAGES, GRAY_LABELS, "pair4_right", 6, 1),
    ("gray_left", GRAY_IMAGES, GRAY_LABELS, "pair4_left", 7, 0),
)


def link_or_copy(source: Path, destination: Path):
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def write_label(source: Path, destination: Path, expected_class: int, target_class: int):
    lines = []
    for line in source.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if int(parts[0]) != expected_class:
            raise ValueError(f"Unexpected class in {source}: {parts[0]}")
        parts[0] = str(target_class)
        lines.append(" ".join(parts))
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_synthetic(output: Path):
    for split in ("train", "val"):
        for image in sorted((SYNTHETIC / "images" / split).glob("*.png")):
            label = SYNTHETIC / "labels" / split / f"{image.stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(label)
            stem = f"synthetic_{image.stem}"
            link_or_copy(image, output / "images" / split / f"{stem}.png")
            link_or_copy(label, output / "labels" / split / f"{stem}.txt")


def add_real(output: Path):
    # Per class, every fifth sorted image is validation. This prevents one
    # presentation sequence from dominating validation while keeping all four
    # classes represented in both splits.
    for name, image_root, label_root, folder, source_class, target_class in REAL_SOURCES:
        images = sorted(
            image for image in image_root.rglob("*.jpg")
            if image.parent.name == folder or image.name.startswith(folder + "__")
        )
        if not images:
            raise FileNotFoundError(f"No images found for {folder}")
        for index, image in enumerate(images):
            label = label_root / image.relative_to(image_root).with_suffix(".txt")
            if not label.is_file():
                raise FileNotFoundError(label)
            split = "val" if index % 5 == 0 else "train"
            stem = f"real_{name}_{image.stem}"
            link_or_copy(image, output / "images" / split / f"{stem}.jpg")
            write_label(label, output / "labels" / split / f"{stem}.txt", source_class, target_class)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "datasets/white_gray_final"))
    parser.add_argument("--real-only", action="store_true",
                        help="omit the synthetic images for a real-only baseline")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing dataset: {output}")
    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True)
        (output / "labels" / split).mkdir(parents=True)
    if not args.real_only:
        add_synthetic(output)
    add_real(output)
    (output / "data.yaml").write_text(
        f"path: {output}\ntrain: images/train\nval: images/val\n"
        "kpt_shape: [2, 3]\nflip_idx: [0, 1]\nnames:\n"
        "  0: gray_left\n  1: gray_right\n  2: white_left\n  3: white_right\n",
        encoding="utf-8",
    )
    for split in ("train", "val"):
        count = len(list((output / "images" / split).glob("*")))
        print(f"{split}: {count} images")
    print(f"Dataset written to {output}")


if __name__ == "__main__":
    main()
