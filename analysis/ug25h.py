#!/usr/bin/env python3
"""U-G25H: (G25)'s error at 802.11b past occupancy 0.78, without capture, quantified once
(Mohamed, 2026-11-21, F (c); registration `predictions/UG25H.md`).

(G25) held at 802.11b up to occupancy 0.78 (U-G25). At 0.84–0.87, inside U-F's capture runs, its
loss curve was 3.6–5.5 % optimistic (F140). Mohamed: state it as a limit; one registered test at
0.80–0.90 without capture quantifies the error; no new model.

**The cells.** 802.11b 1 Mb/s, long preamble, equal power (no capture), the designated periodic
source, 20 s. Four (frame, rate, ε) never simulated (`--scan`), whose (G25) root lies at
occupancy N·f·T_f between 0.80 and 0.90, at two loss targets and N ≈ 10 and 16–20:

    python analysis/ug25h.py           -> the predictions
    python analysis/ug25h.py --scan    -> stored CSV rows at a cell's (bytes, frames/s)
    python analysis/ug25h.py --score   -> results/raw/ug25h_scored.csv
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import ug25  # noqa: E402

from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

CELLS: dict[str, tuple[ug25.G25Cell, float]] = {
    "LB200F40": (ug25.G25Cell("80211b", 200, 40.0), 0.05),
    "LB300F30": (ug25.G25Cell("80211b", 300, 30.0), 0.05),
    "LB120F30": (ug25.G25Cell("80211b", 120, 30.0), 0.08),
    "LB173F30": (ug25.G25Cell("80211b", 173, 30.0), 0.08),
}
F140_BAND = (3.6, 5.5)          # % optimistic, as F140 found it (linear; quadratic 3.6–4.8)
OUT = REPO / "results" / "raw" / "ug25h_scored.csv"


def predictions() -> list[dict[str, object]]:
    rows = []
    for name, (c, eps) in CELLS.items():
        g25 = pc.n_root_periodic(c.fps, c.tf_s, eps, c.access)
        rows.append({"cell": name, "frame_bytes": c.frame_bytes, "fps": c.fps, "eps": eps,
                     "tf_us": round(c.tf_s * 1e6, 3), "g25_root": g25,
                     "occupancy_at_g25_root": g25 * c.fps * c.tf_s,
                     "poisson_root": uc.n_root(c.fps, c.tf_s, eps, c.access)})
    return rows


def scan() -> list[tuple[str, str, int, float]]:
    saved = ug25.CELLS
    ug25.CELLS = {name: c for name, (c, _e) in CELLS.items()}
    try:
        return ug25.scan_prior()
    finally:
        ug25.CELLS = saved


def score() -> list[dict[str, object]]:
    pred = {r["cell"]: r for r in predictions()}
    rows = []
    for name, (c, eps) in CELLS.items():
        lines = [ln for ln in (REPO / "results" / "raw" / f"ug25h_{name.lower()}.csv")
                 .read_text().splitlines() if not ln.startswith("#")]
        level = f"CROSSING@{1 - eps:g}"
        r = next(x for x in csv.DictReader(lines) if x["n_nodes"] == level)
        ns3 = float(r["delivered_mean"])
        p = pred[name]
        err = 100 * (float(p["g25_root"]) - ns3) / ns3      # type: ignore[arg-type]
        rows.append({"cell": name, "eps": eps, "ns3_crossing": ns3,
                     "ci_lo": float(r["delivered_min"]), "ci_hi": float(r["delivered_max"]),
                     "occupancy_at_ns3": ns3 * c.fps * c.tf_s, "g25_root": p["g25_root"],
                     "g25_err_pct": err,
                     "in_f140_band": int(F140_BAND[0] <= err <= F140_BAND[1]),
                     "poisson_err_pct": 100 * (float(p["poisson_root"]) - ns3) / ns3})  # type: ignore[arg-type]
    return rows


def main() -> None:
    if "--scan" in sys.argv:
        hits = scan()
        print(f"{len(hits)} stored rows at a cell's (bytes, frames/s)")
        for h in hits:
            print("  ", h)
        return
    if "--score" in sys.argv:
        from authbc.bench import provenance
        rows = score()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "ug25h_scored"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        OUT.write_text(buf.getvalue())
        for r in rows:
            print(r)
        return
    for r in predictions():
        print(r)


if __name__ == "__main__":
    main()
