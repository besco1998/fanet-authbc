#!/usr/bin/env python3
"""C, second part (Mohamed, 2026-11-20): the unsaturated fixed-point model of Malone–Duffy–Leith,
adapted to broadcast (`authbc.models.unsat_broadcast`), against the event simulation at N = 2.

* **The reference:** rule A's simulation (`analysis/finite_station_check.rule_a`), which tracks
  ns-3 at N = 2–3 (F137). Also ns-3 itself, where the F137 diagnostic ran it.
* **The setting:** the designated source; 10 seeds of 100 s.
* **The PHYs:** 802.11b 1 Mb/s with 145 B and 802.11a 6 Mb/s with 1 400 B.
* **The loads:** occupancy u = N·f·T_f from 0.3 to 0.9 in steps of 0.1.

**The criterion, fixed before any comparison was computed:** the model holds at N = 2 only if
its loss is within ±15 % of rule A's simulation at every u, at both PHYs. If it does not, it is
not proposed (Mohamed: "Propose it to me only if it holds there").

    python analysis/mdl_check.py   -> results/raw/mdl_check.csv
"""
from __future__ import annotations

import csv
import io
import random
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import finite_station_check as fsc  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402
from authbc.models import unsat_broadcast as ub  # noqa: E402

OUT = REPO / "results" / "raw" / "mdl_check.csv"
LOADS = tuple(round(0.3 + 0.1 * k, 1) for k in range(7))
TOL = 0.15
N = 2


def ns3_loss(phy_name: str, u: float) -> float | None:
    std, size = ("b", 145) if phy_name.startswith("80211b") else ("a", 1400)
    path = REPO / "results" / "raw" / f"diag_smalln_dg{std}{size}n{N}u{round(u * 100)}_runs.csv"
    if not path.exists():
        return None
    d = [float(r["delivered_frac"]) for r in csv.DictReader(
        ln for ln in path.open() if not ln.startswith("#"))]
    return 1 - sum(d) / len(d)


def rows() -> list[dict[str, object]]:
    out = []
    for name, (ph, acc, size) in fsc.PHYS.items():
        tf = uc.airtime_s(ph, size)
        for u in LOADS:
            f = u / (N * tf)
            sims = []
            for seed in range(1, fsc.SEEDS + 1):
                rng = random.Random(1000 * seed + N)
                sims.append(fsc.rule_a(fsc.arrivals(N, f, "jitter", rng), tf, acc, rng))
            sim = st.mean(sims)
            model = ub.solve(N, f, tf, acc)["loss"]
            ns3 = ns3_loss(name, u)
            out.append({"phy": name, "occupancy": u, "frames_per_s": round(f, 3),
                        "rule_a_loss": sim, "rule_a_se": st.stdev(sims) / fsc.SEEDS ** 0.5,
                        "mdl_loss": model, "mdl_over_rule_a": model / sim,
                        "ns3_loss": "" if ns3 is None else ns3,
                        "mdl_over_ns3": "" if ns3 is None else model / ns3,
                        "within_15pct": int(abs(model / sim - 1) <= TOL)})
    return out


def main() -> None:
    data = rows()
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "mdl_check"}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(data[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(data)
    OUT.write_text(buf.getvalue())
    held = all(r["within_15pct"] for r in data)
    for r in data:
        print(f"{r['phy']:13s} u {r['occupancy']}: rule A {r['rule_a_loss']:.5f} "
              f"MDL {r['mdl_loss']:.5f} ratio {r['mdl_over_rule_a']:.2f}  ns-3 {r['ns3_loss']}")
    print("HOLDS at N = 2" if held else "DOES NOT HOLD at N = 2: not proposed")


if __name__ == "__main__":
    main()
