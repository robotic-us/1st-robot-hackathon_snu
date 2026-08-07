"""Render red/blue candidate endpoints for each shoe scan.

Run in Blender from the Scripting workspace. It writes candidate images to
keypoint_review/. For each image, identify which colored marker is at the toe.
"""

from pathlib import Path
import math

import bpy
from mathutils import Vector


ROOT = Path("/home/phorce/comp")
OUTPUT = ROOT / "keypoint_review_white_gray"
ASSETS = {
    "white_right": ROOT / "obj_files/object1/3DModel.obj",
    "white_left": ROOT / "obj_files/object2/3DModel.obj",
    "gray_right": ROOT / "obj_files/grayR/3DModel.obj",
    "gray_left": ROOT / "obj_files/grayL/3DModel.obj",
}


def look_at(obj, target=(0, 0, 0)):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def material(name, color):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = 0.35
    return result


RED = material("RED endpoint A", (0.95, 0.02, 0.02))
BLUE = material("BLUE endpoint B", (0.02, 0.15, 1.0))


def import_and_normalize(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.obj(filepath=str(path))
    shoe = next(obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH")
    shoe.rotation_euler = (math.radians(90), 0, 0)  # source Y-up -> Blender Z-up
    bpy.context.view_layer.update()

    corners = [shoe.matrix_world @ Vector(corner) for corner in shoe.bound_box]
    min_corner = Vector((min(point[i] for point in corners) for i in range(3)))
    max_corner = Vector((max(point[i] for point in corners) for i in range(3)))
    shoe.scale *= 1 / max(max_corner.x - min_corner.x, max_corner.y - min_corner.y)
    bpy.context.view_layer.update()

    corners = [shoe.matrix_world @ Vector(corner) for corner in shoe.bound_box]
    min_corner = Vector((min(point[i] for point in corners) for i in range(3)))
    max_corner = Vector((max(point[i] for point in corners) for i in range(3)))
    shoe.location.x -= (min_corner.x + max_corner.x) / 2
    shoe.location.y -= (min_corner.y + max_corner.y) / 2
    shoe.location.z -= min_corner.z
    bpy.context.view_layer.update()
    return shoe


def endpoints_from_shape(shoe):
    """Find the two ends of the shoe's longest horizontal PCA axis."""
    points = [shoe.matrix_world @ vertex.co for vertex in shoe.data.vertices]
    mean_x = sum(point.x for point in points) / len(points)
    mean_y = sum(point.y for point in points) / len(points)
    xx = sum((point.x - mean_x) ** 2 for point in points)
    yy = sum((point.y - mean_y) ** 2 for point in points)
    xy = sum((point.x - mean_x) * (point.y - mean_y) for point in points)
    angle = 0.5 * math.atan2(2 * xy, xx - yy)
    axis = Vector((math.cos(angle), math.sin(angle), 0))
    ordered = sorted(points, key=lambda point: (point.x - mean_x) * axis.x + (point.y - mean_y) * axis.y)
    # Average a tiny extreme band: more stable than an isolated scan outlier.
    band_size = max(20, int(len(ordered) * 0.015))
    end_a = sum(ordered[:band_size], Vector()) / band_size
    end_b = sum(ordered[-band_size:], Vector()) / band_size
    end_a.z = max(0.07, end_a.z)
    end_b.z = max(0.07, end_b.z)
    return end_a, end_b


def marker(location, marker_material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.065, location=location)
    sphere = bpy.context.object
    sphere.data.materials.append(marker_material)


def setup_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 3
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.12, 0.12, 0.12)
    bpy.ops.mesh.primitive_plane_add(size=10)
    bpy.context.object.data.materials.append(material("Review floor", (0.12, 0.12, 0.12)))
    for location, energy, size in [((3, -3, 5), 950, 4), ((-3, 0, 3), 500, 3)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.size = size
        look_at(light)
    bpy.ops.object.camera_add(location=(0, -3.2, 4.3))
    camera = bpy.context.object
    camera.data.lens = 55
    look_at(camera)
    scene.camera = camera


OUTPUT.mkdir(parents=True, exist_ok=True)
for name, path in ASSETS.items():
    clear_scene()
    setup_scene()
    shoe = import_and_normalize(path)
    end_a, end_b = endpoints_from_shape(shoe)
    marker(end_a, RED)
    marker(end_b, BLUE)
    bpy.context.scene.render.filepath = str(OUTPUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"{name}: red=A, blue=B; tell which color is the TOE")

print(f"Review images saved to {OUTPUT}")
