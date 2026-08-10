# Development record

This record summarizes the evolution represented by the repository history and
the current implementation.

| Area | Work completed | Current role |
| --- | --- | --- |
| Vision prototypes | Webcam, floor-subtraction, and cloud-assisted shoe experiments | Earlier experiments retained under `vision/references/` |
| Pose estimation | Synthetic Blender data plus manually labelled real images; heel/toe keypoints | Local YOLO pose model supplies controller landmarks |
| Calibration | Perspective mapping from four floor corners to a measured workspace | Centimetre telemetry and calibration record |
| Robot control | Evolved from multi-situation matching to one safe, angle-only condition | Selects a manually verified four-slot PHORCE sequence |
| Safety | Dry-run behavior, stable lock, preview, and human confirmation | Required before any execution |

## Design decisions

- **Use a single 0-degree condition first.** Reducing the action space made
  testing and verification tractable during the hackathon.
- **Ignore position for motion selection.** The current taught sequence is
  angle-based; calibrated position is shown for operator awareness rather than
  treated as a precise grasp target.
- **Keep left/right classification out of control.** It remained unreliable
  for some gray shoes, so it is visual guidance only.
- **Version code and evidence, not bulk artifacts.** Source data, checkpoints,
  virtual environments, and renders stay local or belong in dedicated artifact
  storage; this Git repository stays cloneable and reviewable.

## Reproducing the project state

Use the scripts in `scripts/` and `tools/blender/` to recreate data-generation
steps, `vision/requirements-jetson-gpu.txt` for the Jetson environment, and
`operations/README.md` for the supervised camera and robot-control workflow.
