# Curated runtime artifacts

These files are deliberately kept small enough for ordinary Git and make the
repository demonstrable after a fresh clone.

- `models/shoe-detector.pt` — one-class shoe detector used by the live tracker.
- `models/shoe-pose-real-only-baseline.pt` — default controller pose model;
  trained from manually labelled real captures.
- `models/shoe-pose-mixed-baseline.pt` — mixed synthetic/real comparison
  checkpoint.
- `training/` — selected configuration, metric, confusion-matrix, curve, and
  validation-prediction outputs for both pose experiments.

The controller defaults to the real-only pose checkpoint. These checkpoints
are demonstration artifacts, not a substitute for supervised live-camera and
robot-motion verification.
