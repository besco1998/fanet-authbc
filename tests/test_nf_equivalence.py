"""Revision A12: the N·f equivalence (predictions/A12.md, analysis/nf_equivalence.py).

Held here: the plan runs exactly the registered splits, each split keeps the registered N·f,
the (N − 1)/N correction is the arithmetic the registration states, and nothing is scored
before the runs exist.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
_spec = importlib.util.spec_from_file_location("nf_equivalence",
                                               REPO / "analysis" / "nf_equivalence.py")
assert _spec and _spec.loader
nf = importlib.util.module_from_spec(_spec)
sys.modules["nf_equivalence"] = nf
_spec.loader.exec_module(nf)

import run_nmax_direct as drv  # noqa: E402

with nf.PREDICTIONS.open(encoding="utf-8") as _fh:
    REG = list(csv.DictReader(ln for ln in _fh if not ln.startswith("#")))


def test_the_plan_runs_the_registered_splits_and_the_extra_reference_point() -> None:
    plan = {(cell, n) for cell, spec, ns in
            drv.read_plan(REPO / "experiments" / "nf-equivalence" / "plan.txt") for n in ns}
    assert plan == {(r["ns3_cell"], int(r["n_nodes"])) for r in REG} | {("C", 29)}


def test_each_split_keeps_its_crossings_total_rate() -> None:
    for r in REG:
        total = int(r["n_nodes"]) * float(r["frames_per_s"])
        assert total == pytest.approx(1550 if r["frame_bytes"] == "173" else 1750, rel=0.005)


def test_every_split_is_the_drivers_cell() -> None:
    for r in REG:
        c = drv.CELLS[r["ns3_cell"]]
        assert (c.frame_bytes, c.fps) == (int(r["frame_bytes"]), float(r["frames_per_s"]))


@pytest.mark.parametrize(("n", "f", "frame", "eq"), [(8, 194.0, 173, 109.64),
                                                      (5, 350.0, 146, 29.0),
                                                      (124, 12.5, 173, 124.0)])
def test_the_correction_counts_the_other_nodes_load(n: int, f: float, frame: int,
                                                    eq: float) -> None:
    assert nf.n_equivalent(n, f, frame) == pytest.approx(eq)


def test_nothing_is_scored_before_the_runs(tmp_path: Path,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nf, "RAW", tmp_path)
    monkeypatch.setattr(nf, "PREDICTIONS", REPO / "results" / "raw" /
                        "nf_equivalence_predictions.csv")
    assert nf.score() == []


def test_the_reference_split_is_the_papers_configuration() -> None:
    with (REPO / "results" / "raw" / "nf_equivalence_predictions.csv").open() as fh:
        reg = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    assert nf.reference_split([r for r in reg if r["frame_bytes"] == "173"], 173) == ("D", 124)
    assert nf.reference_split([r for r in reg if r["frame_bytes"] == "146"], 146) == ("C", 35)
