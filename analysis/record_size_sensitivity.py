#!/usr/bin/env python3
"""Revision A9 — does the result hold for richer records and other airframes? (predictions/A9.md)

The paper's record has nine fields from a synthetic generator, checked against flight logs at
5 Hz and one simulated 50 Hz flight. Here PX4 SIH flights of three airframes
(`analysis/px4_airframe_flight.py`, logged at 20 ms) give records of 9, 15 and 25 fields on the
20 ms grid of the operating point:

    9  ts, lat, lon, alt, vel_x, vel_y, vel_z, battery, mode          (the paper's record)
    15 + roll, pitch, yaw (centidegrees), roll/pitch/yaw rate (mrad/s)
    25 + GNSS fix type, satellites, horizontal and vertical accuracy (cm), true airspeed
         (cm/s), wind north and east (cm/s), current mission item, a status word (arming
         state, failsafe), thrust (per mille)

Each record is coded as the lean format codes its own (`placement/wire_v2.py`: LEB128 varints,
non-negative fields unsigned in a keyframe, every delta zig-zag), and every frame length is
exact (`models/frame.lean_frame_bytes`, the sizing convention's sender and sequence numbers).
Capacity is the closed form of docs/02 §6g (no fitted constant; within 5.5 % of the eighteen
simulated crossings), baseline at 50 frames/s, the design at 12.5.

    python analysis/record_size_sensitivity.py FLIGHT_DIR ...   # results/raw/record_size.csv
    ... --nearest FLIGHT_DIR ...     # nearest sample, not held: record_size_nearest.csv (F105)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dcf_model_check as rule  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.encodings.base import svarint_encode, uvarint_encode  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.models import frame as frame_model  # noqa: E402

OUT = REPO / "results" / "raw" / "record_size.csv"
SPACING_MS = 20
LAMBDA = 50.0
FIELDS_9 = ("ts", "lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
FIELDS_15 = FIELDS_9 + ("roll", "pitch", "yaw", "p", "q", "r")
FIELDS_25 = FIELDS_15 + ("fix", "sats", "eph", "epv", "airspeed", "wind_n", "wind_e",
                         "mission", "status", "thrust")
SETS = {9: FIELDS_9, 15: FIELDS_15, 25: FIELDS_25}
UNSIGNED = frozenset({"ts", "battery", "mode", "fix", "sats", "eph", "epv", "airspeed",
                      "mission", "status", "thrust"})


def _hold(t_src: np.ndarray, v: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Sample-and-hold of `v` (timestamps `t_src`) at `t`; NaN before the first sample."""
    idx = np.searchsorted(t_src, t, side="right") - 1
    out = v[np.clip(idx, 0, len(v) - 1)].astype(float)
    out[idx < 0] = np.nan
    return out


def _nearest(t_src: np.ndarray, v: np.ndarray, t: np.ndarray) -> np.ndarray:
    """The sample of `v` nearest in time to each `t`; NaN before the first sample.

    A sensitivity check on `_hold` (F105): the SIH logs' samples alternate 16 and 24 ms apart, so
    holding them on the 20 ms grid repeats every other value and doubles the next step.
    """
    right = np.clip(np.searchsorted(t_src, t, side="left"), 0, len(t_src) - 1)
    left = np.clip(right - 1, 0, len(t_src) - 1)
    idx = np.where(np.abs(t_src[left] - t) <= np.abs(t_src[right] - t), left, right)
    out = v[idx].astype(float)
    out[t < t_src[0]] = np.nan
    return out


def records(path: Path, *, nearest: bool = False) -> list[dict[str, int]]:
    """In-flight records on the 20 ms grid, every field present.

    Timestamps are placed an hour into a flight (the sizing convention's origin,
    `leanframes.CONVENTION_TS0_MS`): a keyframe's time field is then as long as the paper's.
    Each topic is held (the registered method) or, with ``nearest``, its nearest sample taken.
    """
    resample = _nearest if nearest else _hold
    from pyulog import ULog  # a pinned development dependency; only this reader needs it

    log = ULog(str(path))
    d = {m.name: m.data for m in log.data_list if m.multi_id == 0}

    def col(topic: str, field: str, t: np.ndarray) -> np.ndarray:
        if topic not in d or field not in d[topic]:
            return np.full(t.shape, np.nan)
        return resample(d[topic]["timestamp"], d[topic][field], t)

    gp, lp = d["vehicle_global_position"], d["vehicle_local_position"]
    t = np.arange(max(gp["timestamp"][0], lp["timestamp"][0]),
                  min(gp["timestamp"][-1], lp["timestamp"][-1]), SPACING_MS * 1000,
                  dtype=np.int64)
    q = [col("vehicle_attitude", f"q[{k}]", t) for k in range(4)]
    roll = np.arctan2(2 * (q[0] * q[1] + q[2] * q[3]), 1 - 2 * (q[1] ** 2 + q[2] ** 2))
    pitch = np.arcsin(np.clip(2 * (q[0] * q[2] - q[3] * q[1]), -1, 1))
    yaw = np.arctan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
    thrust = (np.abs(col("vehicle_thrust_setpoint", "xyz[0]", t))
              + np.abs(col("vehicle_thrust_setpoint", "xyz[2]", t)))
    landed = col("vehicle_land_detected", "landed", t)
    raw = {
        "ts": leanframes.CONVENTION_TS0_MS + (t - t[0]) / 1000.0,
        "lat": col("vehicle_global_position", "lat", t) * 1e7,
        "lon": col("vehicle_global_position", "lon", t) * 1e7,
        "alt": col("vehicle_global_position", "alt", t) * 100.0,
        "vel_x": col("vehicle_local_position", "vx", t) * 100.0,
        "vel_y": col("vehicle_local_position", "vy", t) * 100.0,
        "vel_z": col("vehicle_local_position", "vz", t) * 100.0,
        "battery": np.clip(col("battery_status", "remaining", t), 0, 1) * 100.0,
        "mode": col("vehicle_status", "nav_state", t) % 8,
        "roll": np.degrees(roll) * 100, "pitch": np.degrees(pitch) * 100,
        "yaw": np.degrees(yaw) * 100,
        "p": col("vehicle_angular_velocity", "xyz[0]", t) * 1000,
        "q": col("vehicle_angular_velocity", "xyz[1]", t) * 1000,
        "r": col("vehicle_angular_velocity", "xyz[2]", t) * 1000,
        "fix": col("sensor_gps", "fix_type", t), "sats": col("sensor_gps", "satellites_used", t),
        "eph": col("sensor_gps", "eph", t) * 100, "epv": col("sensor_gps", "epv", t) * 100,
        "airspeed": np.clip(np.nan_to_num(col("airspeed_validated", "true_airspeed_m_s", t)),
                            0, None) * 100,
        "wind_n": np.nan_to_num(col("wind", "windspeed_north", t)) * 100,
        "wind_e": np.nan_to_num(col("wind", "windspeed_east", t)) * 100,
        "mission": np.nan_to_num(col("mission_result", "seq_current", t)),
        "status": col("vehicle_status", "arming_state", t) * 16
        + np.nan_to_num(col("vehicle_status", "failsafe", t)),
        "thrust": np.clip(np.nan_to_num(thrust), 0, 2) * 1000,
    }
    mat = np.column_stack([raw[f] for f in FIELDS_25])
    ok = np.isfinite(mat).all(axis=1) & (landed == 0)
    rows = np.rint(np.nan_to_num(mat)).astype(np.int64)
    return [dict(zip(FIELDS_25, r.tolist(), strict=True)) for r, good in zip(rows, ok,
                                                                              strict=True)
            if good]


def key_bytes(rec: dict[str, int], fields: tuple[str, ...]) -> int:
    return sum(len(uvarint_encode(rec[f]) if f in UNSIGNED else svarint_encode(rec[f]))
               for f in fields)


def delta_bytes(rec: dict[str, int], prev: dict[str, int], fields: tuple[str, ...]) -> int:
    return sum(len(svarint_encode(rec[f] - prev[f])) for f in fields)


def frame(n: int, stream: int) -> int:
    return frame_model.lean_frame_bytes(src=leanframes.CONVENTION_SRC,
                                        base_seq=leanframes.CONVENTION_BASE_SEQ, n=n,
                                        stream_bytes=stream)


def capacity(frame_bytes: float, fps: float) -> float:
    return rule.closed_form_crossing(fps, bianchi.t_broadcast(frame_bytes))


def frames(recs: list[dict[str, int]], fields: tuple[str, ...], b: int) -> list[int]:
    """Exact lengths of the frames of `b` consecutive records (a keyframe, then deltas).

    A group that straddles a gap in the log (records dropped on the ground) is not a frame.
    """
    out = []
    for i in range(0, len(recs) - b + 1, b):
        group = recs[i:i + b]
        if group[-1]["ts"] - group[0]["ts"] > (b - 1) * SPACING_MS:
            continue
        stream = key_bytes(group[0], fields) + sum(
            delta_bytes(r, p, fields) for p, r in zip(group, group[1:], strict=False))
        out.append(frame(b, stream))
    return out


def summarise(recs: list[dict[str, int]], fields: tuple[str, ...]) -> dict[str, float]:
    keys = [key_bytes(r, fields) for r in recs]
    deltas = [delta_bytes(r, p, fields) for p, r in zip(recs, recs[1:], strict=False)
              if r["ts"] - p["ts"] == SPACING_MS]
    out: dict[str, float] = {"records": len(recs), "key_mean": st.mean(keys),
                             "delta_mean": st.mean(deltas), "delta_p95": float(
                                 np.percentile(deltas, 95))}
    for b in (1, 2, 3, 4):
        out[f"frame_{b}"] = st.mean(frames(recs, fields, b))
    out["bytes_per_rec_4"] = out["frame_4"] / 4
    out["saving_pct"] = 100 * (1 - out["bytes_per_rec_4"] / out["frame_1"])
    out["n_base"] = capacity(out["frame_1"], LAMBDA)
    out["n_design"] = capacity(out["frame_4"], LAMBDA / 4)
    out["ratio"] = out["n_design"] / out["n_base"]
    return out


def ratio_at(key: float, delta: float) -> float:
    """The closed form's design/baseline ratio for records of these sizes."""
    return (capacity(frame(4, round(key + 3 * delta)), LAMBDA / 4)
            / capacity(frame(1, round(key)), LAMBDA))


def where_ratio_falls_below(target: float, key_per_delta: float) -> float:
    """Delta size (B) at which the ratio first drops below `target`, keyframes scaled with it."""
    for delta in np.arange(5.0, 2000.0, 1.0):
        if ratio_at(key_per_delta * delta, delta) < target:
            return float(delta)
    return float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("flights", nargs="+", type=Path)
    ap.add_argument("--nearest", action="store_true",
                    help="take each topic's nearest sample instead of holding it (F105)")
    args = ap.parse_args()
    rows = []
    for flight in args.flights:
        plan = json.loads((flight / "mission.json").read_text())
        recs = records(flight / "flight.ulg", nearest=args.nearest)
        # the speed drawn, the cruise commanded (fixed wing and VTOL capped at 15 m/s, decided
        # 2026-10-22) and the ground speed flown, mean over the in-flight records
        flown = st.mean(float(np.hypot(r["vel_x"], r["vel_y"])) / 100.0 for r in recs)
        for n_fields, fields in SETS.items():
            rows.append({"airframe": plan["airframe"], "mission": plan["number"],
                         "speed_mps": plan["speed_mps"],
                         "cruise_mps": plan.get("cruise_flown_mps", plan["speed_mps"]),
                         "ground_speed_mps": round(flown, 2), "fields": n_fields,
                         **{k: round(v, 3) for k, v in summarise(recs, fields).items()}})
    for n_fields in SETS:
        group = [r for r in rows if r["fields"] == n_fields]
        k_per_d = st.mean(r["key_mean"] for r in group) / st.mean(r["delta_mean"] for r in group)
        for r in group:
            r["delta_where_ratio_below_2"] = round(where_ratio_falls_below(2.0, k_per_d), 1)
    buf = io.StringIO()
    config: dict[str, object] = {"sets": SETS, "spacing": SPACING_MS}
    if args.nearest:   # the registered hold keeps its hash
        config["resample"] = "nearest"
    for k, v in {**provenance.env_block(), "run": "record_size",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    (OUT.with_name("record_size_nearest.csv") if args.nearest else OUT).write_text(buf.getvalue())
    for r in rows:
        print({k: r[k] for k in ("airframe", "mission", "fields", "key_mean", "delta_mean",
                                 "saving_pct", "ratio")})


if __name__ == "__main__":
    main()
