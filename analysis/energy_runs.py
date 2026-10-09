#!/usr/bin/env python3
"""The energy runs of 2026-10-09, one row each, beside what was written down for them.

hw/BENCH_SESSION.md, "Expected of the energy runs of 2026-10-09", committed in a38994f before
the first run. Four runs on `authbc-pi4b` through meter channel 2, after the rig check passed
(results/hw/energy/rig/): a control that repeats July's baseline row, the lean sender with four
records to a frame and with one, and the JSON row with ten repetitions.

Each reduced file is the output of `hw/ina219_capture.py --reduce` on the capture and the
manifest beside it. This script adds nothing to a repetition: it divides by the records in a
frame, keeps a repetition only if its idle window is within `IDLE_TOLERANCE` of the session's
median idle power — the rule of the energy table — and sets the median beside the expectation.

    python analysis/energy_runs.py        # writes results/raw/energy_runs.csv
"""
from __future__ import annotations

import csv
import io
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402

RUNS = REPO / "results" / "hw" / "energy" / "e2e_2026-10-09"
JULY = REPO / "results" / "hw" / "energy" / "e2e"
OUT = REPO / "results" / "raw" / "energy_runs.csv"
IDLE_TOLERANCE = 0.05          # as experiments/energy-table/config.yaml
MIN_CLEAN_REPS = 3
POWER_RANGE_W = (0.70, 0.80)   # registered for every run

# name -> (what it is, registered range of µJ per record)
REGISTERED: dict[str, tuple[str, tuple[float, float]]] = {
    "control_cbor": ("control: first format, CBOR, every record signed", (113.0, 125.0)),
    "lean_b4": ("lean sender, four records to a frame", (146.0, 179.0)),
    "lean_b1": ("lean sender, one record to a frame", (256.0, 313.0)),
    "ajson_r10": ("first format, JSON, every record signed, ten repetitions", (115.0, 127.0)),
}


def _rows(path: Path) -> list[dict[str, str]]:
    body = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def reduce_run(name: str, idle_median_w: float) -> dict:
    """One run: its usable repetitions, in µJ per record."""
    what, (lo, hi) = REGISTERED[name]
    manifest = json.loads((RUNS / f"manifest_{name}.json").read_text())
    batch = int(manifest["configuration"]["batch"])
    reps = _rows(RUNS / f"energy_{name}.csv")
    clean = [r for r in reps
             if abs(float(r["p_idle_w"]) - idle_median_w) <= IDLE_TOLERANCE * idle_median_w]
    per_record = sorted(float(r["energy_per_op_uj"]) / batch for r in clean)
    power = sorted(float(r["delta_p_w"]) for r in clean)
    ok = len(clean) >= MIN_CLEAN_REPS
    median = st.median(per_record) if per_record else float("nan")
    predicted = float(manifest["predicted_cpu_uj_per_record"])
    return {
        "run": name, "what": what, "format": manifest["model_inputs"].get("format", "first"),
        "batch": batch, "board": manifest["host"], "meter_channel": 2,
        "reps_metered": len(reps), "reps_clean": len(clean), "reportable": int(ok),
        "uj_per_record_median": round(median, 3),
        "uj_per_record_min": round(per_record[0], 3), "uj_per_record_max": round(per_record[-1], 3),
        "added_power_w_median": round(st.median(power), 4),
        "added_power_w_min": round(power[0], 4), "added_power_w_max": round(power[-1], 4),
        "records_per_s": round(st.mean(batch * int(r["n_ops"]) / float(r["t_loop_s"])
                                       for r in clean), 1),
        "registered_lo": lo, "registered_hi": hi,
        "inside_registered": int(lo <= median <= hi),
        "power_inside_registered": int(POWER_RANGE_W[0] <= st.median(power) <= POWER_RANGE_W[1]),
        "script_predicted_uj_per_record": round(predicted, 3),
        "metered_over_predicted": round(median / predicted, 4),
    }


def collect() -> list[dict]:
    names = [n for n in REGISTERED if (RUNS / f"energy_{n}.csv").exists()]
    idle = st.median(float(r["p_idle_w"]) for n in names for r in _rows(RUNS / f"energy_{n}.csv"))
    rows = [reduce_run(n, idle) for n in names]
    for r in rows:
        r["idle_power_median_w"] = round(idle, 4)
    return rows


def july_baseline() -> tuple[float, float]:
    """July's baseline row on the other board and sensor: (µJ per record, added power)."""
    reps = _rows(JULY / "energy_d1_baseline.csv")
    return (st.median(float(r["energy_per_op_uj"]) for r in reps),
            st.median(float(r["delta_p_w"]) for r in reps))


def main() -> None:
    rows = collect()
    buf = io.StringIO()
    config = {"idle_tolerance": IDLE_TOLERANCE, "min_clean_reps": MIN_CLEAN_REPS,
              "registered": {k: v[1] for k, v in REGISTERED.items()}, "power": POWER_RANGE_W}
    for k, v in {**provenance.env_block(), "run": "energy_runs",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    uj, watts = july_baseline()
    print(f"July's baseline row, other board and sensor: {uj:.1f} µJ per record, {watts:.3f} W")
    for r in rows:
        print(f"  {r['run']:13} {r['uj_per_record_median']:8.1f} µJ/record "
              f"[{r['uj_per_record_min']:.1f}, {r['uj_per_record_max']:.1f}]  "
              f"{r['added_power_w_median']:.3f} W  {r['reps_clean']} of {r['reps_metered']} reps  "
              f"registered {r['registered_lo']:.0f}–{r['registered_hi']:.0f}: "
              f"{'inside' if r['inside_registered'] else 'OUTSIDE'}; "
              f"power {'inside' if r['power_inside_registered'] else 'OUTSIDE'} 0.70–0.80 W")


if __name__ == "__main__":
    main()
