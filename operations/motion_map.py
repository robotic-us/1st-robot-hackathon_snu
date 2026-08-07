"""Verified PHORCE motion-slot assignments.

Fill a value only after the corresponding motion has been taught in PHORCE
Studio, manually tested, and confirmed with ``phorce list``.  ``None`` means
the operation is deliberately unavailable.

Motion IDs are not stored in this repository: the PCM's SD card is the source
of truth.  Do not copy the old brainstormed IDs from the reference document.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MotionMap:
    """One short, safe taught motion per state transition."""

    approach_station: Optional[int] = None
    probe_shoe: Optional[int] = None
    retract_probe: Optional[int] = None
    lift_shoe: Optional[int] = None
    place_shoe: Optional[int] = None
    return_home: Optional[int] = None


# This is intentionally empty.  Set verified IDs here after teaching motions.
MOTIONS = MotionMap()


def validate_motion_id(motion_id: Optional[int], action: str) -> int:
    """Reject unconfigured and out-of-contract motion requests."""
    if motion_id is None:
        raise RuntimeError(f"No verified motion ID configured for '{action}'.")
    if not 1 <= motion_id <= 50:
        raise RuntimeError(f"Invalid motion ID {motion_id} for '{action}'; valid range is 1..50.")
    return motion_id
