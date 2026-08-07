"""Render a simple, labeled preview of every OBJ in obj_files.

Run from the project folder:
    blender --background --python scripts/preview_models.py
"""

from pathlib import Path
import math
import bpy
from mathutils import Vector


# Keep this usable from Blender's Text Editor, which can run a temporary copy.
ROOT = Path("/home/phorce/comp")
ASSETS = sorted(ROOT.glob("obj_files/*/3DModel.obj"))
OUTPUT = ROOT / "renders" / "previews"
OUTPUT.mkdir(parents=True, exist_ok=True)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in datablocks:
            if datablock.users == 0:
                datablocks.remove(datablock)


def add_floor(size):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    floor = bpy.context.object
    material = bpy.data.materials.new("Preview floor")
    material.diffuse_color = (0.15, 0.17, 0.20, 1)
    floor.data.materials.append(material)
    return floor


def render_asset(path):
    clear_scene()
    bpy.ops.import_scene.obj(filepath=str(path))
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError(f"No mesh found in {path}")

    shoe = mesh_objects[0]
    bpy.context.view_layer.objects.active = shoe
    shoe.select_set(True)
    bpy.ops.object.shade_smooth()

    corners = [shoe.matrix_world @ Vector(corner) for corner in shoe.bound_box]
    min_corner = Vector((min(v[i] for v in corners) for i in range(3)))
    max_corner = Vector((max(v[i] for v in corners) for i in range(3)))
    centre = (min_corner + max_corner) / 2
    size = max(max_corner - min_corner)
    shoe.location.z -= min_corner.z
    centre.z -= min_corner.z

    add_floor(max(2.5, size * 3))
    bpy.ops.object.light_add(type="AREA", location=(size * 1.5, -size * 1.5, size * 2))
    bpy.context.object.data.energy = 800
    bpy.context.object.data.size = size * 2
    bpy.ops.object.light_add(type="AREA", location=(-size, size, size))
    bpy.context.object.data.energy = 400
    bpy.context.object.data.size = size

    bpy.ops.object.camera_add(location=(size * 1.8, -size * 1.8, size * 1.3))
    camera = bpy.context.object
    camera.data.lens = 50
    look_at(camera, centre)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT / f"{path.parent.name}.png")
    scene.world.color = (0.055, 0.065, 0.08)
    bpy.ops.render.render(write_still=True)


for asset in ASSETS:
    render_asset(asset)
    print(f"Rendered {asset}")
