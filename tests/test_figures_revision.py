"""What the revision's figures show must be true of their artifacts, and agree with the text.

`analysis/figures_revision.py` draws one figure per reviewer point. Each test here pins the claim
the paper makes beside a figure, read from the same artifact the figure reads, so a figure and
its sentence cannot come apart.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import figures_revision as fr  # noqa: E402


def _macro(name: str) -> str:
    text = (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")
    hit = re.search(r"\\newcommand\{\\" + name + r"\}\{([^}]*)\}", text)
    assert hit, name
    return hit.group(1)


def test_the_design_map_outlines_every_simulated_cell_and_no_other() -> None:
    _, _, cells = fr.design_map_cells()
    checked = fr.validated_cells()
    assert checked <= set(cells)
    assert len(fr.pn.rows(fr.RAW / "design_map_validation.csv")) == int(_macro("dmCells"))
    assert cells[(50, 100)]["b_star"] == "4"
    assert cells[(100, 100)]["b_star"] == _macro("dmBatch")


def test_at_the_papers_budget_every_interval_the_rule_admits_clears_the_target() -> None:
    """The text: 'with epsilon = 0.05 and p <= epsilon - 0.02 it meets the target, intervals
    included, under every one of them'. At epsilon = 0.1 it does not (paper_numbers.margin_rule
    names the two cells)."""
    admitted = 1 - fr.V_TARGET - fr.RULE_MARGIN
    for model, *_ in fr.LOSS_MODELS:
        pts = fr.margin_points(model)
        assert len(pts) == 5, model
        for p, _, lo, _ in pts:
            if p <= admitted + 1e-9:
                assert lo >= fr.V_TARGET, (model, p, lo)


def test_the_flood_figure_shows_what_the_text_says() -> None:
    limit = fr.pn.flood_channel_limit()
    assert all(v >= 0.95 for _, v in fr.flood_curve("mac", "outsider"))
    assert all(v >= float(_macro("flCapOneV")) for r, v in fr.flood_curve("cap", "forged-one")
               if r <= limit)
    for policy, attack in (("none", "forged"), ("mac", "insider"), ("cap", "forged")):
        assert min(v for _, v in fr.flood_curve(policy, attack)) < 0.95, (policy, attack)


def test_the_spread_figure_draws_ratios_inside_the_quoted_range() -> None:
    sc = fr.pn.rows(fr.RAW / "spatial_capacity.csv")
    lo, hi = float(_macro("spRatioLo")), float(_macro("spRatioHi"))
    for scenario, _ in fr.SPREAD[1:]:
        ratio = float(fr.pn.one(sc, scenario=scenario, config="design")["ratio_to_base"])
        assert lo - 0.005 <= ratio <= hi + 0.005, scenario


def test_the_controller_ages_are_half_a_period_longer_than_sent_at_fill() -> None:
    """The text: these peak ages include the source's send instant, drawn over the next period,
    and are on average half a frame period longer than at fill (F113). With b = 4 fixed at
    50 records/s the period is 80 ms: 1.5 periods plus a few ms of channel."""
    curve = fr.adaptive_curve(fr.RAW / "ns3_adaptive_ts", "fixed4")
    assert all(b == 4 for _, b, _, _ in curve)
    light = [age for n, _, _, age in curve if n < 60]
    assert 1.5 * 80 <= sum(light) / len(light) <= 1.5 * 80 + 6
