# SNU — 제1회 로봇 해커톤 2026

로보틱어스(Roboticus)가 주최하는 제1회 로봇 해커톤(2026. 8. 5.~8. 8., KAIST) 참가팀 **SNU**(서울대)의 저장소입니다.

- 팀원: 이재희 · 안준표 · 차민재
- 대회: https://robotic-us.com

## 지적재산권

> 본 프로젝트의 지적재산권은 SNU 팀(팀원 전원)에게 있으며, 본 대회의 주최 측(로보틱어스)은 아카이브 및 홍보 목적으로만 본 저장소를 활용합니다.

라이선스는 팀이 선택해 `LICENSE` 파일로 추가하세요(MIT 또는 Apache-2.0 권장).

## Shoe vision prototype

The vision stack has two complementary paths:

- `vision_shoe_test.py`: real overhead-camera test. It can use lightweight
  empty-floor subtraction or a trained instance-segmentation model.
- `generate_synthetic_shoes.py`: Blender renderer that turns the textured OBJ
  scans into labeled overhead scenes for training.

Robot motion must not be selected directly from an unvalidated detection. The
vision output is an observation for the deterministic behavior graph described
in `hackathon-reference.md`.

### 1. Confirm scan metadata

The current provisional metadata records `object1` as the right white shoe,
`object2` as the left, white length as 30 cm, and brown length as 29 cm. Edit
`shoe_assets.json` if physical verification changes those labels.

- leave object 3's side unknown unless it is physically verified.

### 2. Run the real-camera baseline

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python vision_shoe_test.py --camera 0
```

Clear the floor and press `R`, add shoes, then press `S` to save a raw frame,
mask, overlay, and structured JSON under `data/vision_captures/`.

#### Optional Kimi API identity backup

The main test can ask Kimi K3 to match detected crops against
the three known shoes. Position and orientation still come from OpenCV. An API
request is made only when you press `A`, not on every camera frame.

After the one-time dependency installation, the everyday command is:

```bash
./run_vision.sh
```

If the current terminal does not already have `MOONSHOT_API_KEY`, the launcher
asks for it invisibly before starting. The one-time setup command is
`.venv/bin/python -m pip install -r requirements-api.txt`.

To test only the Kimi connection, without opening the camera, run:

```bash
./test_kimi.sh
```

For the lean one-photo Kimi shoe detector, run:

```bash
./shoe_photo.sh
```

Press Space or Enter to capture one frame. Kimi receives that single image,
returns normalized shoe boxes, and the program saves a boxed JPEG and JSON
under `data/kimi_shoe_photos/`.

In the camera window: clear the floor and press `R`, place the shoes, then
press `A` to identify them. Press `S` afterward to save the labeled result.
Camera `0`, Kimi K3, the 65 cm camera height, and 55-degree horizontal FOV are
the defaults. Use command-line options only when one of those values changes;
use `--no-api` for an explicitly offline run.
The key is read invisibly and is not written to this repository. It must be a
key for the global Kimi platform endpoint at `https://api.moonshot.ai/v1`.
Kimi API billing and an internet connection are required.

The scan preview images are used as fallback references. Recognition should be
better with several real overhead photos per shoe, placed like this:

```text
shoe_references/
  white_pair_object1/   # provisional right shoe
  white_pair_object2/   # left shoe
  brown_pair_object3/   # side remains unknown
```

Put 3–6 `.jpg`, `.png`, or `.webp` views in each directory, ideally under the
actual camera and lighting at different rotations. Do not connect API output
directly to robot motion; reject `unknown`, low-confidence, or merged results.

For metric floor coordinates, capture an empty overhead image and click its
corners in top-left, top-right, bottom-right, bottom-left order:

```bash
.venv/bin/python calibrate_floor.py empty_floor.jpg \
  --width-cm 60 --height-cm 35 --output floor_calibration.json
.venv/bin/python vision_shoe_test.py --calibration floor_calibration.json
```

### 3. Render synthetic training scenes

Install Blender 3.6+ on a rendering machine, then run:

```bash
blender --background --python generate_synthetic_shoes.py -- \
  --manifest shoe_assets.json --output data/synthetic_shoes --count 2000 \
  --camera-height-cm 65 --horizontal-fov-deg 55 \
  --area-width-cm 60 --area-height-cm 35
.venv/bin/python build_synthetic_annotations.py data/synthetic_shoes
```

The dataset contains RGB images, exact instance masks, scene metadata, JSON
polygons, and YOLO segmentation labels. The default 28 cm shoe length is only
a placeholder when `length_cm` is missing.

### 4. Train and test the segmentation model

ML dependencies are kept separate because they are substantially larger and
may need a Jetson-specific PyTorch installation:

```bash
.venv/bin/python -m pip install -r requirements-ml.txt
.venv/bin/python train_shoe_segmentation.py data/synthetic_shoes \
  --epochs 80 --device 0
.venv/bin/python vision_shoe_test.py \
  --model data/synthetic_shoes/runs/shoe_segmentation/weights/best.pt \
  --calibration floor_calibration.json
```

Synthetic-only validation is not sufficient. Capture real overhead scenes with
separated shoes, touching shoes, hard floor/shoe color combinations, and mild
lighting changes. Review false positives and incorrect masks before connecting
the output to any behavior decision.
