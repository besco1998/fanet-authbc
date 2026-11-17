#!/usr/bin/env python3
"""U-C2: capacity at 16, 32 and 64 records per frame, scored as predictions/UC2.md fixes it (the
model: docs/revision/2026-11-17_unified_model_spec.md, `authbc.models.unified_capacity`).

Reads the driver's summaries `results/raw/unified_c2_b{16,32,64}.csv` (their CROSSING@0.95 rows)
and, for the gain, the stored b ≤ 8 crossings in `results/raw/unified_model_vs_ns3.csv`.
Writes `results/raw/unified_c2_scored.csv`:
* **scored:** each crossing against the law (G9) and, separately, the root of (G5); each holds when
  within ±5 % of ns-3's (the registered tolerance, not widened);
* **reported, not scored:** the gain Γ(b) = (N(b) − 1)/(N(1) − 1), ns-3's against the design
  law's b(1 + β)/(b + β).

    python analysis/unified_c2.py
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "unified_c2_scored.csv"
TOL = 0.05
EPS = 0.05
LAMBDA = 50.0                       # records/s
FIXED_B, PER_RECORD_B = 137, 9      # the lean format: ℓ(b) = 137 + 9b
BATCHES = (16, 32, 64)
# The stored b ≤ 8 crossings the registration names, keyed as unified_model_vs_ns3.csv holds them.
STORED = {1: ("ns3_nmax_direct", "C", "20/0ppm", 35.26),
          2: ("batch_capacity", "B2", "40", 66.73),
          3: ("batch_capacity", "B3", "60", 96.51),
          4: ("ns3_nmax_direct", "D", "80/0ppm", 124.55),
          8: ("batch_capacity", "B8", "160", 222.33)}


def err_pct(model: float, ns3: float) -> float:
    return 100.0 * (model - ns3) / ns3


def held(model: float, ns3: float, tol: float = TOL) -> bool:
    return abs(model - ns3) <= tol * ns3


def gain(n_b: float, n_1: float) -> float:
    """Γ(b): capacity at batch b over capacity at b = 1, one (the receiver) taken from each."""
    return (n_b - 1.0) / (n_1 - 1.0)


def model_values(b: int) -> dict[str, float]:
    p = phy.ofdm_20mhz(6)
    tf = uc.airtime_s(p, FIXED_B + PER_RECORD_B * b)
    f = LAMBDA / b
    dl = uc.design_law(LAMBDA, *uc.affine_airtime(p, FIXED_B, PER_RECORD_B), EPS)
    return {"frame_bytes": FIXED_B + PER_RECORD_B * b, "f": f, "tf_us": tf * 1e6,
            "law": uc.n_law(f, tf, EPS), "root": uc.n_root(f, tf, EPS), "design": dl.n_max(b),
            "beta": dl.beta, "n_inf": dl.n_inf}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def crossing(b: int) -> tuple[float, float, float]:
    """ns-3's crossing and its bootstrap interval, from the driver's summary of U-C2's run."""
    # The driver writes a crossing row into the summary's columns: mean → the crossing,
    # min/max → its bootstrap interval, stdev → "bracketed <share of resamples that bracket>".
    rows = [r for r in _rows(RAW / f"unified_c2_b{b}.csv") if r["n_nodes"] == "CROSSING@0.95"]
    if len(rows) != 1 or rows[0]["delivered_stdev"] != "bracketed 1.000":
        raise ValueError(f"b={b}: expected one CROSSING@0.95 row bracketed in every resample")
    r = rows[0]
    if int(r["seeds"]) != 30:
        raise ValueError(f"b={b}: {r['seeds']} seeds, 30 registered")
    return float(r["delivered_mean"]), float(r["delivered_min"]), float(r["delivered_max"])


def stored_crossings() -> dict[int, float]:
    table = _rows(RAW / "unified_model_vs_ns3.csv")
    out = {}
    for b, (src, cell, jitter, registered) in STORED.items():
        hits = [r for r in table if (r["source_file"], r["cell"], r["jitter_ms"]) == (src, cell,
                                                                                      jitter)]
        if len(hits) != 1 or float(hits[0]["ns3"]) != registered:
            raise ValueError(f"b={b}: stored crossing not the registered {registered}")
        out[b] = registered
    return out


def main() -> None:
    stored = stored_crossings()
    n1 = stored[1]
    rows: list[dict[str, object]] = []
    measured: dict[int, float] = dict(stored)
    for b in BATCHES:
        m = model_values(b)
        ns3, lo, hi = crossing(b)
        measured[b] = ns3
        rows.append({"kind": "crossing", "b": b, "frame_bytes": m["frame_bytes"],
                     "frames_per_s": m["f"], "tf_us": round(m["tf_us"], 3), "ns3": ns3,
                     "ci_lo": lo, "ci_hi": hi, "law": round(m["law"], 3),
                     "root": round(m["root"], 3), "design": round(m["design"], 3),
                     "law_err_pct": round(err_pct(m["law"], ns3), 2),
                     "root_err_pct": round(err_pct(m["root"], ns3), 2),
                     "law_held": held(m["law"], ns3), "root_held": held(m["root"], ns3),
                     "ns3_gain": "", "design_gain": "", "gain_err_pct": ""})
    dl = model_values(BATCHES[0])
    law = uc.DesignLaw(n_inf=dl["n_inf"], beta=dl["beta"])
    for b in sorted(measured):
        g_ns3, g_law = gain(measured[b], n1), law.gain(b)
        rows.append({"kind": "gain (reported, not scored)", "b": b, "frame_bytes": "",
                     "frames_per_s": "", "tf_us": "", "ns3": measured[b], "ci_lo": "",
                     "ci_hi": "", "law": "", "root": "", "design": "", "law_err_pct": "",
                     "root_err_pct": "", "law_held": "", "root_held": "",
                     "ns3_gain": round(g_ns3, 4), "design_gain": round(g_law, 4),
                     "gain_err_pct": round(err_pct(g_law, g_ns3), 2)})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "unified_c2",
                 "config_hash": provenance.config_hash({"tol": TOL, "eps": EPS, "lambda": LAMBDA,
                                                        "batches": BATCHES,
                                                        "stored": STORED})}.items():
        buf.write(f"# {k}={v}\n")
    buf.write(f"# design law: N_inf={law.n_inf:.4f} beta={law.beta:.4f}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
