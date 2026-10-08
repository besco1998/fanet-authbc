"""Delivery against neighbourhood size, from the direct ns-3 search (docs/02 §6e).

One figure, `fig_nmax_direct.png`: the lean baseline and the lean design, each with its 30-seed
mean, the spread of its runs, and the 0.95 line it has to stay above. Everything drawn is read
from `results/raw/ns3_nmax_direct.csv`; the traffic source is the one the design ladder's config
names, so the figure and the tables cannot be about different runs.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 110, "bbox_inches": "tight", "metadata": {"Software": None}}
PANELS = (("lean/inline-1", "per-record signing", "#b2182b"),
          ("lean/batch-delta", "AUTHBC, four records per frame", "#1b7837"))
V_TARGET = 0.95


def _rows() -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in (RAW / "ns3_nmax_direct.csv").read_text().splitlines()
                               if not ln.startswith("#")))


def fig_nmax_direct() -> None:
    cfg = yaml.safe_load((REPO / "experiments" / "design-ladder" / "config.yaml").read_text())
    lam = float(cfg["operating_points"][0][1])

    def designated(r: dict[str, str]) -> bool:
        """Runs of the traffic source the ladder's config names, at the adopted point."""
        period_ms = 1000.0 * float(r["batch"]) / float(r["lambda_rec_per_s"])
        want = period_ms if cfg["nmax_source"] == "period" else float(cfg["nmax_source"])
        return (float(r["lambda_rec_per_s"]) == lam and float(r["skew_ppm"]) == 0.0
                and float(r["jitter_ms"]) == float(f"{want:g}"))    # as the driver writes it

    mine = [r for r in _rows() if designated(r)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, (config, title, colour) in zip(axes, PANELS, strict=True):
        pts = sorted((r for r in mine if r["config"] == config and r["n_nodes"] != "CROSSING"),
                     key=lambda r: int(r["n_nodes"]))
        (cross,) = [r for r in mine if r["config"] == config and r["n_nodes"] == "CROSSING"]
        ns = [int(r["n_nodes"]) for r in pts]
        mean = [float(r["delivered_mean"]) for r in pts]
        lo = [m - float(r["delivered_min"]) for m, r in zip(mean, pts, strict=True)]
        hi = [float(r["delivered_max"]) - m for m, r in zip(mean, pts, strict=True)]
        ax.errorbar(ns, mean, yerr=[lo, hi], color=colour, marker="o", markersize=3.5,
                    linewidth=1.3, capsize=2, elinewidth=0.8)
        ax.axhline(V_TARGET, color="black", linestyle="--", linewidth=1)
        n_max = int(cross["n_max_mean"])
        ax.axvline(n_max, color=colour, linestyle=":", linewidth=1)
        ax.set_title(f"{title}\n$N_{{max}}$ = {n_max}", fontsize=9)
        ax.set_xlabel("neighbourhood size $N$")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("delivered fraction of frames")
    fig.savefig(FIGS / "fig_nmax_direct.png", **_SAVE)
    plt.close(fig)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig_nmax_direct()
    print(f"wrote {FIGS / 'fig_nmax_direct.png'}")


if __name__ == "__main__":
    main()
