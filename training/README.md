# Training record

The deployed model is `../vision/models/shoe-detector.pt`.

- Architecture: YOLO26s, one class (`shoe`)
- Training data: 1,683 images; validation data: 495 images; held-out test data: 261 images
- Training: 50 epochs at 640 px
- Best validation result: precision 0.866, recall 0.684, mAP@50 0.785, mAP@50-95 0.472

`args.yaml`, `results.csv`, and `results.png` preserve the original run record.
The 105 MB source dataset is deliberately excluded from this deployment-focused
project; it remains at `/home/phorce/yolo/datasets/general_shoes`.

This model detects shoes only. Toe, heel, tongue, and hook-target estimates in
the live vision module are provided separately by optional Gemini image analysis;
they are not outputs of this YOLO model.
