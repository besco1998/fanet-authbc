#!/usr/bin/env python3
"""Run the links scenario at published settings and record the result beside the published run
(`tests/test_links_scenario.py` holds the two equal) — once untraced and once with its links
traced, because a trace must observe the run, not change it (a variable built and then given
its stream took an automatic stream index and shifted every later one; fixed 2026-10-20).

    python analysis/links_identity.py      # results/raw/links_identity.csv
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

import run_links  # noqa: E402

from authbc.bench import provenance  # noqa: E402

CHECKS = (("C", 146, 50.0, 35, 1), ("C", 146, 50.0, 35, 2), ("D", 173, 12.5, 124, 1))


def main() -> None:
    rows = []
    for (cell, fb, fps, n, seed), traced in ((c, t) for c in CHECKS for t in (False, True)):
        got, _ = run_links.run_one(run_links.Cell(f"identity/{cell}", fb, fps), n, seed, traced)
        rows.append({"cell": cell, "n_nodes": n, "seed": seed, "traced": int(traced),
                     "jitter_ms": f"{run_links.one_period_ms(fps):g}",
                     "tx_frames": int(got["tx_frames"]), "rx_frames": int(got["rx_frames"]),
                     "delivered_frac": f"{got['delivered_frac']:g}"})
    buf = io.StringIO()
    config = {"checks": CHECKS, "traced": (0, 1)}
    for k, v in {**provenance.env_block(), "run": "links_identity",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    (REPO / "results" / "raw" / "links_identity.csv").write_text(buf.getvalue())
    print(buf.getvalue())


if __name__ == "__main__":
    main()
