"""The links scenario reproduces the published one at its defaults (revision A10, A11).

`ns3/authbc-links.cc` is `authbc-delay.cc` with three options absent by default. ns-3 does not
run in CI, so the check is recorded: `results/raw/links_identity.csv` holds runs of the links
binary at published settings, and each must equal, in every reported digit, the published run
of the same cell, node count and seed.
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def test_every_recorded_identity_run_equals_the_published_run() -> None:
    published = {(r["cell"], r["n_nodes"], r["seed"], r["jitter_ms"]): r
                 for r in _rows(RAW / "ns3_nmax_direct_runs.csv")}
    checks = _rows(RAW / "links_identity.csv")
    assert len(checks) >= 3
    for c in checks:
        p = published[(c["cell"], c["n_nodes"], c["seed"], c["jitter_ms"])]
        for field in ("tx_frames", "rx_frames", "delivered_frac"):
            assert c[field] == p[field], (c, field)


def test_the_check_covers_both_published_frames() -> None:
    assert {c["cell"] for c in _rows(RAW / "links_identity.csv")} >= {"C", "D"}


def test_a_traced_run_is_the_untraced_run() -> None:
    # tracing once moved the random streams (2026-10-20): every check is made both ways
    checks = _rows(RAW / "links_identity.csv")
    assert {(c["cell"], c["seed"]) for c in checks if c["traced"] == "1"} == {
        (c["cell"], c["seed"]) for c in checks if c["traced"] == "0"}
