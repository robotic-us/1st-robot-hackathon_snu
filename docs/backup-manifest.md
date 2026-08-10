# Backup manifest

This repository is prepared as the durable project record before the local
machine is reformatted.

## Kept in Git

- Current robot-control, vision, calibration, data-preparation, and Blender
  source code.
- Current camera-floor calibration configuration.
- Curated detector and pose checkpoints plus selected training evidence in
  `artifacts/`.
- All source shoe meshes in `assets/meshes/`.
- Original real-shoe captures, their manual labels, and floor references in
  `archive/`.
- Earlier small prototype source, reference material, and general-detector
  experiment records in `archive/`.

## Deliberately omitted

- Local Python virtual environments and bytecode: reconstructed from the
  versioned requirements files.
- Blender temporary files and renders: regenerated from the versioned Blender
  scripts and source meshes.
- Generated synthetic datasets, derived training datasets, and duplicate
  experiment runs: regenerated from scripts plus the retained source meshes,
  floor references, and raw captures.
- The third-party general-shoe dataset: its configuration and preparation tool
  are retained, but the bulk downloaded copy is not republished here.

No API keys or `.env` files are included. Before reformatting, confirm the
remote repository shows the latest commit and clone it once on another device
if an independent restore check is desired.
