#!/usr/bin/env python3
"""U-FS: the finite-station form (work package C) against ns-3, where Mohamed accepted it.

Registration `predictions/UFS.md`; the form is `authbc.models.finite_station`.

* **Where it is accepted** (Mohamed, 2026-11-20): N = 3–5 at occupancy u = N·f·T_f ≤ 0.5.
* **The new cells:** 802.11b at 1 Mb/s with a 223 B frame, and 802.11a at 6 Mb/s with a 1 031 B
  frame. No stored result has either size (the event comparison used 145 B and 1 400 B);
  N = 3, 4, 5; u = 0.3 and 0.5.
* **The measurement:** ns-3's loss, 1 − the 30-seed mean delivered fraction. Each run lasts 100 s,
  with the designated source.
* **The score:** the finite-station loss within ±15 % of ns-3's. The Poisson loss (G5) and
  (G25)'s are reported beside it.

    python analysis/ufs.py --markdown   -> the registration's table
    python analysis/ufs.py --score      -> results/raw/ufs_scored.csv
"""
from __future__ import annotations

import csv
import io
import random
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.models import finite_station as fs  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

TOL = 0.15
SIM_S = 100.0
OUT = REPO / "results" / "raw" / "ufs_scored.csv"


@dataclass(frozen=True)
class FSCell:
    standard: str
    frame_bytes: int
    n_nodes: int
    occupancy: float

    @property
    def name(self) -> str:
        return (f"FS{'B' if self.standard == '80211b' else 'A'}{self.frame_bytes}"
                f"N{self.n_nodes}U{round(self.occupancy * 100)}")

    @property
    def access(self) -> uc.Access:
        return uc.A80211B if self.standard == "80211b" else uc.A80211A

    @property
    def tf_s(self) -> float:
        ph = phy.DSSS_1M if self.standard == "80211b" else phy.OFDM_20MHZ_6M
        return uc.airtime_s(ph, self.frame_bytes)

    @property
    def fps(self) -> float:
        return self.occupancy / (self.n_nodes * self.tf_s)

    def losses(self) -> dict[str, float]:
        n, f, tf, acc = self.n_nodes, self.fps, self.tf_s, self.access
        return {"finite": fs.loss(n, f, tf, acc), "g5": uc.loss((n - 1) * f, tf, acc),
                "g25": pc.loss_periodic(n, f, tf, acc)}


CELLS = [FSCell(std, size, n, u) for std, size in (("80211b", 223), ("80211a", 1031))
         for n in (3, 4, 5) for u in (0.3, 0.5)]


def markdown() -> str:
    lines = ["| cell | PHY | frame | N | u | frames/s | T_f (µs) | **finite-station loss** | "
             "(G5) | (G25) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for c in CELLS:
        lo = c.losses()
        lines.append(f"| {c.name} | {c.standard} | {c.frame_bytes} B | {c.n_nodes} | "
                     f"{c.occupancy:g} | {c.fps:.4f} | {c.tf_s * 1e6:g} | "
                     f"**{lo['finite']:.5f}** | {lo['g5']:.5f} | {lo['g25']:.5f} |")
    return "\n".join(lines)


def score() -> list[dict[str, object]]:
    rows = []
    rng = random.Random(0)
    for c in CELLS:
        path = REPO / "results" / "raw" / f"ufs_{c.name.lower()}_runs.csv"
        runs = [r for r in csv.DictReader(ln for ln in path.open() if not ln.startswith("#"))]
        d = [float(r["delivered_frac"]) for r in runs]
        meas = 1 - sum(d) / len(d)
        boot = sorted(1 - sum(rng.choice(d) for _ in d) / len(d) for _ in range(1000))
        lo = c.losses()
        err = (lo["finite"] - meas) / meas
        rows.append({"cell": c.name, "standard": c.standard, "n_nodes": c.n_nodes,
                     "occupancy": c.occupancy, "seeds": len(d), "ns3_loss": meas,
                     "ci_lo": boot[25], "ci_hi": boot[974], "finite": lo["finite"],
                     "finite_err_pct": 100 * err, "held": int(abs(err) <= TOL),
                     "side": "" if abs(err) <= TOL else
                             ("pessimistic" if err > 0 else "optimistic"),
                     "g5": lo["g5"], "g5_err_pct": 100 * (lo["g5"] - meas) / meas,
                     "g25": lo["g25"], "g25_err_pct": 100 * (lo["g25"] - meas) / meas})
    return rows


def main() -> None:
    if "--markdown" in sys.argv:
        print(markdown())
    elif "--score" in sys.argv:
        from authbc.bench import provenance
        rows = score()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "ufs_scored"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        OUT.write_text(buf.getvalue())
        print(f"{sum(int(r['held']) for r in rows)} of {len(rows)} held")
        for r in rows:
            print(f"  {r['cell']}: ns-3 {r['ns3_loss']:.5f} ({r['ci_lo']:.5f}-{r['ci_hi']:.5f}) "
                  f"finite {r['finite']:.5f} {r['finite_err_pct']:+.1f} %  G5 "
                  f"{r['g5_err_pct']:+.1f} %  G25 {r['g25_err_pct']:+.1f} %  "
                  f"{'held' if r['held'] else 'FAILED ' + str(r['side'])}")


if __name__ == "__main__":
    main()
