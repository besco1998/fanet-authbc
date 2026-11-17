"""The audit twin `ns3/authbc-links-audit.cc` (task of 2026-11-17, work package B).

Held here, without NS-3:
* the twin only ADDS lines: every line of `authbc-links.cc` appears in it, in order, except the log
  component's name — so its default path is the published code;
* every trace it adds sits behind an option that is off by default;
* the recorded gate (`ns3/verify_audit_twin.py`) found its default output byte-identical to the
  original's and to the frozen runs, for every cell and seed it ran.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ORIG = (REPO / "ns3" / "authbc-links.cc").read_text().splitlines()
TWIN = (REPO / "ns3" / "authbc-links-audit.cc").read_text().splitlines()


def test_the_twin_only_adds_lines() -> None:
    renamed = 'NS_LOG_COMPONENT_DEFINE("AuthbcLinks");'
    it = iter(TWIN)
    for line in ORIG:
        if line == renamed:
            continue
        assert any(t == line for t in it), f"missing or out of order: {line!r}"


def test_every_added_trace_is_off_by_default() -> None:
    text = "\n".join(TWIN)
    defaults = {"traceMac": "false", "traceRx": "0", "traceStateNode": "-1",
                "traceAllRx": "false", "constants": "false"}
    for name, value in defaults.items():
        assert re.search(rf"\b{name} = {re.escape(value)};", text), name


def test_the_gate_held_for_every_run() -> None:
    with (REPO / "results" / "raw" / "links_audit_identity.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    assert len(rows) == 9
    assert all(r["identical"] == "True" for r in rows)
    assert all(r["delivered_twin"] == r["delivered_stored"] != "" for r in rows)
