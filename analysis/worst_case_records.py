#!/usr/bin/env python3
"""W4(a): a record size that no telemetry of the schema can exceed, and the capacity there.

predictions/W4a.md. AUTHBC's records are delta-coded, so their size depends on how much the
telemetry changes from one record to the next, and that was measured on synthetic telemetry and
twelve real logs at 5 Hz. Instead of collecting more flights, this bounds the size: frames are
built from records whose every field changes by the most a bound allows, encoded by `wire_v2`,
decoded and verified (F45: a size is the length of an emitted byte string), and their capacity is
computed beside per-record signing's.

Two bounds, defined in the registration before any capacity was computed:

* **schema**: two records A and B at opposite extremes of every field's schema range
  (`bench/telemgen.py`), alternating, so every delta is the full span of its field. No telemetry
  inside the schema has a larger delta record.
* **physical**: the key at the schema's extremes, deltas at 50 Hz (20 ms) from the schema's speed
  limit of ±30 m/s: 60 cm of travel per record (54 units of latitude; 3 089 of longitude at 89°),
  60 cm of altitude, the whole velocity range in one record, ±1 % battery, any mode change, and a
  time step of 63 ms.

    python analysis/worst_case_records.py   -> results/raw/w4a_worst_case.csv
"""
from __future__ import annotations

import csv
import io
import math
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "ns3"))

import dcf_model_check as rule_check  # noqa: E402

from authbc.bench import leanframes, provenance, telemgen  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.ledger.record import Record  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402
from authbc.sim import dcf_own_queue as oq  # noqa: E402

OUT = REPO / "results" / "raw" / "w4a_worst_case.csv"
SEEDS = 30
V_TARGET = 0.95
BATCH = 4
FPS = {"AUTHBC": 50.0 / BATCH, "per-record": 50.0}
U16_MAX, U32_MAX = 2**16 - 1, 2**32 - 1

# The two extremes of the schema (telemgen's ranges); every delta between them is a full span.
A: dict[str, int] = {"ts": U32_MAX, "lat": telemgen.LAT_RANGE[0], "lon": telemgen.LON_RANGE[0],
                     "alt": telemgen.ALT_RANGE[1], "vel_x": telemgen.VEL_RANGE[0],
                     "vel_y": telemgen.VEL_RANGE[0], "vel_z": telemgen.VEL_RANGE[0],
                     "battery": telemgen.BATTERY_RANGE[1], "mode": telemgen.N_MODES - 1}
B: dict[str, int] = {"ts": 0, "lat": telemgen.LAT_RANGE[1], "lon": telemgen.LON_RANGE[1],
                     "alt": telemgen.ALT_RANGE[0], "vel_x": telemgen.VEL_RANGE[1],
                     "vel_y": telemgen.VEL_RANGE[1], "vel_z": telemgen.VEL_RANGE[1],
                     "battery": telemgen.BATTERY_RANGE[0], "mode": 0}
# The physical bound's deltas at 20 ms, applied with alternating sign from the key A.
PHYSICAL_DELTA: dict[str, int] = {"ts": 63, "lat": 54, "lon": 3089, "alt": 60, "vel_x": 6000,
                                  "vel_y": 6000, "vel_z": 6000, "battery": 1, "mode": 7}
ZERO: dict[str, int] = dict.fromkeys(A, 0)


def _chain(values: list[dict[str, int]], *, src: int, base_seq: int) -> list[Record]:
    recs, ph = [], bytes(32)
    for i, v in enumerate(values):
        rec = Record(src=src, seq=base_seq + i, ts=v["ts"], prev_hash=ph,
                     pl={k: v[k] for k in wire_v2.PAYLOAD_FIELDS})
        recs.append(rec)
        ph = rec.record_hash()
    return recs


def schema_values(n: int) -> list[dict[str, int]]:
    return [A if i % 2 == 0 else B for i in range(n)]


def physical_values(n: int) -> list[dict[str, int]]:
    out, cur = [], dict(A, ts=U32_MAX - 64 * n)
    for i in range(n):
        out.append(dict(cur))
        sign = 1 if i % 2 == 0 else -1
        nxt = dict(cur)
        for k, d in PHYSICAL_DELTA.items():
            # time only moves forward; every other field reverses each record to stay in range
            nxt[k] = cur[k] + (d if k == "ts" else (d if A[k] <= B[k] else -d) * sign)
        cur = nxt
    return out


def frame(values: list[dict[str, int]], *, inline: bool, src: int, base_seq: int,
          sk: object, pk: object) -> tuple[int, int, int]:
    """(frame bytes, key-record bytes, largest delta-record bytes), after a checked round trip."""
    recs = _chain(values, src=src, base_seq=base_seq)
    f = wire_v2.build_A_v2(recs, sk) if inline else wire_v2.build_B_v2(recs, sk)
    data = wire_v2.encode_frame_v2(f)
    back = wire_v2.decode_frame_v2(data)
    if back.recs != tuple(recs) or not wire_v2.verify_v2(back, pk):
        raise SystemExit("a worst-case frame did not decode to its records and verify")
    vals = [wire_v2._values(r) for r in recs]
    key = len(wire_v2._key_bytes(vals[0]))
    deltas = [len(wire_v2._delta_bytes(vals[i], vals[i - 1])) for i in range(1, len(vals))]
    return len(data), key, max(deltas, default=0)


def cases() -> list[dict]:
    sk, pk = Ed25519Scheme().keygen(seed=bytes(range(32)))
    big = {"src": U16_MAX, "base_seq": U32_MAX - 8}
    small = {"src": 0, "base_seq": 0}
    rows = []
    for name, values, inline, hdr in (
            ("AUTHBC, schema bound", schema_values(BATCH), False, big),
            ("AUTHBC, physical bound", physical_values(BATCH), False, big),
            ("per-record, schema bound", schema_values(1), True, big),
            ("per-record, smallest", [ZERO], True, small)):
        n_bytes, key, delta = frame(values, inline=inline, sk=sk, pk=pk, **hdr)
        rows.append({"case": name, "scheme": "per-record" if inline else "AUTHBC",
                     "frame_bytes": n_bytes, "key_record_bytes": key,
                     "delta_record_bytes": delta if not inline else ""})
    published = {"AUTHBC": leanframes.lean_frame_sizes(BATCH).mean,
                 "per-record": leanframes.lean_frame_sizes(1, inline=True).mean}
    for scheme, mean in published.items():
        rows.append({"case": f"{scheme}, published mean", "scheme": scheme,
                     "frame_bytes": round(mean, 2), "key_record_bytes": "",
                     "delta_record_bytes": ""})
    return rows


def closed_form(scheme: str, frame_bytes: float) -> float:
    return rule_check.closed_form_crossing(FPS[scheme], bianchi.t_broadcast(frame_bytes))


def _job(job: tuple[str, float, int, int]) -> tuple[str, float, int, float]:
    scheme, frame_bytes, n, seed = job
    air = bianchi.t_broadcast(round(frame_bytes)) - oq.DIFS_S
    return scheme, frame_bytes, n, oq.run(n, FPS[scheme], air, seed=seed).delivered_frac


def model_crossings(rows: list[dict], workers: int) -> dict[tuple[str, float], float | None]:
    jobs = []
    for r in rows:
        centre = closed_form(r["scheme"], r["frame_bytes"])
        step = 1 if centre < 60 else 3
        for n in range(int(0.8 * centre), int(1.2 * centre) + step, step):
            jobs += [(r["scheme"], r["frame_bytes"], n, s) for s in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_job, jobs, chunksize=20)
    by: dict[tuple[str, float], dict[int, list[float]]] = {}
    for scheme, fb, n, d in got:
        by.setdefault((scheme, fb), {}).setdefault(n, []).append(d)
    return {k: interpolated_crossing({n: st.mean(v) for n, v in per.items()}, V_TARGET)
            for k, per in by.items()}


def break_even_frame_bytes(per_record_frame: float) -> float:
    """The AUTHBC frame size at which its crossing equals per-record signing's (closed form)."""
    target = closed_form("per-record", per_record_frame)
    lo, hi = 100.0, 1500.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if closed_form("AUTHBC", mid) > target else (lo, mid)
    return lo


def analyse(workers: int) -> list[dict]:
    rows = cases()
    model = model_crossings(rows, workers)
    for r in rows:
        r["closed_form_crossing"] = round(closed_form(r["scheme"], r["frame_bytes"]), 2)
        x = model[(r["scheme"], r["frame_bytes"])]
        r["model_crossing"] = round(x, 2) if x is not None else ""
    by = {r["case"]: r for r in rows}
    schema = by["AUTHBC, schema bound"]
    out = list(rows)
    for authbc in ("AUTHBC, published mean", "AUTHBC, physical bound", "AUTHBC, schema bound"):
        for base in ("per-record, published mean", "per-record, schema bound",
                     "per-record, smallest"):
            a, b = by[authbc], by[base]
            out.append({"case": f"ratio: {authbc} / {base}", "scheme": "ratio",
                        "frame_bytes": "", "key_record_bytes": "", "delta_record_bytes": "",
                        "closed_form_crossing": round(a["closed_form_crossing"]
                                                      / b["closed_form_crossing"], 3),
                        "model_crossing": round(a["model_crossing"] / b["model_crossing"], 3)
                        if a["model_crossing"] and b["model_crossing"] else ""})
    smallest = by["per-record, smallest"]["frame_bytes"]
    f_star = break_even_frame_bytes(smallest)
    d_star = schema["delta_record_bytes"] + (f_star - schema["frame_bytes"]) / (BATCH - 1)
    out.append({"case": "break-even against per-record at its smallest", "scheme": "AUTHBC",
                "frame_bytes": round(f_star, 1), "key_record_bytes": schema["key_record_bytes"],
                "delta_record_bytes": round(d_star, 1),
                "closed_form_crossing": round(closed_form("AUTHBC", f_star), 2),
                "model_crossing": ""})
    return out


def _write(rows: list[dict]) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "batch": BATCH, "fps": FPS, "A": A, "B": B,
              "physical_delta": PHYSICAL_DELTA, "v_target": V_TARGET}
    for k, v in {**provenance.env_block(), "run": "w4a_worst_case",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    fields = ["case", "scheme", "frame_bytes", "key_record_bytes", "delta_record_bytes",
              "closed_form_crossing", "model_crossing"]
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    rows = analyse(workers)
    _write(rows)
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))
    if any(math.isnan(float(r["closed_form_crossing"])) for r in rows):
        raise SystemExit("a closed-form crossing is not a number")


if __name__ == "__main__":
    main()
