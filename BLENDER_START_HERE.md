# Create your shoe dataset in Blender

You only need to do this once for a quick preview, then once more for the full dataset.

1. Start Blender.
2. At the top of Blender, click the **Scripting** workspace.
3. In the large text-editor panel, click **Open** and select
   `scripts/generate_shoe_dataset.py` from this project folder.
4. Click the triangular **Run Script** button.
5. Wait for the status text to say `Done.` The full run creates 600 images.
6. Open the folder `synthetic_shoes/images/train` and check a few images:
   - the shoe textures should look normal;
   - object1 is the right shoe of pair 1;
   - object2 is the left shoe of pair 1;
   - object3 is the right shoe of pair 2.
7. Inspect a few images and their pose previews before training.

The finished YOLO dataset is written to `synthetic_shoes/`:

- `images/train` and `images/val`: generated PNG images;
- `labels/train` and `labels/val`: matching YOLO pose annotation files;
- `data.yaml`: the class names and train/validation paths.

The current classes are `pair1_right`, `pair1_left`, `pair2_right`, `pair2_left`, `pair3_right`, and `pair3_left`. All are real scans—there are no texture-distorting mirrored models.

Each label contains the bounding box followed by two pose keypoints in this order: **heel**, then **toe**. After generating the dataset, keep the best 20–50 real photos from the actual camera setup. We can label those with the same classes and use them to fine-tune the synthetic model.
