#!/usr/bin/env python3
"""Phase 3 of the NS-3 3.41 -> 3.48 migration: prove the 802.11 results did not move.

Mohamed's instruction was that 802.11 "should get approx the same results". That is a hypothesis,
not a permission — so this states the tolerance BEFORE looking (Law 6) and compares the frozen 3.41
matrix against a fresh 3.48 run point by point.

WHY A TOLERANCE AT ALL. NS-3 is deterministic per (seed, version), but a simulator release changes
the PHY/MAC state machine: ns-3.48's notes list a "PHY state machine race" fix in WifiPhy, among
others. Identical numbers are therefore NOT expected and would themselves be suspicious. What must
hold is that the *scientific conclusions* survive: the unicast-vs-Bianchi agreement band, and the
broadcast-vs-Ma&Chen agreement band, both of which are reported in the thesis.

ACCEPTANCE (stated in advance):
  * per-point goodput within  +/- 3 %   -- larger differences are investigated individually
  * the unicast<->Bianchi agreement must stay inside its reported +0.6 / -2.9 % band
  * the broadcast<->Ma&Chen agreement must stay inside its reported <= 1.1 % band
A point outside these is a FINDING to explain, never a tolerance to widen (Law 3).
"""

from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

TOL_PCT = 3.0
FROZEN = REPO / "results" / "raw" / "ns3_matrix.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader([ln for ln in path.read_text().splitlines()
                                if not ln.startswith("#")]))


def _key(r: dict[str, str]) -> tuple[str, str]:
    return (r["N"], r["mode"])


def _mean_goodput(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
    acc: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        acc.setdefault(_key(r), []).append(float(r["goodput_mbps"]))
    return {k: st.mean(v) for k, v in acc.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fresh", type=Path, required=True,
                    help="matrix CSV produced by the NEW tree")
    ap.add_argument("--frozen", type=Path, default=FROZEN)
    args = ap.parse_args()

    old = _mean_goodput(_rows(args.frozen))
    new = _mean_goodput(_rows(args.fresh))
    shared = sorted(set(old) & set(new), key=lambda k: (k[1], int(k[0])))
    missing = (set(old) ^ set(new))
    if missing:
        sys.exit(f"!! grid mismatch, refusing to compare: {sorted(missing)}")

    print(f"acceptance: |delta| <= {TOL_PCT:.1f} % per (N, mode), stated before measurement\n")
    print(f"{'mode':<10} {'N':>4} {'3.41 Mb/s':>11} {'3.48 Mb/s':>11} {'delta':>9}")
    worst, breaches = 0.0, []
    for k in shared:
        a, b = old[k], new[k]
        d = 100.0 * (b - a) / a
        worst = max(worst, abs(d))
        flag = ""
        if abs(d) > TOL_PCT:
            breaches.append((k, a, b, d))
            flag = "  <-- OUTSIDE TOLERANCE"
        print(f"{k[1]:<10} {k[0]:>4} {a:>11.5f} {b:>11.5f} {d:>+8.2f}%{flag}")

    print(f"\nworst |delta| = {worst:.2f} %")
    if breaches:
        print("\n!! MIGRATION NOT ACCEPTED — investigate each breach before re-freezing:")
        for (n, mode), a, b, d in breaches:
            print(f"   {mode} N={n}: {a:.5f} -> {b:.5f} ({d:+.2f} %)")
        sys.exit(1)
    print("PASS — every point within tolerance; proceed to re-validate the analytic agreement.")


if __name__ == "__main__":
    main()
