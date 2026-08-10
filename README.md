# PHORCE Shoe Valet

An overhead-camera shoe valet prototype built for the 1st Robot Hackathon at
Seoul National University. The project detects one or two shoes, estimates
their heel-to-toe heading, waits for a stable safe condition, and then selects
a manually verified PHORCE motion sequence.

> **Safety status:** this is a supervised prototype. Camera-only dry-run is
> the default. Real robot motion requires explicit `--execute`, manually
> verified PCM slots, a clear workspace, and the physical E-stop.

## What it demonstrates

- **Computer vision:** YOLO pose inference on a fixed overhead camera, with
  shoe boxes, heel/toe landmarks, tracking, and orientation overlays.
- **Physical calibration:** four-corner perspective calibration converts camera
  pixels to a measured 50 x 80 cm floor workspace.
- **Robot integration:** a five-second stability lock plus double-Space
  confirmation gates a four-part taught PHORCE sequence.
- **Data work:** Blender-generated and manually labelled real-shoe data were
  used for the pose-model experiments. Representative samples and training
  metrics are included; full datasets and weights remain local.

## System flow

```text
overhead camera -> YOLO pose + tracking -> heading validation
       -> 5 s stable lock -> double-Space confirmation -> verified PCM slots
```

The current controller accepts either one shoe or two shoes aligned within
18 degrees. Their selected heading must be 0 degrees (+/-18 degrees), then it
runs the four manually taught slots `11 -> 12 -> 13 -> 16` when execution is
explicitly enabled.

## Repository layout

- `operations/` — the safe, discrete PHORCE controller and camera-floor
  calibration utility.
- `vision/` — Jetson GPU tracker, model setup, and vision experiments.
- `scripts/`, `tools/blender/` — capture, labelling, dataset-preparation, and
  synthetic-data tools.
- `sample_images/`, `training/` — curated evidence of the data and training
  workflow.
- `artifacts/` — small, runnable pose/detection weights and selected training
  outputs used to document the final result.
- `assets/meshes/` — the shoe meshes used by the synthetic-data workflow.
- `docs/` — architecture, implementation notes, and hackathon references.

## Run a camera-only demonstration

On the Jetson used for development (JetPack 6.2 / CUDA 12.6):

```bash
git clone https://github.com/robotic-us/1st-robot-hackathon_snu.git
cd 1st-robot-hackathon_snu/vision
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-jetson-gpu.txt \
  --extra-index-url=https://pypi.jetson-ai-lab.io/jp6/cu126
cd ..
bash operations/run_shoe_valet_gpu.sh
```

The default invocation never connects to or moves the robot. Press `Q` or
`Esc` to exit. Press `C` in the controller to record the four floor corners in
TL, TR, BR, BL order when recalibrating the workspace.

To operate the arm, first review and manually verify every taught PCM slot.
Only then use `bash operations/run_shoe_valet_gpu.sh --execute` under direct
supervision.

## Results and limitations

The real-only pose baseline achieved 99.5% box/pose mAP@50 and 98.3% pose
mAP@50-95 on 51 held-out images from the captured data. Because these images
share capture sessions with the training material, live-camera evaluation is
the meaningful acceptance test. Left/right classification was not reliable
enough to become a robot-control input.

See [the architecture](docs/architecture.md),
[the development record](docs/project-history.md), and
[the controller guide](operations/README.md) for details.

## What is intentionally not committed

Large generated datasets, Blender scenes, local virtual environments, and
cloud API credentials are excluded through `.gitignore`. The repository keeps
the irreplaceable raw shoe/floor captures, source meshes, curated sample
images, selected small checkpoints, and training evidence. Never commit `.env`
files, keys, or hardware-specific secrets.

For the retained-versus-regenerated inventory, see
[the backup manifest](docs/backup-manifest.md).
