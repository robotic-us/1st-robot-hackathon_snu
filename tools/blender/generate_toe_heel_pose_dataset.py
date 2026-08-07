"""Render randomized shoe images and YOLO pose labels from a marked .blend.

The .blend must contain a ``SHOES`` collection.  Each object named ``SHOE_*``
must have child EMPTY objects with custom landmark values ``toe`` and ``heel``.
Markers are hidden from renders and become the two keypoints in each YOLO label.
"""
import argparse
import os
import random
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


IMAGE_SIZE = 640


def cli_args():
    args = sys.argv
    return args[args.index("--") + 1 :] if "--" in args else []


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="YOLO dataset directory")
    parser.add_argument("--images", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--max-shoes", type=int, default=2)
    parser.add_argument("--two-shoe-probability", type=float, default=0.65)
    parser.add_argument("--same-pair-probability", type=float, default=0.70,
                        help="when rendering two shoes, chance to render a left/right pair")
    parser.add_argument("--resume", action="store_true", help="continue an interrupted render in an existing output directory")
    parser.add_argument("--yaw-min-deg", type=float, default=0,
                        help="minimum in-plane shoe rotation (default: 0)")
    parser.add_argument("--yaw-max-deg", type=float, default=360,
                        help="maximum in-plane shoe rotation (default: 360)")
    parser.add_argument("--light-jitter", type=float, default=0.15,
                        help="maximum proportional light-energy variation (default: 0.15)")
    return parser.parse_args(cli_args())


def descendants(root, kind=None):
    result = []
    pending = list(root.children)
    while pending:
        obj = pending.pop()
        pending.extend(obj.children)
        if kind is None or obj.type == kind:
            result.append(obj)
    return result


def set_render_visibility(root, visible):
    """Roots are empties, so explicitly apply visibility to every child mesh."""
    for obj in [root, *descendants(root)]:
        obj.hide_render = not visible


def point_in_image(scene, camera, point):
    projected = world_to_camera_view(scene, camera, point)
    return projected.x, 1.0 - projected.y, projected.z


def shoe_label(scene, camera, root, class_id):
    markers = {obj.get("landmark"): obj for obj in descendants(root, "EMPTY")}
    if not {"toe", "heel"}.issubset(markers):
        raise RuntimeError(f"{root.name} needs toe and heel child landmark markers")

    coords = []
    for mesh in descendants(root, "MESH"):
        for vertex in mesh.data.vertices:
            x, y, depth = point_in_image(scene, camera, mesh.matrix_world @ vertex.co)
            if depth > 0:
                coords.append((x, y))
    if not coords:
        return None
    min_x, max_x = max(0, min(x for x, _ in coords)), min(1, max(x for x, _ in coords))
    min_y, max_y = max(0, min(y for _, y in coords)), min(1, max(y for _, y in coords))
    if max_x - min_x < 0.015 or max_y - min_y < 0.015:
        return None

    keypoints = []
    # Keep the order consistent with the manually labelled real dataset:
    # heel first, toe second.
    for name in ("heel", "toe"):
        marker = markers[name]
        if "landmark_local" in marker:
            point = root.matrix_world @ Vector(marker["landmark_local"])
        else:
            point = marker.matrix_world.translation
        x, y, depth = point_in_image(scene, camera, point)
        # YOLO keypoint visibility: 2 = visible/labelled, 0 = outside image.
        visible = 2 if depth > 0 and 0 <= x <= 1 and 0 <= y <= 1 else 0
        keypoints.extend((x if visible else 0, y if visible else 0, visible))
    return [class_id, (min_x + max_x) / 2, (min_y + max_y) / 2, max_x - min_x, max_y - min_y, *keypoints]


def fmt(label):
    return " ".join(str(value) if isinstance(value, int) else f"{value:.6f}" for value in label)


def main():
    args = parse_args()
    if (not 0 < args.val_ratio < 1 or args.images < 1 or args.max_shoes < 1
            or not 0 <= args.two_shoe_probability <= 1
            or not 0 <= args.same_pair_probability <= 1
            or args.yaw_min_deg > args.yaw_max_deg or args.light_jitter < 0):
        raise SystemExit("--images and --max-shoes must be positive; --val-ratio must be between 0 and 1")
    random.seed(args.seed)
    scene = bpy.context.scene
    camera = scene.camera
    shoes_collection = bpy.data.collections.get("SHOES")
    if not camera or not shoes_collection:
        raise SystemExit("Scene needs DatasetCamera and SHOES collection; run prepare_shoe_scene.py first")
    roots = [obj for obj in shoes_collection.objects if obj.name.startswith("SHOE_")]
    if not roots:
        raise SystemExit("No SHOE_* roots found")
    class_names = []
    for root in roots:
        class_name = root.get("class_name")
        if not class_name:
            raise SystemExit(f"{root.name} has no class_name. Recreate the scene with prepare_white_gray_scene.py.")
        class_names.append(class_name)
    class_names = sorted(set(class_names))
    class_id = {name: index for index, name in enumerate(class_names)}
    for root in roots:
        for marker in descendants(root, "EMPTY"):
            marker.hide_render = True
            marker.hide_viewport = True

    scene.render.resolution_x = IMAGE_SIZE
    scene.render.resolution_y = IMAGE_SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    output = os.path.abspath(args.output)
    if os.path.exists(output) and not args.resume:
        raise SystemExit(f"Refusing to overwrite existing output: {output}")
    for split in ("train", "val"):
        os.makedirs(os.path.join(output, "images", split), exist_ok=args.resume)
        os.makedirs(os.path.join(output, "labels", split), exist_ok=args.resume)
    with open(os.path.join(output, "data.yaml"), "w", encoding="utf-8") as file:
        names = "\n".join(f"  {index}: {name}" for name, index in class_id.items())
        file.write(f"path: .\ntrain: images/train\nval: images/val\nkpt_shape: [2, 3]\nflip_idx: [0, 1]\nnames:\n{names}\n")

    completed = sum(
        1 for split in ("train", "val")
        for entry in os.scandir(os.path.join(output, "images", split))
        if entry.is_file() and entry.name.lower().endswith(".png")
    )
    if completed and not args.resume:
        raise SystemExit(f"Output already contains {completed} images; use --resume to continue it")
    if completed >= args.images:
        print(f"Dataset is already complete: {completed}/{args.images} images")
        return
    original = {root: (root.location.copy(), root.rotation_euler.copy(), root.scale.copy()) for root in roots}
    # Preserve the deliberately balanced lighting stored in the .blend.  The
    # old 350--1000 W override was the source of the washed-out renders.
    base_light_energy = {
        light: light.data.energy
        for light in bpy.data.objects
        if light.type == "LIGHT"
    }
    try:
        for index in range(completed, args.images):
            split = "val" if random.random() < args.val_ratio else "train"
            for root in roots:
                set_render_visibility(root, False)
            active = [random.choice(roots)]
            if len(roots) > 1 and args.max_shoes >= 2 and random.random() < args.two_shoe_probability:
                matching_pair = [root for root in roots if root.get("pair_name") == active[0].get("pair_name") and root != active[0]]
                if matching_pair and random.random() < args.same_pair_probability:
                    active.append(random.choice(matching_pair))
                else:
                    active.append(random.choice([root for root in roots if root != active[0]]))
            occupied = []
            for root in active:
                set_render_visibility(root, True)
                # Keep multi-shoe samples separated so that one keypoint is
                # not hidden by another synthetic shoe.
                location = Vector((random.uniform(-0.55, 0.55), random.uniform(-0.55, 0.55), 0))
                for _ in range(20):
                    if all((location - other).length >= 0.42 for other in occupied):
                        break
                    location = Vector((random.uniform(-0.55, 0.55), random.uniform(-0.55, 0.55), 0))
                occupied.append(location)
                root.location = location
                # Keep the sole on the floor and the camera overhead: only
                # yaw changes, never pitch/roll.  Bound yaw to the real setup
                # if shoes are usually presented from a limited direction.
                root.rotation_euler = (0, 0, random.uniform(args.yaw_min_deg, args.yaw_max_deg) * 0.01745329252)
                scale = random.uniform(0.88, 1.12)
                root.scale = (scale, scale, scale)
            # Retain the real floor texture and make only a subtle, bounded
            # lighting change per image. This keeps exposure realistic.
            for light, energy in base_light_energy.items():
                light.data.energy = energy * random.uniform(
                    1 - args.light_jitter, 1 + args.light_jitter
                )

            bpy.context.view_layer.update()
            labels = [shoe_label(scene, camera, root, class_id[root["class_name"]]) for root in active]
            labels = [label for label in labels if label is not None]
            if not labels:
                continue
            stem = f"shoe_{index:06d}"
            image_path = os.path.join(output, "images", split, stem + ".png")
            scene.render.filepath = image_path
            bpy.ops.render.render(write_still=True)
            with open(os.path.join(output, "labels", split, stem + ".txt"), "w", encoding="utf-8") as file:
                file.write("\n".join(fmt(label) for label in labels) + "\n")
    finally:
        for root, (location, rotation, scale) in original.items():
            root.location, root.rotation_euler, root.scale = location, rotation, scale
        for light, energy in base_light_energy.items():
            light.data.energy = energy
    print(f"Dataset written to {output}")


if __name__ == "__main__":
    main()
