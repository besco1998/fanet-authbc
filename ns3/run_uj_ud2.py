#!/usr/bin/env python3
"""The runs of U-J and U-D2 (predictions/UJ.md, predictions/UD2.md), as registered, through
`ns3/run_unified.py`:

1. **The pilot:** 5 seeds on the union of seven-count grids at ±5 % steps around each of the cell's
   registered roots (stem `<test>_pilot_<cell>`).
2. **The measurement:** 30 seeds on U-C2's grid around each pilot crossing — the centre is the pilot
   crossing rounded, the step max(1, round(2 % of the centre)), seven counts — the union over the
   cell's levels (stem `<test>_<cell>`).

A pilot that does not cross a level stops the campaign (the registration: nothing is re-gridded to
make a curve cross).

    python ns3/run_uj_ud2.py uj  [--workers 6]
    python ns3/run_uj_ud2.py ud2 [--workers 6]
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "src")]

import ud2  # noqa: E402
import uj  # noqa: E402

RAW = REPO / "results" / "raw"


def roots(test: str) -> dict[str, dict[float, float]]:
    """Per cell, {level: registered root}."""
    out: dict[str, dict[float, float]] = {}
    if test == "uj":
        for r in uj.predictions():
            out[str(r["cell"])] = {0.95: float(str(r["root"]))}
    else:
        for r in ud2.predictions():
            out.setdefault(str(r["cell"]), {})[round(1 - float(str(r["eps"])), 2)] = float(
                str(r["g25_root"])
            )
    return out


def pilot_counts(rs: list[float]) -> list[int]:
    return sorted({max(2, round(r * (1 + 0.05 * k))) for r in rs for k in range(-3, 4)})


def uc2_counts(centres: list[float]) -> list[int]:
    out: set[int] = set()
    for x in centres:
        c = round(x)
        step = max(1, round(0.02 * c))
        out |= {max(2, c + k * step) for k in range(-3, 4)}
    return sorted(out)


def run(cell: str, counts: list[int], seeds: int, stem: str, levels: list[float], workers: int):
    cmd = [
        sys.executable,
        str(REPO / "ns3" / "run_unified.py"),
        "--cells",
        cell,
        "--n",
        *map(str, counts),
        "--seeds",
        str(seeds),
        "--stem",
        stem,
        "--levels",
        *map(str, levels),
        "--workers",
        str(workers),
    ]
    print(" ".join(cmd[1:]), flush=True)
    subprocess.run(cmd, check=True)


def crossings(stem: str) -> dict[float, float]:
    lines = [ln for ln in (RAW / f"{stem}.csv").read_text().splitlines() if not ln.startswith("#")]
    return {
        float(r["n_nodes"].split("@")[1]): float(r["delivered_mean"])
        for r in csv.DictReader(lines)
        if r["n_nodes"].startswith("CROSSING@") and r["delivered_mean"] not in ("", "nan")
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("test", choices=("uj", "ud2"))
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    for cell, by_level in roots(args.test).items():
        levels = sorted(by_level)
        pstem = f"{args.test}_pilot_{cell.lower()}"
        run(cell, pilot_counts(list(by_level.values())), 5, pstem, levels, args.workers)
        got = crossings(pstem)
        missing = [lv for lv in levels if lv not in got]
        if missing:
            raise SystemExit(f"STOP: the pilot of {cell} does not cross {missing}")
        run(
            cell,
            uc2_counts([got[lv] for lv in levels]),
            30,
            f"{args.test}_{cell.lower()}",
            levels,
            args.workers,
        )


if __name__ == "__main__":
    main()
