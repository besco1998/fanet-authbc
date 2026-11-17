#!/usr/bin/env python3
"""Gate for the audit twin (task of 2026-11-17, work package B): `authbc-links-audit.cc` at its
defaults must be `authbc-links.cc` — the same output file, byte for byte — and both must equal the
frozen runs on file. Run before any audit run; it writes results/raw/links_audit_identity.csv.

Three cells (802.11a C and D, 802.11b Pb1D, the last through the non-default PHY branch), three
seeds each, the designated source (jitter of one period), 20 simulated seconds.

    python ns3/verify_audit_twin.py
"""
from __future__ import annotations

import csv
import filecmp
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "links_audit_identity.csv"
SEEDS = (1, 2, 3)
# cell: (nodes, frames/s, bytes, jitter ms, standard, mode, stored runs file)
CELLS = {
    "C": (35, 50.0, 146, 20.0, "80211a", "OfdmRate6Mbps", "ns3_nmax_direct_runs.csv"),
    "D": (124, 12.5, 173, 80.0, "80211a", "OfdmRate6Mbps", "ns3_nmax_direct_runs.csv"),
    "Pb1D": (31, 12.5, 173, 80.0, "80211b", "DsssRate1Mbps", "ns3_links_w1b_runs.csv"),
}


def _args(cell: str, seed: int, prefix: Path) -> list[str]:
    n, fps, size, jit, std, mode, _ = CELLS[cell]
    a = [f"--nNodes={n}", f"--framesPerSec={fps!r}", f"--frameSize={size}",
         f"--txJitterMs={jit!r}", "--simTime=20", f"--seed={seed}", f"--outPrefix={prefix}"]
    return a + ([f"--standard={std}", f"--dataMode={mode}"] if std != "80211a" else [])


def _stored(cell: str, seed: int) -> str:
    n, _fps, _size, jit, _std, _mode, runs = CELLS[cell]
    with (RAW / runs).open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if (r["cell"] == cell and int(r["n_nodes"]) == n and int(r["seed"]) == seed
                    and float(r.get("jitter_ms", jit)) == jit):
                return r["delivered_frac"]
    return ""


def main() -> None:
    build = ns3_root() / "build" / "scratch"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for cell in CELLS:
            for seed in SEEDS:
                out = {}
                for which in ("links", "links-audit"):
                    prefix = Path(td) / f"{which}_{cell}_{seed}"
                    exe = build / f"ns3.48-authbc-{which}-optimized"
                    subprocess.run([str(exe), *_args(cell, seed, prefix)], check=True, env=env,
                                   capture_output=True)
                    out[which] = prefix.with_suffix(".csv")
                twin = dict(ln.split(",", 1) for ln in out["links-audit"].read_text().split()
                            if "," in ln)
                rows.append({"cell": cell, "seed": seed,
                             "identical": filecmp.cmp(out["links"], out["links-audit"],
                                                      shallow=False),
                             "delivered_twin": twin["delivered_frac"],
                             "delivered_stored": _stored(cell, seed)})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "links_audit_identity",
                 "config_hash": provenance.config_hash({"cells": str(CELLS),
                                                        "seeds": SEEDS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    good = sum(r["identical"] and r["delivered_twin"] == r["delivered_stored"] for r in rows)
    print(f"wrote {OUT.relative_to(REPO)}: {good}/{len(rows)} identical to the original and the "
          "frozen runs")
    if good != len(rows):
        raise SystemExit("GATE FAILED: the twin at its defaults is not the published one")


if __name__ == "__main__":
    main()
