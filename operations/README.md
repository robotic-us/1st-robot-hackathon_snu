# Ten-situation shoe controller

The camera runs live inside the controller and keeps showing the YOLO boxes,
labeled heel/toe points, heel-to-toe arrow, and every configured situation.
The wide right-side telemetry panel shows a rolling numeric stream plus box,
landmark, angle, confidence, tracking, and lock information for every visible
shoe. Thin yellow lines connect every shoe centre to the camera's bottom-centre
origin; these show each shoe's origin bearing. A situation is a known
combination of shoe position and rotation.  Each mapped PHORCE slot is a full
taught motion from that input situation to the one destination at 0 degrees.

```text
live camera -> same situation for 5 seconds -> double-tap Space -> robot.play(mapped_slot)
```

## Camera-only test

```bash
cd /home/phorce/comp
bash operations/run_shoe_valet_gpu.sh
```

It cannot connect to or move the robot. Double-tapping Space simply reports
that it is in dry-run mode.

The launcher is important: it uses the project's CUDA 12.6 virtual environment
that can access the Orin GPU. The global `python3` has an incompatible CUDA
13.0 PyTorch installation, so it is CPU-only here.

## Configure the ten situations

Edit `operations/motion_map.py` for each physical setup:

1. Put the shoe in the desired position and rotation.
2. Read its pixel centre and displayed angle from the camera window.
3. Teach/test its complete collection-to-destination motion in Studio.
4. Enter its centre, expected angle, and verified PCM motion slot ID.

Once all ten are verified, explicitly enable real motion:

```bash
bash operations/run_shoe_valet_gpu.sh --execute
```

Show exactly one shoe. The controller requires the same situation for five
seconds, shows `LOCKED`, and then still requires two Space presses within 0.5
seconds. `Q`/`Esc` quits only when no motion is running; the physical E-stop
remains the emergency stop.
