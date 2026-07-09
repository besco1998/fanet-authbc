"""E4 figure — the Ed25519↔BLS break-even power ratio κ*(b) vs the plausible platform band.

Regenerated FROM the frozen raw CSV only (docs/04 §5): reads results/raw/e4_crossover.csv and
draws κ*=P_r/P_c(b) for each relay fraction ρ. BLS is energy-optimal only where P_r/P_c > κ*;
the shaded band marks physically plausible ratios (Wi-Fi receive power below CPU-active power,
P_r/P_c ≲ 0.5). Every κ* curve sits far above the band ⇒ Ed25519 wins across 802.11 (docs/02 T4).
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write a file, never open a display
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CSV = REPO / "results" / "raw" / "e4_crossover.csv"
OUT = REPO / "results" / "figures" / "e4_crossover.png"


def _load() -> tuple[dict, list[dict]]:
    lines = CSV.read_text().splitlines()
    meta = {}
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
        else:
            start = i
            break
    return meta, list(csv.DictReader(lines[start:]))


def main() -> None:
    meta, rows = _load()
    plausible = float(meta.get("plausible_kappa_max", 0.5))

    # κ* depends on (ρ, b) only (Λ-independent) → collapse to one point per (ρ, b).
    series: dict[float, dict[int, tuple[float, float, float]]] = defaultdict(dict)
    for r in rows:
        rho, b = float(r["rho"]), int(r["b"])
        series[rho][b] = (float(r["kappa_star_med"]), float(r["kappa_star_lo"]),
                          float(r["kappa_star_hi"]))

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.axhspan(0, plausible, color="tab:red", alpha=0.12,
               label=f"plausible $P_r/P_c \\leq {plausible}$ (Ed25519 wins)")
    ax.axhline(plausible, color="tab:red", lw=1, ls="--")

    inf_rhos: list[float] = []
    for rho in sorted(series):
        # At g_agg=96 B, pure-own traffic (ρ=0) has κ*=+∞ (BLS carries more bytes than Ed25519,
        # so it can never win) — plot only the finite (relay-mixed) crossovers, note the rest.
        bs = [b for b in sorted(series[rho]) if math.isfinite(series[rho][b][0])]
        if not bs:
            inf_rhos.append(rho)
            continue
        med = [series[rho][b][0] for b in bs]
        if rho == max(r for r in series if any(math.isfinite(series[r][b][0])
                                               for b in series[r])):
            lo = [series[rho][b][0] - series[rho][b][1] for b in bs]
            hi = [series[rho][b][2] - series[rho][b][0] for b in bs]
            ax.errorbar(bs, med, yerr=[lo, hi], marker="o", capsize=3, label=f"ρ={rho} (95% CI)")
        else:
            ax.plot(bs, med, marker="o", label=f"ρ={rho}")
    if inf_rhos:
        ax.plot([], [], " ",
                label=f"ρ={','.join(f'{r:g}' for r in inf_rhos)}: κ*=∞ (BLS costs bytes on own)")

    ax.set_yscale("log")
    ax.set_xscale("log", base=2)
    ax.set_xticks([2, 4, 8, 16, 32])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("batch size b (records aggregated)")
    ax.set_ylabel("break-even power ratio  κ* = $P_r/P_c$")
    ax.set_title("E4: BLS needs κ* > plausible to win — it never does on 802.11 (6 Mb/s)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, which="both", alpha=0.25)
    fig.text(0.01, 0.01,
             f"src: results/raw/e4_crossover.csv  cfg={meta.get('config_hash','?')}  "
             f"Ed25519 verify {meta.get('ed25519_verify_speedup_vs_bls','?')}× < BLS",
             fontsize=6, color="gray")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
