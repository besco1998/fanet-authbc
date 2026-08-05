#!/usr/bin/env python3
"""Sensitivity of the co-design selection to the loss probability p (item O2 / Tier-2 #5).

**Why.** Every feasibility verdict in the 802.11 arm rests on `p = 0.05`, which `OPEN_ITEMS` B4
justifies by *mechanism* (broadcast carries no ACK, so the receiver sees the raw channel error rate)
but which is not a measured value for our link. If the selected configuration changes across a
plausible range of p, that constant is load-bearing and must be reported as a range; if it does not,
the result is robust and we can say so with evidence instead of hope.

⚠️ **The specific worry this was written to test.** Placement B has `V = 1 − p`, and the constraint
is `V ≥ 1 − ε` with ε = 0.05. At p = 0.05 that is `0.95 ≥ 0.95` — satisfied **exactly**. The adopted
configuration therefore sits precisely on the feasibility boundary, where any increase in p flips it
infeasible. That is a knife edge in the *model*, of the same family as the knife edges audit S3
found in the *data*.

Grid: p spans the hardware measurement (F35: 2.3e-4 on the two-Pi rig, benign case) through the
assumed 0.05 and beyond, so both directions are covered.

Writes results/raw/sensitivity_p.csv.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.experiments import _measured_inputs, load_config  # noqa: E402
from authbc.models import optimizer  # noqa: E402
from authbc.models.optimizer import Placement  # noqa: E402

# Spans the measured hardware value through the assumed one and past it, plus points either side of
# the ε boundary so the flip is bracketed rather than inferred.
P_GRID = [0.00023, 0.001, 0.005, 0.01, 0.02, 0.03, 0.04, 0.045, 0.049,
          0.05, 0.051, 0.06, 0.08, 0.10, 0.15, 0.20]


def main() -> None:
    cfg = load_config("e5")
    encs, schemes = _measured_inputs(cfg)
    plat = optimizer.Platform(p_cpu_w=cfg["p_cpu_w"], p_radio_w=cfg["p_radio_w"],
                              t_hash_s=cfg["t_hash_ns"] * 1e-9,
                              frame_hdr_bytes=cfg["h_f"], mtu_bytes=cfg["mtu"])
    rows = []
    for p in P_GRID:
        con = optimizer.Constraints(epsilon=cfg["epsilon"], p_loss=p,
                                    lam=cfg["lam"], n_local=cfg["n_local"])
        res = optimizer.solve(encs, schemes, list(Placement), cfg["batches"], plat, con)
        if not res.feasible:
            rows.append({"p_loss": p, "feasible": 0, "encoding": "", "scheme": "",
                         "placement": "", "batch": "", "bytes_per_rec": "", "V": "",
                         "n_feasible": 0})
            print(f"  p={p:<8} INFEASIBLE — nothing satisfies V >= {1 - cfg['epsilon']}")
            continue
        best = min(res.feasible, key=lambda c: (c.bytes_per_record, c.energy_j))
        rows.append({
            "p_loss": p, "feasible": 1, "encoding": best.encoding, "scheme": best.scheme,
            "placement": str(best.placement), "batch": best.batch,
            "bytes_per_rec": round(best.bytes_per_record, 3),
            "V": round(best.verifiability, 6), "n_feasible": len(res.feasible),
        })
        print(f"  p={p:<8} {best.encoding}/{best.scheme}/{best.placement} b={best.batch:<3} "
              f"bytes/rec={best.bytes_per_record:7.3f}  V={best.verifiability:.5f}  "
              f"({len(res.feasible)} feasible)")

    out = REPO / "results" / "raw" / "sensitivity_p.csv"
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "sensitivity_p",
            "config_hash": provenance.config_hash({"grid": P_GRID, "eps": cfg["epsilon"],
                                                   "lam": cfg["lam"], "n": cfg["n_local"]})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    buf.write("# O2/Tier-2 #5: does the co-design SELECTION depend on the assumed p = 0.05?\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    print(f"\nwrote {out}")

    sel = {(r["encoding"], r["scheme"], r["placement"], r["batch"])
           for r in rows if r["feasible"]}
    print(f"\ndistinct selections across the grid: {len(sel)}")
    for s in sorted(map(str, sel)):
        print(f"  {s}")
    infeasible = [r["p_loss"] for r in rows if not r["feasible"]]
    if infeasible:
        print(f"⚠️ infeasible at p = {infeasible}")


if __name__ == "__main__":
    main()
