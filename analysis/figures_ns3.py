"""Bianchi ↔ NS-3 comparison figure + contention export (P6b, docs/02 §6, docs/06 §2).

Reads results/raw/ns3_matrix.csv (frozen) ONLY. For each N compares each NS-3 mode to its
MATCHING analytic variant — never crossed (the docs' scientific-integrity trap):
  unicast   ↔ ACK-Bianchi  = models.bianchi.solve(N, L)
  broadcast ↔ no-ACK/no-retry variant (τ = 2/(W+1), no ACK in the busy slot)
Writes fig_ns3_bianchi.png (byte-stable), results/raw/ns3_contention.csv, and a PROVENANCE row.
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
from authbc.models import bianchi  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 110, "bbox_inches": "tight", "metadata": {"Software": None}}


def _airtime_s(nbytes: float) -> float:
    return 8.0 * nbytes / bianchi.R_BPS


def broadcast_bianchi_mbps(n: int, payload_bytes: float) -> float:
    """No-ACK/no-retry broadcast saturation throughput (matches NS-3 broadcast), Mbit/s.

    Broadcast never ACKs, retransmits, or grows CW, so τ is the single-stage value 2/(W+1)
    (N-independent). A busy slot costs T_air_b = T_phy + 8(L+34)/R + DIFS + δ (no ACK/SIFS) for
    both success and collision. Successful (non-colliding) payload carries the throughput.
    """
    tau = 2.0 / (bianchi.W + 1)
    p_tr = 1.0 - (1.0 - tau) ** n
    p_s = n * tau * (1.0 - tau) ** (n - 1) / p_tr
    t_air_b = (bianchi.T_PHY + _airtime_s(payload_bytes + bianchi.MAC_OVH_BYTES)
               + bianchi.DIFS + bianchi.DELTA)
    e_slot = (1.0 - p_tr) * bianchi.SLOT + p_tr * t_air_b
    return p_tr * p_s * (8.0 * payload_bytes) / e_slot / 1e6


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
            if mode == "unicast":
                analytic = bianchi.solve(n, payload).throughput_bps / 1e6
            else:
                analytic = broadcast_bianchi_mbps(n, payload)
            out["cells"][(mode, n)] = {
                "ns3": round(med, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                "analytic": round(analytic, 4),
                "gap_pct": round(100 * (med - analytic) / analytic, 2),
            }
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
        ax.plot(ns, an, "-", color=colors[mode], lw=1.2,
                label=f"Bianchi {'ACK' if mode == 'unicast' else 'no-ACK'} {mode}")
    ax.axhline(6.0, ls=":", color="gray", label="6 Mb/s PHY ceiling")
    ax.set_xlabel("N saturated stations")
    ax.set_ylabel("saturation throughput [Mb/s]")
    ax.set_title(f"Bianchi vs NS-3 3.41 (L={int(s['L'])} B, per-mode matched)")
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
                         "bianchi_mbps": c["analytic"], "gap_pct": c["gap_pct"],
                         "airtime_share": round(c["ns3"] / 6.0, 4)})
    with (RAW / "ns3_contention.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["N", "mode", "ns3_goodput_mbps", "bianchi_mbps",
                                           "gap_pct", "airtime_share"])
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
            print(f"  {mode:9} N={n:<2} NS3={c['ns3']:.3f} "
                  f"Bianchi={c['analytic']:.3f} gap={c['gap_pct']:+.1f}%")


if __name__ == "__main__":
    main()
