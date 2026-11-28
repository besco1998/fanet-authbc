"""U-D2's cells, predictions and scorer (analysis/ud2.py): the runner's cells are U-D2's at the
registered windows, and the scorer reads known crossings back at ±5 %."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "ns3"), str(REPO / "src")]

import run_unified as ru  # noqa: E402
import ud2  # noqa: E402

from authbc.models import periodic_capacity as pc  # noqa: E402


def test_the_runner_holds_every_cell_at_its_window() -> None:
    assert len(ud2.CELLS) == 6
    for c in ud2.CELLS:
        args = ru.CELLS[c.name].args()
        assert f"--cwMin={c.w - 1}" in args
        assert "--standard=80211b" in args and "--dataMode=DsssRate1Mbps" in args
        assert f"--txJitterMs={ru.one_period_ms(c.fps)!r}" in args, "the designated source"
        assert c.access.w == c.w and c.access.slot_s == 20e-6 and c.access.difs_s == 50e-6


def test_the_cells_are_new() -> None:
    assert ud2.scan_prior() == []


def test_predictions_are_the_model_code() -> None:
    rows = ud2.predictions()
    assert len(rows) == 18
    for r in rows:
        c = next(x for x in ud2.CELLS if x.name == r["cell"])
        assert r["g25_root"] == pc.n_root_periodic(c.fps, c.tf_s, float(str(r["eps"])), c.access)


def test_the_score_at_five_percent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ud2, "RAW", tmp_path)
    pred = {(r["cell"], r["eps"]): float(str(r["g25_root"])) for r in ud2.predictions()}
    for c in ud2.CELLS:
        lines = ["cell,n_nodes,seeds,delivered_mean,delivered_min,delivered_max,delivered_stdev"]
        for eps, level in ((0.02, "0.98"), (0.05, "0.95"), (0.10, "0.9")):
            # within 4 % at W = 8 and 16; 6 % above the root (the model conservative) at W = 32
            ns3 = pred[(c.name, eps)] / (0.94 if c.w == 32 else 0.96)
            lines.append(f"{c.name},CROSSING@{level},30,{ns3},{ns3 - 0.3},{ns3 + 0.3},bracketed")
        (tmp_path / f"ud2_{c.name.lower()}.csv").write_text("\n".join(lines) + "\n")
    rows = ud2.score()
    assert len(rows) == 18
    for r in rows:
        if r["w"] == 32:
            assert r["held"] == 0 and r["side"] == "conservative"
        else:
            assert r["held"] == 1 and r["side"] == ""
    assert {r["eps"] for r in rows} == {0.02, 0.05, 0.1}
