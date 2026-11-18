"""The decode-dependency rules of src/authbc/sim/verified.py, on receptions made up by hand.

Held here:
* key record once in r frames: a frame verifies only with every earlier frame of its group;
  r = 1 makes every received frame verify (the plain delivered count);
* a unit over n frames verifies only with all n; n = 1 is again the plain delivered count;
* the expectation over independent losses is the spec's formula (1/r)·Σ_j (1 − p)^j.
"""
from __future__ import annotations

import itertools
import random

import pytest

from authbc.sim.verified import (
    unit_completion_ns,
    units_sent,
    verified_key_chain,
    verified_units,
)


def test_key_chain_by_hand() -> None:
    # source 7 sends seq 0..7 (r = 4: groups 0..3 and 4..7); receiver 1 misses 2 and 4
    got = [(1, 7, s) for s in (0, 1, 3, 5, 6, 7)]
    # group 0: 0 ok, 1 ok, 3 needs 0,1,2 -> no; group 1: 5, 6, 7 need 4 -> no
    assert verified_key_chain(got, 4) == 2
    # r = 2: (0, 1) both; 3 needs 2; 5 needs 4; (6, 7) both
    assert verified_key_chain(got, 2) == 2 + 0 + 0 + 2
    assert verified_key_chain(got, 1) == 6


def test_key_chain_keeps_receivers_and_sources_apart() -> None:
    got = [(1, 7, 0), (2, 7, 1), (1, 8, 1)]   # seq 1 never arrives with its key at one receiver
    assert verified_key_chain(got, 2) == 1


def test_units_by_hand() -> None:
    got = [(1, 7, s) for s in (0, 1, 2, 4, 5)] + [(2, 7, 3)]
    assert verified_units(got, 2) == 2                    # units 0 and 2 at receiver 1
    assert verified_units(got, 3) == 1                    # unit 0 only
    assert verified_units(got, 1) == 6


def test_expectation_is_the_spec_formula() -> None:
    # 200 000 frames: the sampling error of the mean is about 0.002, well inside 0.006
    rnd, p, r, frames = random.Random(5), 0.2, 4, 200_000
    got = [(1, 0, s) for s in range(frames) if rnd.random() > p]
    expect = sum((1 - p) ** j for j in range(1, r + 1)) / r
    assert verified_key_chain(got, r) / frames == pytest.approx(expect, abs=0.006)
    assert verified_units(got, 3) / (frames // 3) == pytest.approx((1 - p) ** 3, abs=0.006)


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_r_or_n_below_one(bad: int) -> None:
    with pytest.raises(ValueError):
        verified_key_chain([], bad)
    with pytest.raises(ValueError):
        verified_units([], bad)


def test_no_double_count_on_repeated_reception() -> None:
    got = list(itertools.repeat((1, 7, 0), 3))
    assert verified_key_chain(got, 2) == 1 and verified_units(got, 1) == 1


def test_a_part_sent_last_unit_does_not_count() -> None:
    # source 7 sent 5 frames one by one, n = 2: units 0 and 1 are whole, unit 2 is half-sent
    got = [(1, 7, s) for s in range(5)]
    assert verified_units(got, 2, {7: 5}) == 2
    assert units_sent({7: 5, 8: 4}, 2) == 2 + 2


def test_completion_time_of_a_unit() -> None:
    got = [(1, 7, 0, 100), (1, 7, 1, 40_100), (1, 7, 2, 80_000), (2, 7, 0, 105)]
    # n = 2: unit 0 complete at receiver 1 (40 000 ns); unit 1 has one frame; receiver 2 one frame
    assert unit_completion_ns(got, 2) == [40_000]
