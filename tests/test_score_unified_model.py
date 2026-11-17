"""The scoring of the unified model against every stored ns-3 crossing
(analysis/score_unified_model.py -> results/raw/unified_model_vs_ns3.csv).

Held here:
* the file on disk is exactly what the script produces now (not stale, not hand-edited);
* every bracketed crossing of every listed file is scored, once;
* the model's airtime equals the airtime each file stored, wherever one was stored;
* an error is 100·(model − ns-3)/ns-3, recomputed from the row's own numbers.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"


def _load():
    spec = importlib.util.spec_from_file_location("score_unified_model",
                                                  REPO / "analysis" / "score_unified_model.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["score_unified_model"] = mod
    spec.loader.exec_module(mod)
    return mod


def _file_rows(name: str) -> list[dict[str, str]]:
    with (RAW / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


SCORE = _load()
ON_DISK = _file_rows("unified_model_vs_ns3.csv")


def test_the_file_is_what_the_script_produces() -> None:
    fresh = [{k: str(v) for k, v in r.items()} for r in SCORE.all_rows()]
    assert fresh == ON_DISK


def test_every_stored_crossing_is_scored_once() -> None:
    direct = [r for r in _file_rows("ns3_nmax_direct.csv")
              if r["n_nodes"] == "CROSSING" and r.get("n_cross_interp")]
    expected = {"ns3_nmax_direct": len(direct),
                "batch_capacity": len(_file_rows("batch_capacity.csv")),
                "design_map_validation": len(_file_rows("design_map_validation.csv")),
                "phy_links": len(_file_rows("phy_links.csv")),
                "pq_capacity": len(_file_rows("pq_capacity.csv")),
                "capacity_97": len(_file_rows("capacity_97.csv")),
                "w1a": sum(r["cell"] in ("C", "D") for r in _file_rows("w1a.csv")),
                "w1b": sum(r["what"] == "crossing" for r in _file_rows("w1b.csv")),
                "ns3_rule_cw31": 2, "ns3_rule_levels": 4}
    got: dict[str, int] = {}
    for r in ON_DISK:
        got[r["source_file"]] = got.get(r["source_file"], 0) + 1
    assert got == expected


def test_the_airtime_is_the_one_each_file_stored() -> None:
    stored = [r for r in ON_DISK if r["tf_stored_us"]]
    assert len(stored) == 14
    assert all(abs(float(r["tf_us"]) - float(r["tf_stored_us"])) < 0.5 for r in stored)


@pytest.mark.parametrize("which", ["law", "root"])
def test_each_error_follows_from_its_row(which) -> None:
    for r in ON_DISK:
        ns3, model = float(r["ns3"]), float(r[which])
        assert float(r[f"{which}_err_pct"]) == pytest.approx(100 * (model - ns3) / ns3, abs=0.02)
