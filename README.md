# Shoe valet hackathon project

This folder is the clean working project for the hackathon. Original files in
`/home/phorce/yolo` and `/home/phorce/Downloads/1st-robot-hackathon_snu` remain
unchanged.

## Current status

The vision module is working on the fixed overhead webcam and Jetson GPU. It
detects shoes, keeps ByteTrack IDs, displays robot-relative bearings, and has
an optional Gemini-assisted toe/heel/tongue estimate for sneaker hook pickup.

## Model status

Two white/gray sneaker pose models are available:

- **Mixed model:** 1,000 Blender-generated images plus 250 labelled real
  images — `/home/phorce/runs/pose/runs/shoe_pose_white_gray_final/weights/best.pt`.
- **Real-only baseline:** 250 labelled real images —
  `/home/phorce/runs/pose/runs/shoe_pose_real_only_baseline/weights/best.pt`.

The real-only model scored 99.5% box/pose mAP@50 and 98.3% pose mAP@50–95 on
its 51 held-out real images. It locates shoes and heel/toe points very well,
but left/right classification remains unreliable, especially for gray shoes.
Those validation images came from the same capture sequences as training, so
live-camera testing is the deciding evaluation.

The robot operations skeleton is in `operations/`. It is dry-run by default,
has no verified motion IDs, and cannot move the robot until those IDs are
explicitly configured. Before real execution, complete the following in order:

1. Calibrate camera pixels to the physical floor and robot coordinate frame.
2. Test Gemini toe/heel/tongue estimates on the actual shoes and choose a
   confidence threshold that reliably rejects uncertain results.
3. Define a safe hook approach, insertion, lift, retreat, and bin-placement
   motion for the PHORCE arm.
4. Add a manual approval/stop path and workspace safety boundaries before any
   autonomous motion.

## Layout

- `vision/` — runnable GPU shoe detector/tracker, model, orientation mode, and
  camera calibration.
- `datasets/white_gray_final/` — final combined training dataset: 1,000
  synthetic images plus 250 labelled real white/gray images.
- `generated/white_gray_pose_1000/` — Blender-generated source images and
  YOLO pose labels; keep this as the reproducible synthetic-data source.
- `real_shoes/` — original captures and manual labels; keep untouched.
- `obj_files/` and `floor/` — Blender shoe meshes and real-floor references.
- `runs/` — earlier local training runs kept for comparison.
- `scripts/` and `tools/blender/` — capture, labelling, dataset-preparation,
  and Blender-generation utilities.
- `docs/hackathon-reference.md` — PHORCE API, motion-slot, and safety reference.
- `operations/` — safe discrete state machine and the verified-motion map.

Start with [vision/README.md](vision/README.md).

## Fast start

```bash
cd /home/phorce/comp/vision
bash run_live_shoe_tracker_gpu.sh --gemini-orientation
```

Use `Q` or `Esc` to quit. Gemini orientation is visual guidance only; it must
not directly command the arm.
