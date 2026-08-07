#!/usr/bin/env python3
"""Conservative vision -> discrete PHORCE-motion state machine.

This is the operations *skeleton*, not an autonomous robot launcher.  It is
dry-run by default and all real motion IDs start unset in ``motion_map.py``.

Eventually the vision bridge will pass stable ``ShoeObservation`` values into
``ShoeValetController.observe``.  The controller deliberately ignores shoe
colour and left/right: current vision only needs a stable generic shoe at the
fixed pickup station.
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Protocol

from motion_map import MOTIONS, validate_motion_id


LOG = logging.getLogger("shoe_valet")


class State(Enum):
    IDLE = auto()
    SHOE_STABLE = auto()
    WAITING_FOR_APPROVAL = auto()
    APPROACHING = auto()
    PROBING = auto()
    CHECKING_ENGAGEMENT = auto()
    LIFTING = auto()
    PLACING = auto()
    RETURNING_HOME = auto()
    COMPLETE = auto()
    BLOCKED = auto()


@dataclass(frozen=True)
class ShoeObservation:
    """The small, intentionally conservative contract from vision to operations."""

    track_id: int
    confidence: float
    stable_seconds: float
    in_pickup_station: bool
    toe_visible: bool = True

    @property
    def safe_to_attempt(self) -> bool:
        return (
            self.confidence >= 0.70
            and self.stable_seconds >= 1.0
            and self.in_pickup_station
            and self.toe_visible
        )


class MotionRunner(Protocol):
    def play(self, action: str, motion_id: Optional[int]) -> bool:
        """Play exactly one taught motion and return whether it succeeded."""


class DryRunMotionRunner:
    """Default runner: exposes every decision but never connects to PHORCE."""

    def play(self, action: str, motion_id: Optional[int]) -> bool:
        LOG.info("DRY RUN: would play %-18s slot=%s", action, motion_id)
        return True


class PhorceMotionRunner:
    """Minimal adapter for the official pre-recorded-motion API.

    Construct this only with ``--execute``.  No feedback callback makes motion
    decisions; feedback is inspected only after a taught motion ends.
    """

    def __init__(self, target: str = "robot") -> None:
        try:
            import phorce
        except ImportError as error:
            raise RuntimeError("PHORCE Python API is not installed in this environment.") from error
        self._phorce = phorce
        # The documented real-robot form is ``connect()``.  Named targets are
        # for the simulator (for example ``sim:demo``).
        self._connection = phorce.connect() if target == "robot" else phorce.connect(target)
        self._robot = self._connection.__enter__()

    def close(self) -> None:
        self._connection.__exit__(None, None, None)

    def play(self, action: str, motion_id: Optional[int]) -> bool:
        slot = validate_motion_id(motion_id, action)
        status = self._robot.status()
        if getattr(status, "estop_active", True):
            raise RuntimeError("PHORCE reports E-stop/unsafe status; motion is blocked.")
        LOG.info("PHORCE: playing %-18s slot=%d", action, slot)
        result = self._robot.play(slot)
        return bool(result.ok)


class ShoeValetController:
    """Choose one short motion, then reassess at the slot boundary."""

    def __init__(self, runner: MotionRunner, require_approval: bool = True) -> None:
        self.runner = runner
        self.require_approval = require_approval
        self.state = State.IDLE
        self.selected_shoe: Optional[ShoeObservation] = None

    def observe(self, shoe: Optional[ShoeObservation]) -> State:
        """Accept the latest stable vision result; never start from weak input."""
        if self.state is not State.IDLE:
            return self.state
        if shoe is None or not shoe.safe_to_attempt:
            return self.state
        self.selected_shoe = shoe
        self.state = State.WAITING_FOR_APPROVAL if self.require_approval else State.SHOE_STABLE
        LOG.info("Stable shoe %s selected; state=%s", shoe.track_id, self.state.name)
        return self.state

    def approve(self) -> State:
        if self.state is State.WAITING_FOR_APPROVAL:
            self.state = State.SHOE_STABLE
            LOG.info("Operator approval received.")
        return self.state

    def step(self, engaged: Optional[bool] = None) -> State:
        """Advance one decision boundary; call after each real motion completes."""
        if self.state is State.SHOE_STABLE:
            self._run("approach_station", State.APPROACHING)
        elif self.state is State.APPROACHING:
            self._run("probe_shoe", State.PROBING)
        elif self.state is State.PROBING:
            self.state = State.CHECKING_ENGAGEMENT
            LOG.info("Probe finished; awaiting a validated engagement check.")
        elif self.state is State.CHECKING_ENGAGEMENT:
            if engaged is None:
                LOG.info("No engagement result yet; staying blocked at the safe boundary.")
            elif engaged:
                self._run("lift_shoe", State.LIFTING)
            else:
                self._run("retract_probe", State.BLOCKED)
        elif self.state is State.LIFTING:
            self._run("place_shoe", State.PLACING)
        elif self.state is State.PLACING:
            self._run("return_home", State.RETURNING_HOME)
        elif self.state is State.RETURNING_HOME:
            self.state = State.COMPLETE
            LOG.info("Cycle complete.")
        return self.state

    def _run(self, action: str, success_state: State) -> None:
        try:
            success = self.runner.play(action, getattr(MOTIONS, action))
        except Exception as error:
            self.state = State.BLOCKED
            LOG.error("%s blocked: %s", action, error)
            return
        self.state = success_state if success else State.BLOCKED
        if not success:
            LOG.error("%s did not complete successfully; manual inspection required.", action)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Connect to PHORCE and allow configured motion slots to play")
    parser.add_argument("--target", default="robot", help="PHORCE target, e.g. robot or sim:demo")
    parser.add_argument("--demo-shoe", action="store_true", help="Run one simulated stable-shoe decision cycle")
    parser.add_argument("--auto-approve", action="store_true", help="Only for dry-run demos; bypass operator approval")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    runner: MotionRunner
    if args.execute:
        LOG.warning("EXECUTE mode enabled. Confirm the workspace is clear and E-stop is reachable.")
        runner = PhorceMotionRunner(args.target)
    else:
        runner = DryRunMotionRunner()

    try:
        controller = ShoeValetController(runner, require_approval=not args.auto_approve)
        if not args.demo_shoe:
            LOG.info("Ready. A future vision bridge should call controller.observe(observation).")
            return 0

        controller.observe(ShoeObservation(1, 0.95, 2.0, True))
        if args.auto_approve:
            controller.approve()
        while controller.state not in {State.COMPLETE, State.BLOCKED, State.WAITING_FOR_APPROVAL}:
            controller.step(engaged=True)
            time.sleep(0.1)
        LOG.info("Final state: %s", controller.state.name)
        return 0 if controller.state is State.COMPLETE else 1
    finally:
        if isinstance(runner, PhorceMotionRunner):
            runner.close()


if __name__ == "__main__":
    raise SystemExit(main())
