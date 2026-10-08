#!/usr/bin/env python3
"""Record sizes at the operating rate, and the 50 Hz stream's timing, from one PX4 SITL flight.

docs/PX4_LOGS_EXPECTATIONS.md, "records at the operating rate". The flight's log goes through
**the same functions as the twelve public logs** (`px4_log_sizes.flight_runs`, `sizes`), on a
20 ms grid — the spacing of the adopted operating point, which no public log reaches — and on
the 200 ms grid where the public multicopter logs can be compared with it.

    python analysis/px4_sitl_sizes.py                       # results/raw/px4_sitl/quadx
    python analysis/px4_sitl_sizes.py --flight <directory>

Writes `results/raw/px4_sitl_sizes.csv` and `results/raw/px4_sitl_stream_timing.csv`.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import px4_log_sizes as logs  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
FLIGHT = RAW / "px4_sitl" / "quadx"
OPERATING_MS = 20                   # 50 records/s
COMPARISON_MS = 200                 # the native spacing of the public logs
Row = tuple[int, ...]


def within(runs: list[list[Row]], start_ms: int, end_ms: int) -> list[list[Row]]:
    """The parts of `runs` whose records fall in [start, end); no difference crosses the cut."""
    out = [[r for r in run if start_ms <= r[0] < end_ms] for run in runs]
    return [run for run in out if len(run) > logs.BATCH]


def size_row(label: str, spacing_ms: int, runs: list[list[Row]]) -> dict:
    s = logs.sizes(runs)
    frame_1, frame_b = st.mean(s["frame_1"]), st.mean(s["frame_b"])
    # horizontal speed, from the records themselves (vx, vy are in cm/s)
    speed = [(r[4] ** 2 + r[5] ** 2) ** 0.5 / 100.0 for run in runs for r in run]
    return {"part": label, "spacing_ms": spacing_ms, "records": sum(len(r) for r in runs),
            "mean_speed_mps": round(st.mean(speed), 2), "max_speed_mps": round(max(speed), 2),
            "lean_key_mean": round(st.mean(s["lean_key"]), 3),
            "lean_delta_mean": round(st.mean(s["lean_delta"]), 3),
            "lean_delta_min": min(s["lean_delta"]), "lean_delta_max": max(s["lean_delta"]),
            "delta_at_floor_pct": round(100.0 * s["lean_delta"].count(min(s["lean_delta"]))
                                        / len(s["lean_delta"]), 1),
            "frame_1_mean": round(frame_1, 3), "frame_b_mean": round(frame_b, 3),
            "bytes_per_rec": round(frame_b / logs.BATCH, 3),
            "saving_pct": round(100.0 * (1.0 - frame_b / logs.BATCH / frame_1), 2)}


def sizes(flight: Path) -> list[dict]:
    topics = logs._topics(flight / "flight.ulg")
    phases = json.loads((flight / "phases.json").read_text())["phases_boot_ms"]
    rows = []
    for spacing in (OPERATING_MS, COMPARISON_MS):
        runs = logs.flight_runs(topics, spacing)
        if not runs:
            raise SystemExit(f"under {logs.MIN_FLIGHT_S:.0f} s of flight at {spacing} ms")
        rows.append(size_row("whole flight", spacing, runs))
        if spacing == OPERATING_MS:
            for name, (start, end) in phases.items():
                part = within(runs, start, end)
                if part:
                    rows.append(size_row(name, spacing, part))
    return rows


CLOCK_STEP_MS = (0.0, 60.0)        # an interval outside this is the host's clock, not PX4


def _interval_stats(label: str, intervals_ms: list[float], note: str = "",
                    clock_ratio: float | None = None) -> dict:
    """Spread of a list of intervals. `half_p16_p84_ms` is the half-width of the central 68 %:
    a standard deviation that a handful of stalled datagrams cannot inflate. `clock_ratio` is
    the autopilot's elapsed time over this clock's, where both are known."""
    q = st.quantiles(intervals_ms, n=100)
    return {"quantity": label, "n": len(intervals_ms), "mean_ms": round(st.mean(intervals_ms), 4),
            "sd_ms": round(st.pstdev(intervals_ms), 4),
            "half_p16_p84_ms": round((q[83] - q[15]) / 2, 4),
            "min_ms": round(min(intervals_ms), 4), "p01_ms": round(q[0], 4),
            "median_ms": round(st.median(intervals_ms), 4), "p99_ms": round(q[98], 4),
            "max_ms": round(max(intervals_ms), 4),
            "autopilot_per_clock": "" if clock_ratio is None else round(clock_ratio, 4),
            "note": note}


def _ratio(cap: dict[str, list[int]], clock: str) -> float:
    """Autopilot time elapsed per unit of a host clock over a capture (1 = real time)."""
    boot_s = (cap["time_boot_ms"][-1] - cap["time_boot_ms"][0]) / 1e3
    return boot_s / ((cap[clock][-1] - cap[clock][0]) / 1e9)


def _capture(path: Path) -> dict[str, list[int]]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {k: [int(r[k]) for r in rows] for k in rows[0]}


def _intervals(stamps: list[int], per_ms: float) -> list[float]:
    return [(b - a) / per_ms for a, b in zip(stamps, stamps[1:], strict=False)]


def timing(flight: Path) -> list[dict]:
    """Intervals between consecutive 50 Hz position messages.

    *Received* is when the datagram reached this host: on the wall clock (the kernel's receive
    timestamp) or on the monotonic clock (read as the datagram is taken from the socket). The
    wall clock of the host was stepped during the flight, so its raw spread is reported and
    then reported again without the intervals a clock step produced. *Stamped* is the message's
    own `time_boot_ms`: the autopilot's clock at the position sample the message carries, which
    is not when it was sent.
    """
    lo, hi = CLOCK_STEP_MS
    cap = _capture(flight / "stream_timing.csv")
    wall = _intervals(cap["recv_ns"], 1e6)
    kept = [x for x in wall if lo < x < hi]
    stamped = _intervals(cap["time_boot_ms"], 1.0)
    out = [
        _interval_stats("flight: received, wall clock", wall,
                        "as registered; the host clock was stepped during the flight",
                        _ratio(cap, "recv_ns")),
        _interval_stats("flight: received, wall clock, clock steps removed", kept,
                        f"{len(wall) - len(kept)} intervals outside {lo:g}-{hi:g} ms removed; "
                        "decided after seeing the data"),
        _interval_stats("flight: stamped (time_boot_ms)", stamped,
                        "sample time of the position each message carries, not its send time; "
                        + ", ".join(f"{100 * stamped.count(v) / len(stamped):.1f} % at {v:g} ms"
                                    for v in (16.0, 20.0, 24.0))),
    ]
    ground = flight / "stream_timing_ground.csv"
    if ground.exists():
        g = _capture(ground)
        mono = _intervals(g["recv_mono_ns"], 1e6)
        g_wall = _intervals(g["recv_ns"], 1e6)
        out += [
            _interval_stats("ground: received, monotonic clock", mono,
                            "second capture, vehicle on the ground; not the registered capture",
                            _ratio(g, "recv_mono_ns")),
            _interval_stats("ground: received, wall clock", g_wall,
                            f"{sum(not lo < x < hi for x in g_wall)} intervals outside "
                            f"{lo:g}-{hi:g} ms", _ratio(g, "recv_ns")),
        ]
    return out


def _write(path: Path, rows: list[dict], run: str, flight: Path) -> None:
    meta = json.loads((flight / "phases.json").read_text())
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run, "px4": meta["px4"],
                 "model": meta["model"], "host_loadavg_at_end": meta["loadavg_at_end"],
                 "config_hash": provenance.config_hash({"px4": meta["px4"],
                                                        "model": meta["model"]})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flight", type=Path, default=FLIGHT)
    args = ap.parse_args()
    size_rows, timing_rows = sizes(args.flight), timing(args.flight)
    _write(RAW / "px4_sitl_sizes.csv", size_rows, "px4_sitl_sizes", args.flight)
    _write(RAW / "px4_sitl_stream_timing.csv", timing_rows, "px4_sitl_stream_timing", args.flight)
    for r in size_rows:
        print(f"  {r['part']:<16} {r['spacing_ms']:>4} ms  records {r['records']:>6}  key "
              f"{r['lean_key_mean']:>6}  delta {r['lean_delta_mean']:>6} "
              f"[{r['lean_delta_min']}, {r['lean_delta_max']}]  B/rec {r['bytes_per_rec']}")
    for r in timing_rows:
        print(f"  {r['quantity']:<52} n {r['n']:>6}  mean {r['mean_ms']:>8}  sd {r['sd_ms']:>7}"
              f"  central 68 % ±{r['half_p16_p84_ms']}  median {r['median_ms']}  "
              f"p99 {r['p99_ms']}  clock {r['autopilot_per_clock']}")


if __name__ == "__main__":
    main()
