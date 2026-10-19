#!/usr/bin/env python3
"""Revision A2 — the design over record rate × deadline, not at one operating point.

Every result of the paper sits at Λ·D_max = 5, so b ≤ 4 follows from the operating point and not
from the design (the reviewer's objection; `docs/AUTHBC Revision Plan.md`, A2). This script
lays the design over the plan's grid of record rates Λ and deadlines D_max:

    python analysis/design_map.py --predict   # results/raw/design_map.csv (every cell, model)
                                              # results/raw/design_map_predictions.csv (ten
                                              # cells registered for ns-3)
    python analysis/design_map.py --score     # results/raw/design_map_validation.csv

For each cell: b* from Eq. (2) of the paper with the measured worst channel delay and the
measured Ed25519 verification (`results/raw/freshness_budget.csv`); the lean frame the codec
EMITS at that record spacing (a delta is a difference, so its size depends on the spacing,
audit F48); bytes per record; and the capacity of the baseline (one record per frame) and of
the design (b* records per frame) by the access-rule model, which has nothing fitted
(`authbc.sim.dcf_unsaturated`, docs/02 §6g). The ten validation cells are then simulated in
ns-3 through `ns3/run_nmax_direct.py`, cells `MB*` and `MD*`.

Registration: `predictions/A2.md`, committed before any ns-3 run of these cells.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from functools import cache
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

import dcf_model_check as rule  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

RAW = REPO / "results" / "raw"
MAP = RAW / "design_map.csv"
PREDICTIONS = RAW / "design_map_predictions.csv"
SCORE = RAW / "design_map_validation.csv"
STEM = "ns3_design_map"

LAMBDAS: tuple[int, ...] = (10, 20, 25, 40, 50, 75, 100)            # records/s
D_MAX_MS: tuple[int, ...] = (40, 60, 80, 100, 150, 200, 250, 500)
MTU_BYTES = 1500
V_TARGET = 0.95
SEEDS = 30
TOLERANCE = 0.05            # the plan: simulated N_max within 5 % of the event model
# Four corners, the inner diagonal of the grid, and the paper's operating point as a control.
VALIDATION: tuple[tuple[int, int], ...] = (
    (10, 40), (10, 500), (100, 40), (100, 500),
    (20, 60), (25, 80), (40, 100), (50, 150), (75, 200),
    (50, 100))
# Beyond the plan's ten: the plan's own example of a large gain, (100, 100) with b* = 9, so
# that "ratio > 5×" is simulated and not only modelled.
EXTRA: tuple[tuple[int, int], ...] = ((100, 100),)


def budget() -> tuple[float, float]:
    """(T_ch, t_v) in ms: the worst channel delay simulated at the design's crossing and one
    Ed25519 verification on the board, as the paper's freshness table uses them."""
    with (RAW / "freshness_budget.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    row = next(r for r in rows if r["op"] == "adopted" and r["scheme"] == "ed25519"
               and r["channel_stat"] == "delay_max_ms")
    return float(row["channel_ms"]), float(row["verify_ms"])


def b_star(lam: float, d_max_ms: float, t_ch_ms: float, t_v_ms: float) -> int:
    """Largest b with b/Λ + T_ch + t_v ≤ D_max (Eq. 2); 0 if not even one record fits."""
    b = 0
    while 1000.0 * (b + 1) / lam + t_ch_ms + t_v_ms <= d_max_ms:
        b += 1
    return b


def step_ms(lam: float) -> int:
    """Record spacing of the generator walk at Λ (whole milliseconds; 13 ms at 75 records/s)."""
    return round(1000.0 / lam)


@cache
def frame_bytes(lam: float, batch: int) -> float:
    """Mean length of the lean frames the codec emits with `batch` records `step_ms` apart."""
    return leanframes.lean_frame_sizes(batch, step_ms=step_ms(lam)).mean


def mtu_records(lam: float) -> int:
    """Largest batch whose emitted frame fits the MTU, by bisection over emitted frames."""
    lo, hi = 1, wire_v2.MAX_RECORDS
    if frame_bytes(lam, hi) <= MTU_BYTES:
        raise ValueError(f"the MTU does not bind below the format's {hi} records")
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if frame_bytes(lam, mid) <= MTU_BYTES else (lo, mid)
    return lo


def _one(job: tuple[int, float, float, int]) -> tuple[int, float, float, float]:
    n, fps, t_s, seed = job
    return n, fps, t_s, model.run(n, fps, t_s - model.DIFS_S, seed=seed).delivered_frac


def _means(points: list[tuple[int, float, float]], workers: int
           ) -> dict[tuple[int, float, float], float]:
    jobs = [(n, fps, t_s, s) for n, fps, t_s in points for s in range(1, SEEDS + 1)]
    got: dict[tuple[int, float, float], list[float]] = {}
    with Pool(workers) as pool:
        for n, fps, t_s, d in pool.imap_unordered(_one, jobs, chunksize=8):
            got.setdefault((n, fps, t_s), []).append(d)
    return {k: st.mean(v) for k, v in got.items()}


def scan_points(estimate: float) -> list[int]:
    """Node counts about a first estimate: ±16 % in steps of 4 %, at least one node apart."""
    return sorted({max(2, round(estimate * (1 + 0.04 * k))) for k in range(-4, 5)})


def model_crossings(configs: list[tuple[float, float]], workers: int
                    ) -> dict[tuple[float, float], float]:
    """Access-rule crossing of V = 0.95 for each (frames/s, frame bytes), 30 seeds per point.

    The scan is centred on the closed form of docs/02 §6g and widened until it brackets.
    """
    out: dict[tuple[float, float], float] = {}
    todo = {cfg: scan_points(rule.closed_form_crossing(cfg[0], bianchi.t_broadcast(cfg[1])))
            for cfg in configs}
    while todo:
        pts = [(n, fps, bianchi.t_broadcast(fb)) for (fps, fb), ns in todo.items() for n in ns]
        got = _means(pts, workers)
        nxt: dict[tuple[float, float], list[int]] = {}
        for (fps, fb), ns in todo.items():
            t_s = bianchi.t_broadcast(fb)
            means = {n: got[(n, fps, t_s)] for n in ns}
            x = interpolated_crossing(means, V_TARGET)
            if x is not None:
                out[(fps, fb)] = x
                continue
            centre = ns[0] if means[ns[0]] < V_TARGET else ns[-1]
            nxt[(fps, fb)] = scan_points(centre)
        todo = nxt
    return out


def cells(t_ch: float, t_v: float) -> list[dict]:
    """Every cell of the grid with its batch and emitted frame sizes (no capacity yet)."""
    rows = []
    for lam in LAMBDAS:
        base = frame_bytes(lam, 1)
        for d in D_MAX_MS:
            b = b_star(lam, d, t_ch, t_v)
            row = {"lambda_rec_per_s": lam, "d_max_ms": d, "lam_dmax": round(lam * d / 1000, 3),
                   "b_star": b, "feasible": int(b >= 1), "step_ms": step_ms(lam),
                   "base_frame_bytes": round(base, 3), "base_bytes_per_rec": round(base, 3),
                   "base_frames_per_s": lam}
            if b >= 1:
                fb = frame_bytes(lam, b)
                row |= {"design_frame_bytes": round(fb, 3),
                        "design_bytes_per_rec": round(fb / b, 3),
                        "byte_reduction_pct": round(100 * (1 - fb / b / base), 2),
                        "design_frames_per_s": round(lam / b, 4),
                        "d_of_b_ms": round(1000 * b / lam + t_ch + t_v, 3),
                        "margin_ms": round(d - 1000 * b / lam - t_ch - t_v, 3),
                        "fits_mtu": int(fb <= MTU_BYTES)}
            rows.append(row)
    return rows


def capacity_map(t_ch: float, t_v: float, workers: int) -> list[dict]:
    rows = cells(t_ch, t_v)
    configs = {(float(r["lambda_rec_per_s"]), r["base_frame_bytes"]) for r in rows}
    configs |= {(r["design_frames_per_s"], r["design_frame_bytes"]) for r in rows if r["feasible"]}
    got = model_crossings(sorted(configs), workers)
    for r in rows:
        nb = got[(float(r["lambda_rec_per_s"]), r["base_frame_bytes"])]
        r["model_n_base"] = round(nb, 2)
        if r["feasible"]:
            nd = got[(r["design_frames_per_s"], r["design_frame_bytes"])]
            r |= {"model_n_design": round(nd, 2), "model_ratio": round(nd / nb, 3)}
    return rows


def ns3_cell(lam: int, d: int, role: str) -> str:
    """The `run_nmax_direct` cell that simulates this role of this grid cell."""
    if (lam, role) == (50, "base"):
        return "C"
    if (lam, d, role) == (50, 100, "design"):
        return "D"
    return f"MB{lam}" if role == "base" else f"MD{lam}-{d}"


def ns3_grid(x: float) -> list[int]:
    """Seven node counts about the model's crossing, 2.5 % apart, at least one node apart."""
    step = max(1, round(0.025 * x))
    return [round(x) + k * step for k in range(-3, 4)]


def predictions(rows: list[dict]) -> list[dict]:
    """The ten validation cells: each role that has a frame, with the model's band."""
    by = {(r["lambda_rec_per_s"], r["d_max_ms"]): r for r in rows}
    out, seen = [], set()
    for lam, d in VALIDATION + EXTRA:
        r = by[(lam, d)]
        roles = [("base", float(lam), r["base_frame_bytes"], 1, r["model_n_base"])]
        if r["b_star"] >= 2:
            roles.append(("design", r["design_frames_per_s"], r["design_frame_bytes"],
                          r["b_star"], r["model_n_design"]))
        for role, fps, fb, b, x in roles:
            cell = ns3_cell(lam, d, role)
            out.append({"lambda_rec_per_s": lam, "d_max_ms": d, "b_star": r["b_star"],
                        "role": role, "ns3_cell": cell, "batch": b,
                        "frame_bytes": round(fb), "frames_per_s": round(fps, 4),
                        "model_crossing": x, "band_lo": round((1 - TOLERANCE) * x, 2),
                        "band_hi": round((1 + TOLERANCE) * x, 2),
                        "ns3_grid": " ".join(map(str, ns3_grid(x))),
                        "in_plan": int((lam, d) in VALIDATION),
                        "shared_with": "" if cell not in seen else "an earlier row"})
            seen.add(cell)
    return out


def _write(path: Path, rows: list[dict], run: str, config: dict) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def _config() -> dict:
    return {"lambdas": LAMBDAS, "d_max_ms": D_MAX_MS, "seeds": SEEDS, "level": V_TARGET,
            "tolerance": TOLERANCE, "validation": VALIDATION, "extra": EXTRA,
            "mtu": MTU_BYTES}


def registered() -> list[dict[str, str]]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def score() -> list[dict]:
    """Each registered role against its ns-3 crossing; scored only on the registered grid with
    all thirty seeds, as every earlier registration of this work."""
    import run_nmax_direct as drv
    runs = drv.read_runs(RAW / f"{STEM}_runs.csv")
    crossing = {r["cell"]: r for r in drv.summarise(runs, SEEDS) if r["n_nodes"] == "CROSSING"}
    out = []
    for reg in registered():
        if reg["shared_with"]:
            continue
        r = crossing.get(reg["ns3_cell"])
        if r is None or r.get("grid") != reg["ns3_grid"] or r.get("bracketed") != 1:
            continue
        got, x = float(r["n_cross_interp"]), float(reg["model_crossing"])
        out.append({"ns3_cell": reg["ns3_cell"], "lambda_rec_per_s": reg["lambda_rec_per_s"],
                    "d_max_ms": reg["d_max_ms"], "role": reg["role"], "batch": reg["batch"],
                    "frame_bytes": reg["frame_bytes"], "frames_per_s": reg["frames_per_s"],
                    "ns3_crossing": got, "ns3_lo": r["n_cross_interp_lo"],
                    "ns3_hi": r["n_cross_interp_hi"], "n_max": r["n_max_mean"],
                    "model_crossing": x, "vs_model_pct": round(100 * (got - x) / x, 2),
                    "within_band": int(abs(got - x) <= TOLERANCE * x)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    if args.predict:
        t_ch, t_v = budget()
        rows = capacity_map(t_ch, t_v, args.workers)
        mtu = {lam: mtu_records(lam) for lam in LAMBDAS}
        for r in rows:
            r["mtu_records"] = mtu[r["lambda_rec_per_s"]]
        _write(MAP, rows, "design_map", _config())
        reg = predictions(rows)
        _write(PREDICTIONS, reg, "design_map_predictions", _config())
        for r in reg:
            print(f"({r['lambda_rec_per_s']}, {r['d_max_ms']}) {r['role']:6s} {r['ns3_cell']:9s} "
                  f"b={r['batch']:<2} {r['frame_bytes']} B at {r['frames_per_s']}/s: model "
                  f"{r['model_crossing']} [{r['band_lo']}, {r['band_hi']}] grid {r['ns3_grid']}")
        return
    rows = score()
    if not rows:
        raise SystemExit("no registered cell has its full grid on file yet")
    _write(SCORE, rows, "design_map_validation", _config())
    for r in rows:
        print(f"{r['ns3_cell']}: ns-3 {r['ns3_crossing']} vs model {r['model_crossing']} "
              f"({r['vs_model_pct']:+.2f} %, {'in' if r['within_band'] else 'OUT OF'} band)")


if __name__ == "__main__":
    main()
