"""Bytes per record, and capacity, against batch size (docs/02 §6c, §6e).

`fig_capacity_vs_deadline.png`: the neighbourhood the lean design serves at each batch size a
deadline admits — the five batch sizes that were simulated, with the airtime line drawn through
the others. It exists because the saving depends on the deadline: at 50 records/s a deadline
of 40 ms admits one record to a frame and nothing is gained (audit F80, weak point 2).

`fig_bytes_vs_batch.png`: the first format with a chain link in every record, the
same format with one link per frame, and the lean format. Everything drawn is read from
`results/raw/frame_components.csv`; the batch that is marked is the one the exhaustive search
returns in `design_ladder.csv`, so the figure and the tables cannot be about different designs.

The three colours were checked for colour-vision deficiency before use (worst pair ΔE 20.8 under
deuteranopia). Orange has low contrast on white, so every curve is also told apart by its marker
and by a label at the marked batch. Both figures are drawn in the paper's style (`figstyle`).
"""

from __future__ import annotations

import csv
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

import figstyle  # noqa: E402
import nmax_airtime_line as airtime  # noqa: E402

from authbc.models import bianchi  # noqa: E402

RAW = REPO / "results" / "raw"
RATE = 50.0                         # records/s: the adopted operating point
FIGS = REPO / "results" / "figures"
# (format, item in frame_components.csv, legend text, colour, marker, where its value is written)
CURVES = (
    ("first", "self-batch (byte model)", "record-linked format", "#b2182b", "o",
     {"xytext": (5, 5), "ha": "left"}),
    ("first", "self-batch; one link per frame (byte model)",
     "record-linked, link moved to the frame", "#e08214", "s", {"xytext": (5, 5), "ha": "left"}),
    ("lean", "self-batch", "frame-linked format", "#2166ac", "^",
     {"xytext": (-5, -12), "ha": "right"}),
)


def _rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in (RAW / name).read_text().splitlines()
                               if not ln.startswith("#")))


def _curve(fmt: str, item: str) -> dict[int, float]:
    return {int(r["batch"]): float(r["bytes_per_rec"]) for r in _rows("frame_components.csv")
            if (r["kind"], r["format"], r["item"], r["ref_interval"]) == ("frame", fmt, item, "1")}


def _one_decimal(value: float) -> str:
    """Half up, as `paper_numbers.f` rounds: 43.25 is 43.3 in the text, so it is here too."""
    return str(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _adopted_batch() -> int:
    (best,) = [r for r in _rows("design_ladder.csv")
               if (r["op"], r["format"], r["rung"]) == ("adopted", "lean", "SEARCH_OPTIMUM")]
    return int(best["batch"])


@figstyle.paper_figure
def fig_bytes_vs_batch() -> None:
    """The note on the adopted batch sits at the top of its line, above every curve: between the
    curves it crowded the values (review L-29)."""
    adopted = _adopted_batch()
    fig, ax = plt.subplots(figsize=(figstyle.WIDTH, 3.0))
    ax.axvline(adopted, color="0.45", linestyle=":", linewidth=1)
    for fmt, item, label, colour, marker, where in CURVES:
        curve = _curve(fmt, item)
        batches = sorted(curve)
        ax.plot(batches, [curve[b] for b in batches], color=colour, marker=marker,
                markersize=4.5, linewidth=1.5, label=label)
        ax.annotate(_one_decimal(curve[adopted]), (adopted, curve[adopted]),
                    textcoords="offset points", fontsize=figstyle.NOTE, color="black", **where)
    ax.annotate(f"$b$ = {adopted}: the batch the deadline allows", (adopted, 176), xytext=(4, 0),
                textcoords="offset points", fontsize=figstyle.NOTE, color="0.25", va="top")
    ax.set_xlabel("records per frame $b$")
    ax.set_ylabel("bytes per record")
    ax.set_xticks(sorted(_curve(*CURVES[0][:2])))
    ax.set_ylim(0, 180)
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.9))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig(FIGS / "fig_bytes_vs_batch.png", **figstyle.SAVE)
    plt.close(fig)


def simulated_crossings() -> dict[int, tuple[float, float, float]]:
    """Batch size -> (crossing of 0.95 delivery, lower, upper) for the lean design at 50
    records/s: cells C and D of the direct search, and the three cells of follow-up F6."""
    direct = airtime.crossings("period")
    out = {b: (float(direct[cell]["n_cross_interp"]), float(direct[cell]["n_cross_interp_lo"]),
               float(direct[cell]["n_cross_interp_hi"])) for b, cell in ((1, "C"), (4, "D"))}
    for r in _rows("batch_capacity.csv"):
        out[int(r["batch"])] = (float(r["ns3_crossing"]), float(r["ns3_lo"]), float(r["ns3_hi"]))
    return dict(sorted(out.items()))


def line_capacities() -> dict[int, float]:
    """Batch size -> the airtime line's capacity, slope as calibrated on cells A-F."""
    slope, _ = airtime.calibrate(airtime.crossings("period"))
    frames = {int(r["batch"]): round(float(r["mean_bytes"])) for r in _rows(
        "frame_components.csv") if (r["kind"], r["format"], r["item"], r["ref_interval"])
        == ("frame", "lean", "self-batch", "1")}
    return {b: airtime.n_line(slope, RATE / b, bianchi.t_broadcast(size))
            for b, size in sorted(frames.items())}


def deadline_ms(batch: int) -> float:
    """The smallest freshness bound that admits `batch` records: (b + 1) record periods."""
    return 1000.0 * (batch + 1) / RATE


@figstyle.paper_figure
def fig_capacity_vs_deadline() -> None:
    measured, line = simulated_crossings(), line_capacities()
    adopted = _adopted_batch()
    fig, ax = plt.subplots(figsize=(figstyle.WIDTH, 3.3))
    ax.axvline(adopted, color="0.45", linestyle=":", linewidth=1)
    ax.plot(list(line), list(line.values()), color="0.35", linewidth=1.2,
            label="airtime capacity law (one fitted constant)")
    batches = list(measured)
    values = [measured[b][0] for b in batches]
    ax.errorbar(batches, values,
                yerr=[[measured[b][0] - measured[b][1] for b in batches],
                      [measured[b][2] - measured[b][0] for b in batches]],
                fmt="^", color="#2166ac", markersize=5.5, linewidth=1, capsize=2,
                label="simulated in ns-3 (95 % interval)")
    for b in batches:
        ax.annotate(_one_decimal(measured[b][0]), (b, measured[b][0]), xytext=(5, -10),
                    textcoords="offset points", fontsize=figstyle.NOTE, color="black")
    ax.annotate("100 ms: AUTHBC", (adopted, 20), xytext=(5, 0), textcoords="offset points",
                fontsize=figstyle.NOTE, color="0.25", va="center")
    ticks = [b for b in line if b in (1, 2, 3, 4, 6, 8, 10, 12)]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{b}\n{deadline_ms(b):.0f}" for b in ticks])
    ax.set_xlabel("records per frame $b$; below it, the smallest\n"
                  "deadline that admits it (ms)")
    ax.set_ylabel("nodes served at 95 % delivery")
    ax.set_ylim(0, 320)
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, loc="upper left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig(FIGS / "fig_capacity_vs_deadline.png", **figstyle.SAVE)
    plt.close(fig)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig_bytes_vs_batch()
    fig_capacity_vs_deadline()
    print(f"wrote {FIGS / 'fig_bytes_vs_batch.png'} and "
          f"{FIGS / 'fig_capacity_vs_deadline.png'}")


if __name__ == "__main__":
    main()
