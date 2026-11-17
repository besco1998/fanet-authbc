#!/usr/bin/env python3
"""U-D's D1 and D2, scored as predictions/UD.md fixes them: the unified model at standard
802.11b, DSSS 1 Mb/s, long preamble (σ = 20 µs, DIFS = 50 µs, δ = 4 µs; the model:
docs/revision/2026-11-17_unified_model_spec.md, `authbc.models.unified_capacity`).

Reads the driver's summaries `results/raw/unified_d1.csv` and `unified_d2_b{1,…,32}.csv` (their
CROSSING rows). Writes `results/raw/unified_d_scored.csv`:
* **D1:** Pb1B and Pb1D at W = 32, 16 and 8, each at ε = 2, 5 and 10 % (levels 0.98 / 0.95 / 0.90);
* **D2:** b = 1 … 32 at 10 records/s, ℓ(b) = 137 + 9b, at ε = 5 %;
* each crossing scored for the law (G9) and, separately, the root of (G5), by the band of
  ns-3's crossing: ±5 % from 15 stations, −9 … +5 % from 8 to 14, not scored below 8;
* reported, not scored: D2's gain (N(b) − 1)/(N(1) − 1) against b(1 + β)/(b + β).

    python analysis/unified_d.py
"""
from __future__ import annotations

import csv
import io
import sys
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "unified_d_scored.csv"
D1_CELLS = {"Pb1B": (146, 50.0), "Pb1D": (173, 12.5)}
WINDOWS = (32, 16, 8)
LEVELS = {0.98: 0.02, 0.95: 0.05, 0.90: 0.10}
D2_RATE = 10.0                     # records/s
FIXED_B, PER_RECORD_B = 137, 9
BATCHES = (1, 2, 4, 8, 16, 32)


def band(ns3: float) -> tuple[float, float] | None:
    """The registered tolerance, by ns-3's crossing: (low, high) in %, or None = not scored."""
    if ns3 >= 15:
        return (-5.0, 5.0)
    if ns3 >= 8:
        return (-9.0, 5.0)
    return None


def _band_text(ns3: float) -> str:
    b = band(ns3)
    return "" if b is None else f"{b[0]:+g} … {b[1]:+g} %"


def err_pct(model: float, ns3: float) -> float:
    return 100.0 * (model - ns3) / ns3


def verdict(model: float, ns3: float) -> str:
    b = band(ns3)
    if b is None:
        return "not scored (< 8 stations)"
    return "held" if b[0] <= err_pct(model, ns3) <= b[1] else "failed"


def access(w: int) -> uc.Access:
    return replace(uc.A80211B, w=w)


def d1_model(cell: str, w: int, eps: float) -> tuple[float, float]:
    size, f = D1_CELLS[cell]
    tf = uc.airtime_s(phy.DSSS_1M, size)
    return uc.n_law(f, tf, eps, access(w)), uc.n_root(f, tf, eps, access(w))


def d2_model(b: int) -> tuple[float, float]:
    tf = uc.airtime_s(phy.DSSS_1M, FIXED_B + PER_RECORD_B * b)
    f = D2_RATE / b
    return uc.n_law(f, tf, 0.05, uc.A80211B), uc.n_root(f, tf, 0.05, uc.A80211B)


def d2_design() -> uc.DesignLaw:
    return uc.design_law(D2_RATE, *uc.affine_airtime(phy.DSSS_1M, FIXED_B, PER_RECORD_B), 0.05,
                         uc.A80211B)


def crossings(path: Path) -> dict[tuple[str, float], tuple[float, float, float]]:
    """{(cell, level): (crossing, ci_lo, ci_hi)} from a driver summary; 30 seeds, bracketed."""
    with path.open() as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    out = {}
    for r in rows:
        if not r["n_nodes"].startswith("CROSSING@"):
            continue
        if int(r["seeds"]) != 30 or r["delivered_stdev"] != "bracketed 1.000":
            raise ValueError(f"{path.name} {r['cell']} {r['n_nodes']}: not 30 seeds, bracketed")
        out[(r["cell"], float(r["n_nodes"].split("@")[1]))] = (
            float(r["delivered_mean"]), float(r["delivered_min"]), float(r["delivered_max"]))
    return out


def _row(item: str, cell: str, w: int, eps: float, ns3: tuple[float, float, float],
         law: float, root: float) -> dict[str, object]:
    x, lo, hi = ns3
    return {"item": item, "cell": cell, "window": w, "eps": eps, "ns3": x, "ci_lo": lo,
            "ci_hi": hi, "law": round(law, 3), "root": round(root, 3),
            "law_err_pct": round(err_pct(law, x), 2), "root_err_pct": round(err_pct(root, x), 2),
            "band": _band_text(x),
            "law_verdict": verdict(law, x), "root_verdict": verdict(root, x),
            "ns3_gain": "", "design_gain": "", "gain_err_pct": ""}


def main() -> None:
    rows: list[dict[str, object]] = []
    d1 = crossings(RAW / "unified_d1.csv")
    for cell in D1_CELLS:
        for w in WINDOWS:
            name = cell if w == 32 else f"{cell}W{w}"
            for level, eps in LEVELS.items():
                law, root = d1_model(cell, w, eps)
                rows.append(_row("D1", name, w, eps, d1[(name, level)], law, root))
    d2: dict[int, float] = {}
    for b in BATCHES:
        x = crossings(RAW / f"unified_d2_b{b}.csv")[(f"DB{b}", 0.95)]
        d2[b] = x[0]
        rows.append(_row("D2", f"DB{b}", 32, 0.05, x, *d2_model(b)))
    law = d2_design()
    for b in BATCHES:
        g_ns3 = (d2[b] - 1) / (d2[1] - 1)
        rows.append({**{k: "" for k in rows[0]}, "item": "D2 gain (reported, not scored)",
                     "cell": f"DB{b}", "ns3": d2[b], "ns3_gain": round(g_ns3, 4),
                     "design_gain": round(law.gain(b), 4),
                     "gain_err_pct": round(err_pct(law.gain(b), g_ns3), 2)})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "unified_d",
                 "config_hash": provenance.config_hash({"d1": D1_CELLS, "windows": WINDOWS,
                                                        "levels": LEVELS, "batches": BATCHES,
                                                        "rate": D2_RATE})}.items():
        buf.write(f"# {k}={v}\n")
    buf.write(f"# D2 design law: N_inf={law.n_inf:.4f} beta={law.beta:.4f}\n")
    w_ = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w_.writeheader()
    w_.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
