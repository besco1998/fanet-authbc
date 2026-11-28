#!/usr/bin/env python3
"""The model report's figures (docs/reports/2026-11-27_model_report/figures/), drawn from the stored
results only. One y-axis per panel; at most three series per panel, in the reference palette's first
three hues (blue, orange, aqua: validated all-pairs for colour-vision deficiency, worst ΔE 12.6),
each also with its own marker so that no reading depends on colour alone.

    python analysis/report_figures.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw"
FIG = REPO / "docs" / "reports" / "2026-11-27_model_report" / "figures"
BLUE, ORANGE, AQUA = "#257de0", "#f47230", "#00b894"
INK, GREY, BAND = "#191919", "#666666", "#e8e8e8"
WIDTH = 6.3  # inches: the report's text width

plt.rcParams.update(
    {
        "font.size": 8.5,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9,
        "legend.fontsize": 7.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "axes.edgecolor": GREY,
        "axes.labelcolor": INK,
        "xtick.color": GREY,
        "ytick.color": GREY,
        "axes.grid": True,
        "grid.color": BAND,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "lines.linewidth": 1.6,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
    }
)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def save(fig: plt.Figure, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


def band(ax: plt.Axes, lo: float = -5, hi: float = 5, label: str = "±5 % tolerance") -> None:
    ax.axhspan(lo, hi, color=BAND, zorder=0, label=label)
    ax.axhline(0, color=GREY, lw=0.8, zorder=1)


# ---- figure 2: the closed form against ns-3, every stored capacity
def fig_scorecard() -> None:
    sc = [r for r in rows(RAW / "unified_model_vs_ns3.csv") if r["root_err_pct"] and r["ns3"]]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    band(ax)
    for std, col, mk, lab in (
        ("80211a", BLUE, "o", "802.11a"),
        ("80211p", ORANGE, "s", "802.11p"),
        ("80211b", AQUA, "^", "802.11b"),
    ):
        sub = [r for r in sc if r["standard"] == std]
        ax.scatter(
            [float(r["ns3"]) for r in sub],
            [float(r["root_err_pct"]) for r in sub],
            s=22,
            marker=mk,
            color=col,
            edgecolor="white",
            linewidth=0.6,
            label=lab,
            zorder=3,
        )
    ax.set_xscale("log")
    ax.set_xlabel("capacity in ns-3, $N_{\\max}$ (stations, log scale)")
    ax.set_ylabel("model − ns-3 (%)")
    ax.legend(loc="lower center", ncol=4, bbox_to_anchor=(0.5, 1.0))
    save(fig, "fig_scorecard")


# ---- figure 3: the sending pattern, (G25) against Poisson
def fig_g25() -> None:
    import ug25

    pts = []
    for r in rows(RAW / "ug25_scored.csv"):
        c = ug25.CELLS[r["cell"]]
        occ = float(r["ns3_crossing"]) * c.fps * c.tf_s
        pts.append((occ, float(r["poisson_err_pct"]), float(r["g25_err_pct"]), "UG25"))
    for r in rows(RAW / "ug25h_scored.csv"):
        pts.append(
            (
                float(r["occupancy_at_ns3"]),
                float(r["poisson_err_pct"]),
                float(r["g25_err_pct"]),
                "UG25H",
            )
        )
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    band(ax)
    ax.axvline(0.78, color=GREY, lw=0.8, ls=":")
    ax.text(0.785, 4.0, "checked range ends\n(occupancy 0.78)", fontsize=7, color=GREY, va="top")
    ax.scatter(
        [p[0] for p in pts],
        [p[1] for p in pts],
        s=22,
        marker="s",
        color=ORANGE,
        edgecolor="white",
        linewidth=0.6,
        label="Poisson sources, (G5)",
        zorder=3,
    )
    ax.scatter(
        [p[0] for p in pts],
        [p[2] for p in pts],
        s=24,
        marker="o",
        color=BLUE,
        edgecolor="white",
        linewidth=0.6,
        label="periodic sources, (G25)",
        zorder=4,
    )
    ax.set_xlabel("occupancy at ns-3's crossing, $N f T_f$")
    ax.set_ylabel("model − ns-3 (%)")
    ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, 1.0))
    save(fig, "fig_g25")


# ---- figure 4: capture in ns-3, UF2
def fig_uf2() -> None:
    u = rows(RAW / "uf2_scored.csv")
    configs = list(dict.fromkeys(r["config"] for r in u))
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    band(ax)
    for key, col, mk, lab, dx in (
        ("(a)", BLUE, "o", "average delivery, (G23) with (G22a)", -0.18),
        ("statistic 1", AQUA, "^", "every sender, pooled, (G24)", 0.0),
        ("statistic 2", ORANGE, "s", "worst sender per 20 s window, (G24a)", 0.18),
    ):
        sub = {r["config"]: float(r["err_pct"]) for r in u if r["claim"].startswith(key)}
        ax.scatter(
            [i + dx for i, c in enumerate(configs)],
            [sub[c] for c in configs],
            s=24,
            marker=mk,
            color=col,
            edgecolor="white",
            linewidth=0.6,
            label=lab,
            zorder=3,
        )
    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels([c.replace("F", "\nF", 1) for c in configs], fontsize=6.5)
    ax.set_ylabel("model − ns-3 (%)")
    ax.set_ylim(-7, 6)
    ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.18))
    save(fig, "fig_uf2")


# ---- figure 5: hardware contention, W1e (frame burst on) and W1r (off)
POINTS = [
    ("AB", 131),
    ("AC", 131),
    ("BC", 131),
    ("ABC", 87),
    ("AB", 183),
    ("AC", 183),
    ("BC", 183),
    ("ABC", 122),
    ("AB", 222),
    ("AC", 222),
    ("BC", 222),
    ("ABC", 148),
]


def fig_hw_contention() -> None:
    w1e = {r["group"]: r for r in rows(RAW / "w1e_w1e_2026-11-05.csv") if r["what"] == "contention"}
    w1r = {
        r["item"].split(" (")[0]: r
        for r in rows(RAW / "w1r_w1r_2026-11-22.csv")
        if r["what"] == "point"
    }
    pred = {(r["group"], int(r["fps_per_board"])): r for r in rows(RAW / "w1r_predictions.csv")}
    x = list(range(len(POINTS)))
    labels = [f"{g}\n{f}/s" for g, f in POINTS]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(WIDTH, 4.6), sharex=True)
    # top: W1e against its registered model
    m = [float(w1e[f"{g} at {f}/s"]["measured"]) * 100 for g, f in POINTS]
    p = [float(w1e[f"{g} at {f}/s"]["predicted"]) * 100 for g, f in POINTS]
    lo = [float(w1e[f"{g} at {f}/s"]["band_lo"]) * 100 for g, f in POINTS]
    hi = [float(w1e[f"{g} at {f}/s"]["band_hi"]) * 100 for g, f in POINTS]
    a1.vlines(x, lo, hi, color=BAND, lw=7, label="registered band", zorder=1)
    a1.scatter(
        x,
        p,
        marker="_",
        s=120,
        color=BLUE,
        lw=2,
        label="event simulation (W1c), registered",
        zorder=3,
    )
    a1.scatter(
        x,
        m,
        marker="o",
        s=26,
        color=ORANGE,
        edgecolor="white",
        linewidth=0.6,
        label="hardware, W1e (frame burst on)",
        zorder=4,
    )
    a1.set_ylabel("loss (%)")
    held = sum(w1e[f"{g} at {f}/s"]["held"] == "True" for g, f in POINTS)
    a1.set_title(f"W1e, 2026-11-05: {held} of {len(POINTS)} points inside their bands", loc="left")
    a1.legend(loc="upper left", ncol=3)
    # bottom: W1r against both ns-3 settings
    hw, ci_lo, ci_hi = [], [], []
    for g, f in POINTS:
        mm = re.match(r"([\d.]+) \(([\d.-]+)-([\d.]+)\)", w1r[f"{g} at {f}/s"]["measured"])
        if mm is None:
            raise ValueError(f"W1r {g} at {f}/s: no interval in its measured field")
        hw.append(float(mm[1]) * 100)
        ci_lo.append(float(mm[2]) * 100)
        ci_hi.append(float(mm[3]) * 100)
    s20 = [float(pred[(g, f)]["ns3_s20d50_equal"]) * 100 for g, f in POINTS]
    s9 = [float(pred[(g, f)]["ns3_s9d28_equal"]) * 100 for g, f in POINTS]
    a2.vlines(x, ci_lo, ci_hi, color=ORANGE, lw=1.2, zorder=2)
    a2.scatter(
        x,
        hw,
        marker="o",
        s=26,
        color=ORANGE,
        edgecolor="white",
        linewidth=0.6,
        label="hardware, W1r (frame burst off), 95 % CI",
        zorder=4,
    )
    a2.scatter(
        x, s20, marker="^", s=24, color=BLUE, label="ns-3, slot 20 µs / DIFS 50 µs", zorder=3
    )
    a2.scatter(x, s9, marker="s", s=20, color=AQUA, label="ns-3, slot 9 µs / DIFS 28 µs", zorder=3)
    a2.set_ylabel("loss (%)")
    a2.set_title("W1r, 2026-11-22: reported against both settings (W not identified)", loc="left")
    a2.legend(loc="upper left", ncol=1)
    a2.set_xticks(x)
    a2.set_xticklabels(labels, fontsize=6.5)
    a2.set_xlabel("group and rate per board (occupancy 0.50, 0.70, 0.85 left to right)")
    save(fig, "fig_hw_contention")


# ---- figure 6: the capacity ratio on four radios
def fig_ratio() -> None:
    vals = []
    for run, lab in (("w1i_w1j_2026-11-06_run.csv", "W1j"), ("w1i_w1k_2026-11-06_run.csv", "W1k")):
        r = next(x for x in rows(RAW / run) if x["what"] == "ratio")
        vals.append(
            (
                lab,
                float(r["measured"]),
                float(r["predicted"]),
                float(r["band_lo"]),
                float(r["band_hi"]),
            )
        )
    fig, ax = plt.subplots(figsize=(3.2, 2.4))
    ax.axhspan(vals[0][3], vals[0][4], color=BAND, label="registered band")
    ax.axhline(vals[0][2], color=BLUE, lw=1.6, label=f"event simulation (W1c), {vals[0][2]:.2f}")
    ax.scatter(
        [0, 1],
        [v[1] for v in vals],
        s=40,
        color=ORANGE,
        edgecolor="white",
        zorder=3,
        label="hardware, four radios",
    )
    for i, v in enumerate(vals):
        ax.text(i + 0.08, v[1], f"{v[1]:.2f}", fontsize=7.5, va="center", color=INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([v[0] for v in vals])
    ax.set_xlim(-0.5, 1.6)
    ax.set_ylabel("capacity ratio,\nAUTHBC / per-record signing")
    ax.legend(loc="lower left", fontsize=6.5)
    save(fig, "fig_ratio")


# ---- figure 7: capture on the hardware
def fig_capture_hw() -> None:
    import w1s

    curve = w1s.curve_points()
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    ax.plot(
        [-8, -4, -4, 4, 4, 8],
        [1, 1, 0, 0, 1, 1],
        color=GREY,
        lw=1,
        ls="--",
        label="ns-3's rule: the stronger frame kept at ≥ 4 dB",
    )
    ok = [m for m in curve if m["enters"]]
    ax.scatter(
        [m["delta_db"] for m in ok],
        [max(m["q_a"], m["q_b"]) for m in ok],
        s=30,
        marker="o",
        color=BLUE,
        edgecolor="white",
        label="W1q: the stronger frame kept",
        zorder=3,
    )
    ax.scatter(
        [m["delta_db"] for m in ok],
        [min(m["q_a"], m["q_b"]) for m in ok],
        s=30,
        marker="s",
        color=AQUA,
        edgecolor="white",
        label="W1q: the weaker frame kept",
        zorder=3,
    )
    w1s_rows = [r for r in rows(RAW / "w1s_w1s_2026-11-23.csv") if r["what"] == "A: step"]
    for r in w1s_rows:
        mm = re.match(r"Δ ([+-][\d.]+) dB; q_A ([-\d.]+), q_B ([-\d.]+)", r["measured"])
        if not mm:
            continue
        d, qa, qb = float(mm[1]), float(mm[2]), float(mm[3])
        ax.scatter([d], [max(qa, qb)], s=34, marker="D", color=ORANGE, edgecolor="white", zorder=4)
    ax.scatter([], [], s=34, marker="D", color=ORANGE, label="W1s: the stronger frame kept")
    ax.set_xlabel("signal difference at the receiver, $\\Delta$ (dB)")
    ax.set_ylabel("share of collided frames kept, $q$")
    ax.set_xlim(-8, 8)
    ax.set_ylim(-0.15, 1.1)
    ax.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.0), fontsize=6.8)
    save(fig, "fig_capture_hw")


# ---- figure 8: the radios' own timing, C1
def fig_c1_gaps() -> None:
    import hw_mac_timing as mt
    import s0

    session = HW / "frame_campaign" / "c1_2026-11-27"
    frames = s0.sniffer_frames(session)
    spans = s0.window_spans(session)
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.2), sharey=True)
    for ax, (n, label, col) in zip(
        axes,
        (
            (1, "pi-A (BCM4345/6)", BLUE),
            (2, "pi-B (BCM4345/6)", BLUE),
            (3, "the Pi 3 (BCM43430/1)", ORANGE),
        ),
        strict=True,
    ):
        tag = next(t for t in sorted(spans) if t.split("_")[1] == f"Q{n}")  # 145 B, saturated
        d = mt.intervals(s0.in_window(frames, spans[tag], n))
        gaps = [x - mt.airtime_us(145) for x in d]
        stats = mt.gap_stats(gaps)
        floor, slot = float(stats["gap_floor_us"]), int(stats["lattice_us"])
        # one bin per backoff slot, centred on the board's own lattice (floor + k·slot)
        edges = [floor - slot / 2 + slot * i for i in range(int((600 - floor) // slot) + 2)]
        ax.hist(
            [g for g in gaps if g < edges[-1]],
            bins=edges,
            color=col,
            edgecolor="white",
            linewidth=0.8,
        )
        ax.set_title(label, fontsize=8)
        ax.set_xlabel("gap after a frame (µs)")
        ax.set_xlim(0, 600)
        ax.text(
            0.97,
            0.72,
            f"floor {floor:.0f} µs, slot {slot} µs\nat the floor: "
            f"{100 * stats['share_no_backoff']:.0f} %",
            transform=ax.transAxes,
            ha="right",
            fontsize=7,
            color=INK,
        )
    axes[0].set_ylabel("frames")
    save(fig, "fig_c1_gaps")


# ---- figure 9 (full version): the sniffer's completeness
def fig_sniffer() -> None:
    import s0_diag

    sessions = [
        ("S0", "s0_2026-11-23", ("G1", "G2", "G3")),
        ("D1a", "d1a_2026-11-23", ("DA", "DB", "DC")),
        ("D1b", "d1b_2026-11-23", ("DA", "DB", "DC")),
        ("P1", "p1x_2026-11-27", ("DA", "DB", "DC")),
    ]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.4))
    ax.axhline(99, color=GREY, lw=0.8, ls="--", label="the gate's rule, 99 %")
    for (_name, folder, labels), i in zip(sessions, range(len(sessions)), strict=True):
        rws = s0_diag.rows(HW / "frame_campaign" / folder)
        for (lab, col, mk), dx in zip(
            ((labels[0], BLUE, "o"), (labels[1], ORANGE, "s"), (labels[2], AQUA, "^")),
            (-0.15, 0.0, 0.15),
            strict=True,
        ):
            v = [
                float(str(r["sniffer"])) * 100 for r in rws if str(r["window"]).split("_")[1] == lab
            ]
            ax.scatter([i + dx], v[:1], s=30, marker=mk, color=col, edgecolor="white", zorder=3)
    for col, mk, lab in ((BLUE, "o", "pi-A"), (ORANGE, "s", "pi-B"), (AQUA, "^", "the Pi 3")):
        ax.scatter([], [], s=30, marker=mk, color=col, label=lab)
    ax.set_xticks(range(len(sessions)))
    ax.set_xticklabels([s[0] for s in sessions])
    ax.set_ylabel("frames the sniffer recorded (%)")
    ax.set_ylim(86, 101)
    ax.legend(loc="lower right", ncol=4)
    save(fig, "fig_sniffer")


# ---- figure: the gain of batching, (G12) against ns-3
def fig_batching() -> None:
    a = [r for r in rows(RAW / "unified_c2_scored.csv") if r["kind"].startswith("gain")]
    d = [r for r in rows(RAW / "unified_d_scored.csv") if r["item"].startswith("D2 gain")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.4), sharey=True)
    for ax, pts, title in (
        (
            a1,
            [(float(r["b"]), float(r["ns3_gain"]), float(r["design_gain"])) for r in a],
            "802.11a, 6 Mb/s",
        ),
        (
            a2,
            [
                (float(r["cell"].removeprefix("DB")), float(r["ns3_gain"]), float(r["design_gain"]))
                for r in d
            ],
            "802.11b, 1 Mb/s",
        ),
    ):
        pts.sort()
        ax.plot([p[0] for p in pts], [p[2] for p in pts], color=BLUE, label="model, (G12)")
        ax.scatter(
            [p[0] for p in pts],
            [p[1] for p in pts],
            s=26,
            marker="s",
            color=ORANGE,
            edgecolor="white",
            linewidth=0.6,
            label="ns-3",
            zorder=3,
        )
        ax.set_xscale("log", base=2)
        ax.set_xlabel("records per frame, $b$")
        ax.set_title(title, loc="left", fontsize=8)
    a1.set_ylabel("gain over one record per frame")
    a1.legend(loc="upper left")
    save(fig, "fig_batching")


# ---- figure: few stations, the finite-station form against ns-3 and (G5)
def fig_fewstations() -> None:
    u = rows(RAW / "ufs_scored.csv")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.5), sharey=False)
    for ax, std, title in zip(axes, ("80211b", "80211a"), ("802.11b", "802.11a"), strict=True):
        sub = sorted(
            (r for r in u if r["standard"] == std),
            key=lambda r: (float(r["occupancy"]), int(r["n_nodes"])),
        )
        x = list(range(len(sub)))
        ns3 = [float(r["ns3_loss"]) * 100 for r in sub]
        lo = [float(r["ci_lo"]) * 100 for r in sub]
        hi = [float(r["ci_hi"]) * 100 for r in sub]
        # side by side, so that a finite-station mark lying inside the CI is not hidden by it
        xn = [i - 0.14 for i in x]
        xf = [i + 0.14 for i in x]
        ax.vlines(xn, lo, hi, color=ORANGE, lw=1.2, zorder=2)
        ax.scatter(
            xn,
            ns3,
            s=26,
            marker="o",
            color=ORANGE,
            edgecolor="white",
            linewidth=0.6,
            label="ns-3, 95 % CI",
            zorder=4,
        )
        ax.scatter(
            xf,
            [float(r["finite"]) * 100 for r in sub],
            s=60,
            marker="_",
            color=BLUE,
            linewidths=2,
            label="finite-station form",
            zorder=3,
        )
        ax.scatter(
            x,
            [float(r["g5"]) * 100 for r in sub],
            s=22,
            marker="^",
            color=AQUA,
            label="Poisson, (G5)",
            zorder=3,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(
            [f"N={r['n_nodes']}\nu={float(r['occupancy']):.1f}" for r in sub], fontsize=6.5
        )
        ax.set_title(title, loc="left", fontsize=8)
    axes[0].set_ylabel("loss (%)")
    axes[0].legend(loc="upper left", fontsize=6.8)
    save(fig, "fig_fewstations")


# ---- figure: V1a, the closed form as stated against the radios
def fig_v1a() -> None:
    from report_numbers import v1a_points

    pts = v1a_points()
    u = [p["u"] for p in pts]
    fig, ax = plt.subplots(figsize=(WIDTH * 0.62, 2.6))
    ax.plot(
        u,
        [100 * p["finite"] for p in pts],
        color=BLUE,
        marker="o",
        ms=4,
        label="closed form as stated (FS, W = 32)",
    )
    ax.plot(
        u,
        [100 * p["ns3"] for p in pts],
        color=AQUA,
        marker="s",
        ms=4,
        ls="--",
        label="ns-3, standard rule",
    )
    ax.vlines(u, [100 * p["lo"] for p in pts], [100 * p["hi"] for p in pts], color=ORANGE, lw=1.4)
    ax.scatter(
        u,
        [100 * p["loss"] for p in pts],
        s=34,
        color=ORANGE,
        edgecolor="white",
        zorder=4,
        label="radios, V1a (95 % interval)",
    )
    ax.set_xticks(u)
    ax.set_xlabel("occupancy of the three radios, $u$")
    ax.set_ylabel("loss (%)")
    ax.set_ylim(0, 1.15 * max(100 * p["hi"] for p in pts))
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7)
    save(fig, "fig_v1a")


# ---- figure: UJ, the root of (G5) and the law (G9) by traffic source
UJ_NAMES = {"FZ": "frozen", "DR": "20 ppm", "J01": "0.1 ms", "J1": "1 ms", "DS": "designated"}


def fig_uj() -> None:
    u = rows(RAW / "uj_scored.csv")
    fig, ax = plt.subplots(figsize=(WIDTH, 2.5))
    band(ax)
    x = list(range(len(u)))
    ax.scatter(
        x,
        [float(r["root_err_pct"]) for r in u],
        s=30,
        marker="o",
        color=BLUE,
        edgecolor="white",
        zorder=3,
        label="root of (G5)",
    )
    ax.scatter(
        x,
        [float(r["law_err_pct"]) for r in u],
        s=26,
        marker="s",
        color=ORANGE,
        edgecolor="white",
        zorder=3,
        label="law (G9)",
    )
    labels = []
    for r in u:
        cell = "230 B, 40/s" if r["cell"].startswith("JA230") else "260 B, 30/s"
        labels.append(f"{UJ_NAMES[r['source']]}\n{cell}")
    for i, r in enumerate(u):
        if r["source"] == "FZ":
            ax.axvspan(
                i - 0.4,
                i + 0.4,
                facecolor="none",
                edgecolor=GREY,
                hatch="///",
                lw=0,
                zorder=0.5,
                label="frozen: reported, not scored" if i == 0 else None,
            )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("model − ns-3 (%)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, fontsize=7)
    save(fig, "fig_uj")


# ---- figure: UD2, (G25) and the Poisson root at 802.11b by window and target
def fig_ud2() -> None:
    q = rows(RAW / "ud2_scored.csv")
    q.sort(key=lambda r: (int(r["w"]), r["cell"], float(r["eps"])))
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    band(ax)
    x = list(range(len(q)))
    ax.scatter(
        x,
        [float(r["poisson_err_pct"]) for r in q],
        s=24,
        marker="s",
        color=ORANGE,
        edgecolor="white",
        zorder=3,
        label="Poisson root of (G5), reported",
    )
    ax.scatter(
        x,
        [float(r["g25_err_pct"]) for r in q],
        s=30,
        marker="o",
        color=BLUE,
        edgecolor="white",
        zorder=4,
        label="(G25), scored",
    )
    for i, r in enumerate(q):
        if r["past_range"] == "True":
            ax.annotate(
                "past 0.78",
                (i, float(r["g25_err_pct"])),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=6,
                color=GREY,
            )
    for k, w in enumerate((8, 16, 32)):
        ax.axvline(6 * k - 0.5, color=GREY, lw=0.5) if k else None
        ax.text(6 * k + 2.5, -8.6, f"W = {w}", ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['cell'][2:5]}\n{float(r['eps']):g}" for r in q], fontsize=6.5)
    ax.set_xlabel("frame size (B) and loss target ε, at each window W")
    ax.set_ylim(-9.2, 5.8)
    ax.set_ylabel("model − ns-3 (%)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    save(fig, "fig_ud2")


def main() -> None:
    for f in (
        fig_scorecard,
        fig_g25,
        fig_uf2,
        fig_hw_contention,
        fig_ratio,
        fig_capture_hw,
        fig_c1_gaps,
        fig_sniffer,
        fig_batching,
        fig_fewstations,
        fig_v1a,
        fig_uj,
        fig_ud2,
    ):
        f()
        print(f.__name__, "written")


if __name__ == "__main__":
    main()
