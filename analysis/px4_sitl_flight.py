#!/usr/bin/env python3
"""Fly the registered mission in PX4 software-in-the-loop and record what it sends.

docs/PX4_LOGS_EXPECTATIONS.md, "records at the operating rate". PX4 runs its own estimator,
controllers, logger and MAVLink module against its built-in simulator (`sihsim_quadx`); this
script only starts it, flies the mission that was fixed before any flight, and listens.

    <px4 venv>/bin/python analysis/px4_sitl_flight.py --px4 ~/projects/px4/PX4-Autopilot \
        --out .cache/px4_sitl/quadx

Needs a built `px4_sitl_default` and `pymavlink` (PX4's own Python environment has it; it is not
a dependency of this package). Writes into `--out`:

    flight.ulg          the autopilot's own log, position topics every 20 ms
    stream_timing.csv   one row per GLOBAL_POSITION_INT on the companion-computer link:
                        kernel receive time (wall clock), a monotonic-clock reading taken as
                        the datagram is read, and the message's own time_boot_ms
    phases.json         when each part of the mission began and ended, in time_boot_ms

The mission: take off to 30 m; a 150 m square at a commanded 5 m/s; the same square at 12 m/s;
60 s of position hold; land.

`--ground-seconds N` does not fly: it starts the autopilot, records the stream for N seconds and
stops. The stream's timing does not depend on flying, and the first flight's capture was spoiled
by the host: its wall clock was stepped back eight times during the flight. The monotonic column
exists because of that.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import socket
import struct
import subprocess
import threading
import time
from pathlib import Path

LOGGER_TOPICS = ("vehicle_global_position 20\nvehicle_local_position 20\nbattery_status 20\n"
                 "vehicle_status 20\nvehicle_land_detected 0\n")
ONBOARD_PORT = 14540          # the `-m onboard` MAVLink instance sends here (px4-rc.mavlink)
GCS_PORT = 14550              # the ground-station instance; used for setpoints only
GLOBAL_POSITION_INT = 33
SO_TIMESTAMPNS = 35
TAKEOFF_ALT_M = 30.0
SQUARE_M = 150.0
SPEEDS_MPS = (5.0, 12.0)
HOLD_S = 60.0
LEGS = ((1, 0), (0, 1), (-1, 0), (0, -1))          # north, east, south, west


class Recorder(threading.Thread):
    """Every GLOBAL_POSITION_INT on the onboard link, with its kernel receive time."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        # recv_ns (wall clock, kernel), recv_mono_ns, time_boot_ms, relative_alt_mm
        self.rows: list[tuple[int, int, int, int]] = []
        self.latest: tuple[int, int] | None = None         # (time_boot_ms, relative_alt_mm)
        self._halt = threading.Event()   # (`_stop` is Thread's own)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPNS, 1)
        self._sock.bind(("127.0.0.1", ONBOARD_PORT))
        self._sock.settimeout(1.0)

    def run(self) -> None:
        while not self._halt.is_set():
            try:
                data, ancillary, _flags, _addr = self._sock.recvmsg(4096, 256)
            except TimeoutError:
                continue
            mono_ns = time.monotonic_ns()                   # no time sync steps this clock
            recv_ns = next((sec * 1_000_000_000 + nsec
                            for level, kind, raw in ancillary
                            if level == socket.SOL_SOCKET and kind == SO_TIMESTAMPNS
                            for sec, nsec in [struct.unpack("qq", raw[:16])]), None)
            i = 0
            while i + 12 <= len(data):                     # MAVLink 2 frames in one datagram
                if data[i] != 0xFD:
                    i += 1
                    continue
                length, incompat = data[i + 1], data[i + 2]
                msgid = data[i + 7] | data[i + 8] << 8 | data[i + 9] << 16
                payload = data[i + 10:i + 10 + length].ljust(28, b"\0")   # zeros are truncated
                if msgid == GLOBAL_POSITION_INT and recv_ns is not None:
                    boot_ms, _lat, _lon, _alt, rel_alt = struct.unpack("<Iiiii", payload[:20])
                    self.rows.append((recv_ns, mono_ns, boot_ms, rel_alt))
                    self.latest = (boot_ms, rel_alt)
                i += 12 + length + (13 if incompat & 1 else 0)

    def stop(self) -> None:
        self._halt.set()


def client(px4: Path, tool: str, *args: str) -> str:
    """Run one of PX4's client commands against the running instance."""
    out = subprocess.run([str(px4 / "build/px4_sitl_default/bin" / f"px4-{tool}"), *args],
                         capture_output=True, text=True, timeout=30)
    return out.stdout + out.stderr


def wait_for(what: str, test, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if test():
            return
        time.sleep(0.2)
    raise SystemExit(f"timed out waiting for {what}")


def fly(px4: Path, rec: Recorder) -> dict[str, list[int]]:
    """The registered mission. Returns the phases as [start, end] in time_boot_ms."""
    from pymavlink import mavutil

    def boot_ms() -> int:
        assert rec.latest is not None
        return rec.latest[0]

    def alt_m() -> float:
        return rec.latest[1] / 1000.0 if rec.latest else 0.0

    phases: dict[str, list[int]] = {}
    wait_for("the position stream", lambda: rec.latest is not None, 120)
    for name, value in (("MIS_TAKEOFF_ALT", TAKEOFF_ALT_M), ("NAV_DLL_ACT", 0),
                        ("NAV_RCL_ACT", 0), ("COM_RCL_EXCEPT", 4), ("COM_OF_LOSS_T", 5),
                        ("MPC_XY_VEL_MAX", 12.0)):
        client(px4, "param", "set", name, str(value))
    gcs = mavutil.mavlink_connection(f"udpin:127.0.0.1:{GCS_PORT}")
    gcs.wait_heartbeat(timeout=60)

    def velocity(vn: float, ve: float) -> None:
        gcs.mav.set_position_target_local_ned_send(
            0, gcs.target_system, gcs.target_component, mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            0b0000_1101_1100_0111,                         # use velocity; hold yaw
            0, 0, 0, vn, ve, 0.0, 0, 0, 0, 0, 0)

    start = boot_ms()
    for _ in range(40):                                    # pre-flight checks take a while
        client(px4, "commander", "takeoff")
        time.sleep(3.0)
        if alt_m() > 0.5:
            break
    else:
        raise SystemExit("the vehicle never left the ground")
    # The climb is over when the altitude has stopped changing near the commanded height. (The
    # vehicle settles a metre or two under it: the height is taken from the take-off point and
    # the stream reports it from the home position.)
    def climbed() -> bool:
        before = alt_m()
        time.sleep(3.0)
        return before >= 0.8 * TAKEOFF_ALT_M and abs(alt_m() - before) < 0.2

    wait_for("the end of the climb", climbed, 300)
    phases["takeoff"] = [start, boot_ms()]

    for _ in range(40):                                    # offboard needs setpoints first
        velocity(0.0, 0.0)
        time.sleep(0.05)
    client(px4, "commander", "mode", "offboard")
    for speed in SPEEDS_MPS:
        start = boot_ms()
        for north, east in LEGS:
            leg_end = boot_ms() + int(1000 * SQUARE_M / speed)
            while boot_ms() < leg_end:
                velocity(north * speed, east * speed)
                time.sleep(0.05)
        phases[f"square_{speed:g}mps"] = [start, boot_ms()]

    start = boot_ms()
    client(px4, "commander", "mode", "auto:loiter")
    wait_for("the hold to run its time", lambda: boot_ms() >= start + int(1000 * HOLD_S),
             HOLD_S * 4 + 60)
    phases["hold"] = [start, boot_ms()]

    start = boot_ms()
    client(px4, "commander", "land")
    wait_for("the ground", lambda: alt_m() < 0.3, 240)
    time.sleep(5.0)
    phases["land"] = [start, boot_ms()]
    return phases


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--px4", type=Path, required=True, help="the PX4-Autopilot source tree")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="sihsim_quadx")
    ap.add_argument("--ground-seconds", type=float, default=0.0,
                    help="record the stream for this long without flying, then stop")
    args = ap.parse_args()
    build = args.px4 / "build" / "px4_sitl_default"
    rootfs = build / "rootfs"
    (build / "etc" / "logging").mkdir(parents=True, exist_ok=True)
    (build / "etc" / "logging" / "logger_topics.txt").write_text(LOGGER_TOPICS)
    shutil.rmtree(rootfs / "log", ignore_errors=True)       # one flight, one log
    args.out.mkdir(parents=True, exist_ok=True)

    rec = Recorder()
    rec.start()
    with (args.out / "px4_console.log").open("w") as console:
        px4 = subprocess.Popen([str(build / "bin" / "px4"), "-d"], cwd=rootfs, stdout=console,
                               stderr=subprocess.STDOUT,
                               env={**os.environ, "PX4_SIM_MODEL": args.model,
                                    "PX4_SIMULATOR": "sihsim"})
        try:
            if args.ground_seconds > 0:
                wait_for("the position stream", lambda: rec.latest is not None, 120)
                time.sleep(args.ground_seconds)
                phases = {}
            else:
                phases = fly(args.px4, rec)
        finally:
            client(args.px4, "shutdown")
            try:
                px4.wait(timeout=30)
            except subprocess.TimeoutExpired:
                px4.kill()
            rec.stop()

    ground = args.ground_seconds > 0
    if not ground:
        logs = sorted((rootfs / "log").rglob("*.ulg"))
        if len(logs) != 1:
            raise SystemExit(f"expected one flight log, found {len(logs)}")
        shutil.copyfile(logs[0], args.out / "flight.ulg")
    name = "stream_timing_ground.csv" if ground else "stream_timing.csv"
    with (args.out / name).open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["recv_ns", "recv_mono_ns", "time_boot_ms", "relative_alt_mm"])
        w.writerows(rec.rows)
    if ground:
        print(f"wrote {args.out / name}: {len(rec.rows)} position messages on the ground, "
              f"load average {os.getloadavg()[0]:.1f}")
        return
    version = subprocess.run(["git", "-C", str(args.px4), "describe", "--tags"],
                             capture_output=True, text=True).stdout.strip()
    (args.out / "phases.json").write_text(json.dumps(
        {"px4": version, "model": args.model, "phases_boot_ms": phases,
         "loadavg_at_end": os.getloadavg()[0]}, indent=2))
    print(f"wrote {args.out}: {len(rec.rows)} position messages, phases {list(phases)}")


if __name__ == "__main__":
    main()
