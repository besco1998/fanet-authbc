"""The missions the A9 flights upload (analysis/px4_airframe_flight.py).

The climb-out waypoint (A9-fast, 2026-10-22): PX4's fixed-wing controller slides each leg's
altitude target from the previous waypoint's altitude to the current one's
(FixedWingModeManager::control_auto_position, "altitude first order hold"). After a fixed-wing
takeoff the first leg's previous point lay at ground level, and every registered A9 airplane
flight flew most of that leg at ground level. A waypoint above home at mission altitude, right
after the takeoff item, makes the first leg start from that altitude.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("px4_airframe_flight",
                                               REPO / "analysis" / "px4_airframe_flight.py")
assert _spec and _spec.loader
fl = importlib.util.module_from_spec(_spec)
sys.modules["px4_airframe_flight"] = fl
_spec.loader.exec_module(fl)


def test_the_registered_mission_is_takeoff_then_the_waypoints() -> None:
    plan = fl.mission("airplane", 3)
    items = fl.mission_items(plan)
    assert items[0] == (fl.CMD_TAKEOFF, *fl.HOME, plan["alt_m"])
    assert [i[1:3] for i in items[1:]] == [tuple(w) for w in plan["waypoints"]]
    assert all(i[0] == fl.CMD_WAYPOINT and i[3] == plan["alt_m"] for i in items[1:])


def test_the_climb_out_waypoint_sits_above_home_right_after_takeoff() -> None:
    plan = {**fl.mission("airplane", 3), "climbout": True}
    items = fl.mission_items(plan)
    assert items[1] == (fl.CMD_WAYPOINT, *fl.HOME, plan["alt_m"])
    assert items[2:] == fl.mission_items(fl.mission("airplane", 3))[1:]


def test_a_vtol_takes_off_as_a_vtol() -> None:
    assert fl.mission_items(fl.mission("vtol", 1))[0][0] == fl.CMD_VTOL_TAKEOFF


@pytest.mark.parametrize("mission", [1, 10])
def test_ad_hoc_options_are_refused_for_registered_missions(mission: int) -> None:
    with pytest.raises(SystemExit):
        fl.check_options(mission, cruise=20.0, params=[], climbout=False, profile=None)
    with pytest.raises(SystemExit):
        fl.check_options(mission, cruise=None, params=[], climbout=True, profile=None)
    fl.check_options(mission, cruise=None, params=[], climbout=False, profile=None)


def test_the_fast_profile_flies_the_drawn_speed_with_its_parameters() -> None:
    for af in ("airplane", "vtol"):
        plan = fl.apply_profile(fl.mission(af, 3), "fast")
        assert plan["cruise_flown_mps"] == plan["speed_mps"]          # not capped at 15 m/s
        assert plan["profile"] == "fast"
        assert plan["extra_params"] == fl.PROFILES["fast"][af]["params"]
        assert plan.get("climbout", False) == fl.PROFILES["fast"][af]["climbout"]
    assert fl.PROFILES["fast"]["airplane"]["params"]["SIH_KDV"] == 0.0   # the brake is the cause
    assert fl.PROFILES["fast"]["vtol"]["params"]["SIH_KDV"] == 0.0


def test_the_profile_is_allowed_for_registered_missions_but_not_for_the_quadrotor() -> None:
    fl.check_options(3, cruise=None, params=[], climbout=False, profile="fast")
    with pytest.raises(SystemExit):
        fl.apply_profile(fl.mission("quadx", 3), "fast")
