"""Revision A3, part 2: ns-3 link traces replayed through the real codec (predictions/A3.md).

The trace replaces the loss process and nothing else, so the arithmetic is checked on masks
whose answer is known: at r = 1 every received frame verifies alone (V = 1 − loss, exactly);
at r = 2 a lost reference frame takes its dependent frame with it, a lost dependent frame only
itself.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from authbc.bench import leanframes
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.models import frame as frame_model
from authbc.placement.session_v2 import LeanSender

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "verifiability_margin", REPO / "analysis" / "verifiability_margin.py")
assert _spec and _spec.loader
vm = importlib.util.module_from_spec(_spec)
sys.modules["verifiability_margin"] = vm
_spec.loader.exec_module(vm)

_SK, _PK = Ed25519Scheme().keygen(seed=bytes(range(32)))


def _stream(n: int, ref: int, batch: int = 1) -> list[bytes]:
    recs = leanframes.chained_records(1, n * batch)
    sender = LeanSender(_SK, ref_interval=ref)
    return [sender.frame(recs[i:i + batch]) for i in range(0, len(recs), batch)]


def _mask(bits: str) -> np.ndarray:
    return np.array([c == "0" for c in bits])


def test_read_traces(tmp_path: Path) -> None:
    f = tmp_path / "s1-r1000.design.217.3.csv"
    f.write_text("link,src,rx,got\n0,4,9,1101\n1,7,2,0011\n")
    got = vm.read_traces(f)
    assert [m.tolist() for m in got] == [[False, False, True, False], [True, True, False, False]]


def test_burst_stats() -> None:
    lost, bursts = vm.burst_stats([_mask("1001011000"), _mask("0111")])
    assert (lost, bursts) == (2 + 1 + 3 + 1, 4)     # runs of 2, 1, 3, and 1


def test_r1_v_is_one_minus_loss_exactly() -> None:
    frames = _stream(12, ref=1)
    masks = [_mask("110111011111"), _mask("111111111111"), _mask("000011110000")]
    assert vm.v_of_masks(frames, _PK, masks) == [10 / 12, 1.0, 4 / 12]


@pytest.mark.parametrize(("bits", "v"), [
    ("01111111", 6 / 8),   # reference lost: its dependent frame cannot be rebuilt
    ("10111111", 7 / 8),   # a dependent frame lost: only itself
    ("11111110", 7 / 8),
])
def test_r2_loss_propagates_to_the_dependent_frame_only(bits: str, v: float) -> None:
    assert vm.v_of_masks(_stream(8, ref=2), _PK, [_mask(bits)]) == [v]


def test_a_trace_longer_than_the_stream_is_refused() -> None:
    with pytest.raises(ValueError):
        vm.v_of_masks(_stream(4, ref=1), _PK, [_mask("11111")])


def test_trace_cell_scores_runs_against_both_bounds() -> None:
    rng = np.random.default_rng(5)
    runs = [[rng.random(40) < 0.05 for _ in range(3)] for _ in range(4)]
    (row,) = vm.trace_cell((1, 2, {"g": runs}))
    masks = [m for run in runs for m in run]
    p_hat = sum(int(m.sum()) for m in masks) / (40 * len(masks))
    assert row["runs"] == 4 and row["links"] == 12 and row["p_hat"] == round(p_hat, 5)
    assert row["V_iid"] == round(frame_model.verifiability(p_hat, 2), 5)
    assert row["V_gilbert8"] == round(frame_model.verifiability_gilbert(p_hat, 8.0, 2), 5)
    assert row["V_ci_lo"] <= row["V_trace"] <= row["V_ci_hi"]
