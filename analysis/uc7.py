#!/usr/bin/env python3
"""U-C7: duty-cycled ALOHA over C channels in ns-3's LoRaWAN module (work package E of
`docs/prompts/NEXT_PHASE_PROMPT.md`); registration `predictions/UC7.md`.

**The prediction** (`authbc.models.unified_capacity.n_aloha_duty`):

    N_max = 1 + floor(C·ln(1/(1 − ε))/(2d))

It holds whatever the frame length, batch and data rate.
* Its continuous form N* = 1 + C·ln(1/(1 − ε))/(2d) is where the per-frame loss
  1 − exp(−2(N − 1)d/C) reaches ε.
* **d is the effective duty cycle:**
  * every node sends at its limit: the period is P = ToA/d;
  * a one-sided jitter of J = 2·ToA is added to each interval, so that phases do not freeze;
  * the mean interval is then P + ToA, and d_eff = ToA/(P + ToA) = d/(1 + d).
* **ToA is the module's own** (`durations.txt` of `ns3/authbc-lora-dc.cc` at SF7): 66.816 ms for
  a 20 B payload, 333.056 ms for 200 B.

    python analysis/uc7.py --markdown    -> the registration's table
    python analysis/uc7.py --score STEM  -> results/raw/uc7_scored.csv
"""
from __future__ import annotations

import csv
import io
import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

EPS = 0.05
TOL = 0.05
# The module's own time on air (its durations.txt), by (payload, DR): DR5 = SF7, DR4 = SF8.
TOA_S = {(20, 5): 0.066816, (200, 5): 0.333056, (120, 4): 0.379392}
DUTIES = (0.001, 0.01, 0.1)
CHANNELS = (1, 3, 8)
FRAMES_PER_NODE = 60
OUT = REPO / "results" / "raw" / "uc7_scored.csv"


@dataclass(frozen=True)
class C7Cell:
    duty: float
    channels: int
    payload: int
    dr: int = 5                     # LoRaWAN data rate: 5 = SF7 (U-C7), 4 = SF8 (U-C7B)

    @property
    def name(self) -> str:
        sf = "" if self.dr == 5 else f"SF{12 - self.dr}"
        return f"D{self.duty * 100:g}C{self.channels}L{self.payload}{sf}"

    @property
    def toa_s(self) -> float:
        return TOA_S[(self.payload, self.dr)]

    @property
    def period_s(self) -> float:
        return self.toa_s / self.duty

    @property
    def jitter_s(self) -> float:
        return 2 * self.toa_s

    @property
    def duty_eff(self) -> float:
        return self.toa_s / (self.period_s + self.jitter_s / 2)

    @property
    def sim_s(self) -> float:
        return FRAMES_PER_NODE * (self.period_s + self.jitter_s / 2)

    def n_star(self) -> float:
        return 1 + self.channels * math.log(1 / (1 - EPS)) / (2 * self.duty_eff)

    def n_max(self) -> int:
        return uc.n_aloha_duty(self.channels, self.duty_eff, EPS)

    def loss_at(self, n: int) -> float:
        return 1 - math.exp(-2 * (n - 1) * self.duty_eff / self.channels)

    @property
    def scored_by(self) -> str:
        """N* ≥ 5: the crossing ±5 %. 2 ≤ N* < 5: N_max exact. N* < 2: the loss at N = 2 > ε."""
        if self.n_star() < 2:
            return "loss at N = 2 above eps"
        return "crossing ±5 % (N_max reported)" if self.n_star() >= 5 else "N_max exact"


CELLS = [C7Cell(d, c, pl) for d in DUTIES for c in CHANNELS for pl in (20, 200)]
# U-C7B (predictions/UC7B.md, Mohamed 2026-11-20): one new 10 % cell whose period exceeds 2.5 s,
# so that the Class A receive windows (RX2 at 2 s) cannot hold the uplinks back.
CELLS_B = [C7Cell(0.1, 8, 120, dr=4)]


def markdown() -> str:
    lines = ["| cell | d | C | payload | ToA (ms) | period (s) | d_eff | **N_max** | N* | "
             "loss at N = 2 | scored by |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in CELLS:
        lines.append(f"| {c.name} | {c.duty:g} | {c.channels} | {c.payload} B | "
                     f"{c.toa_s * 1e3:g} | {c.period_s:.4f} | {c.duty_eff:.6f} | "
                     f"**{c.n_max()}** | {c.n_star():.2f} | {c.loss_at(2):.4f} | {c.scored_by} |")
    return "\n".join(lines)


def score(stem_dir: Path) -> list[dict[str, object]]:
    """One row per cell from `results/raw/uc7_<cell>_runs.csv` (30-seed means per N)."""
    rows = []
    for c in CELLS:
        path = stem_dir / f"uc7_{c.name.lower()}_runs.csv"
        runs = [r for r in csv.DictReader(ln for ln in path.open() if not ln.startswith("#"))]
        by_n: dict[int, list[float]] = {}
        for r in runs:
            by_n.setdefault(int(r["n_devices"]), []).append(float(r["delivered_frac"]))
        # the measurement is the 30-seed grid; a pilot's 5-seed node counts share the file
        by_n = {n: v for n, v in by_n.items() if len(v) >= 30}
        ns = sorted(by_n)
        means = [sum(by_n[n]) / len(by_n[n]) for n in ns]
        ok = [n for n, m in zip(ns, means, strict=True) if m >= 1 - EPS]
        measured_nmax = max(ok) if ok else 1
        crossing = interpolated_crossing(dict(zip(ns, means, strict=True)), 1 - EPS)
        row: dict[str, object] = {"cell": c.name, "n_max_predicted": c.n_max(),
                                  "n_max_measured": measured_nmax, "n_star": c.n_star(),
                                  "crossing": crossing if crossing is not None else "",
                                  "seeds": min(len(v) for v in by_n.values())}
        if c.n_star() < 2:
            loss2 = 1 - sum(by_n[2]) / len(by_n[2])
            row.update({"loss_at_2": loss2, "loss_at_2_predicted": c.loss_at(2),
                        "held": int(loss2 > EPS)})
        elif c.n_star() >= 5:
            row["held"] = int(crossing is not None
                              and abs(c.n_star() - crossing) / crossing <= TOL)
        else:
            row["held"] = int(measured_nmax == c.n_max() and c.n_max() + 1 in by_n)
        rows.append(row)
    return rows


OUT_NODES = REPO / "results" / "raw" / "uc7_per_node.csv"


def _moments(xs: list[float]) -> tuple[float, float]:
    """Sample skewness g and excess kurtosis κ (bias-adjusted, as Sarle's coefficient takes)."""
    n = len(xs)
    m = sum(xs) / n
    m2 = sum((x - m) ** 2 for x in xs) / n
    if m2 == 0 or n < 4:
        return 0.0, 0.0
    m3 = sum((x - m) ** 3 for x in xs) / n
    m4 = sum((x - m) ** 4 for x in xs) / n
    g1, g2 = m3 / m2 ** 1.5, m4 / m2 ** 2 - 3
    g = g1 * math.sqrt(n * (n - 1)) / (n - 2)
    k = ((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3))
    return g, k


def per_node(c: C7Cell) -> dict[str, object]:
    """UC7B Part 2: per-node loss at the grid node count nearest N* (N = 2 when N* < 2)."""
    path = REPO / "results" / "raw" / f"uc7_{c.name.lower()}_pn_nodes.csv"
    rows = [r for r in csv.DictReader(ln for ln in path.open() if not ln.startswith("#"))]
    ns = sorted({int(r["n_devices"]) for r in rows})
    target = 2 if c.n_star() < 2 else min(ns, key=lambda n: (abs(n - c.n_star()), n))
    sel = [r for r in rows if int(r["n_devices"]) == target]
    loss = [1 - int(r["received"]) / int(r["sent"]) for r in sel if int(r["sent"]) > 0]
    srt = sorted(loss)
    mean = sum(loss) / len(loss)
    worst = max(sel, key=lambda r: 1 - int(r["received"]) / max(1, int(r["sent"])))
    g, k = _moments(loss)
    n = len(loss)
    bc = (g * g + 1) / (k + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))) if n > 3 else float("nan")
    zero = sum(x == 0 for x in loss) / n
    return {"cell": c.name, "n_devices": target, "node_runs": n, "mean": mean,
            "median": srt[n // 2], "p90": srt[int(0.9 * (n - 1))], "max": srt[-1],
            "worst_seed": worst["seed"], "worst_node": worst["node"],
            "share_zero": zero, "share_over_2x_mean": sum(x > 2 * mean for x in loss) / n,
            "bimodality_coef": bc, "bimodal": int(bc > 5 / 9 and zero >= 0.25)}


def main() -> None:
    if "--per-node" in sys.argv:
        rows = [per_node(c) for c in [*CELLS, *CELLS_B]]
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "uc7_per_node"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        OUT_NODES.write_text(buf.getvalue())
        for r in rows:
            print(f"{r['cell']:13s} N {r['n_devices']:3d} mean {r['mean']:.4f} "
                  f"med {r['median']:.4f} p90 {r['p90']:.4f} max {r['max']:.4f} "
                  f"zero {r['share_zero']:.2f} "
                  f"BC {r['bimodality_coef']:.3f} bimodal {r['bimodal']}")
        return
    if "--markdown" in sys.argv:
        print(markdown())
    elif "--score" in sys.argv:
        rows = score(REPO / "results" / "raw")
        fields = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k)
                        if k in rows[0] else 99)
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "uc7_scored"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        OUT.write_text(buf.getvalue())
        print(f"{sum(int(r['held']) for r in rows)} of {len(rows)} held")


if __name__ == "__main__":
    main()
