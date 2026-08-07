# Vision module

This module detects and tracks shoes from the fixed overhead webcam. It is the
vision input to the later robot-control module; it does **not** command the arm.

## Contents

- `models/shoe-detector.pt` — trained one-class shoe detector.
- `live_shoe_tracker.py` — webcam detection with ByteTrack IDs, confidence,
  FPS, robot-relative bearings, and optional cloud orientation estimates.
- `calibration/calibrate_floor.py` — converts camera pixels to floor centimeters.
- `config/camera_setup.json` — current camera mounting assumptions.
- `references/` — the earlier floor-subtraction prototype and shoe metadata.

## One-time Jetson GPU setup

Run on this Jetson (AGX Orin, JetPack 6.2 / CUDA 12.6):

```bash
cd /home/phorce/comp/vision
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-jetson-gpu.txt \
  --extra-index-url=https://pypi.jetson-ai-lab.io/jp6/cu126
```

Confirm that the GPU is usable from your normal terminal:

```bash
.venv/bin/python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

The expected CUDA build is `12.6`, and `torch.cuda.is_available()` should be
`True`. Do not use the prior global CUDA 13 Torch installation for this module.

## Run the live tracker

```bash
bash run_live_shoe_tracker_gpu.sh --confidence 0.25
```

Controls: `Q`/`Esc` quits, `Space` pauses, and `S` saves an annotated frame to
`live_captures/`. Lower `--confidence` to `0.20` to reduce missed shoes; raise
it if false detections occur.

Each detected shoe is also labelled with its bearing from the robot position,
shown as the red point at the bottom-center of the frame. The shoe's bounding-
box center is used: straight up is `0°`, left is positive (up to `+90°`), and
right is negative (down to `-90°`). This is an image-space aiming angle, not
the shoe's physical rotation and not yet a calibrated arm angle.

If the live display is slower than needed, use a smaller inference size first:

```bash
bash run_live_shoe_tracker_gpu.sh --imgsz 480 --width 640 --height 480
```

GPU inference has been verified on this Jetson at 33.2 FPS for the model alone
at 640 px. Webcam capture, tracking, drawing boxes, and the desktop window add
overhead, so live FPS will be lower.

## Legacy Kimi orientation

Kimi can estimate the toe and heel for each newly stable tracked shoe. It runs
in the background only once per ByteTrack ID, so the local camera and YOLO
tracking keep running while the API responds. The green (or amber, low-
confidence) arrow points from heel to toe.

Set the key in your shell, then run:

```bash
bash run_live_shoe_tracker_gpu.sh --kimi-orientation
```

The default is `kimi-k3`; override it with `--kimi-model <model-name>` if your
Kimi account enables a different vision-capable model.
Kimi is retained only as an older experimental option. Prefer Gemini below.

## Gemini sneaker orientation and tongue target

Gemini is the preferred cloud orientation mode for the current use case:
upright, separated sneakers picked using a hook near the tongue. It receives
one cropped image for each new stable shoe track and returns validated JSON
toe, heel, and tongue coordinates. The live feed draws a heel-to-toe arrow and
a magenta tongue/hook target when it arrives. Low-confidence answers are
ignored and cached, so an uncertain shoe does not repeatedly consume API calls.

Set the key in your shell, then run:

```bash
bash run_live_shoe_tracker_gpu.sh --gemini-orientation
```

The default model is `gemini-3.5-flash`. It can be changed with
`--gemini-model <model-name>`. A key in the Python file is convenient for the
hackathon but must not be committed or shared. This mode remains display-only
until you test it on your actual shoes.

The green arrow is the toe/heel axis. Its displayed angle uses the same image
convention as the robot bearing: straight up is `0°`, left is positive, and
right is negative. Set a stricter acceptance threshold when needed, for example
`--gemini-min-confidence 0.80`.

Expected terminal messages are:

```text
Gemini: evaluating orientation for track ID 3...
Gemini: track ID 3 orientation ready (confidence 0.84).
```

An `ignored` message means the returned confidence did not meet the threshold;
move or replace the shoe to create a new track if you want another assessment.

## Gemini shoe understanding and pair hypotheses

The optional full-understanding mode keeps YOLO and ByteTrack as the fast local
detector/tracker, then asks Gemini once per stable track for shoe type,
left/right side, toe, heel, visible opening, and a conservative hook target.
It also sends an occasional labelled contact sheet of up to six visible stable
tracks so Gemini can propose likely left/right pairs. Results are cached by
track ID and are visual guidance only.

```bash
export GEMINI_API_KEY='your-key'
bash run_live_shoe_tracker_gpu.sh --gemini-understanding
```

The display draws a cyan line for each pair hypothesis and labels it with its
confidence. A green hook label is only a candidate: calibration, collision
checks, and real hook-insertion tests are still required before a robot motion.

## Camera calibration

The camera is fixed overhead, but camera pixels are not robot coordinates yet.
First create a floor calibration after measuring the visible work area:

```bash
.venv/bin/python calibration/calibrate_floor.py empty_floor.jpg \
  --width-cm <width> --height-cm <height> --output floor_calibration.json
```

This produces floor coordinates in centimeters. A later robot-calibration step
must map those coordinates and the shoe's required orientation to safe arm
motion slots. Do not connect detections directly to physical arm commands.
