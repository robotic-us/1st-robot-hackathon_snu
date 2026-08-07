"""Fine-tune YOLO pose on the generated six-class overhead shoe dataset.

Run from a normal Jetson terminal:
    /home/phorce/comp/vision/.venv/bin/python /home/phorce/comp/vision/train_shoe_pose_gpu.py
"""

from pathlib import Path

import torch
from ultralytics import YOLO


ROOT = Path("/home/phorce/comp")

if not torch.cuda.is_available():
    raise RuntimeError("CUDA is unavailable. Run this with the Jetson CUDA 12.6 virtual environment.")

print(f"Training on: {torch.cuda.get_device_name(0)}")
model = YOLO(str(ROOT / "yolo11n-pose.pt"))
model.train(
    data=str(ROOT / "synthetic_shoes/data.yaml"),
    epochs=100,
    imgsz=640,
    batch=-1,
    device=0,
    fliplr=0,  # Must stay off: a flip changes left/right identity.
    project=str(ROOT / "runs"),
    name="shoe_pose_overhead_gpu",
)
