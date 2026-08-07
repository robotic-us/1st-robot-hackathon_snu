"""Import OBJ shoes into a Blender scene and add editable toe/heel markers.

Run from Blender:
  blender --python tools/blender/prepare_shoe_scene.py -- obj_files out/toe_heel_scene.blend

The marker positions are only first guesses.  Open the saved .blend and move
the two landmark EMPTY objects for EVERY SHOE_n root until they sit at the
real anatomical toe and heel.  The renderer uses those exact 3-D locations as
its ground truth.
"""
import os
import sys

import bpy
from mathutils import Vector


def cli_args():
    args = sys.argv
    return args[args.index("--") + 1 :] if "--" in args else []


def import_obj(path):
    bpy.ops.object.select_all(action="DESELECT")
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=path)
    else:  # Blender 3.x
        bpy.ops.import_scene.obj(filepath=path)
    return list(bpy.context.selected_objects)


def add_marker(name, location, parent):
    bpy.ops.object.empty_add(type="SPHERE", radius=0.015, location=location)
    marker = bpy.context.object
    # Blender object names are globally unique, so use unique display names
    # while retaining the semantic name in a custom property.
    marker.name = f"{name}_{parent.name}"
    marker["landmark"] = name
    marker.empty_display_size = 0.025
    marker.color = (0.1, 0.9, 0.15, 1.0) if name == "toe" else (0.95, 0.1, 0.1, 1.0)
    marker.parent = parent
    marker.matrix_parent_inverse = parent.matrix_world.inverted()
    return marker


def setup_camera_and_lights():
    bpy.ops.object.camera_add(location=(0, 0, 2.8))
    camera = bpy.context.object
    camera.name = "DatasetCamera"
    camera.data.lens = 50
    bpy.context.scene.camera = camera

    for loc, energy, size in [((-1.5, -1.0, 2.5), 900, 1.8), ((1.4, 0.8, 2.0), 500, 1.2)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size

    bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, -0.02))
    floor = bpy.context.object
    floor.name = "Floor"
    material = bpy.data.materials.new("FloorMaterial")
    material.diffuse_color = (0.28, 0.28, 0.28, 1)
    floor.data.materials.append(material)


def main():
    args = cli_args()
    if len(args) != 2:
        raise SystemExit("Usage: -- <obj_files_directory> <output.blend>")
    obj_dir, output = map(os.path.abspath, args)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    shoes = bpy.data.collections.new("SHOES")
    bpy.context.scene.collection.children.link(shoes)

    obj_paths = []
    for entry in sorted(os.listdir(obj_dir)):
        candidate = os.path.join(obj_dir, entry, "3DModel.obj")
        if os.path.isfile(candidate):
            obj_paths.append(candidate)
    if not obj_paths:
        raise SystemExit("No obj_files/*/3DModel.obj files found")

    for number, path in enumerate(obj_paths, start=1):
        objects = import_obj(path)
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        root = bpy.context.object
        root.name = f"SHOE_{number}"
        root["source_obj"] = path
        # Spread the models out for easy first-time marker placement.  The
        # dataset renderer replaces these positions for every rendered image.
        root.location.x = (number - (len(obj_paths) + 1) / 2) * 0.8
        shoes.objects.link(root)
        bpy.context.collection.objects.unlink(root)

        vertices = []
        for obj in objects:
            # Move imported meshes under the SHOES collection and root.
            for collection in list(obj.users_collection):
                collection.objects.unlink(obj)
            shoes.objects.link(obj)
            obj.parent = root
            obj.matrix_parent_inverse = root.matrix_world.inverted()
            if obj.type == "MESH":
                vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
        if not vertices:
            raise RuntimeError(f"{path} did not import a mesh")

        # A rough visual starting point only.  Move these markers manually.
        low_x = min(v.x for v in vertices)
        high_x = max(v.x for v in vertices)
        center_y = sum(v.y for v in vertices) / len(vertices)
        low_z = min(v.z for v in vertices)
        add_marker("toe", Vector((high_x, center_y, low_z)), root)
        add_marker("heel", Vector((low_x, center_y, low_z)), root)

    setup_camera_and_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    os.makedirs(os.path.dirname(output), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output)
    print(f"Saved {output}. Manually place toe/heel empties before rendering.")


if __name__ == "__main__":
    main()
