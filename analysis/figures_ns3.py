"""Bianchi ↔ NS-3 comparison figure + contention export (P6b, docs/02 §6, docs/06 §2).

Reads results/raw/ns3_matrix.csv (frozen) ONLY. For each N compares each NS-3 mode to its
MATCHING analytic variant — never crossed (the docs' scientific-integrity trap):
  unicast   ↔ ACK-Bianchi  = models.bianchi.solve(N, L)
  broadcast ↔ **Ma & Chen's broadcast model** (`models.broadcast_dcf`), which accounts for the
              backoff counter Consecutive Freeze Process that broadcast's frozen contention
              window makes dominant.
Writes fig_ns3_bianchi.png (byte-stable), results/raw/ns3_contention.csv, and a PROVENANCE row.

The figure also plots the **naive reduction** (unicast Bianchi with the ACK removed, τ = 2/(W+1)).
That is NOT a published model — it is the in-house adaptation this project used until P7, and it
under-predicts NS-3 by 16× at N=50. It is drawn only to show that failure explicitly; Ma & Chen
warned against exactly this reduction (docs/audits/p7.md F9, docs/literature/f9_broadcast_dcf.md).
"""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from authbc.bench.stats import bootstrap_ci  # noqa: E402
from authbc.models import bianchi, broadcast_dcf  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 110, "bbox_inches": "tight", "metadata": {"Software": None}}


def broadcast_maachen_mbps(n: int, payload_bytes: float) -> float:
    """Broadcast saturation throughput per Ma & Chen (IEEE TVT 57(6):3757–3768, 2008), Mbit/s.

    The published broadcast model: it splits the backoff counter into the sequential backoff
    process and the Consecutive Freeze Process, because with no ACK the contention window never
    doubles and a station that has just transmitted may redraw 0 and seize the next slot.
    """
    return broadcast_dcf.solve(
        n, payload_bytes, bianchi.t_broadcast(payload_bytes), w0=bianchi.W,
        slot_s=bianchi.SLOT,
    ).throughput_bps / 1e6


def broadcast_naive_mbps(n: int, payload_bytes: float) -> float:
    """The DISCARDED in-house reduction (τ = 2/(W+1)), plotted only to show that it fails."""
    return broadcast_dcf.naive_reduction_mbps(
        n, payload_bytes, bianchi.t_broadcast(payload_bytes), w=bianchi.W,
        slot_s=bianchi.SLOT,
    )


def load_matrix() -> tuple[list[dict], dict]:
    meta: dict[str, str] = {}
    data: list[str] = []
    for line in (RAW / "ns3_matrix.csv").read_text().splitlines(keepends=True):
        if line.startswith("#"):
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
        else:
            data.append(line)
    return list(csv.DictReader(io.StringIO("".join(data)))), meta


def summarize(rows: list[dict]) -> dict:
    """{(mode, N): {ns3_median, ci_lo, ci_hi, analytic, gap_pct}} + payload L."""
    ns = sorted({int(r["N"]) for r in rows})
    modes = sorted({r["mode"] for r in rows})
    payload = float(next(iter(rows))["frameSize"])
    out: dict = {"L": payload, "N": ns, "modes": modes, "cells": {}}
    for mode in modes:
        for n in ns:
            g = [float(r["goodput_mbps"]) for r in rows if r["mode"] == mode and int(r["N"]) == n]
            med = float(median(g))
            lo, hi = bootstrap_ci(g, seed=12345)
            # The slot-exact model is a no-RETRY process, so it applies to broadcast only;
            # unicast's CW doubling is what the ACK-Bianchi solver already models.
            if mode == "unicast":
                # Exact OFDM airtimes, so the comparison is against the simulator's real PHY and
                # not against a 0.4–12 % airtime approximation (audit A1/A10).
                analytic = bianchi.solve(
                    n, payload,
                    t_s=bianchi.t_success(payload),
                    t_c=bianchi.t_collision(payload),
                ).throughput_bps / 1e6
                naive = None
            else:
                analytic = broadcast_maachen_mbps(n, payload)
                naive = broadcast_naive_mbps(n, payload)
            cell = {
                "ns3": round(med, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                "analytic": round(analytic, 4),
                "gap_pct": round(100 * (med - analytic) / analytic, 2),
                "naive": None if naive is None else round(naive, 4),
                "naive_gap_pct": (None if naive is None
                                  else round(100 * (med - naive) / naive, 2)),
            }
            out["cells"][(mode, n)] = cell
    return out


def make_figure(s: dict) -> str:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = {"unicast": "#48c", "broadcast": "#c44"}
    for mode in s["modes"]:
        ns = s["N"]
        ns3 = [s["cells"][(mode, n)]["ns3"] for n in ns]
        lo = [s["cells"][(mode, n)]["ns3"] - s["cells"][(mode, n)]["ci_lo"] for n in ns]
        hi = [s["cells"][(mode, n)]["ci_hi"] - s["cells"][(mode, n)]["ns3"] for n in ns]
        an = [s["cells"][(mode, n)]["analytic"] for n in ns]
        ax.errorbar(ns, ns3, yerr=[lo, hi], fmt="o", color=colors[mode], capsize=3,
                    label=f"NS-3 {mode}")
        label = "Bianchi ACK (unicast)" if mode == "unicast" else "Ma & Chen (broadcast)"
        ax.plot(ns, an, "-", color=colors[mode], lw=1.2, label=label)
        if all(s["cells"][(mode, n)]["naive"] is not None for n in ns):
            naive = [s["cells"][(mode, n)]["naive"] for n in ns]
            # ⚠️ derived, never hardcoded: this label read "16x" for weeks after the 30-seed
            # regeneration moved it to 17.3x.
            worst = max(ns)
            factor = s["cells"][(mode, worst)]["ns3"] / s["cells"][(mode, worst)]["naive"]
            ax.plot(ns, naive, "--", color="#888", lw=1.4,
                    label=f"naive no-ACK reduction (fails, {factor:.1f}x at N={worst})")
    ax.axhline(6.0, ls=":", color="gray", label="6 Mb/s PHY ceiling")
    ax.set_xlabel("N saturated stations")
    ax.set_ylabel("saturation throughput [Mb/s]")
    ax.set_title(f"Analytic DCF models vs NS-3 3.48 (L={int(s['L'])} B, per-mode matched)")
    ax.legend(fontsize=7)
    out = FIGS / "fig_ns3_bianchi.png"
    fig.savefig(out, **_SAVE)
    plt.close(fig)
    return out.name


def write_contention(s: dict) -> None:
    """Effective airtime share (goodput/PHY) vs N for the integrator's E5."""
    rows = []
    for mode in s["modes"]:
        for n in s["N"]:
            c = s["cells"][(mode, n)]
            rows.append({"N": n, "mode": mode, "ns3_goodput_mbps": c["ns3"],
                         "analytic_mbps": c["analytic"], "gap_pct": c["gap_pct"],
                         "naive_reduction_mbps": c["naive"],
                         "naive_gap_pct": c["naive_gap_pct"],
                         "airtime_share": round(c["ns3"] / 6.0, 4)})
    with (RAW / "ns3_contention.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["N", "mode", "ns3_goodput_mbps", "analytic_mbps",
                                           "gap_pct", "naive_reduction_mbps", "naive_gap_pct",
                                           "airtime_share"])
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    rows, _ = load_matrix()
    s = summarize(rows)
    name = make_figure(s)
    write_contention(s)
    sha = hashlib.sha256((FIGS / name).read_bytes()).hexdigest()[:16]
    prov = REPO / "results" / "PROVENANCE.md"
    row = f"| {name} | results/raw/ns3_matrix.csv | {sha} |\n"
    lines = [ln for ln in prov.read_text().splitlines(keepends=True) if name not in ln]
    prov.write_text("".join(lines) + row)  # idempotent: replace this figure's row
    print(f"wrote {name} (sha {sha}) + ns3_contention.csv")
    for mode in s["modes"]:
        for n in s["N"]:
            c = s["cells"][(mode, n)]
            extra = ("" if c["naive"] is None else
                     f"  naive={c['naive']:.3f} gap={c['naive_gap_pct']:+.1f}%")
            print(f"  {mode:9} N={n:<2} NS3={c['ns3']:.3f} "
                  f"model={c['analytic']:.3f} gap={c['gap_pct']:+.2f}%{extra}")


if __name__ == "__main__":
    main()
