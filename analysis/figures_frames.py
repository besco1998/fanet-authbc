"""Bytes per record against batch size, by where the chain link sits (docs/02 §6c).

One figure, `fig_bytes_vs_batch.png`: the first format with a chain link in every record, the
same format with one link per frame, and the lean format. Everything drawn is read from
`results/raw/frame_components.csv`; the batch that is marked is the one the exhaustive search
returns in `design_ladder.csv`, so the figure and the tables cannot be about different designs.

The three colours were checked for colour-vision deficiency before use (worst pair ΔE 20.8 under
deuteranopia). Orange has low contrast on white, so every curve is also told apart by its marker
and by a label at the marked batch.
"""

from __future__ import annotations

import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 200, "bbox_inches": "tight", "metadata": {"Software": None}}
# (format, item in frame_components.csv, legend text, colour, marker, where its value is written)
CURVES = (
    ("first", "self-batch (byte model)", "first format: a link in every record", "#b2182b", "o",
     {"xytext": (5, 5), "ha": "left"}),
    ("first", "self-batch; one link per frame (byte model)",
     "first format: one link per frame", "#e08214", "s", {"xytext": (5, 5), "ha": "left"}),
    ("lean", "self-batch", "lean format: one link per frame", "#2166ac", "^",
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


def fig_bytes_vs_batch() -> None:
    adopted = _adopted_batch()
    fig, ax = plt.subplots(figsize=(4.4, 2.9))
    ax.axvline(adopted, color="0.45", linestyle=":", linewidth=1)
    for fmt, item, label, colour, marker, where in CURVES:
        curve = _curve(fmt, item)
        batches = sorted(curve)
        ax.plot(batches, [curve[b] for b in batches], color=colour, marker=marker,
                markersize=4.5, linewidth=1.5, label=label)
        ax.annotate(_one_decimal(curve[adopted]), (adopted, curve[adopted]),
                    textcoords="offset points", fontsize=8, color="black", **where)
    ax.annotate(f"$b$ = {adopted}, the batch freshness allows", (adopted, 9), xytext=(5, 0),
                textcoords="offset points", fontsize=8, color="0.25", va="center")
    ax.set_xlabel("records per frame $b$")
    ax.set_ylabel("bytes per record")
    ax.set_xticks(sorted(_curve(*CURVES[0][:2])))
    ax.set_ylim(0, 180)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig(FIGS / "fig_bytes_vs_batch.png", **_SAVE)
    plt.close(fig)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig_bytes_vs_batch()
    print(f"wrote {FIGS / 'fig_bytes_vs_batch.png'}")


if __name__ == "__main__":
    main()
