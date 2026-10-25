"""Figures of the reviewer revision (docs/AUTHBC Revision Plan.md, A1-A7; one per reviewer point).

Each figure is drawn only from the artifact its experiment wrote, the same one
`analysis/paper_numbers.py` reads for the numbers in the text, so the two cannot disagree:

* `fig_spread.png` (A1, F88, F103): nodes served at 95 % delivery, and the design's ratio to
  per-record signing, as the swarm spreads over discs of growing radius; the moving swarm at
  1 km beside them. `spatial_capacity.csv`, `spatial_motion.csv`.
* `fig_design_map.png` (A2, F100): the batch the deadline admits and the capacity ratio it buys
  over record rate x deadline; the cells simulated in ns-3 are outlined. `design_map.csv`,
  `design_map_validation.csv`.
* `fig_margin.png` (A3, F86): the design's verifiability against frame loss under five loss
  processes, with the region the margin rule admits. `verifiability_margin.csv`.
* `fig_adaptive.png` (A4/A4b, F102): the growing swarm, second by second, under the registered
  controller, the controller with twice the margin, and a fixed batch of four.
  `ns3_adaptive_ts/`, `ns3_adaptive_b_ts/`.
* `fig_flood.png` (A7, F109): honest delivery on one Raspberry Pi 4 receiver core against the
  rate of forged frames, for each defence and attacker. `results/hw/flood_udp.authbc-pi4b.csv`.

Colours: the repository's red, orange and blue (per-record signing, an intermediate design, the
design) plus purple. Checked with the dataviz palette validator over all pairs: every check
passes. Blue and purple sit in the 6-8 band under deuteranopia, and orange has low contrast on
white, so every series is also told apart by its marker or line style and by a label.
"""

from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import adaptive_batching as adaptive  # noqa: E402
import paper_numbers as pn  # noqa: E402

RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 200, "bbox_inches": "tight", "metadata": {"Software": None}}
V_TARGET = 0.95
RED, ORANGE, BLUE, PURPLE = "#b2182b", "#e08214", "#2166ac", "#762a83"
INK, MUTED = "black", "0.35"

# A1: the layouts on one radius axis; "fixed" is the one collision domain of the paper
SPREAD = (("fixed", "one\ndomain"), ("s1-r100", "100 m"), ("s1-r300", "300 m"),
          ("s1-r600", "600 m"), ("s1-r1000", "1 km"))
SPREAD_CONFIGS = (("base", "per-record signing", RED, "o"),
                  ("inline4", "four records, four signatures", ORANGE, "s"),
                  ("design", "AUTHBC", BLUE, "^"))
MOTION = (("gm-r1000-v0", "0"), ("gm-r1000-v5", "5"), ("gm-r1000-v15", "15"))

# A3: the design (b = 4, one keyframe per frame) under each loss process
LOSS_MODELS = (("iid", "independent", BLUE, "o"),
               ("gilbert2", "bursts of 2", ORANGE, "v"),
               ("gilbert4", "bursts of 4", "#1baf7a", "D"),
               ("gilbert8", "bursts of 8", PURPLE, "s"),
               ("ber", "bit errors", RED, "^"))
RULE_MARGIN = 0.02          # the deployment rule: loss budget at least 0.02 above the loss

# A4/A4b: (directory, policy, label, colour, line style)
POLICIES = ((RAW / "ns3_adaptive_ts", "fixed4", "fixed $b=4$", BLUE, "-"),
            (RAW / "ns3_adaptive_ts", "adaptive", "controller, as registered", ORANGE, "--"),
            (RAW / "ns3_adaptive_b_ts", "adaptive-m20", "controller, margin 0.02", PURPLE, "-."))
SEEDS = range(1, 11)

# A7: (policy, attack, label, colour, line style) at the 41 senders one core keeps up with
FLOOD_SENDERS = "41"
FLOODS = (("none", "forged", "no defense", RED, "-"),
          ("cheap", "forged", "header checks", ORANGE, "-"),
          ("mac", "outsider", "group MAC, outsider", BLUE, "-"),
          ("mac", "insider", "group MAC, member", BLUE, "--"),
          ("cap", "forged-one", "rate cap, one sender", PURPLE, "-"),
          ("cap", "forged", "rate cap, every sender", PURPLE, "--"))


def _tidy(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(alpha=0.3, linewidth=0.6)
    ax.tick_params(labelsize=8)


def spread_points() -> dict[str, list[tuple[float, float]]]:
    """(x position, nodes at the crossing) per configuration, in SPREAD order."""
    sc = pn.rows(RAW / "spatial_capacity.csv")
    return {cfg: [(i, float(pn.one(sc, scenario=s, config=cfg)["n_cross"]))
                  for i, (s, _) in enumerate(SPREAD)] for cfg, *_ in SPREAD_CONFIGS}


def fig_spread() -> None:
    sc, mv = pn.rows(RAW / "spatial_capacity.csv"), pn.rows(RAW / "spatial_motion.csv")
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(3.5, 3.4), sharex=True,
                                      gridspec_kw={"height_ratios": [1.5, 1]})
    moving_x = len(SPREAD) - 1 + 0.35
    for cfg, label, colour, marker in SPREAD_CONFIGS:
        pts = spread_points()[cfg]
        top.plot(*zip(*pts, strict=True), color=colour, marker=marker, markersize=5,
                 linewidth=1.3, label=label)
        if cfg != "inline4":
            moving = [float(pn.one(mv, scenario=s, config=cfg)["n_cross"]) for s, _ in MOTION]
            top.plot([moving_x] * len(moving), moving, linestyle="none", marker=marker,
                     markersize=5, markerfacecolor="white", color=colour)
    for cfg, colour, marker in (("inline4", ORANGE, "s"), ("design", BLUE, "^")):
        rows = [pn.one(sc, scenario=s, config=cfg) for s, _ in SPREAD]
        ratio = [float(r["ratio_to_base"]) for r in rows]
        err = [[q - float(r["ratio_lo"]) for q, r in zip(ratio, rows, strict=True)],
               [float(r["ratio_hi"]) - q for q, r in zip(ratio, rows, strict=True)]]
        bottom.errorbar(range(len(SPREAD)), ratio, yerr=err, color=colour, marker=marker,
                        markersize=5, linewidth=1.3, capsize=2, elinewidth=0.8)
    for s, _ in MOTION:
        r = pn.one(mv, scenario=s, config="design")
        bottom.plot(moving_x, float(r["ratio_to_base"]), linestyle="none", marker="^",
                    markersize=5, markerfacecolor="white", color=BLUE)
    lowest = min(float(pn.one(mv, scenario=s, config="base")["n_cross"]) for s, _ in MOTION)
    top.text(moving_x, lowest - 12, "moving,\n" + "/".join(v for _, v in MOTION) + " m/s",
             fontsize=7.5, color=MUTED, ha="center", va="top")
    top.set_ylabel("nodes served\nat 95 % delivery", fontsize=8)
    top.legend(fontsize=7.5, frameon=False, loc="upper left")
    bottom.set_ylabel("ratio to\nper-record signing", fontsize=8)
    bottom.set_ylim(0, 4.2)
    hidden = [pn.one(sc, scenario=s, config="design")["hidden_share"] for s, _ in SPREAD]
    ticks = [f"{name}\n{'' if not h else f'{100 * float(h):.0f} %'}"
             for (_, name), h in zip(SPREAD, hidden, strict=True)]
    bottom.set_xticks(range(len(SPREAD)), ticks)
    bottom.set_xlabel("disc radius; below it, the share of interferers\n"
                      "that cannot hear the sender", fontsize=8)
    for ax in (top, bottom):
        _tidy(ax)
    fig.savefig(FIGS / "fig_spread.png", **_SAVE)
    plt.close(fig)


def design_map_cells() -> tuple[list[int], list[int], dict[tuple[int, int], dict[str, str]]]:
    t = pn.rows(RAW / "design_map.csv")
    rates = sorted({int(r["lambda_rec_per_s"]) for r in t})
    deadlines = sorted({int(r["d_max_ms"]) for r in t})
    return rates, deadlines, {(int(r["lambda_rec_per_s"]), int(r["d_max_ms"])): r for r in t}


def validated_cells() -> set[tuple[int, int]]:
    return {(int(r["lambda_rec_per_s"]), int(r["d_max_ms"]))
            for r in pn.rows(RAW / "design_map_validation.csv")}


def fig_design_map() -> None:
    rates, deadlines, cells = design_map_cells()
    checked = validated_cells()
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    cmap = plt.get_cmap("Blues")
    top = max(float(c["model_ratio"]) for c in cells.values() if c["model_ratio"])
    for i, lam in enumerate(rates):
        for j, dmax in enumerate(deadlines):
            c = cells[(lam, dmax)]
            if c["feasible"] != "1":
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor="0.92", edgecolor="white",
                                       hatch="///", linewidth=0))
                continue
            ratio = float(c["model_ratio"])
            shade = 0.12 + 0.78 * (ratio - 1) / (top - 1)
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=cmap(shade), edgecolor="white"))
            ink = "white" if shade > 0.55 else INK
            weight = "bold" if (lam, dmax) == (50, 100) else "normal"
            ax.text(j + 0.5, i + 0.64, f"b={c['b_star']}", ha="center", va="center",
                    fontsize=6.5, color=ink, weight=weight)
            ax.text(j + 0.5, i + 0.3, f"{ratio:.1f}\u00d7", ha="center", va="center",
                    fontsize=6.5, color=ink, weight=weight)
    for lam, dmax in checked:
        ax.add_patch(Rectangle((deadlines.index(dmax) + 0.04, rates.index(lam) + 0.04), 0.92,
                               0.92, fill=False, edgecolor=INK, linewidth=1.3))
    ax.set_xlim(0, len(deadlines))
    ax.set_ylim(0, len(rates))
    ax.set_xticks([j + 0.5 for j in range(len(deadlines))], [str(d) for d in deadlines])
    ax.set_yticks([i + 0.5 for i in range(len(rates))], [str(r) for r in rates])
    ax.set_xlabel("deadline $D_{\\max}$ (ms)", fontsize=8)
    ax.set_ylabel("records per second $\\Lambda$", fontsize=8)
    ax.tick_params(labelsize=8, length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    fig.savefig(FIGS / "fig_design_map.png", **_SAVE)
    plt.close(fig)


def margin_points(model: str) -> list[tuple[float, float, float, float]]:
    """(p, V, interval low, interval high) of the design under one loss process."""
    return sorted((float(r["p"]), float(r["V_meas"]), float(r["V_ci_lo"]), float(r["V_ci_hi"]))
                  for r in pn.rows(RAW / "verifiability_margin.csv")
                  if r["loss_model"] == model and r["batch"] == "4" and r["ref_interval"] == "1")


def fig_margin() -> None:
    """Drawn at the column's own width (3.5 in), so 8 pt text prints at 8 pt. The loss rates are
    evenly spaced categories and the five processes sit side by side in each, unjoined: lines
    between them crossed and their intervals overlapped (Mohamed, 2026-10-25: hard to read)."""
    losses = [p for p, *_ in margin_points(LOSS_MODELS[0][0])]
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    admitted = [i for i, p in enumerate(losses) if p <= 1 - V_TARGET - RULE_MARGIN + 1e-9]
    ax.axvspan(-0.5, admitted[-1] + 0.5, color="0.92", linewidth=0)
    ax.text(admitted[-1] / 2, 0.892, "the rule admits\nthese losses at $\\epsilon = 0.05$",
            fontsize=7.5, color=MUTED, ha="center")
    ax.axhline(V_TARGET, color=INK, linestyle="--", linewidth=1)
    ax.text(len(losses) - 0.55, V_TARGET + 0.002, "target", fontsize=7.5, color=INK, ha="right")
    width = 0.15
    for k, (model, label, colour, marker) in enumerate(LOSS_MODELS):
        pts = margin_points(model)
        assert [p for p, *_ in pts] == losses, model
        x = [i + (k - 2) * width for i in range(len(pts))]
        v = [q for _, q, _, _ in pts]
        err = [[q - lo for _, q, lo, _ in pts], [hi - q for _, q, _, hi in pts]]
        ax.errorbar(x, v, yerr=err, color=colour, marker=marker, markersize=4.5, linestyle="none",
                    capsize=1.8, elinewidth=1.0, label=label)
    ax.set_xticks(range(len(losses)), [f"{p:g}" for p in losses])
    ax.set_xlim(-0.5, len(losses) - 0.5)
    ax.set_ylim(0.885, 1.0)
    ax.set_xlabel("frame loss $p$", fontsize=8)
    ax.set_ylabel("records verified, $V$", fontsize=8)
    ax.legend(fontsize=7.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0),
              ncol=3, handletextpad=0.3, columnspacing=0.9)
    _tidy(ax)
    ax.grid(axis="x", visible=False)
    fig.savefig(FIGS / "fig_margin.png", **_SAVE)
    plt.close(fig)


def adaptive_curve(directory: Path, policy: str) -> list[tuple[float, float, float, float]]:
    """(active nodes, batch, V, age in ms) per one-second window of the ramp, mean of the seeds."""
    runs = [adaptive.series("ramp", policy, s, directory) for s in SEEDS]
    out = []
    for windows in zip(*runs, strict=True):
        if any(w["active"] != windows[0]["active"] for w in windows):
            raise ValueError("the seeds of one policy grow the swarm on the same schedule")
        out.append((windows[0]["active"], st.mean(w["mean_b"] for w in windows),
                    st.mean(w["v"] for w in windows), st.mean(w["age"] for w in windows)))
    return out


def fig_adaptive() -> None:
    fig, axes = plt.subplots(3, 1, figsize=(3.5, 3.9), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.3, 1]})
    for directory, policy, label, colour, style in POLICIES:
        curve = adaptive_curve(directory, policy)
        n = [c[0] for c in curve]
        for ax, k in zip(axes, (1, 2, 3), strict=True):
            ax.plot(n, [c[k] for c in curve], color=colour, linestyle=style, linewidth=1.3,
                    label=label)
    axes[1].axhline(V_TARGET, color=INK, linestyle=":", linewidth=1)
    axes[0].set_ylabel("batch $b$", fontsize=8)
    axes[1].set_ylabel("$V$, per second", fontsize=8)
    axes[2].set_ylabel("peak age (ms)", fontsize=8)
    axes[1].set_ylim(0.9, 1.0)
    axes[2].set_xlabel("active nodes, as the swarm grows", fontsize=8)
    axes[0].legend(fontsize=7.5, frameon=False, loc="lower right")
    for ax in axes:
        _tidy(ax)
    fig.savefig(FIGS / "fig_adaptive.png", **_SAVE)
    plt.close(fig)


def flood_curve(policy: str, attack: str) -> list[tuple[float, float]]:
    return sorted((float(r["attack_rate_sent"]), float(r["honest_V"]))
                  for r in pn.rows(HW / "flood_udp.authbc-pi4b.csv")
                  if r["senders"] == FLOOD_SENDERS and r["policy"] == policy
                  and r["attack"] == attack)


def fig_flood() -> None:
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    for policy, attack, label, colour, style in FLOODS:
        ax.plot(*zip(*flood_curve(policy, attack), strict=True), color=colour, linestyle=style,
                marker="o", markersize=3, linewidth=1.3, label=label)
    ax.axhline(V_TARGET, color=INK, linestyle=":", linewidth=1)
    limit = pn.flood_channel_limit()
    ax.axvline(limit, color=MUTED, linestyle=":", linewidth=1)
    ax.text(limit - 40, 0.6, "most one\nchannel\ncarries", fontsize=7.5, color=MUTED, ha="right")
    ax.set_xlabel("forged frames per second at the receiver", fontsize=8)
    ax.set_ylabel("honest records accepted, $V$", fontsize=8)
    ax.set_ylim(0, 1.03)
    ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=2)
    _tidy(ax)
    fig.savefig(FIGS / "fig_flood.png", **_SAVE)
    plt.close(fig)


FIGURES = (fig_spread, fig_design_map, fig_margin, fig_adaptive, fig_flood)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    for make in FIGURES:
        make()
        print(f"wrote {FIGS / (make.__name__ + '.png')}")


if __name__ == "__main__":
    main()
