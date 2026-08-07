# Synthetic toe/heel YOLO-pose dataset

This generator makes labels for two **keypoints** on every shoe: `toe` and
`heel`.  This is a better fit than object-detection boxes when the desired
output is an endpoint and an orientation vector.

## 1. Create and mark a Blender scene

From the repository root, run this once (requires Blender 3.6+):

```bash
mkdir -p generated
blender --python tools/blender/prepare_shoe_scene.py -- obj_files generated/toe_heel_scene.blend
blender generated/toe_heel_scene.blend
```

The setup script imports all three `obj_files/*/3DModel.obj` files.  Each is a
root named `SHOE_1`, `SHOE_2`, or `SHOE_3`, with two green/red Empty markers
below it (displayed as `toe_SHOE_n` and `heel_SHOE_n`).  In Blender's Outliner
expand every `SHOE_*`, select those two markers, and move them to the exact
physical toe and heel.  Do this from a side/solid view so the marker lands on
the shoe surface rather than floating above it.
Save the `.blend` when every shoe is marked.

The two shoes that form a pair do not need special labels: both use the same
two landmarks.  Rename their `SHOE_*` roots if useful, but do not rename the
the marker names or their `landmark` custom properties.

## 2. Render the training dataset

After saving the marked scene:

```bash
blender --background generated/toe_heel_scene.blend \
  --python tools/blender/generate_toe_heel_pose_dataset.py -- \
  --output generated/toe_heel_pose --images 1500 --max-shoes 2
```

This writes images and matching Ultralytics YOLO pose labels to
`generated/toe_heel_pose/`, plus `data.yaml`.  It renders one or two shoes per
image, with random placement, in-plane rotation, scale, floor colour, and
lighting.  The camera remains directly overhead: shoes are never pitched,
rolled, or rendered from their side. The marker spheres never appear in the
output images.

By default the shoe can have any flat, in-plane orientation (0–360°). If your
camera setup only sees a restricted range, match that range rather than adding
unrealistic examples. For instance, render only orientations from -40° to 40°:

```bash
blender --background generated/toe_heel_scene.blend \
  --python tools/blender/generate_toe_heel_pose_dataset.py -- \
  --output generated/toe_heel_pose --images 1500 --yaw-min-deg -40 --yaw-max-deg 40
```

The output label layout is YOLO pose format:

```text
class box_cx box_cy box_width box_height toe_x toe_y toe_visible heel_x heel_y heel_visible
```

Coordinates are normalized to 0–1 and the visibility value `2` means the point
is labelled and visible.  Check a handful of image/label pairs before training;
the labels are only as correct as the marker placement.

## 3. Train a pose model

Use an Ultralytics pose checkpoint, not the current `shoe-detector.pt` box
checkpoint:

```bash
yolo pose train model=yolo11s-pose.pt data=generated/toe_heel_pose/data.yaml imgsz=640 epochs=100
```

For real-camera performance, mix in manually labelled photographs from the
actual overhead camera.  Synthetic renders are useful to bootstrap training,
but their lighting, occlusion, background, and shoe appearance will not fully
match the deployed view.
