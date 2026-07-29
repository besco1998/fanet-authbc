"""Feasibility-envelope, T6-exclusion and LoRa figures from frozen CSVs (items E6/A1).

Three panels the thesis lacked, all from `results/raw/`, all byte-stable (Agg backend, no timestamp
metadata) so the frozen-figure discipline holds:

* **fig_envelope.png** — largest single collision domain each configuration can serve. This is the
  co-design claim that needs all four axes *and* the channel model (audit F13/A1), so it deserves a
  figure more than the auth-byte ratio does.
* **fig_t6_exclusion.png** — T6's three exclusion tiers across EU868 data rates: what fits, what is
  excluded by the signature alone, and what misses on the encoding.
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

H_F, G_A = 44, 64          # measured wire header (B1) + Ed25519
S_MIN_LORA = 13.0          # delta record under per-frame chaining (F5)


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
                  "measured $V{\\geq}0.95$ boundary is $U{\\approx}2.8$)")
    ax.set_title("Feasibility envelope: how many UAVs each configuration can actually serve",
                 fontsize=10)
    for bar, v in zip(bars, n_max, strict=True):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2, str(v),
                va="center", fontsize=9, fontweight="bold")
    ax.axvline(50, color="#333333", linestyle="--", linewidth=1)
    ax.annotate("N=50 quoted — between\nthe baseline and co-design limits",
                xy=(50, -0.62), fontsize=7.5, color="#333333", ha="center", va="bottom",
                annotation_clip=False)
    ax.set_xlim(0, max(n_max) * 1.18)
    ax.grid(axis="x", alpha=0.3)
    fig.savefig(FIGS / "fig_envelope.png", **_SAVE)
    plt.close(fig)


def fig_t6_exclusion() -> None:
    """T6: s_max = M − H_f − g_a against the smallest available record, per EU868 data rate."""
    drs = [0, 1, 2, 3, 4, 5, 6]
    payload = [51, 51, 51, 115, 242, 242, 242]          # RP002-1.0.3 Table 13
    s_max = [m - H_F - G_A for m in payload]
    tiers = ["signature" if m < G_A else
             ("framing" if m < H_F + G_A else
              ("encoding" if m - H_F - G_A < S_MIN_LORA else "feasible")) for m in payload]
    colour = {"signature": "#b2182b", "framing": "#ef8a62",
              "encoding": "#fddbc7", "feasible": "#1b7837"}

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(drs, payload, color=[colour[t] for t in tiers], edgecolor="black", linewidth=0.6,
           label="_nolegend_")
    ax.axhline(H_F + G_A, color="black", linestyle="--", linewidth=1.2,
               label=f"$H_f+g_a={H_F + G_A}$ B — header + signature")
    ax.axhline(G_A, color="#b2182b", linestyle=":", linewidth=1.2,
               label=f"$g_a={G_A}$ B — signature alone")
    for dr, m, sm in zip(drs, payload, s_max, strict=True):
        note = (f"$s_{{max}}={sm:.0f}$ B" if sm < 0
                else (f"$s_{{max}}={sm:.0f}$ B\n(needs {S_MIN_LORA:.0f})" if sm < S_MIN_LORA
                      else f"$s_{{max}}={sm:.0f}$ B"))
        # lift the excluded-tier labels clear of the g_a reference line at y=64
        y = 76 if m < G_A else m + 8
        ax.text(dr, y, note, ha="center", fontsize=7.5)
    ax.set_xticks(drs)
    ax.set_xticklabels([f"DR{d}" for d in drs])
    ax.set_ylabel("max application payload $M$ (B)")
    ax.set_title("T6: EU868 data rates that cannot carry authenticated telemetry", fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=colour[k], ec="black", lw=0.6)
               for k in ("signature", "encoding", "feasible")]
    labels = ["excluded — signature alone overflows the payload",
              f"excluded — no record fits $s_{{max}}$ (smallest is {S_MIN_LORA:.0f} B)",
              "feasible"]
    line_h, line_l = ax.get_legend_handles_labels()
    ax.legend(handles + line_h, labels + line_l, fontsize=7.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False)
    ax.set_ylim(0, 300)
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
