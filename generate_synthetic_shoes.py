#!/usr/bin/env python3
"""Render labeled overhead shoe scenes from the textured OBJ scans in Blender.

Run with:
  blender --background --python generate_synthetic_shoes.py -- \
    --manifest shoe_assets.json --output data/synthetic_shoes --count 500

The renderer writes RGB images, color-coded instance masks, and scene metadata.
Run build_synthetic_annotations.py afterward to create per-instance JSON and
YOLO segmentation labels.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

try:
    import bpy
except ImportError as error:
    raise SystemExit("This script must be run by Blender, not regular Python.") from error


ID_COLORS = [
    (1.0, 0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0, 1.0),
    (0.0, 0.0, 1.0, 1.0),
    (1.0, 1.0, 0.0, 1.0),
    (1.0, 0.0, 1.0, 1.0),
    (0.0, 1.0, 1.0, 1.0),
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("shoe_assets.json"))
    parser.add_argument("--output", type=Path, default=Path("data/synthetic_shoes"))
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--min-shoes", type=int, default=2)
    parser.add_argument("--max-shoes", type=int, default=6)
    parser.add_argument("--assumed-length-cm", type=float, default=28.0)
    parser.add_argument("--camera-height-cm", type=float, default=65.0)
    parser.add_argument("--horizontal-fov-deg", type=float, default=55.0)
    parser.add_argument("--area-width-cm", type=float, default=60.0)
    parser.add_argument("--area-height-cm", type=float, default=35.0)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)


def add_floor(width_m: float, height_m: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "floor"
    floor.scale = (width_m, height_m, 1.0)
    material = bpy.data.materials.new("floor_material")
    material.diffuse_color = (0.35, 0.35, 0.35, 1.0)
    floor.data.materials.append(material)
    return floor


def add_camera(width: int, height: int, height_m: float, horizontal_fov_deg: float) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=(0.0, 0.0, height_m), rotation=(0.0, 0.0, 0.0))
    camera = bpy.context.object
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.sensor_width = 36.0
    camera.data.lens = camera.data.sensor_width / (2.0 * math.tan(math.radians(horizontal_fov_deg) / 2.0))
    # Cameras look down local -Z. No rotation is needed at this location.
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    return camera


def add_light(rng: random.Random) -> bpy.types.Object:
    bpy.ops.object.light_add(type="AREA", location=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1.0))
    light = bpy.context.object
    light.data.energy = rng.uniform(500.0, 900.0)
    light.data.shape = "DISK"
    light.data.size = rng.uniform(0.4, 0.8)
    return light


def import_asset(asset: dict[str, object], root: Path) -> bpy.types.Object:
    path = (root / str(asset["obj_path"])).resolve()
    forward = str(asset.get("source_toe_axis", "+Z")).replace("+", "")
    up = str(asset.get("source_up_axis", "+Y")).replace("+", "")
    before = set(bpy.context.scene.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(path), forward_axis=forward, up_axis=up)
    else:
        bpy.ops.import_scene.obj(filepath=str(path), axis_forward=forward, axis_up=up)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise RuntimeError(f"OBJ import produced no mesh: {path}")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    if len(imported) > 1:
        bpy.ops.object.join()
    shoe = bpy.context.object
    shoe.name = str(asset["asset_id"])
    return shoe


def normalize_and_place(
    shoe: bpy.types.Object,
    target_length_m: float,
    x: float,
    y: float,
    yaw: float,
) -> None:
    bpy.context.view_layer.update()
    corners = [shoe.matrix_world @ __import__("mathutils").Vector(corner) for corner in shoe.bound_box]
    horizontal_extent = max(max(p.x for p in corners) - min(p.x for p in corners), max(p.y for p in corners) - min(p.y for p in corners))
    scale = target_length_m / horizontal_extent
    shoe.scale = (scale, scale, scale)
    shoe.rotation_euler[2] = yaw
    bpy.context.view_layer.update()
    corners = [shoe.matrix_world @ __import__("mathutils").Vector(corner) for corner in shoe.bound_box]
    center_x = (min(p.x for p in corners) + max(p.x for p in corners)) / 2.0
    center_y = (min(p.y for p in corners) + max(p.y for p in corners)) / 2.0
    min_z = min(p.z for p in corners)
    shoe.location += __import__("mathutils").Vector((x - center_x, y - center_y, 0.004 - min_z))


def emission_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission") if "ShaderNodeEmission" in dir(bpy.types) else nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def set_engine() -> None:
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def render(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest["assets"]
    if not assets:
        raise SystemExit("Manifest contains no assets")
    if args.max_shoes > len(ID_COLORS):
        raise SystemExit(f"--max-shoes cannot exceed {len(ID_COLORS)}")

    clear_scene()
    set_engine()
    area_width_m = args.area_width_cm / 100.0
    area_height_m = args.area_height_cm / 100.0
    # The measured work area is an ROI on a larger physical floor, so extend
    # the rendered floor beyond the camera frustum instead of drawing an edge.
    floor = add_floor(max(1.2, area_width_m * 1.5), max(0.9, area_height_m * 2.0))
    add_camera(args.width, args.height, args.camera_height_cm / 100.0, args.horizontal_fov_deg)
    light = add_light(rng)
    world = bpy.context.scene.world

    for frame_index in range(args.count):
        for obj in list(bpy.context.scene.objects):
            if obj.get("synthetic_shoe"):
                bpy.data.objects.remove(obj, do_unlink=True)

        floor.data.materials[0].diffuse_color = (*[rng.uniform(0.12, 0.72) for _ in range(3)], 1.0)
        world.color = tuple(rng.uniform(0.03, 0.18) for _ in range(3))
        light.data.energy = rng.uniform(450.0, 950.0)
        count = rng.randint(args.min_shoes, args.max_shoes)
        shoes: list[bpy.types.Object] = []
        records: list[dict[str, object]] = []
        positions: list[tuple[float, float]] = []
        for instance_id in range(1, count + 1):
            asset = rng.choice(assets)
            shoe = import_asset(asset, manifest_path.parent)
            shoe["synthetic_shoe"] = True
            # Mostly separated samples, with occasional close/touching layouts.
            for _attempt in range(100):
                x_margin = min(0.15, area_width_m * 0.22)
                y_margin = min(0.15, area_height_m * 0.22)
                x = rng.uniform(-area_width_m / 2.0 + x_margin, area_width_m / 2.0 - x_margin)
                y = rng.uniform(-area_height_m / 2.0 + y_margin, area_height_m / 2.0 - y_margin)
                min_gap = 0.10 if rng.random() < 0.2 else 0.18
                if all(math.hypot(x - px, y - py) >= min_gap for px, py in positions):
                    break
            positions.append((x, y))
            yaw = rng.uniform(-math.pi, math.pi)
            measured = asset.get("length_cm")
            length_cm = float(measured) if measured is not None else args.assumed_length_cm
            normalize_and_place(shoe, length_cm / 100.0, x, y, yaw)
            shoe["instance_id"] = instance_id
            shoes.append(shoe)
            records.append(
                {
                    "instance_id": instance_id,
                    "mask_rgb": [int(round(c * 255)) for c in ID_COLORS[instance_id - 1][:3]],
                    "asset_id": asset["asset_id"],
                    "pair_id": asset["pair_id"],
                    "side": asset["side"],
                    "length_cm": length_cm,
                    "length_is_assumed": measured is None,
                    "center_world_m": [round(x, 5), round(y, 5), 0.0],
                    "yaw_rad": round(yaw, 6),
                }
            )

        stem = f"scene_{frame_index:06d}"
        render(args.output / "images" / f"{stem}.png")
        original_materials = [[slot.material for slot in shoe.material_slots] for shoe in shoes]
        floor_original = floor.data.materials[0]
        floor.data.materials.clear()
        floor.data.materials.append(emission_material(f"mask_floor_{frame_index}", (0.0, 0.0, 0.0, 1.0)))
        light.hide_render = True
        for shoe, color in zip(shoes, ID_COLORS):
            shoe.data.materials.clear()
            shoe.data.materials.append(emission_material(f"mask_{frame_index}_{shoe['instance_id']}", color))
        render(args.output / "instance_masks" / f"{stem}.png")
        floor.data.materials.clear()
        floor.data.materials.append(floor_original)
        light.hide_render = False
        for shoe, materials in zip(shoes, original_materials):
            shoe.data.materials.clear()
            for material in materials:
                shoe.data.materials.append(material)

        meta_path = args.output / "metadata" / f"{stem}.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "image_size_px": [args.width, args.height],
                    "camera": {
                        "height_cm": args.camera_height_cm,
                        "horizontal_fov_deg": args.horizontal_fov_deg,
                        "mount": "overhead_downward",
                    },
                    "work_area_cm": [args.area_width_cm, args.area_height_cm],
                    "instances": records,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Rendered {frame_index + 1}/{args.count}: {stem}")


if __name__ == "__main__":
    main()
