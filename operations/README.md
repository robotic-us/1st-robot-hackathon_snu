# Operations skeleton

`shoe_valet.py` is the conservative bridge between vision and PHORCE:

```text
camera observation -> safe discrete state -> one taught slot -> feedback check -> next state
```

It does not drive to image coordinates.  A shoe must first be physically in a
known pickup station, so that each transition can be a short prerecorded
motion.

## Safe dry-run

```bash
cd /home/phorce/comp
python3 operations/shoe_valet.py --demo-shoe --auto-approve
```

This prints the decisions without connecting to or moving the robot.

## Before real execution

1. Teach and manually test every motion in PHORCE Studio.
2. Run `phorce list` and copy only the verified slot IDs into `motion_map.py`.
3. Implement a calibrated vision bridge that sets `in_pickup_station=True`
   only within a small safe region.
4. Define and validate the engagement check from valid PHORCE feedback.
5. Keep manual approval on during initial hardware trials.

Only then use `--execute`.  If a slot is missing or feedback is unsafe, the
controller blocks rather than guessing.
