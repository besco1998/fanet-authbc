"""P1's registered placement rule (`analysis/s0_diag.py`): a placement qualifies for a re-gate only
if every sender's sniffer share is at least 0.99."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import s0_diag  # noqa: E402


@pytest.mark.parametrize(("shares", "ok"), [((0.99, 0.995, 1.0), True),
                                            ((0.99, 0.989, 1.0), False),
                                            ((0.948, 0.952, 0.97), False)])
def test_every_sender_must_reach_the_rule(shares: tuple[float, ...], ok: bool) -> None:
    rows = [{"sniffer": v} for v in shares]
    assert s0_diag.placement_verdict(rows) is ok  # type: ignore[arg-type]
