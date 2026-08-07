"""Create a four-sneaker Blender scene with editable toe/heel markers.

Run:
  blender --python tools/blender/prepare_white_gray_scene.py -- generated/white_gray_scene.blend
"""

import os
import sys
import math

import bpy
from mathutils import Vector


ROOT = "/home/phorce/comp"
FLOOR_TEXTURE = f"{ROOT}/generated/floor_texture_80x60.png"
ASSETS = (
    ("white_right", "white", "right", f"{ROOT}/obj_files/object1/3DModel.obj"),
    ("white_left", "white", "left", f"{ROOT}/obj_files/object2/3DModel.obj"),
    ("gray_right", "gray", "right", f"{ROOT}/obj_files/grayR/3DModel.obj"),
    ("gray_left", "gray", "left", f"{ROOT}/obj_files/grayL/3DModel.obj"),
)
TOE_IS_RED = {
    "white_right": True,
    "white_left": True,
    "gray_right": False,
    "gray_left": True,
}


def cli_args():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def import_obj(path):
    bpy.ops.object.select_all(action="DESELECT")
    if "obj_import" in dir(bpy.ops.wm):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.obj(filepath=path)
    return list(bpy.context.selected_objects)


def add_marker(name, location, parent):
    bpy.ops.object.empty_add(type="SPHERE", radius=0.015, location=location)
    marker = bpy.context.object
    marker.name = f"{name}_{parent.name}"
    marker["landmark"] = name
    # The renderer uses this root-local coordinate directly. This avoids
    # Blender-version differences in Empty parent-inverse transforms.
    marker["landmark_local"] = tuple(location)
    marker.empty_display_size = 0.025
    marker.color = (0.1, 0.9, 0.15, 1.0) if name == "toe" else (0.95, 0.1, 0.1, 1.0)
    marker.parent = parent


def setup_camera_and_lights():
    bpy.ops.object.camera_add(location=(0, 0, 4.2))
    camera = bpy.context.object
    camera.name = "DatasetCamera"
    camera.data.lens = 55
    bpy.context.scene.camera = camera
    for location, energy, size in [((-3.0, -3.0, 5.0), 500, 3.5), ((3.0, 1.5, 4.0), 250, 3.0)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
    if not os.path.isfile(FLOOR_TEXTURE):
        raise FileNotFoundError(f"Missing floor texture: {FLOOR_TEXTURE}")
    # Shoes are normalized to roughly one unit long. A 25 cm shoe therefore
    # maps the physical 80 x 60 cm surface to 3.2 x 2.4 scene units.
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -0.02))
    floor = bpy.context.object
    floor.name = "Floor"
    floor.scale = (1.6, 1.2, 1)
    floor["physical_width_cm"] = 80
    floor["physical_height_cm"] = 60
    material = bpy.data.materials.new("FloorMaterial")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = 0.85
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(FLOOR_TEXTURE, check_existing=True)
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    floor.data.materials.append(material)
    bpy.context.scene.world.color = (0.08, 0.08, 0.08)


def candidate_endpoints(vertices):
    """Return the red (A) and blue (B) endpoints used in the review renders."""
    mean_x = sum(vertex.x for vertex in vertices) / len(vertices)
    mean_y = sum(vertex.y for vertex in vertices) / len(vertices)
    xx = sum((vertex.x - mean_x) ** 2 for vertex in vertices)
    yy = sum((vertex.y - mean_y) ** 2 for vertex in vertices)
    xy = sum((vertex.x - mean_x) * (vertex.y - mean_y) for vertex in vertices)
    angle = 0.5 * math.atan2(2 * xy, xx - yy)
    axis = Vector((math.cos(angle), math.sin(angle), 0))
    ordered = sorted(vertices, key=lambda vertex: (vertex.x - mean_x) * axis.x + (vertex.y - mean_y) * axis.y)
    band_size = max(20, int(len(ordered) * 0.015))
    red = sum(ordered[:band_size], Vector()) / band_size
    blue = sum(ordered[-band_size:], Vector()) / band_size
    height = max(vertex.z for vertex in vertices) + 0.025
    red.z = height
    blue.z = height
    return red, blue


def main():
    args = cli_args()
    if len(args) != 1:
        raise SystemExit("Usage: -- <output.blend>")
    output = os.path.abspath(args[0])
    missing = [path for _name, _pair, _side, path in ASSETS if not os.path.isfile(path)]
    if missing:
        raise SystemExit("Missing OBJ files: " + ", ".join(missing))
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    shoes = bpy.data.collections.new("SHOES")
    bpy.context.scene.collection.children.link(shoes)
    for number, (class_name, pair_name, side, path) in enumerate(ASSETS, start=1):
        objects = import_obj(path)
        meshes = [obj for obj in objects if obj.type == "MESH"]
        # KIRI OBJ scans are Y-up; rotate them into Blender's Z-up convention.
        for mesh in meshes:
            mesh.rotation_euler = (math.radians(90), 0, 0)
        bpy.context.view_layer.update()
        vertices = [mesh.matrix_world @ vertex.co for mesh in meshes for vertex in mesh.data.vertices]
        if not vertices:
            raise RuntimeError(f"{path} did not import a mesh")
        horizontal_size = max(
            max(vertex.x for vertex in vertices) - min(vertex.x for vertex in vertices),
            max(vertex.y for vertex in vertices) - min(vertex.y for vertex in vertices),
        )
        for mesh in meshes:
            mesh.scale *= 1.0 / horizontal_size
        bpy.context.view_layer.update()
        vertices = [mesh.matrix_world @ vertex.co for mesh in meshes for vertex in mesh.data.vertices]
        floor_offset = min(vertex.z for vertex in vertices)
        for mesh in meshes:
            mesh.location.z -= floor_offset
        bpy.context.view_layer.update()
        vertices = [mesh.matrix_world @ vertex.co for mesh in meshes for vertex in mesh.data.vertices]
        red, blue = candidate_endpoints(vertices)
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        root = bpy.context.object
        root.name = f"SHOE_{class_name}"
        root["class_name"] = class_name
        root["pair_name"] = pair_name
        root["side"] = side
        root["source_obj"] = path
        for collection in list(root.users_collection):
            collection.objects.unlink(root)
        shoes.objects.link(root)
        for obj in objects:
            for collection in list(obj.users_collection):
                collection.objects.unlink(obj)
            shoes.objects.link(obj)
            obj.parent = root
        toe, heel = (red, blue) if TOE_IS_RED[class_name] else (blue, red)
        add_marker("toe", toe, root)
        add_marker("heel", heel, root)
        root.location.x = (number - 2.5) * 0.85
    setup_camera_and_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output)
    print(f"Saved {output}. Move every toe/heel marker onto the real landmark before rendering.")


if __name__ == "__main__":
    main()
