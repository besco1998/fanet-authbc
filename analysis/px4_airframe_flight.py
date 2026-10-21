#!/usr/bin/env python3
"""Fly an uploaded mission on one of PX4's built-in airframes, logging at 20 ms (revision A9).

`px4_sitl_flight.py` flies the multicopter with velocity setpoints; a fixed-wing aircraft or a
VTOL cannot be flown that way, so this uploads a waypoint mission over MAVLink and lets the
autopilot fly it (AUTO.MISSION). The simulator is PX4's own SIH (no Gazebo): `sihsim_quadx`,
`sihsim_airplane`, `sihsim_standard_vtol`. One flight at a time (fixed ports).

    <px4 venv>/bin/python analysis/px4_airframe_flight.py --px4 ~/projects/px4/PX4-Autopilot \
        --airframe airplane --mission 3 --out ~/.cache/authbc-px4/airplane-03

Writes `flight.ulg` and `mission.json` (the waypoints flown) into `--out`. The mission is a
function of (airframe, mission number) only: a closed polygon of 4–6 legs whose size, heading
and commanded speed are drawn from a generator seeded with the mission number.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import subprocess
import threading
import time
from pathlib import Path

# position, attitude, body rates, GNSS quality, airspeed, wind, mission progress, status: every
# topic the 9-, 15- and 25-field records are built from (analysis/record_size_sensitivity.py)
LOGGER_TOPICS = "\n".join(f"{t} 20" for t in (
    "vehicle_global_position", "vehicle_local_position", "vehicle_attitude",
    "vehicle_angular_velocity", "sensor_gps", "airspeed_validated", "wind", "mission_result",
    "battery_status", "vehicle_status", "vehicle_thrust_setpoint")) + "\n" + \
    "vehicle_land_detected 0\n"
GCS_PORT = 14550
# PX4's SIH airplane flies at 12-15 m/s whatever it is told (airspeed never above 15 in the
# missions flown); told more, it misses its waypoints and circles (A9, missions airplane-02 and
# -06). Decided by Mohamed, 2026-10-22: fixed-wing and VTOL cruise is capped at the airframe's
# own trim, 15 m/s; the drawn speed and the mission's geometry are kept and both are recorded.
FW_CRUISE_CAP_MPS = 15.0
HOME = (47.397742, 8.545594)            # PX4's default SITL home (Zurich)
AIRFRAMES = {
    # model, cruise speed range (m/s), leg length range (m), altitude (m)
    "quadx": ("sihsim_quadx", (5.0, 15.0), (150.0, 400.0), 40.0),
    "airplane": ("sihsim_airplane", (15.0, 25.0), (600.0, 1500.0), 80.0),
    "vtol": ("sihsim_standard_vtol", (15.0, 22.0), (600.0, 1500.0), 80.0),
}


def mission(airframe: str, number: int) -> dict:
    """The waypoints of mission `number`, reproducible from the two arguments alone."""
    _, speeds, legs, alt = AIRFRAMES[airframe]
    rng = random.Random(f"{airframe}:{number}")
    n_legs = rng.randint(4, 6)
    heading = rng.uniform(0.0, 2.0 * math.pi)
    length = rng.uniform(*legs)
    speed = round(rng.uniform(*speeds), 1)
    points, north, east = [], 0.0, 0.0
    for k in range(n_legs - 1):
        a = heading + 2.0 * math.pi * k / n_legs
        north, east = north + length * math.cos(a), east + length * math.sin(a)
        points.append((north, east))
    lat0, lon0 = HOME
    deg = [(lat0 + n / 111_320.0, lon0 + e / (111_320.0 * math.cos(math.radians(lat0))))
           for n, e in points]
    return {"airframe": airframe, "number": number, "speed_mps": speed, "alt_m": alt,
            "leg_m": round(length, 1), "waypoints": deg}


def client(px4: Path, tool: str, *args: str) -> str:
    out = subprocess.run([str(px4 / "build/px4_sitl_default/bin" / f"px4-{tool}"), *args],
                         capture_output=True, text=True, timeout=30)
    return out.stdout + out.stderr


def upload(gcs, plan: dict) -> int:
    """MAVLink mission protocol: count, then each item as it is requested."""
    from pymavlink import mavutil
    m = mavutil.mavlink
    vtol = plan["airframe"] == "vtol"
    alt = plan["alt_m"]
    lat0, lon0 = HOME
    items = [(m.MAV_CMD_NAV_VTOL_TAKEOFF if vtol else m.MAV_CMD_NAV_TAKEOFF, lat0, lon0, alt)]
    # Only in-flight records are used, so the mission ends at its last waypoint: a fixed-wing
    # landing needs an approach pattern, and PX4 refuses return-to-launch in a global frame.
    items += [(m.MAV_CMD_NAV_WAYPOINT, la, lo, alt) for la, lo in plan["waypoints"]]
    gcs.mav.mission_count_send(gcs.target_system, gcs.target_component, len(items),
                               m.MAV_MISSION_TYPE_MISSION)
    sent = 0
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        msg = gcs.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"],
                             blocking=True, timeout=5)
        if msg is None:
            continue
        if msg.get_type() == "MISSION_ACK":
            if msg.type != m.MAV_MISSION_ACCEPTED or sent < len(items):
                raise SystemExit(f"mission refused: {msg}")
            return len(items)
        cmd, la, lo, al = items[msg.seq]
        gcs.mav.mission_item_int_send(
            gcs.target_system, gcs.target_component, msg.seq,
            m.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, cmd, 0, 1, 0, 0, 0, float("nan"),
            int(la * 1e7), int(lo * 1e7), al, m.MAV_MISSION_TYPE_MISSION)
        sent = max(sent, msg.seq + 1)
    raise SystemExit("mission upload timed out")


def fly(px4: Path, plan: dict, timeout_s: float) -> None:
    from pymavlink import mavutil
    speed = plan["cruise_flown_mps"]
    params = [("NAV_DLL_ACT", 0), ("NAV_RCL_ACT", 0), ("COM_RCL_EXCEPT", 4),
              ("COM_DISARM_LAND", 2), ("COM_RC_IN_MODE", 4)]   # no sticks: auto only
    # A fixed wing otherwise requires a landing pattern in every mission, and SIH has no
    # airspeed sensor for the preflight check; the airspeed field then comes from PX4's estimate.
    # The maximum airspeed is kept 5 m/s above the trim, the airframe's own default margin
    # (trim 15, max 20): with a trim above the default maximum (20 m/s) the aircraft took off and
    # never climbed (A9, mission airplane-02, 2026-10-22; added after registration, disclosed).
    params += ([("MPC_XY_CRUISE", speed), ("MPC_XY_VEL_MAX", max(12.0, speed))]
               if plan["airframe"] == "quadx" else
               [("FW_AIRSPD_TRIM", speed), ("FW_AIRSPD_MAX", max(20.0, speed + 5.0)),
                ("MIS_TKO_LAND_REQ", 0), ("SYS_HAS_NUM_ASPD", 0)])
    gcs = mavutil.mavlink_connection(f"udpin:127.0.0.1:{GCS_PORT}")
    gcs.wait_heartbeat(timeout=90)
    beating = threading.Event()

    def heartbeat() -> None:                # a ground station that is seen to be there
        while not beating.is_set():
            gcs.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                                   mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
            time.sleep(1.0)

    threading.Thread(target=heartbeat, daemon=True).start()
    time.sleep(5.0)                         # the airframe's startup script is done by now
    # Set after start-up (set earlier, the airframe script overwrites them) and read back.
    for name, value in params:
        client(px4, "param", "set", name, str(value))
        shown = client(px4, "param", "show", name)
        if f": {float(value):.4f}" not in shown and f": {int(value)}" not in shown:
            raise SystemExit(f"parameter {name} did not take the value {value}: {shown[-200:]}")
    n_items = upload(gcs, plan)
    def armed_within(seconds: float) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            hb = gcs.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
            if (hb is not None and hb.get_srcSystem() == gcs.target_system
                    and hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
                return True
        return False

    for _ in range(60):                                 # pre-flight checks take a while
        client(px4, "commander", "mode", "auto:mission")
        client(px4, "commander", "arm")
        if armed_within(3.0):
            break
    else:
        raise SystemExit("the vehicle never armed")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        msg = gcs.recv_match(type="MISSION_ITEM_REACHED", blocking=True, timeout=5)
        if msg is not None and msg.seq >= n_items - 1:
            time.sleep(5.0)                             # a few seconds past the last waypoint
            beating.set()
            return
    raise SystemExit("the mission did not reach its last waypoint in time")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--px4", type=Path, required=True)
    ap.add_argument("--airframe", choices=list(AIRFRAMES), required=True)
    ap.add_argument("--mission", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=1200.0)
    args = ap.parse_args()
    plan = mission(args.airframe, args.mission)
    plan["cruise_flown_mps"] = (plan["speed_mps"] if args.airframe == "quadx"
                                else min(plan["speed_mps"], FW_CRUISE_CAP_MPS))
    build = args.px4 / "build" / "px4_sitl_default"
    rootfs = build / "rootfs"
    (build / "etc" / "logging").mkdir(parents=True, exist_ok=True)
    (build / "etc" / "logging" / "logger_topics.txt").write_text(LOGGER_TOPICS)
    shutil.rmtree(rootfs / "log", ignore_errors=True)
    for stale in rootfs.glob("parameters*.bson"):       # another airframe's parameters
        stale.unlink()
    (rootfs / "dataman").unlink(missing_ok=True)        # and its stored mission
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "mission.json").write_text(json.dumps(plan, indent=1))
    with (args.out / "px4_console.log").open("w") as console:
        proc = subprocess.Popen([str(build / "bin" / "px4"), "-d"], cwd=rootfs, stdout=console,
                                stderr=subprocess.STDOUT,
                                env={**os.environ, "PX4_SIM_MODEL": AIRFRAMES[args.airframe][0],
                                     "PX4_SIMULATOR": "sihsim"})
        try:
            fly(args.px4, plan, args.timeout)
        except SystemExit:
            # keep what the failed flight logged, for the diagnosis, before the next run clears it
            client(args.px4, "shutdown")
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
            for k, log in enumerate(sorted((rootfs / "log").rglob("*.ulg"))):
                shutil.copyfile(log, args.out / f"failed_flight_{k}.ulg")
            raise
        client(args.px4, "shutdown")
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    logs = sorted((rootfs / "log").rglob("*.ulg"))
    if len(logs) != 1:
        raise SystemExit(f"expected one flight log, found {len(logs)}")
    shutil.copyfile(logs[0], args.out / "flight.ulg")
    print(f"flew {args.airframe} mission {args.mission}: {args.out / 'flight.ulg'}")


if __name__ == "__main__":
    main()
