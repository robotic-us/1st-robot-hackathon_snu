"""Generate a small synthetic YOLO pose dataset from the supplied shoe OBJ files.

Use in Blender 3.x:
  1. Open Blender and switch to the Scripting workspace.
  2. Open this file in the Text Editor.
  3. Press Run Script (the triangle button).

The output appears in synthetic_shoes/ next to this script's project folder.
"""

from pathlib import Path
import math
import random
import shutil

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


# Training-sized generation for all six confirmed left/right shoe classes.
TOTAL_IMAGES = 600
IMAGE_SIZE = 640
TRAIN_FRACTION = 0.8
RANDOM_SEED = 20260807
TOP_DOWN_FRACTION = 0.8  # Match the overhead deployment camera.

# The project location is explicit so the script also works when Blender runs a
# temporary copy of it (where __file__ may appear as /generate_shoe_dataset.py).
ROOT = Path("/home/phorce/comp")
OUTPUT_ROOT = ROOT / "synthetic_shoes"

# Confirmed shoe classes. Each Boolean records whether the red review marker
# (PCA endpoint A) is the toe; slipperL was the single blue-toe exception.
ASSETS = {
    "pair1_right": ROOT / "obj_files/object1/3DModel.obj",
    "pair1_left": ROOT / "obj_files/object2/3DModel.obj",
    "pair2_right": ROOT / "obj_files/object3/3DModel.obj",
    "pair2_left": ROOT / "obj_files/brownL/3DModel.obj",
    "pair3_right": ROOT / "obj_files/slipperR/3DModel.obj",
    "pair3_left": ROOT / "obj_files/slipperL/3DModel.obj",
}
ENDPOINT_A_IS_TOE = {
    "pair1_right": True,
    "pair1_left": True,
    "pair2_right": True,
    "pair2_left": True,
    "pair3_right": True,
    "pair3_left": False,
}
CLASS_ID = {name: index for index, name in enumerate(ASSETS)}


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def delete_scene_objects():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def purge_unused_data():
    """Keep a long render run from retaining one imported mesh per frame."""
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for datablock in list(collection):
            if datablock.users == 0:
                collection.remove(datablock)


def make_material(name, color, roughness=0.75):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1)
    principled.inputs["Roughness"].default_value = roughness
    return material


def add_area_light(location, energy, size):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.size = size
    look_at(light, (0, 0, 0))
    return light


def prepare_scene():
    delete_scene_objects()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 3
    scene.eevee.gtao_factor = 1.3
    scene.render.resolution_x = IMAGE_SIZE
    scene.render.resolution_y = IMAGE_SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.10, 0.10, 0.10)

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "Randomized floor"
    floor.data.materials.append(make_material("Dataset floor", (0.18, 0.18, 0.18)))

    # Soft key and fill lights keep the scan texture visible, while preserving
    # shadows that a camera is likely to see in a real room.
    add_area_light((3.5, -3.0, 5.5), energy=950, size=4.0)
    add_area_light((-3.0, -0.5, 3.0), energy=500, size=3.0)

    bpy.ops.object.camera_add(location=(0, -4.2, 4.8))
    camera = bpy.context.object
    camera.name = "Dataset camera"
    camera.data.lens = 52
    look_at(camera, (0, 0, 0))
    scene.camera = camera
    return floor, camera


def import_shoe(asset_path, position, yaw, endpoint_a_is_toe):
    """Import, make source-Y vertical, normalize its size, then place it."""
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.obj(filepath=str(asset_path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"Expected one mesh in {asset_path}; found {len(imported)}")
    shoe = imported[0]

    # KIRI's OBJ models use Y as their up axis; Blender uses Z.
    shoe.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.view_layer.update()

    corners = [shoe.matrix_world @ Vector(corner) for corner in shoe.bound_box]
    min_corner = Vector((min(point[i] for point in corners) for i in range(3)))
    max_corner = Vector((max(point[i] for point in corners) for i in range(3)))
    horizontal_size = max(max_corner.x - min_corner.x, max_corner.y - min_corner.y)
    shoe.scale *= 1.0 / horizontal_size
    bpy.context.view_layer.update()

    corners = [shoe.matrix_world @ Vector(corner) for corner in shoe.bound_box]
    min_corner = Vector((min(point[i] for point in corners) for i in range(3)))
    max_corner = Vector((max(point[i] for point in corners) for i in range(3)))
    shoe.location.x -= (min_corner.x + max_corner.x) / 2
    shoe.location.y -= (min_corner.y + max_corner.y) / 2
    shoe.location.z -= min_corner.z
    bpy.context.view_layer.update()

    # Store fixed mesh-local landmarks before the randomized placement rotates
    # the shoe, then apply the per-scan toe/heel confirmation.
    endpoint_a_local, endpoint_b_local = keypoint_local_points(shoe)
    if endpoint_a_is_toe:
        toe_local, heel_local = endpoint_a_local, endpoint_b_local
    else:
        toe_local, heel_local = endpoint_b_local, endpoint_a_local

    # Use an empty as a global yaw parent, so the shoe stays upright.
    parent = bpy.data.objects.new("Shoe placement", None)
    bpy.context.collection.objects.link(parent)
    shoe.parent = parent
    parent.location = position
    parent.rotation_euler[2] = yaw
    bpy.context.view_layer.update()
    return shoe, parent, heel_local, toe_local


def keypoint_local_points(shoe):
    """Return (endpoint A, endpoint B) as local points along the PCA axis."""
    points = [shoe.matrix_world @ vertex.co for vertex in shoe.data.vertices]
    mean_x = sum(point.x for point in points) / len(points)
    mean_y = sum(point.y for point in points) / len(points)
    xx = sum((point.x - mean_x) ** 2 for point in points)
    yy = sum((point.y - mean_y) ** 2 for point in points)
    xy = sum((point.x - mean_x) * (point.y - mean_y) for point in points)
    angle = 0.5 * math.atan2(2 * xy, xx - yy)
    axis_x, axis_y = math.cos(angle), math.sin(angle)
    ordered = sorted(points, key=lambda point: (point.x - mean_x) * axis_x + (point.y - mean_y) * axis_y)
    band_size = max(20, int(len(ordered) * 0.015))
    endpoint_a = sum(ordered[:band_size], Vector()) / band_size
    endpoint_b = sum(ordered[-band_size:], Vector()) / band_size
    inverse_matrix = shoe.matrix_world.inverted()
    return inverse_matrix @ endpoint_a, inverse_matrix @ endpoint_b


def yolo_box(scene, camera, shoe):
    """Return a tight projected box around mesh vertices, clipped to the frame."""
    projected = []
    for vertex in shoe.data.vertices:
        point = world_to_camera_view(scene, camera, shoe.matrix_world @ vertex.co)
        if point.z > 0:
            projected.append(point)
    if not projected:
        return None

    xmin = max(0.0, min(point.x for point in projected))
    xmax = min(1.0, max(point.x for point in projected))
    ymin = max(0.0, min(point.y for point in projected))
    ymax = min(1.0, max(point.y for point in projected))
    if xmax - xmin < 0.015 or ymax - ymin < 0.015:
        return None

    # Blender camera coordinates start at the bottom-left; YOLO starts at top-left.
    return ((xmin + xmax) / 2, 1 - (ymin + ymax) / 2, xmax - xmin, ymax - ymin)


def yolo_keypoint(scene, camera, shoe, local_point):
    """Project a local heel/toe point as YOLO pose x y visibility."""
    point = world_to_camera_view(scene, camera, shoe.matrix_world @ local_point)
    if point.z <= 0 or not (0 <= point.x <= 1 and 0 <= point.y <= 1):
        return (0.0, 0.0, 0)
    return (point.x, 1 - point.y, 2)  # 2 = labeled and visible


def choose_positions(count):
    """Mostly separated shoes, with occasional intentional partial overlap."""
    positions = [(random.uniform(-0.75, 0.75), random.uniform(-0.5, 0.55), 0)]
    for _ in range(1, count):
        if random.random() < 0.25:
            base = random.choice(positions)
            positions.append((base[0] + random.uniform(-0.32, 0.32), base[1] + random.uniform(-0.25, 0.25), 0))
        else:
            positions.append((random.uniform(-1.05, 1.05), random.uniform(-0.7, 0.7), 0))
    return positions


def write_dataset_files():
    (OUTPUT_ROOT / "classes.txt").write_text("\n".join(ASSETS) + "\n", encoding="utf-8")
    yaml = "\n".join([
        f"path: {OUTPUT_ROOT}",
        "train: images/train",
        "val: images/val",
        "kpt_shape: [2, 3]",
        "flip_idx: [0, 1]",
        "names:",
        *[f"  {class_id}: {name}" for name, class_id in CLASS_ID.items()],
        "",
    ])
    (OUTPUT_ROOT / "data.yaml").write_text(yaml, encoding="utf-8")


def clear_previous_dataset():
    """Avoid stale files or split duplicates when regenerating all classes."""
    for directory in (OUTPUT_ROOT / "images", OUTPUT_ROOT / "labels"):
        if directory.exists():
            shutil.rmtree(directory)


def main():
    random.seed(RANDOM_SEED)
    if not all(path.exists() for path in ASSETS.values()):
        missing = [str(path) for path in ASSETS.values() if not path.exists()]
        raise FileNotFoundError("Missing OBJ files: " + ", ".join(missing))

    clear_previous_dataset()
    for split in ("train", "val"):
        (OUTPUT_ROOT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_ROOT / "labels" / split).mkdir(parents=True, exist_ok=True)
    write_dataset_files()

    floor, camera = prepare_scene()
    scene = bpy.context.scene
    for frame_number in range(TOTAL_IMAGES):
        split = "train" if random.random() < TRAIN_FRACTION else "val"
        stem = f"shoe_{frame_number:04d}"

        # Randomize one reusable floor material for basic domain variation.
        floor_shader = floor.data.materials[0].node_tree.nodes.get("Principled BSDF")
        floor_shader.inputs["Base Color"].default_value = (
            random.uniform(0.08, 0.35),
            random.uniform(0.08, 0.30),
            random.uniform(0.08, 0.25),
            1,
        )

        instances = []
        asset_names = random.choices(list(ASSETS), k=random.choices([1, 2, 3], weights=[0.35, 0.48, 0.17])[0])
        for name, position in zip(asset_names, choose_positions(len(asset_names))):
            shoe, parent, heel_local, toe_local = import_shoe(
                ASSETS[name], position, random.uniform(0, math.tau), ENDPOINT_A_IS_TOE[name]
            )
            instances.append((name, shoe, parent, heel_local, toe_local))

        # The real camera is mostly overhead. Keep a small oblique minority so
        # the model tolerates mounting/placement variation without drifting from
        # the deployment viewpoint.
        target = (random.uniform(-0.12, 0.12), random.uniform(-0.10, 0.10), 0)
        if random.random() < TOP_DOWN_FRACTION:
            camera.location = (random.uniform(-0.35, 0.35), random.uniform(-0.35, 0.35), random.uniform(5.4, 6.3))
        else:
            camera.location = (random.uniform(-0.25, 0.25), random.uniform(-3.6, -3.0), random.uniform(5.0, 5.7))
        look_at(camera, target)
        scene.render.filepath = str(OUTPUT_ROOT / "images" / split / f"{stem}.png")
        bpy.ops.render.render(write_still=True)

        labels = []
        for name, shoe, _parent, heel_local, toe_local in instances:
            box = yolo_box(scene, camera, shoe)
            if box:
                heel = yolo_keypoint(scene, camera, shoe, heel_local)
                toe = yolo_keypoint(scene, camera, shoe, toe_local)
                labels.append(
                    f"{CLASS_ID[name]} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f} "
                    f"{heel[0]:.6f} {heel[1]:.6f} {heel[2]} "
                    f"{toe[0]:.6f} {toe[1]:.6f} {toe[2]}"
                )
        (OUTPUT_ROOT / "labels" / split / f"{stem}.txt").write_text("\n".join(labels), encoding="utf-8")

        for _name, shoe, parent, _heel_local, _toe_local in instances:
            bpy.data.objects.remove(shoe, do_unlink=True)
            bpy.data.objects.remove(parent, do_unlink=True)
        if frame_number % 25 == 0:
            purge_unused_data()
        if frame_number % 25 == 0 or frame_number == TOTAL_IMAGES - 1:
            print(f"Rendered {frame_number + 1}/{TOTAL_IMAGES}")

    print(f"Done. Dataset written to: {OUTPUT_ROOT}")


main()
