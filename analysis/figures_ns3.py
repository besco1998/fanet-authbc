"""Bianchi ↔ NS-3 comparison figure + contention export (P6b, docs/02 §6, docs/06 §2).

Reads results/raw/ns3_matrix.csv (frozen) ONLY. For each N compares each NS-3 mode to its
MATCHING analytic variant — never crossed (the docs' scientific-integrity trap):
  unicast   ↔ ACK-Bianchi  = models.bianchi.solve(N, L)
  broadcast ↔ no-ACK/no-retry variant (τ = 2/(W+1), no ACK in the busy slot)
              AND the slot-exact reference `sim.dcf_ladder`, which is the same process WITHOUT
              Bianchi's decoupling approximation.
Writes fig_ns3_bianchi.png (byte-stable), results/raw/ns3_contention.csv, and a PROVENANCE row.

The no-ACK Bianchi curve is kept — it is the textbook variant and the figure's point is that it
fails — but it is no longer the only broadcast reference: it under-predicts NS-3 by up to 16× at
N=50, whereas the slot-exact model tracks it to ≈1 % (docs/audits/p7.md, finding F9).
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
from authbc.sim import dcf_ladder  # noqa: E402

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
    e_slot = (1.0 - p_tr) * bianchi.SLOT + p_tr * bianchi.t_broadcast_exact(payload_bytes)
    return p_tr * p_s * (8.0 * payload_bytes) / e_slot / 1e6


# Slot-exact reference run length. p_s is stable to 4 decimals from 2e5 busy periods; 3e5 costs
# ~1 s per N. Seeded, so the figure and ns3_contention.csv re-derive byte-identically.
_LADDER_PERIODS = 300_000
_LADDER_SEED = 1


def broadcast_slotexact_mbps(n: int, payload_bytes: float) -> float:
    """Broadcast saturation throughput from the slot-exact DCF process (sim.dcf_ladder), Mbit/s.

    Identical physics to `broadcast_bianchi_mbps` — same W, same busy-period airtime, same slot —
    except that the backoff process is simulated rather than approximated as independent per-slot
    Bernoulli trials. The difference is the post-transmission head start: a station that has just
    transmitted may redraw backoff 0 and take the medium one slot before any deferring station,
    which with a frozen CW (no ACK ⇒ no retry ⇒ no CW doubling) is the dominant success channel
    at large N.
    """
    t_busy = bianchi.t_broadcast_exact(payload_bytes)
    return dcf_ladder.run(
        n,
        w=bianchi.W,
        busy_periods=_LADDER_PERIODS,
        head_start=True,
        t_busy_s=t_busy,
        slot_s=bianchi.SLOT,
        payload_bytes=payload_bytes,
        seed=_LADDER_SEED,
    ).throughput_bps / 1e6


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
                    t_s=bianchi.t_success_exact(payload),
                    t_c=bianchi.t_collision_exact(payload),
                ).throughput_bps / 1e6
                slotexact = None
            else:
                analytic = broadcast_bianchi_mbps(n, payload)
                slotexact = broadcast_slotexact_mbps(n, payload)
            cell = {
                "ns3": round(med, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                "analytic": round(analytic, 4),
                "gap_pct": round(100 * (med - analytic) / analytic, 2),
                "slotexact": None if slotexact is None else round(slotexact, 4),
                "slotexact_gap_pct": (None if slotexact is None
                                      else round(100 * (med - slotexact) / slotexact, 2)),
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
        ax.plot(ns, an, "-", color=colors[mode], lw=1.2,
                label=f"Bianchi {'ACK' if mode == 'unicast' else 'no-ACK'} {mode}")
        if all(s["cells"][(mode, n)]["slotexact"] is not None for n in ns):
            ax.plot(ns, [s["cells"][(mode, n)]["slotexact"] for n in ns], "--",
                    color="#282", lw=1.4, label=f"slot-exact DCF {mode}")
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
                         "slotexact_mbps": c["slotexact"],
                         "slotexact_gap_pct": c["slotexact_gap_pct"],
                         "airtime_share": round(c["ns3"] / 6.0, 4)})
    with (RAW / "ns3_contention.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["N", "mode", "ns3_goodput_mbps", "bianchi_mbps",
                                           "gap_pct", "slotexact_mbps", "slotexact_gap_pct",
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
            extra = ("" if c["slotexact"] is None else
                     f"  slot-exact={c['slotexact']:.3f} gap={c['slotexact_gap_pct']:+.2f}%")
            print(f"  {mode:9} N={n:<2} NS3={c['ns3']:.3f} "
                  f"Bianchi={c['analytic']:.3f} gap={c['gap_pct']:+.1f}%{extra}")


if __name__ == "__main__":
    main()
