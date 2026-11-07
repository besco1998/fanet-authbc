#!/usr/bin/env python3
"""Rig self-test, board side: a fixed sequence the meter can be judged on (hw/RIG.md §8).

Run on the board under test while `hw/rig_check.py` captures the meter on the host. It drives
the sync line and loads the processor in a known pattern:

    3 s  line low,  idle
    5 s  line HIGH, idle                 — the line's own effect on the reading, if any
    2 s  line low,  idle
    5 s  line HIGH, one core busy        — the load every energy window applies
    2 s  line low,  idle
    5 s  line HIGH, every core busy      — the supply at its worst
    3 s  line low,  idle

Why it exists. On 2026-10-09 the board's ground had come loose from the meter's. The sync wire
still worked and the current still read correctly, so nothing looked wrong; but the voltage
reading moved by 0.29 V with the state of the sync line and the power with it (finding F78).
An energy run on that rig would have produced a tidy number. The three windows above are the
shortest sequence that exposes that fault, a wrong channel, a weak supply and a dead sync line.

    ./hw/rig_selftest.py            # writes results/hw/energy/rig/selftest-<host>-<UTC>.json
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import platform
import socket
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "hw"))

from energy_loop import DEFAULT_CHIP, DEFAULT_LINE, SyncLine, device_state  # noqa: E402

# (seconds, line high, busy cores; -1 = every core)
SEQUENCE: tuple[tuple[float, bool, int], ...] = (
    (3.0, False, 0), (5.0, True, 0), (2.0, False, 0), (5.0, True, 1),
    (2.0, False, 0), (5.0, True, -1), (3.0, False, 0),
)


def _spin(until: float) -> None:
    while time.perf_counter() < until:
        pass


def hold(seconds: float, cores: int) -> None:
    """Keep `cores` cores busy for `seconds`; with none, sleep."""
    until = time.perf_counter() + seconds
    if cores == 0:
        time.sleep(seconds)
        return
    helpers = [multiprocessing.Process(target=_spin, args=(until,)) for _ in range(cores - 1)]
    for h in helpers:
        h.start()
    _spin(until)
    for h in helpers:
        h.join()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chip", default=DEFAULT_CHIP)
    ap.add_argument("--line", type=int, default=DEFAULT_LINE)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    sync = SyncLine(args.chip, args.line)
    if not sync.available:
        sys.exit("no GPIO backend: the sync line cannot be driven, so the rig cannot be tested")
    n_cores = os.cpu_count() or 1
    before = device_state()
    steps = []
    try:
        for seconds, high, cores in SEQUENCE:
            busy = n_cores if cores < 0 else cores
            t0_utc, t0 = datetime.now(UTC).isoformat(), time.perf_counter()
            sync.set(high)
            hold(seconds, busy)
            sync.set(False)
            steps.append({"line_high": high, "busy_cores": busy, "asked_s": seconds,
                          "duration_s": round(time.perf_counter() - t0, 4),
                          "t_start_utc": t0_utc})
    finally:
        sync.close()
    after = device_state()

    host = socket.gethostname().split(".")[0]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or REPO / "results" / "hw" / "energy" / "rig" / f"selftest-{host}-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": "authbc.rig.selftest/1", "host": host, "run_utc": stamp,
        "platform": platform.platform(), "python": sys.version.split()[0],
        "gpio_backend": sync.backend, "cores": n_cores,
        "before": before, "after": after, "steps": steps,
    }, indent=2))
    print(f"wrote {out}")
    print(f"under-voltage events this boot: {before['undervoltage_events']} before, "
          f"{after['undervoltage_events']} after; governor {after['governor']}")


if __name__ == "__main__":
    main()
