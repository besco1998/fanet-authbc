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
TOA_S = {20: 0.066816, 200: 0.333056}            # the module's SF7 time on air (durations.txt)
DUTIES = (0.001, 0.01, 0.1)
CHANNELS = (1, 3, 8)
FRAMES_PER_NODE = 60
OUT = REPO / "results" / "raw" / "uc7_scored.csv"


@dataclass(frozen=True)
class C7Cell:
    duty: float
    channels: int
    payload: int

    @property
    def name(self) -> str:
        return f"D{self.duty * 100:g}C{self.channels}L{self.payload}"

    @property
    def toa_s(self) -> float:
        return TOA_S[self.payload]

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


CELLS = [C7Cell(d, c, pl) for d in DUTIES for c in CHANNELS for pl in TOA_S]


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


def main() -> None:
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
