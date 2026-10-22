#!/usr/bin/env python3
"""Why PX4's SIH fixed wing and VTOL fly no faster than ~14 and ~13 m/s, and what speed does to
the record sizes (revision A9, after its outcome; predictions/A9.md, addendum).

For every fixed-wing and VTOL log in the flight directory (the registered missions, the unused
attempts, and the diagnostic flights of mission 98, which change one SIH parameter): the
commanded cruise, the airspeed held in level flight (|vertical speed| < 0.3 m/s, fixed-wing
mode), its 99th percentile, the throttle there, the share of flight at full throttle, and
whether the mission completed. For the diagnostic flights and two registered ones, the record
sizes of `record_size_sensitivity.py` (both resamplings).

    python analysis/sih_speed_limit.py [DIR]     # DIR defaults to ~/.cache/authbc-px4
        -> results/raw/sih_speed_limit.csv, results/raw/record_size_speed.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import record_size_sensitivity as rs  # noqa: E402

from authbc.bench import provenance  # noqa: E402

OUT = REPO / "results" / "raw" / "sih_speed_limit.csv"
OUT_SIZES = REPO / "results" / "raw" / "record_size_speed.csv"
FIXED_WING = 2                          # vehicle_status.vehicle_type in fixed-wing flight
SIZED = ("airplane-01", "airplane-05", "diag-thrust", "diag-kdv", "diag-ctrl")


def _topic(log, name: str) -> dict | None:
    return next((d.data for d in log.data_list if d.name == name and d.multi_id == 0), None)


def _at(src: dict, field: str, t: np.ndarray) -> np.ndarray:
    i = np.clip(np.searchsorted(src["timestamp"], t) - 1, 0, len(src["timestamp"]) - 1)
    return src[field][i]


def speed_row(directory: Path) -> dict | None:
    from pyulog import ULog  # a pinned development dependency

    ulg = directory / "flight.ulg"
    completed = ulg.exists()
    if not completed:
        ulg = directory / "failed_flight_0.ulg"
        if not ulg.exists():
            return None
    plan = json.loads((directory / "mission.json").read_text())
    log = ULog(str(ulg))
    a, th = _topic(log, "airspeed_validated"), _topic(log, "vehicle_thrust_setpoint")
    lp, vs = _topic(log, "vehicle_local_position"), _topic(log, "vehicle_status")
    if a is None or th is None or lp is None or vs is None:
        return None
    t, tas = a["timestamp"], a["true_airspeed_m_s"]
    thr, vz = _at(th, "xyz[0]", t), _at(lp, "vz", t)
    fw = (_at(vs, "vehicle_type", t) == FIXED_WING) & np.isfinite(tas) & (tas > 5.0)
    level = fw & (np.abs(vz) < 0.3)
    return {"flight": directory.name, "airframe": plan["airframe"], "mission": plan["number"],
            "completed": int(completed), "speed_drawn_mps": plan["speed_mps"],
            "cruise_commanded_mps": plan.get("cruise_flown_mps", plan["speed_mps"]),
            "extra_params": ";".join(f"{k}={v}" for k, v in plan.get("extra_params", {}).items()),
            "level_airspeed_p50": round(float(np.median(tas[level])), 2),
            "airspeed_p99": round(float(np.percentile(tas[fw], 99)), 2),
            "airspeed_max": round(float(tas[fw].max()), 2),
            "level_throttle_p50": round(float(np.median(thr[level])), 3),
            "full_throttle_share": round(float(np.mean(thr[fw] >= 0.99)), 3),
            "log": ulg.name, "sha256": hashlib.sha256(ulg.read_bytes()).hexdigest()}


def size_rows(directory: Path) -> list[dict]:
    out = []
    for nearest in (False, True):
        recs = rs.records(directory / "flight.ulg", nearest=nearest)
        ground = float(np.mean([np.hypot(r["vel_x"], r["vel_y"]) / 100.0 for r in recs]))
        for n_fields, fields in rs.SETS.items():
            s = rs.summarise(recs, fields)
            out.append({"flight": directory.name, "resample": "nearest" if nearest else "hold",
                        "ground_speed_mps": round(ground, 2), "fields": n_fields,
                        **{k: round(s[k], 3) for k in ("key_mean", "delta_mean", "delta_p95",
                                                       "saving_pct", "ratio")}})
    return out


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?", type=Path, default=Path.home() / ".cache" / "authbc-px4")
    args = ap.parse_args()
    dirs = sorted(d for d in args.dir.iterdir()
                  if d.is_dir() and re.match(r"(airplane|vtol|diag)-", d.name))
    rows = [r for d in dirs if (r := speed_row(d)) is not None]
    _write(OUT, rows, "sih_speed_limit")
    sizes = [r for name in SIZED if (args.dir / name / "flight.ulg").exists()
             for r in size_rows(args.dir / name)]
    _write(OUT_SIZES, sizes, "record_size_speed")
    for r in rows:
        print({k: r[k] for k in ("flight", "completed", "cruise_commanded_mps", "extra_params",
                                 "level_airspeed_p50", "airspeed_max", "level_throttle_p50")})
    for r in sizes:
        print(r)


if __name__ == "__main__":
    main()
