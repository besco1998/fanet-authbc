#!/usr/bin/env python3
"""The airtime line of docs/NMAX_DIRECT_EXPECTATIONS.md: calibrate it, predict with it, score it.

Follow-up F2 asks whether the V >= 0.95 crossing of a configuration follows

    0.05 = N · f · (a·T + c)        f = frames per second per node, T = `bianchi.t_broadcast`

with c fixed at 8 µs (twice the simulator's 4 µs preamble-detection period) and one fitted
constant a. The procedure is registered there and this script is only its arithmetic:

    a_i = (0.05 / (N*_i · f_i) − c) / T_i        for the six registered cells A–F
    a   = mean of the six
    N   = 0.05 / (f · (a·T + c))                  for a held-out cell

    python analysis/nmax_airtime_line.py                  # designated source (one period)
    python analysis/nmax_airtime_line.py --source 0       # the strictly periodic stage-1 data

N* is the INTERPOLATED crossing of `results/raw/ns3_nmax_direct.csv`, as registered.
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from authbc.models import bianchi  # noqa: E402

RAW = REPO / "results" / "raw"
LEVEL: float = 0.05                 # the loss level the line is fitted at
C_S: float = 8e-6                   # fixed, not fitted
CALIBRATION = tuple("ABCDEF")
HELD_OUT = ("G", "H", "I", "RA", "RB", "RC", "RD")
DIAGNOSTIC = ("H", "I", "RA", "RC", "RD")    # where the two rules differ by more than 10 %
TOLERANCE: float = 0.06


def a_of(n_star: float, fps: float, t_s: float) -> float:
    """The slope one crossing implies."""
    if min(n_star, fps, t_s) <= 0:
        raise ValueError("crossing, frame rate and frame time must be > 0")
    return (LEVEL / (n_star * fps) - C_S) / t_s


def n_line(a: float, fps: float, t_s: float) -> float:
    """Where the line puts the crossing of a configuration."""
    if min(fps, t_s) <= 0 or a * t_s + C_S <= 0:
        raise ValueError("frame rate and frame time must be > 0")
    return LEVEL / (fps * (a * t_s + C_S))


def crossings(source: str) -> dict[str, dict[str, str]]:
    """cell -> CROSSING row of the summary for one traffic source (`period` or a jitter in ms)."""
    import run_nmax_direct as drv
    out = {}
    with (RAW / "ns3_nmax_direct.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if r["n_nodes"] != "CROSSING" or float(r["skew_ppm"]) != 0.0:
                continue
            jitter, _ = drv.source_of(source, drv.CELLS[r["cell"]].fps)
            if float(r["jitter_ms"]) == jitter:
                out[r["cell"]] = r
    return out


def calibrate(rows: dict[str, dict[str, str]]) -> tuple[float, dict[str, float]]:
    """(a, per-cell a_i) from the six registered cells; refuses a cell that is not bracketed."""
    import run_nmax_direct as drv
    per_cell = {}
    for cell in CALIBRATION:
        r = rows.get(cell)
        if r is None or r["n_cross_interp"] == "":
            raise SystemExit(f"cell {cell} has no interpolated crossing for this source")
        c = drv.CELLS[cell]
        per_cell[cell] = a_of(float(r["n_cross_interp"]), c.fps, bianchi.t_broadcast(c.frame_bytes))
    return st.mean(per_cell.values()), per_cell


def predictions(a: float) -> dict[str, float]:
    """The line's crossing for each held-out cell."""
    import run_nmax_direct as drv
    return {cell: n_line(a, drv.CELLS[cell].fps, bianchi.t_broadcast(drv.CELLS[cell].frame_bytes))
            for cell in HELD_OUT}


def main() -> None:
    import run_nmax_direct as drv
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="period")
    args = ap.parse_args()
    rows = crossings(args.source)
    a, per_cell = calibrate(rows)
    # the slope the original registration used: the same mean over the strictly periodic stage-1
    # crossings (0.0749 to four places; the registered table was computed with it unrounded)
    a_stage1, _ = calibrate(crossings("0"))
    print(f"source {args.source}: a = {a:.4f}  (per cell "
          + ", ".join(f"{k} {v:.4f}" for k, v in per_cell.items())
          + f"; range {min(per_cell.values()):.4f}–{max(per_cell.values()):.4f})")
    print(f"| cell | frame | frames/s | line (this a) | line (stage-1 a = {a_stage1:.4f}) | "
          "single ceiling | measured [95 %] | vs line | vs ceiling |")
    print("|---|---|---|---|---|---|---|---|---|")
    for cell, n_pred in predictions(a).items():
        c = drv.CELLS[cell]
        old = n_line(a_stage1, c.fps, bianchi.t_broadcast(c.frame_bytes))
        r = rows.get(cell)
        if r is None or r["n_cross_interp"] == "":
            measured = vs_line = vs_ceiling = "—"
        else:
            m = float(r["n_cross_interp"])
            measured = f"{m:.1f} [{r['n_cross_interp_lo']}, {r['n_cross_interp_hi']}]"
            vs_line, vs_ceiling = f"{100 * (m - n_pred) / n_pred:+.1f} %", \
                f"{100 * (m - c.model_n) / c.model_n:+.1f} %"
        print(f"| {cell} | {c.frame_bytes} B | {c.fps:g} | {n_pred:.1f} | {old:.1f} | "
              f"{c.model_n} | {measured} | {vs_line} | {vs_ceiling} |")


if __name__ == "__main__":
    main()
