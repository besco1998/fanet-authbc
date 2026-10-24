#!/usr/bin/env python3
"""The access-rule model against ns-3: compare, predict, score (docs/02 §6g).

`authbc.sim.dcf_unsaturated` simulates the 802.11 broadcast access rule and nothing else. This
script is everything that is done with it:

    python analysis/dcf_model_check.py --compare   # every (configuration, N) ns-3 has run
    python analysis/dcf_model_check.py --predict   # conditions ns-3 has NOT run (follow-up F5)
    python analysis/dcf_model_check.py --score     # those predictions against the ns-3 runs

`--compare` writes `results/raw/dcf_model_vs_ns3.csv`: the model's mean delivered fraction at
each point of the designated traffic source beside ns-3's, and both crossings of 0.95 per
configuration. `--predict` writes `results/raw/dcf_model_predictions.csv`, which was committed
before the runs it predicts (docs/NMAX_DIRECT_EXPECTATIONS.md, F5).

The model takes thirty seeds numbered from 1 and 20 simulated seconds per run, as ns-3 does; its
seeds are its own and share nothing with ns-3's.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

RAW = REPO / "results" / "raw"
SEEDS = 30
V_TARGET = 0.95
TOLERANCE = 0.03                    # F5: the model's crossing against ns-3's, registered


@dataclass(frozen=True)
class Case:
    """A condition ns-3 has not been run at: a configuration, a window and a delivery level."""
    name: str
    cell: str
    w0: int                         # contention window in slots (CWmin + 1)
    level: float                    # the delivered fraction whose crossing is predicted
    scan: tuple[int, ...]           # node counts the model is run at to find it
    ns3_grid: tuple[int, ...]       # node counts registered for the ns-3 test
    stem: str                       # results/raw/<stem>_runs.csv holds the ns-3 runs


CASES: tuple[Case, ...] = (
    Case("C, window doubled", "C", 32, 0.95, tuple(range(36, 50)),
         (36, 37, 38, 39, 40, 41, 42), "ns3_rule_cw31"),
    Case("D, window doubled", "D", 32, 0.95, tuple(range(126, 176, 4)),
         (131, 135, 139, 143, 147), "ns3_rule_cw31"),
    Case("C, 10 % loss", "C", 16, 0.90, tuple(range(40, 54)),
         (44, 45, 46, 47, 48, 49, 50), "ns3_rule_levels"),
    Case("D, 10 % loss", "D", 16, 0.90, tuple(range(140, 190, 4)),
         (157, 161, 165, 169, 173), "ns3_rule_levels"),
    Case("C, 2 % loss", "C", 16, 0.98, tuple(range(17, 29)),
         (20, 21, 22, 23, 24, 25, 26), "ns3_rule_levels"),
    Case("D, 2 % loss", "D", 16, 0.98, tuple(range(60, 100, 3)),
         (74, 77, 80, 83, 86), "ns3_rule_levels"),
)


def _driver():
    import run_nmax_direct as drv
    return drv


def closed_form_crossing(fps: float, t_s: float, w: int = model.W0, level: float = 0.05,
                         detect_s: float = 2 * model.DETECT_S) -> float:
    """The neighbourhood at which the closed form of docs/02 §6g reaches ``level`` loss.

    loss(N) = ρ·[1 − (1 − 1/W)^(ρ/(1−ρ))] + (N − 1)·f·c,   ρ = (N − 1)·f·T

    The first term counts ties among stations that wait together, the second the window in
    which a station cannot yet sense another. Nothing is fitted: W, the window c and T are the
    standard's and the simulator's. Loss increases in N below ρ = 1, so the root is bracketed.
    """
    def loss(n: float) -> float:
        rho = (n - 1) * fps * t_s
        return rho * (1 - (1 - 1 / w) ** (rho / (1 - rho))) + (n - 1) * fps * detect_s

    lo, hi = 2.0, 1.0 + 0.999 / (fps * t_s)
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if loss(mid) < level else (lo, mid)
    return lo


def _one(job: tuple[str, int, int, int]) -> tuple[str, int, int, float, int, int, int]:
    cell, n, w0, seed = job
    c = _driver().CELLS[cell]
    r = model.run(n, c.fps, bianchi.t_broadcast(c.frame_bytes) - model.DIFS_S, seed=seed, w0=w0)
    return cell, n, w0, r.delivered_frac, r.frames, r.lost, r.lost_to_ties


def model_means(points: list[tuple[str, int, int]], workers: int
                ) -> dict[tuple[str, int, int], dict[str, float]]:
    """(cell, N, window) -> mean delivered fraction over SEEDS runs, and the share lost to ties."""
    jobs = [(cell, n, w0, seed) for cell, n, w0 in points for seed in range(1, SEEDS + 1)]
    runs: dict[tuple[str, int, int], list[tuple[float, int, int, int]]] = {}
    with Pool(workers) as pool:
        for cell, n, w0, d, frames, lost, ties in pool.imap_unordered(_one, jobs, chunksize=20):
            runs.setdefault((cell, n, w0), []).append((d, frames, lost, ties))
    return {k: {"delivered": st.mean(v[0] for v in rs),
                "tie_share": sum(v[3] for v in rs) / max(1, sum(v[2] for v in rs))}
            for k, rs in runs.items()}


def ns3_designated() -> tuple[dict[str, dict[int, float]], dict[str, float]]:
    """ns-3's mean delivered fraction per (cell, N) and crossing per cell, designated source."""
    drv = _driver()
    means: dict[str, dict[int, float]] = {}
    crossing: dict[str, float] = {}
    with (RAW / "ns3_nmax_direct.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            one_period = provenance.as_written(1000.0 / drv.CELLS[r["cell"]].fps)
            if float(r["skew_ppm"]) != 0.0 or float(r["jitter_ms"]) != one_period:
                continue
            if r["n_nodes"] == "CROSSING":
                if r["n_cross_interp"]:
                    crossing[r["cell"]] = float(r["n_cross_interp"])
            else:
                means.setdefault(r["cell"], {})[int(r["n_nodes"])] = float(r["delivered_mean"])
    return means, crossing


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "slot_s": model.SLOT_S, "difs_s": model.DIFS_S, "w0": model.W0,
              "detect_s": model.DETECT_S}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def compare(workers: int) -> list[dict]:
    drv = _driver()
    ns3, ns3_cross = ns3_designated()
    got = model_means([(cell, n, model.W0) for cell, pts in ns3.items() for n in pts], workers)
    rows: list[dict] = []
    for cell, pts in ns3.items():
        c = drv.CELLS[cell]
        head = {"cell": cell, "config": c.label, "frame_bytes": c.frame_bytes,
                "frames_per_s": c.fps}
        mine = {n: got[(cell, n, model.W0)]["delivered"] for n in sorted(pts)}
        for n in sorted(pts):
            rows.append({**head, "n_nodes": n, "model_delivered": round(mine[n], 5),
                         "ns3_delivered": pts[n], "difference": round(mine[n] - pts[n], 5),
                         "model_tie_share": round(got[(cell, n, model.W0)]["tie_share"], 3),
                         "model_crossing": "", "ns3_crossing": "", "crossing_error_pct": ""})
        x = interpolated_crossing(mine, V_TARGET)
        if x is None or cell not in ns3_cross:
            raise SystemExit(f"cell {cell}: the model's crossing is not bracketed by ns-3's grid")
        rows.append({**head, "n_nodes": "CROSSING", "model_delivered": "", "ns3_delivered": "",
                     "difference": "", "model_tie_share": "", "model_crossing": round(x, 2),
                     "ns3_crossing": ns3_cross[cell],
                     "crossing_error_pct": round(100.0 * (x - ns3_cross[cell]) / ns3_cross[cell],
                                                 2)})
    return rows


def predict(workers: int) -> list[dict]:
    drv = _driver()
    got = model_means([(c.cell, n, c.w0) for c in CASES for n in c.scan], workers)
    rows = []
    for c in CASES:
        cell = drv.CELLS[c.cell]
        means = {n: got[(c.cell, n, c.w0)]["delivered"] for n in c.scan}
        x = interpolated_crossing(means, c.level)
        if x is None:
            raise SystemExit(f"{c.name}: the scan does not bracket the {c.level} crossing")
        rows.append({"case": c.name, "cell": c.cell, "frame_bytes": cell.frame_bytes,
                     "frames_per_s": cell.fps, "window_slots": c.w0, "delivered_level": c.level,
                     "model_crossing": round(x, 2),
                     "band_lo": round((1 - TOLERANCE) * x, 2),
                     "band_hi": round((1 + TOLERANCE) * x, 2),
                     "ns3_grid": " ".join(map(str, c.ns3_grid)), "ns3_stem": c.stem})
    return rows


def ns3_crossing(case: Case) -> tuple[float | None, dict[int, float]]:
    """ns-3's crossing of `case.level` from its own runs file; None while it is not bracketed.

    Only node counts that hold all SEEDS runs enter, so an unfinished campaign cannot be scored.
    """
    path = RAW / f"{case.stem}_runs.csv"
    if not path.exists():
        return None, {}
    per_n: dict[int, list[float]] = {}
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if r["cell"] == case.cell:
                per_n.setdefault(int(r["n_nodes"]), []).append(float(r["delivered_frac"]))
    means = {n: st.mean(v) for n, v in sorted(per_n.items()) if len(v) == SEEDS}
    if len(means) < 2:
        return None, means
    return interpolated_crossing(means, case.level), means


def score() -> list[dict]:
    """Each registered prediction against ns-3; a case that has not been run is left out."""
    with (RAW / "dcf_model_predictions.csv").open(encoding="utf-8") as fh:
        registered = {r["case"]: r for r in csv.DictReader(ln for ln in fh
                                                           if not ln.startswith("#"))}
    out = []
    for c in CASES:
        measured, means = ns3_crossing(c)
        if measured is None:
            continue
        predicted = float(registered[c.name]["model_crossing"])
        out.append({"case": c.name, "predicted": predicted, "ns3": round(measured, 2),
                    "error_pct": round(100.0 * (measured - predicted) / predicted, 2),
                    "within_band": abs(measured - predicted) <= TOLERANCE * predicted,
                    "points": len(means)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--compare", action="store_true")
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.compare:
        rows = compare(args.workers)
        _write(RAW / "dcf_model_vs_ns3.csv", rows, "dcf_model_vs_ns3")
        worst = max(abs(float(r["crossing_error_pct"])) for r in rows
                    if r["n_nodes"] == "CROSSING")
        print(f"wrote dcf_model_vs_ns3.csv: {len(rows)} rows, worst crossing error {worst} %")
    elif args.predict:
        rows = predict(args.workers)
        _write(RAW / "dcf_model_predictions.csv", rows, "dcf_model_predictions")
        for r in rows:
            print(f"  {r['case']:<20} model crossing {r['model_crossing']:>7}  "
                  f"band {r['band_lo']}–{r['band_hi']}")
    else:
        for r in score():
            print(f"  {r['case']:<20} predicted {r['predicted']:>7}  ns-3 {r['ns3']:>7}  "
                  f"{r['error_pct']:+.2f} %  {'inside' if r['within_band'] else 'OUTSIDE'} "
                  f"the band  ({r['points']} node counts)")


if __name__ == "__main__":
    main()
