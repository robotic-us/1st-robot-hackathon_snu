"""Create easy-to-inspect overlays for the generated YOLO pose labels.

Yellow = bounding box, orange = heel, cyan = toe.
Run with: python3 scripts/create_pose_previews.py
"""

from pathlib import Path
import random
import argparse
from PIL import Image, ImageDraw


ROOT = Path("/home/phorce/comp")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dataset", type=Path, default=ROOT / "synthetic_shoes")
parser.add_argument("--output", type=Path, default=ROOT / "pose_previews")
parser.add_argument("--count", type=int, default=36)
parser.add_argument("--prefix", default="", help="only preview image stems with this prefix")
args = parser.parse_args()
DATASET = args.dataset
OUTPUT = args.output
PREVIEW_COUNT = args.count
OUTPUT.mkdir(parents=True, exist_ok=True)


def draw_annotation(draw, values, width, height):
    class_id, cx, cy, box_width, box_height, heel_x, heel_y, heel_v, toe_x, toe_y, toe_v = values
    left = (cx - box_width / 2) * width
    top = (cy - box_height / 2) * height
    right = (cx + box_width / 2) * width
    bottom = (cy + box_height / 2) * height
    draw.rectangle((left, top, right, bottom), outline="yellow", width=3)
    draw.text((left + 3, max(3, top - 18)), f"class {int(class_id)}", fill="yellow", stroke_width=1, stroke_fill="black")
    for x, y, visible, color, name in [
        (heel_x, heel_y, heel_v, "orange", "H"),
        (toe_x, toe_y, toe_v, "cyan", "T"),
    ]:
        if visible:
            px, py = x * width, y * height
            radius = 8
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color, outline="black", width=2)
            draw.text((px + 10, py - 10), name, fill=color, stroke_width=1, stroke_fill="black")


for old_preview in OUTPUT.glob("*.png"):
    old_preview.unlink()

all_images = sorted(
    image
    for extension in ("*.png", "*.jpg", "*.jpeg")
    for image in (DATASET / "images").glob(f"*/{extension}")
    if image.stem.startswith(args.prefix)
)
random.seed(20260807)
selected_images = random.sample(all_images, min(PREVIEW_COUNT, len(all_images)))

for image_path in selected_images:
    split = image_path.parent.name
    label_path = DATASET / "labels" / split / f"{image_path.stem}.txt"
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for line in label_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            draw_annotation(draw, [float(value) for value in line.split()], *image.size)
    output_path = OUTPUT / f"{split}_{image_path.name}"
    image.save(output_path)

print(f"Wrote pose previews to {OUTPUT}")
