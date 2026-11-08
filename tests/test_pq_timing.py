"""The A15 timing reducer reads speed_sig's tables (analysis/pq_timing.py).

A first version credited the `--info` run that follows the last repetition to the last
algorithm (ML-DSA-44 showed four repetitions, one of them Falcon's): a repetition ends at its
"Ended at" line.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("pq_timing", REPO / "analysis" / "pq_timing.py")
assert _spec and _spec.loader
pq = importlib.util.module_from_spec(_spec)
sys.modules["pq_timing"] = pq
_spec.loader.exec_module(pq)


def _table(sign_us: float) -> str:
    return ("Configuration info\nStarted at x\n"
            "Operation | Iterations | Total | Time (us): mean |\n"
            f"keypair | 10 | 10.0 | 4600.0 | 1\nsign | 10 | 10.0 | {sign_us} | 1\n"
            f"verify | 10 | 10.0 | 28.0 | 1\nEnded at y\n")


def test_repetitions_are_counted_and_the_info_run_is_not() -> None:
    log = ("## rep 1 Falcon-512\n" + _table(150.0) + "## rep 1 ML-DSA-44\n" + _table(58.0)
           + "## rep 2 Falcon-512\n" + _table(160.0) + "## rep 2 ML-DSA-44\n" + _table(60.0)
           + _table(999.0))                                       # the --info run
    parsed = pq.parse(log)
    assert parsed[("Falcon-512", "sign")] == [150.0, 160.0]
    assert parsed[("ML-DSA-44", "sign")] == [58.0, 60.0]
    rows = {(r["alg"], r["op"]): r for r in pq.rows_of(parsed)}
    assert rows[("ML-DSA-44", "sign")]["reps"] == 2
    verify = rows[("Falcon-512", "verify")]
    assert verify["core_share_at_design_rate"] == round(28.0 * 1550 / 1e6, 5)
