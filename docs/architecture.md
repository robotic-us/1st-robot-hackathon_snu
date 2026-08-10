# System architecture

## Objective

Move a shoe from a known overhead-camera presentation to a destination using
a PHORCE arm, without allowing unverified visual inference to directly command
hardware.

## Runtime pipeline

```text
fixed overhead webcam
        |
        v
YOLO pose model + ByteTrack
  boxes, heel/toe landmarks, track IDs
        |
        v
heading selection
  one shoe, or two shoes with matching headings
        |
        v
0 degree +/- 18 degree condition held for 5 seconds
        |
        v
double-Space human confirmation
        |
        v
four manually taught PHORCE PCM slots: 11 -> 12 -> 13 -> 16
```

The controller is deliberately discrete: visual output chooses only an
already-tested motion sequence. It is camera-only by default; `--execute` is
required before a robot connection is attempted.

## Coordinate handling

The camera has a fixed, overhead view of a 50 x 80 cm floor workspace.
`operations/calibrate_camera_floor.py` records the four visible floor corners
in top-left, top-right, bottom-right, bottom-left order. The controller stores
that projective mapping in `operations/camera_floor_calibration.json` and uses
it to display shoe positions in centimetres. Position is currently telemetry,
not a motion-selection input.

## Data and model workflow

The project combines Blender-generated shoe imagery with manually labelled
real captures. Dataset-preparation and Blender scripts are versioned; raw
captures, generated datasets, checkpoints, and local training runs are not,
because they are too large for the source repository. Curated sample images
and `training/` results make the work inspectable without bloating the repo.

## Safety boundaries

- No robot connection in default dry-run mode.
- A candidate must remain stable for five seconds.
- Execution requires a double-Space confirmation inside a short time window.
- PCM slots are manually taught and verified; visual detections do not produce
  arbitrary arm trajectories.
- The physical E-stop remains the emergency control.
- Cloud orientation/understanding modes are advisory only.
