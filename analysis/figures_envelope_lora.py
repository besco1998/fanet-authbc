"""Feasibility-envelope, T6-exclusion and LoRa figures from frozen CSVs (items E6/A1).

Three panels the thesis lacked, all from `results/raw/`, all byte-stable (Agg backend, no timestamp
metadata) so the frozen-figure discipline holds:

* **fig_envelope.png** — largest single collision domain each configuration can serve. This is the
  co-design claim that needs all four axes *and* the channel model (audit F13/A1), so it deserves a
  figure more than the auth-byte ratio does.
* **fig_t6_exclusion.png** — T6' across all twelve EU863-870 data rates: what fits, what is
  excluded by the signature alone, and what is excluded by what a frame must contain.
* **fig_lora_chain.png** — the F5 decision on the LoRa arm: per-frame chaining against the 802.11
  per-record format, in the currency LoRa actually rations (sustainable records/s).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 110, "bbox_inches": "tight", "metadata": {"Software": None}}


def _rows(name: str) -> list[dict[str, str]]:
    text = [ln for ln in (RAW / name).read_text().splitlines(keepends=True)
            if not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("".join(text))))


def fig_envelope() -> None:
    """N_max per configuration — the feasibility result (docs/02 §6b)."""
    rows = [r for r in _rows("capacity_envelope.csv") if r["n_local"] == "ENVELOPE"]
    labels = [r["binds"].replace(" @", "\n@") for r in rows]
    n_max = [int(r["verdict"].split("=")[1]) for r in rows]
    colours = ["#1b7837" if "optimized" in r["binds"] and "3GPP" not in r["binds"]
               else ("#7fbf7b" if "optimized" in r["binds"] else "#b2182b") for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bars = ax.barh(range(len(rows)), n_max, color=colours, edgecolor="black", linewidth=0.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("largest sustainable collision domain, $N_{max}$   (at $U<1$ — conservative;\n"
                  "measured $V{\\geq}0.95$ boundary is $U{\\approx}2.44$)")
    ax.set_title("Feasibility envelope: how many UAVs each configuration can actually serve",
                 fontsize=10)
    for bar, v in zip(bars, n_max, strict=True):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2, str(v),
                va="center", fontsize=9, fontweight="bold")
    ax.axvline(50, color="#333333", linestyle="--", linewidth=1)
    # Headroom for the note INSIDE the axes: anchoring it above the frame (va="bottom" at
    # y=-0.62) put it on top of the title, which is how it shipped.
    ax.set_ylim(len(rows) - 0.4, -1.25)
    ax.annotate("N=50 quoted — between\nthe baseline and co-design limits",
                xy=(50, -1.15), fontsize=7.5, color="#333333", ha="center", va="top",
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "white",
                      "edgecolor": "none", "alpha": 0.85})
    ax.set_xlim(0, max(n_max) * 1.18)
    ax.grid(axis="x", alpha=0.3)
    fig.savefig(FIGS / "fig_envelope.png", **_SAVE)
    plt.close(fig)


def fig_t6_exclusion() -> None:
    """T6': the payload each EU863-870 data rate allows against the smallest frame it must carry.

    Everything drawn is read from `exclusion_matrix.csv` (lean format, 64 B signature): the
    payload limits of all twelve data rates, the smallest frame the format can emit at all, and
    the range of frames this telemetry actually produces.
    """
    rows = [r for r in _rows("exclusion_matrix.csv")
            if r["auth_bytes"] == "64" and r["design"] == "lean"]
    drs = [int(r["dr"]) for r in rows]
    payload = [int(r["payload_not_repeater"]) for r in rows]
    sig = int(rows[0]["auth_bytes"])
    floor, lo, hi = (int(rows[0][k]) for k in
                     ("frame_floor_bytes", "frame_min_bytes", "frame_max_bytes"))
    tiers = ["signature" if r["signature_alone_overflows"] == "1" else r["verdict"]
             for r in rows]
    colour = {"signature": "#b2182b", "excluded": "#ef8a62", "feasible": "#1b7837"}

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(drs, payload, color=[colour[t] for t in tiers], edgecolor="black", linewidth=0.6)
    ax.axhspan(lo, hi, color="#555555", alpha=0.18, linewidth=0,
               label=f"one-record frames of this telemetry: {lo}–{hi} B")
    ax.axhline(floor, color="black", linestyle="--", linewidth=1.2,
               label=f"smallest frame the format can emit: {floor} B")
    ax.axhline(sig, color="#b2182b", linestyle=":", linewidth=1.2,
               label=f"the signature alone: {sig} B")
    for dr, m in zip(drs, payload, strict=True):       # inside the bar: clear of the lines
        ax.text(dr, m - 13, f"{m}", ha="center", fontsize=7.5, color="white",
                fontweight="bold")
    ax.set_xticks(drs)
    ax.set_xticklabels([f"DR{d}" for d in drs], fontsize=8)
    ax.set_ylabel("maximum payload $N$ (B)")
    ax.set_title("EU863-870 data rates that cannot carry one signed, hash-chained frame",
                 fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=colour[k], ec="black", lw=0.6)
               for k in ("signature", "excluded", "feasible")]
    labels = [f"excluded: the signature alone overflows ({tiers.count('signature')} rates)",
              f"excluded: header, chain link and signature fill the payload "
              f"({tiers.count('excluded')})",
              f"feasible ({tiers.count('feasible')})"]
    line_h, line_l = ax.get_legend_handles_labels()
    ax.legend(handles + line_h, labels + line_l, fontsize=7.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    ax.set_ylim(0, 290)
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(FIGS / "fig_t6_exclusion.png", **_SAVE)
    plt.close(fig)


def fig_lora_chain() -> None:
    """F5 on LoRa: sustainable record rate per chain mode at each feasible data rate."""
    rows = [r for r in _rows("lora_eu868.csv") if r["encoding"] == "delta"]
    drs = sorted({int(r["dr"]) for r in rows})
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for mode, colour, marker in (("per_record", "#b2182b", "o"), ("per_frame", "#1b7837", "s")):
        best = []
        for dr in drs:
            cand = [float(r["lambda_rec_per_s"]) for r in rows
                    if int(r["dr"]) == dr and r["chain_mode"] == mode]
            best.append(max(cand) if cand else float("nan"))
        label = f"{mode}" + ("  (adopted on LoRa — F5)" if mode == "per_frame"
                             else "  (the 802.11 wire format)")
        ax.plot(drs, best, marker=marker, color=colour, label=label, linewidth=1.6)
    ax.set_xticks(drs)
    ax.set_xticklabels([f"DR{d}" for d in drs])
    ax.set_ylabel("sustainable rate $\\Lambda$ (records/s)")
    ax.set_title("F5 on the LoRa arm: per-frame chaining buys 3.0$\\times$ the telemetry\n"
                 "(EU868, 1 % duty cycle, delta encoding)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(FIGS / "fig_lora_chain.png", **_SAVE)
    plt.close(fig)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig_envelope()
    fig_t6_exclusion()
    fig_lora_chain()
    for name in ("fig_envelope.png", "fig_t6_exclusion.png", "fig_lora_chain.png"):
        print(f"wrote {FIGS / name}")


if __name__ == "__main__":
    main()
