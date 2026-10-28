#!/usr/bin/env python3
"""Rig self-test, host side: judge the meter on the sequence `hw/rig_selftest.py` runs.

No energy figure is to be taken on a rig that has not passed this the same day (hw/RIG.md §8).

    # on this machine, the Arduino attached; then start hw/rig_selftest.py on the board
    ./hw/rig_check.py --port /dev/ttyACM0 --channel 1 --seconds 45
    # or judge a capture already made, with the board's own record of the test
    ./hw/rig_check.py --samples samples.csv --manifest selftest-*.json --channel 1

What is checked, and where each limit comes from. The reference is the rig of July 2026, whose
captures are in results/hw/energy/ and reduce to the published figures bit for bit.

| check | limit | July's rig | fault of 2026-10-09 |
|---|---|---|---|
| the sync line marks three windows of 5 s | 5.0 ± 0.2 s each | — | passed |
| the voltage does not move with the sync line | within 15 mV | −1 to −4 mV | **−290 mV** |
| idle voltage is the same before and after | within 20 mV | 1 mV | 50–110 mV |
| this channel is the board under test | +80 mA or more for one busy core | +140–160 mA | passed |
| … and the other channel does not move | within 30 mA | — | passed |
| supply with one core busy | 4.75 V or more (the board's tolerance) | 4.99 V | 4.73 V |
| supply with every core busy | 4.63 V or more (firmware throttles below) | not run | 4.39 V |
| the chip's power register agrees with V × I | within 5 mW on average | −0.2 mW | passed |
| sampling | 49–51 per second | 50.0 | passed |
| no under-voltage logged by the board during the test | none | none | none |

⚠️ What passing does not show: that the sensor's gain is right. A wrong shunt value or a
miscalibrated sensor passes every check here. That needs a reference load (hw/RIG.md §7,
docs/OPEN_ITEMS.md G22).
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "hw"))

import ina219_capture  # noqa: E402

WINDOW_S = 5.0                 # what rig_selftest.py asks for
WINDOW_TOLERANCE_S = 0.2
LINE_SHIFT_MAX_V = 0.015       # July: −0.001 to −0.004 V
IDLE_DRIFT_MAX_V = 0.020
ONE_CORE_MIN_A = 0.080         # July: +0.138 to +0.157 A for one busy core
OTHER_CHANNEL_MAX_A = 0.030
ONE_CORE_MIN_V = 4.75          # 5 V − 5 %
ALL_CORES_MIN_V = 4.63         # the Raspberry Pi 4's under-voltage threshold
POWER_REGISTER_MAX_W = 0.005
RATE_HZ = (49.0, 51.0)
EDGE = 10                      # samples dropped at each end of a segment (0.2 s)


@dataclass(frozen=True)
class Check:
    name: str
    value: str
    limit: str
    ok: bool | None            # None: reported, not judged


def _runs(rows: list[dict[str, str]]) -> list[tuple[bool, list[dict[str, str]]]]:
    out: list[tuple[bool, list[dict[str, str]]]] = []
    for r in rows:
        high = r["window"] == "1"
        if out and out[-1][0] == high:
            out[-1][1].append(r)
        else:
            out.append((high, [r]))
    return out


def _mean(seg: list[dict[str, str]], col: str) -> float:
    core = seg[EDGE:-EDGE] if len(seg) > 4 * EDGE else seg
    return st.mean(float(r[col]) for r in core)


def assess(rows: list[dict[str, str]], channel: int,
           manifest: dict | None = None) -> list[Check]:
    """Every check of the table above, on one capture of the self-test sequence."""
    other = 2 if channel == 1 else 1
    v, i, p = f"V{channel}", f"I{channel}_mA", f"P{channel}_W"
    runs = _runs(rows)
    windows = [(k, seg) for k, (high, seg) in enumerate(runs) if high and len(seg) >= 50]
    spans = [(int(seg[-1]["ms"]) - int(seg[0]["ms"]) + 20) / 1000.0 for _k, seg in windows]
    sync_ok = len(windows) == 3 and all(abs(s - WINDOW_S) <= WINDOW_TOLERANCE_S for s in spans)
    checks = [Check("the sync line marks three windows of 5 s",
                    ", ".join(f"{s:.2f} s" for s in spans) or "none seen",
                    f"three, each {WINDOW_S} ± {WINDOW_TOLERANCE_S} s", sync_ok)]
    if not sync_ok:
        return checks              # nothing below can be located without the windows

    (k1, idle), (k2, one), (_k3, full) = windows
    low_before, low_after = runs[k1 - 1][1] if k1 else [], runs[k1 + 1][1]
    last_low = runs[-1][1] if not runs[-1][0] else []
    if len(low_before) < 50 or len(low_after) < 50 or len(last_low) < 50:
        return [*checks, Check("idle with the line low before, between and after the windows",
                               "too short", "1 s or more each", False)]
    v_low = st.mean((_mean(low_before[-150:], v), _mean(low_after, v)))
    shift = _mean(idle, v) - v_low
    drift = _mean(last_low, v) - _mean(low_before[-150:], v)
    step = (_mean(one, i) - _mean(idle, i)) / 1000.0
    step_other = (_mean(one, f"I{other}_mA") - _mean(idle, f"I{other}_mA")) / 1000.0
    v_one, v_full = _mean(one, v), _mean(full, v)
    register = st.mean(float(r[p]) - float(r[v]) * float(r[i]) / 1000.0 for r in rows)
    rate = (len(rows) - 1) / ((int(rows[-1]["ms"]) - int(rows[0]["ms"])) / 1000.0)
    amps_full = (_mean(full, i) - _mean(idle, i)) / 1000.0
    checks += [
        Check("the voltage does not move with the sync line", f"{1000 * shift:+.0f} mV",
              f"within {1000 * LINE_SHIFT_MAX_V:.0f} mV", abs(shift) <= LINE_SHIFT_MAX_V),
        Check("idle voltage is the same before and after", f"{1000 * drift:+.0f} mV",
              f"within {1000 * IDLE_DRIFT_MAX_V:.0f} mV", abs(drift) <= IDLE_DRIFT_MAX_V),
        Check("this channel is the board under test",
              f"{1000 * step:+.0f} mA here, {1000 * step_other:+.0f} mA on the other channel",
              f"+{1000 * ONE_CORE_MIN_A:.0f} mA or more here, within "
              f"{1000 * OTHER_CHANNEL_MAX_A:.0f} mA there",
              step >= ONE_CORE_MIN_A and abs(step_other) <= OTHER_CHANNEL_MAX_A),
        Check("supply with one core busy", f"{v_one:.3f} V", f"{ONE_CORE_MIN_V} V or more",
              v_one >= ONE_CORE_MIN_V),
        Check("supply with every core busy", f"{v_full:.3f} V", f"{ALL_CORES_MIN_V} V or more",
              v_full >= ALL_CORES_MIN_V),
        Check("the chip's power register agrees with V × I", f"{1000 * register:+.1f} mW",
              f"within {1000 * POWER_REGISTER_MAX_W:.0f} mW",
              abs(register) <= POWER_REGISTER_MAX_W),
        Check("sampling", f"{rate:.2f} per second", f"{RATE_HZ[0]:.0f}–{RATE_HZ[1]:.0f}",
              RATE_HZ[0] <= rate <= RATE_HZ[1]),
        Check("idle power", f"{_mean(idle, p):.3f} W", "reported", None),
        Check("one busy core adds", f"{_mean(one, p) - _mean(idle, p):.3f} W", "reported", None),
        Check("every core busy adds", f"{_mean(full, p) - _mean(idle, p):.3f} W", "reported",
              None),
        Check("source resistance seen from the board",
              f"{(_mean(idle, v) - v_full) / amps_full:.2f} Ω" if amps_full > 0.05 else "n/a",
              "reported (July: 0.45–0.49 Ω)", None),
    ]
    if manifest is not None:
        before, after = manifest["before"], manifest["after"]
        events = (before["undervoltage_events"], after["undervoltage_events"])
        checks += [
            Check("no under-voltage logged by the board during the test",
                  f"{events[0]} before, {events[1]} after", "the same count, and readable",
                  "NA" not in events and events[0] == events[1]),
            Check("the board's governor", after["governor"], "performance",
                  after["governor"] == "performance"),
        ]
    return checks


def report(checks: list[Check]) -> bool:
    width = max(len(c.name) for c in checks)
    for c in checks:
        verdict = {True: "pass", False: "FAIL", None: "    "}[c.ok]
        print(f"  {verdict}  {c.name:<{width}}  {c.value}   [{c.limit}]")
    passed = all(c.ok is not False for c in checks)
    print("\nRIG CHECK " + ("PASSED" if passed else "FAILED — take no energy figure on this rig"))
    return passed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=Path, help="a capture of the self-test already made")
    ap.add_argument("--port", help="capture now from this serial port instead")
    ap.add_argument("--seconds", type=float, default=45.0, help="length of that capture")
    ap.add_argument("--manifest", type=Path, help="the board's selftest-*.json, if at hand")
    ap.add_argument("--channel", type=int, required=True, choices=(1, 2),
                    help="the meter channel the board under test is on")
    ap.add_argument("--out", type=Path, help="where to write the report (JSON)")
    args = ap.parse_args()
    if bool(args.samples) == bool(args.port):
        ap.error("give exactly one of --samples and --port")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rig_dir = REPO / "results" / "hw" / "energy" / "rig"
    samples = args.samples or rig_dir / f"rigcheck-samples-{stamp}.csv"
    if args.port:
        print(f"start hw/rig_selftest.py on the board now; capturing {args.seconds:.0f} s")
        ina219_capture.capture(args.port, samples, args.seconds)
    rows = ina219_capture._read_samples(samples)
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None
    checks = assess(rows, args.channel, manifest)
    passed = report(checks)
    out = args.out or rig_dir / f"rigcheck-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": "authbc.rig.check/1", "checked_utc": stamp, "channel": args.channel,
        "samples": samples.name, "manifest": args.manifest.name if args.manifest else None,
        "passed": passed, "checks": [asdict(c) for c in checks]}, indent=2))
    print(f"wrote {out}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
