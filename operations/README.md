# 0-degree, angle-only shoe controller

The camera runs live inside the controller and keeps showing the YOLO boxes,
labeled heel/toe points and heel-to-toe arrow. The controller accepts either
one shoe or exactly two shoes in view. Positions are ignored; when two shoes
are shown, their heel-to-toe angles must be aligned within 18° and their shared
average angle chooses the situation. The only valid case is `0°` with a ±18°
tolerance.

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

## Configure the motion sequence

The controller is configured for the `0° ±18°` angle band and runs PCM slots
`11`, `12`, `13`, then `16` after a confirmed double-Space.

Once all four slots are verified, explicitly enable real motion:

```bash
bash operations/run_shoe_valet_gpu.sh --execute
```

Show one shoe, or exactly two shoes aligned within 18°. The controller then
visibly counts down five seconds and shows `NEXT SITUATION` plus a `PREVIEW`
before any key press. The first Space starts a visible confirmation countdown;
the second Space within 0.5 seconds runs the displayed situation's four
motion slots with one-second pauses. Camera updates and keyboard input remain
frozen for the entire sequence; the physical E-stop remains the emergency
stop.
