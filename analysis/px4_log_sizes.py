#!/usr/bin/env python3
"""Record sizes on real flight telemetry: public PX4 logs through the project's own encoders.

Every record size in the project comes from one seeded generator whose delta record is exactly
9 B in every sample. This script answers whether that is representative, by building the same
nine-field record from real flight logs and encoding it with the same code
(`placement/wire_v2.py`, `encodings/delta_enc.py`).

The prediction, the selection rule and what each outcome means were committed before any log was
opened: `docs/PX4_LOGS_EXPECTATIONS.md`.

    python analysis/px4_log_sizes.py --select    # needs network: apply the rule, write the manifest
    python analysis/px4_log_sizes.py             # download what is missing, parse, write the CSV

Needs `pyulog` (`pip install pyulog`); it is not a dependency of the package. Logs are cached in
`.cache/px4/`, which is git-ignored: they are public uploads and are not redistributed here.
Writes `results/raw/px4_log_sizes.csv`.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path
from statistics import mean

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.bench.telemgen import TelemetryRecord  # noqa: E402
from authbc.encodings.delta_enc import DeltaEncoder  # noqa: E402
from authbc.ledger.record import Record  # noqa: E402
from authbc.models import frame as frame_model  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402

INDEX_URL = "https://review.px4.io/dbinfo"
CACHE = REPO / ".cache" / "px4"
MANIFEST = REPO / "experiments" / "px4-logs" / "manifest.yaml"
OUT = REPO / "results" / "raw" / "px4_log_sizes.csv"

# ---- the selection rule (docs/PX4_LOGS_EXPECTATIONS.md) -------------------------------------
DURATION_S = (300, 900)
RELEASES = ("v1.14", "v1.15", "v1.16", "v1.17")
MAX_BYTES = 45_000_000
MIN_FLIGHT_S = 60.0
STRATA: dict[str, tuple[tuple[str, ...], int]] = {
    "quadrotor": (("Quadrotor",), 4),
    "hexa/octorotor": (("Hexarotor", "Octorotor"), 2),
    "fixed wing": (("Fixed Wing",), 3),
    "vtol": (("VTOL Standard", "Tiltrotor VTOL"), 3),
}
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "vehicle_global_position": ("lat", "lon", "alt"),
    "vehicle_local_position": ("vx", "vy", "vz"),
    "battery_status": ("remaining",),
    "vehicle_status": ("nav_state",),
    "vehicle_land_detected": ("landed",),
}
TOPICS = tuple(REQUIRED_FIELDS)

GENERATOR_STEP_MS = 50                       # the generator emits one record every 50 ms
# Record spacing -> generator records per seed at that spacing. Every spacing is a multiple of
# the generator's step, so each has a generator twin; the counts are those of
# experiments/frame-components (1000 per seed at the standard protocol, fewer when records are
# seconds apart and a seed would otherwise need hours of walk).
SPACINGS_MS: dict[int, int] = {50: 1000, 100: 1000, 200: 1000, 1000: 200, 5500: 64}
BATCH = 4
N_MODES = 8                                  # the schema's flight-mode enum (bench/telemgen.py)


# ============================================================================== selection
def eligible(entry: dict) -> bool:
    """The metadata half of the rule; size and content are checked when the log is fetched."""
    return (DURATION_S[0] <= (entry.get("duration_s") or 0) <= DURATION_S[1]
            and entry.get("num_logged_errors") == 0
            and (entry.get("ver_sw_release") or "")[:5] in RELEASES
            and "SITL" not in (entry.get("sys_hw") or "").upper()
            and bool(entry.get("vehicle_uuid")))


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=300) as resp:
        return resp.read()


def _log_path(log_id: str) -> Path:
    return CACHE / f"{log_id}.ulg"


def _download(entry: dict) -> Path | None:
    """The log file, from cache or the server; None if it is over the size limit."""
    path = _log_path(entry["log_id"])
    if not path.exists():
        req = urllib.request.Request(entry["download_url"], method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as resp:
            if int(resp.headers.get("Content-Length", "0")) > MAX_BYTES:
                return None
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_fetch(entry["download_url"]))
    return path


def select() -> None:
    """Apply the rule to the live index and write the manifest. Run once; the manifest is kept."""
    raw = _fetch(INDEX_URL)
    index = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
    pool = sorted((e for e in index if eligible(e)), key=lambda e: e["log_id"])
    used_vehicles: set[str] = set()
    chosen: list[dict] = []
    skipped: list[dict] = []
    for stratum, (types, want) in STRATA.items():
        got = 0
        for e in pool:
            if got == want:
                break
            if e["mav_type"] not in types or e["vehicle_uuid"] in used_vehicles:
                continue
            path = _download(e)
            reason = "over the size limit" if path is None else unusable(path)
            if reason:
                skipped.append({"log_id": e["log_id"], "stratum": stratum, "reason": reason})
                print(f"  skip {e['log_id']}  {reason}")
                continue
            assert path is not None
            used_vehicles.add(e["vehicle_uuid"])
            got += 1
            chosen.append({
                "log_id": e["log_id"], "stratum": stratum, "mav_type": e["mav_type"],
                "release": e["ver_sw_release"].split()[0], "hardware": e["sys_hw"],
                "duration_s": e["duration_s"], "log_date": e["log_date"],
                "url": e["download_url"],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
            print(f"  take {e['log_id']}  {stratum:<15} {e['mav_type']}")
        if got < want:
            raise SystemExit(f"only {got} of {want} usable logs in stratum {stratum!r}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        "# Flight logs measured by analysis/px4_log_sizes.py — written by `--select`, then kept.\n"
        "# Rule: docs/PX4_LOGS_EXPECTATIONS.md. The logs are public uploads to the PX4 Flight\n"
        "# Review service and are not redistributed; each is pinned here by id and SHA-256.\n"
        + yaml.safe_dump({
            "index_url": INDEX_URL, "index_entries": len(index),
            "index_sha256": hashlib.sha256(raw).hexdigest(), "eligible": len(pool),
            "logs": chosen, "skipped": skipped}, sort_keys=False))
    print(f"wrote {MANIFEST} ({len(chosen)} logs, {len(skipped)} skipped)")


# ============================================================================== parsing
def _topics(path: Path) -> dict[str, dict[str, np.ndarray]]:
    from pyulog import ULog
    ulog = ULog(str(path), message_name_filter_list=list(TOPICS), disable_str_exceptions=True)
    return {d.name: d.data for d in ulog.data_list if d.multi_id == 0}


def _flight_mask(t_us: np.ndarray, topics: dict[str, dict[str, np.ndarray]]) -> np.ndarray:
    """True where the vehicle is off the ground, by the log's own land detector."""
    land = topics["vehicle_land_detected"]
    idx = np.searchsorted(land["timestamp"], t_us, side="right") - 1
    return (idx >= 0) & (land["landed"][np.clip(idx, 0, None)] == 0)


def _hold(topic: dict[str, np.ndarray], field: str, t_us: np.ndarray) -> np.ndarray:
    """The last value logged at or before each grid time."""
    idx = np.searchsorted(topic["timestamp"], t_us, side="right") - 1
    return topic[field][np.clip(idx, 0, None)]


def native_period_ms(topics: dict[str, dict[str, np.ndarray]]) -> float:
    """The slower of the two position topics: nothing finer than this is real."""
    return max(float(np.median(np.diff(topics[name]["timestamp"]))) / 1000.0
               for name in ("vehicle_global_position", "vehicle_local_position"))


def unusable(path: Path) -> str:
    """Why a log cannot be measured, or '' if it can."""
    try:
        topics = _topics(path)
    except Exception as exc:   # any parse failure is a reason to skip, and is recorded
        return f"unreadable: {type(exc).__name__}"
    missing = [t for t in TOPICS if t not in topics]
    if missing:
        return "no topic " + ", ".join(missing)
    for topic, fields in REQUIRED_FIELDS.items():
        absent = [f for f in fields if f not in topics[topic]]
        if absent:
            return f"{topic} without {', '.join(absent)}"
        dead = [f for f in fields if not np.isfinite(topics[topic][f].astype(float)).any()]
        if dead:
            return f"{topic}.{', '.join(dead)} is never valid"
    if len(flight_runs(topics, 1000)) == 0:
        return f"under {MIN_FLIGHT_S:.0f} s of flight"
    return ""


def flight_runs(topics: dict[str, dict[str, np.ndarray]], spacing_ms: int
                ) -> list[list[tuple[int, ...]]]:
    """In-flight records on a `spacing_ms` grid, as runs of consecutive grid points.

    Each record is (ts_ms, lat, lon, alt, vx, vy, vz, battery, mode) in the generator's units.
    A run ends where the vehicle lands or a field is invalid, so no difference is ever taken
    across a gap.
    """
    gp, lp = topics["vehicle_global_position"], topics["vehicle_local_position"]
    start = max(t["timestamp"][0] for t in topics.values())
    stop = min(gp["timestamp"][-1], lp["timestamp"][-1])
    t_us = np.arange(start, stop, spacing_ms * 1000, dtype=np.int64)
    if t_us.size == 0:
        return []
    battery = _hold(topics["battery_status"], "remaining", t_us)
    raw = np.column_stack([
        _hold(gp, "lat", t_us) * 1e7, _hold(gp, "lon", t_us) * 1e7, _hold(gp, "alt", t_us) * 100.0,
        _hold(lp, "vx", t_us) * 100.0, _hold(lp, "vy", t_us) * 100.0,
        _hold(lp, "vz", t_us) * 100.0, np.clip(battery, 0.0, 1.0) * 100.0,
    ])
    # A sample-and-hold of a NaN is a NaN, and a NaN cast to an integer is garbage: a grid point
    # with any invalid field ends the run exactly as a landing does.
    usable = _flight_mask(t_us, topics) & np.isfinite(raw).all(axis=1)
    cols = np.column_stack([
        t_us // 1000, np.rint(np.nan_to_num(raw)),
        # PX4 has more navigation states than the schema has modes; folded, one byte either way
        _hold(topics["vehicle_status"], "nav_state", t_us) % N_MODES,
    ]).astype(np.int64)
    runs: list[list[tuple[int, ...]]] = []
    current: list[tuple[int, ...]] = []
    for row, up in zip(cols.tolist(), usable.tolist(), strict=True):
        if up:
            current.append(tuple(row))
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    if sum(len(r) for r in runs) * spacing_ms / 1000.0 < MIN_FLIGHT_S:
        return []
    return runs


# ============================================================================== sizing
def _ledger(row: tuple[int, ...]) -> Record:
    return Record(src=0, seq=0, ts=row[0], prev_hash=bytes(32),
                  pl=dict(zip(wire_v2.PAYLOAD_FIELDS, row[1:], strict=True)))


def _telemetry(row: tuple[int, ...], seq: int) -> TelemetryRecord:
    ts, lat, lon, alt, vx, vy, vz, battery, mode = row
    return TelemetryRecord(src=1, seq=seq, ts=ts, prev_hash=bytes(32), lat=lat, lon=lon,
                           alt=alt, vel_x=vx, vel_y=vy, vel_z=vz, battery=battery, mode=mode)


def sizes(runs: list[list[tuple[int, ...]]]) -> dict[str, list[int]]:
    """Per-record and per-frame byte counts of both formats over the runs of one log."""
    out: dict[str, list[int]] = {k: [] for k in
                                 ("lean_key", "lean_delta", "first_key", "first_delta",
                                  "frame_1", "frame_b")}
    conv = {"src": leanframes.CONVENTION_SRC, "base_seq": leanframes.CONVENTION_BASE_SEQ}
    for run in runs:
        recs = [_ledger(r) for r in run]
        out["lean_key"] += [len(wire_v2.record_stream([r], None)) for r in recs]
        out["lean_delta"] += [len(wire_v2.record_stream([r], p))
                              for p, r in zip(recs, recs[1:], strict=False)]
        out["frame_1"] += [frame_model.lean_frame_bytes(n=1, stream_bytes=k, **conv)
                           for k in out["lean_key"][-len(recs):]]
        for i in range(0, len(recs) - BATCH + 1, BATCH):
            stream = len(wire_v2.record_stream(recs[i:i + BATCH], None))
            out["frame_b"].append(frame_model.lean_frame_bytes(n=BATCH, stream_bytes=stream,
                                                               **conv))
        tele = [_telemetry(r, i) for i, r in enumerate(run)]
        all_keys = DeltaEncoder(keyframe_interval=1)
        out["first_key"] += [len(all_keys.encode(t)) for t in tele]
        one_key = DeltaEncoder(keyframe_interval=len(tele) + 1)
        out["first_delta"] += [len(one_key.encode(t)) for t in tele][1:]
    return out


def _stats(prefix: str, values: list[int]) -> dict[str, float | int]:
    return {f"{prefix}_mean": round(mean(values), 3), f"{prefix}_min": min(values),
            f"{prefix}_max": max(values)}


def _generator_row(spacing_ms: int) -> dict:
    """The generator at the same spacing, through the same sizing code paths."""
    stride, n = spacing_ms // GENERATOR_STEP_MS, SPACINGS_MS[spacing_ms]
    key, delta = leanframes.lean_record_sizes(n=n, stride=stride)
    key1, delta1 = leanframes.v1_delta_record_sizes(n=n, stride=stride)
    f1 = leanframes.lean_frame_sizes(1, n=n, stride=stride)
    fb = leanframes.lean_frame_sizes(BATCH, n=n, stride=stride)
    return {
        "lean_key_mean": round(key.mean, 3), "lean_key_min": key.lo, "lean_key_max": key.hi,
        "lean_delta_mean": round(delta.mean, 3), "lean_delta_min": delta.lo,
        "lean_delta_max": delta.hi,
        "first_key_mean": round(key1.mean, 3), "first_delta_mean": round(delta1.mean, 3),
        "frame_1_mean": round(f1.mean, 3), "frame_b_mean": round(fb.mean, 3),
        "bytes_per_rec": round(fb.mean / BATCH, 3),
        "saving_pct": round(100.0 * (1.0 - fb.mean / BATCH / f1.mean), 2),
        "records": key.n,
    }


def measure(manifest: dict) -> list[dict]:
    per_log: list[dict] = []
    for log in manifest["logs"]:
        path = _download({"log_id": log["log_id"], "download_url": log["url"]})
        if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != log["sha256"]:
            raise SystemExit(f"{log['log_id']}: the file is not the one the manifest pins")
        topics = _topics(path)
        native = native_period_ms(topics)
        for spacing in SPACINGS_MS:
            head = {"row": "log", "log_id": log["log_id"], "stratum": log["stratum"],
                    "mav_type": log["mav_type"], "release": log["release"],
                    "spacing_ms": spacing, "native_period_ms": round(native, 1)}
            runs = flight_runs(topics, spacing) if spacing >= 0.9 * native else []
            if not runs:
                per_log.append({**head, "measured": 0})
                continue
            s = sizes(runs)
            if not s["frame_b"] or not s["lean_delta"]:
                per_log.append({**head, "measured": 0})
                continue
            f1, fb = mean(s["frame_1"]), mean(s["frame_b"])
            per_log.append({
                **head, "measured": 1, "records": len(s["lean_key"]),
                **_stats("lean_key", s["lean_key"]), **_stats("lean_delta", s["lean_delta"]),
                "first_key_mean": round(mean(s["first_key"]), 3),
                "first_delta_mean": round(mean(s["first_delta"]), 3),
                "frame_1_mean": round(f1, 3), "frame_b_mean": round(fb, 3),
                "bytes_per_rec": round(fb / BATCH, 3),
                "saving_pct": round(100.0 * (1.0 - fb / BATCH / f1), 2),
            })
        print(f"  {log['log_id']}  {log['stratum']:<15} native {native:6.1f} ms", flush=True)

    rows = list(per_log)
    means = ("lean_key_mean", "lean_delta_mean", "first_key_mean", "first_delta_mean",
             "frame_1_mean", "frame_b_mean", "bytes_per_rec", "saving_pct")
    for spacing in SPACINGS_MS:
        got = [r for r in per_log if r["spacing_ms"] == spacing and r["measured"]]
        if got:
            # every log counts once, whatever its length
            rows.append({
                "row": "real logs", "spacing_ms": spacing, "measured": len(got),
                "records": sum(r["records"] for r in got),
                **{k: round(mean(r[k] for r in got), 3) for k in means},
                "lean_key_min": min(r["lean_key_min"] for r in got),
                "lean_key_max": max(r["lean_key_max"] for r in got),
                "lean_delta_min": min(r["lean_delta_min"] for r in got),
                "lean_delta_max": max(r["lean_delta_max"] for r in got),
                "log_mean_delta_lo": min(r["lean_delta_mean"] for r in got),
                "log_mean_delta_hi": max(r["lean_delta_mean"] for r in got),
            })
        rows.append({"row": "generator", "spacing_ms": spacing, "measured": 30,
                     **_generator_row(spacing)})
    return rows


def write(rows: list[dict], manifest: dict) -> None:
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "px4_log_sizes",
            "config_hash": provenance.config_hash(
                {"logs": [log["sha256"] for log in manifest["logs"]],
                 "spacings_ms": SPACINGS_MS, "batch": BATCH}),
            "index_sha256": manifest["index_sha256"], "logs": len(manifest["logs"])}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    print(f"wrote {OUT} ({len(rows)} rows)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--select", action="store_true",
                    help="apply the selection rule to the live index and write the manifest")
    args = ap.parse_args()
    if args.select:
        select()
        return
    manifest = yaml.safe_load(MANIFEST.read_text())
    write(measure(manifest), manifest)


if __name__ == "__main__":
    main()
