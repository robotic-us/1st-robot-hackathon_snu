"""The ten camera situations and their verified PHORCE motions.

Each situation is one known shoe centre and toe direction in the fixed overhead
camera view.  Its matching PHORCE slot should contain the *complete* taught
motion: collect from that situation, then place at the one destination in
front of the robot (0 degrees).

Fill ``center_px`` and ``motion_id`` only after camera/robot calibration and
manual motion testing.  An unconfigured situation is ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Situation:
    name: str
    # Centre of the shoe in pixels in the live 1280x720 camera image.
    center_px: Optional[tuple[int, int]]
    # Heel -> toe direction; 0° is up/away from the robot, left is positive.
    angle_deg: float
    # How close a detected shoe must be to this taught situation.
    position_tolerance_px: float = 55.0
    angle_tolerance_deg: float = 15.0
    # PCM slot ID (1..50), after manual verification. None = unavailable.
    motion_id: Optional[int] = None


# Replace each ``None`` centre and motion ID with measured, verified values.
SITUATIONS = (
    Situation("situation_01", None, 0.0),
    Situation("situation_02", None, 0.0),
    Situation("situation_03", None, 0.0),
    Situation("situation_04", None, 0.0),
    Situation("situation_05", None, 0.0),
    Situation("situation_06", None, 0.0),
    Situation("situation_07", None, 0.0),
    Situation("situation_08", None, 0.0),
    Situation("situation_09", None, 0.0),
    Situation("situation_10", None, 0.0),
)
