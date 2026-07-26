#!/usr/bin/env python3
"""INA219 bring-up / windowed power reader for the RPi4 energy rig (P7b; hw/INA219_wiring.md).

Runs ONLY on the Pi with an INA219 wired per hw/INA219_wiring.md and `pip install pi-ina219`.
  --once            one V / I / P reading (smoke test / calibration check)
  --watch           live stream until Ctrl-C
  --window SECONDS  sample for N s and report mean/median/min/max power (idle or load window)

Assumes a 0.1 Ohm shunt at I2C address 0x40 — change SHUNT_OHMS / ADDRESS for your board. This is a
bring-up helper, not the energy driver; the full protocol lives in hw/energy_protocol.md.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time

SHUNT_OHMS = 0.1        # your board's shunt (silkscreen R100 = 0.1 Ohm); change if different
MAX_AMPS = 3.2          # 320 mV / 0.1 Ohm full-scale
ADDRESS = 0x40          # INA219 default (no A0/A1 jumper)
SAMPLE_HZ = 50.0        # windowed-sampling rate


def _open_ina():
    """Configure and return an INA219 handle (imported lazily so --help works off-Pi)."""
    try:
        from ina219 import INA219  # type: ignore[import-not-found]
    except ImportError:
        sys.exit("pi-ina219 not installed — run:  pip install pi-ina219  (on the Pi)")
    ina = INA219(SHUNT_OHMS, MAX_AMPS, address=ADDRESS)
    ina.configure(ina.RANGE_16V, ina.GAIN_8_320MV, ina.ADC_12BIT, ina.ADC_12BIT)
    return ina


def _read(ina) -> tuple[float, float, float]:
    """(bus volts, amps, watts). Returns 0 A/W if the shunt range is momentarily exceeded."""
    from ina219 import DeviceRangeError  # type: ignore[import-not-found]

    volts = ina.voltage()
    try:
        amps = ina.current() / 1000.0
        watts = ina.power() / 1000.0
    except DeviceRangeError:
        amps = watts = 0.0
    return volts, amps, watts


def _once(ina) -> None:
    v, a, w = _read(ina)
    print(f"V={v:.3f} V   I={a * 1000:.1f} mA   P={w:.3f} W")


def _watch(ina) -> None:
    print("V [V]   I [mA]   P [W]   (Ctrl-C to stop)")
    try:
        while True:
            v, a, w = _read(ina)
            print(f"{v:6.3f}  {a * 1000:7.1f}  {w:6.3f}")
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass


def _window(ina, seconds: float) -> None:
    period = 1.0 / SAMPLE_HZ
    watts: list[float] = []
    volts: list[float] = []
    t_end = time.perf_counter() + seconds
    while time.perf_counter() < t_end:
        v, _a, w = _read(ina)
        watts.append(w)
        volts.append(v)
        time.sleep(period)
    n = len(watts)
    print(f"window={seconds:.0f}s  n={n}")
    print(f"  P  mean={statistics.mean(watts):.4f} W  median={statistics.median(watts):.4f} W  "
          f"min={min(watts):.4f}  max={max(watts):.4f}")
    print(f"  V  mean={statistics.mean(volts):.4f} V  min={min(volts):.4f}  max={max(volts):.4f}")
    print("  (P_mean -> energy/op = (P_loop-P_idle)*t_loop/n_ops; check get_throttled=0x0)")


def main() -> None:
    ap = argparse.ArgumentParser(description="INA219 bring-up / windowed power reader (RPi4)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true", help="single V/I/P reading")
    g.add_argument("--watch", action="store_true", help="live stream until Ctrl-C")
    g.add_argument("--window", type=float, metavar="SECONDS", help="mean/median power over N s")
    args = ap.parse_args()

    ina = _open_ina()
    if args.once:
        _once(ina)
    elif args.watch:
        _watch(ina)
    else:
        _window(ina, args.window)


if __name__ == "__main__":
    main()
