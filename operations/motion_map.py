"""The single angle-only camera situation and its verified PHORCE motions.

Position is deliberately ignored: only its heel-to-toe angle chooses the
situation. The sole valid angle band is centred on 0° and accepts a maximum
error of 18°.

Fill ``motion_ids`` only after manually verifying the four-part taught
motion. ``None`` leaves that situation unavailable for real execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Situation:
    name: str
    # Retained for compatibility with the display code.  Angle-only matching
    # deliberately ignores this field.
    center_cm: Optional[tuple[float, float]]
    # Heel -> toe direction; 0° is up/away from the robot, left is positive.
    angle_deg: float
    # Retained for compatibility; position is not used for matching.
    position_tolerance_cm: float = 4.0
    angle_tolerance_deg: float = 15.0
    # Four PCM slot IDs (1..50), after manual verification. The controller
    # pauses one second between them. None = unavailable.
    motion_ids: Optional[tuple[int, int, int, int]] = None


# The four verified PCM steps run in this order after double-Space.
SITUATIONS = (
    Situation("situation_01  (0 deg)", None, 0.0, angle_tolerance_deg=18.0, motion_ids=(11, 12, 13, 16)),
)
