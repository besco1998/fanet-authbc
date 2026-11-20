#!/usr/bin/env python3
"""U-F runs (predictions/UF.md): pilots, 30 seeds around both pilot crossings, then the outlier.

* **Traces** (per-source, per-pair and position files) go to `~/.cache/authbc_uf_traces`, outside
  the repository and outside /tmp, which a restart wipes. The per-run rows go to
  `results/raw/uf_<config>{_pilot,}_runs.csv` through `ns3/run_unified.py`.
* **The two crossings:**
  * **average:** the mean delivered fraction at 0.95;
  * **every-sender:** the seed-mean of each run's worst source's delivered fraction at 0.95.

    python ns3/run_uf.py [workers]
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

from uf import CONFIGS, OUTLIER, n_ref_for, predict  # noqa: E402

from authbc.bench.stats import interpolated_crossing  # noqa: E402

TRACES = Path.home() / ".cache" / "authbc_uf_traces"
RAW = REPO / "results" / "raw"


def drive(cell: str, stem: str, workers: str, *args: str) -> None:
    subprocess.run([sys.executable, str(REPO / "ns3" / "run_unified.py"), "--cells", cell,
                    "--stem", stem, "--trace", str(TRACES), "--trace-opts", "--workers",
                    workers, *args], check=True)


def worst_sender(cell: str, n: int, seed: int) -> float:
    with (TRACES / f"{cell}_n{n}_s{seed}_nodes.csv").open() as fh:
        return min(float(r["delivered_frac"]) for r in csv.DictReader(fh))


def crossings(cell: str, stem: str, seeds: int) -> tuple[float | None, float | None]:
    runs = [r for r in csv.DictReader(ln for ln in (RAW / f"{stem}_runs.csv").open()
                                      if not ln.startswith("#"))]
    by: dict[int, list[dict[str, str]]] = {}
    for r in runs:
        by.setdefault(int(r["n_nodes"]), []).append(r)
    by = {n: v for n, v in by.items() if len(v) >= seeds}
    avg = {n: sum(float(r["delivered_frac"]) for r in v) / len(v) for n, v in by.items()}
    worst = {n: sum(worst_sender(cell, n, int(r["seed"])) for r in v) / len(v)
             for n, v in by.items()}
    return interpolated_crossing(avg, 0.95), interpolated_crossing(worst, 0.95)


def grid(centre: float) -> list[int]:
    c = round(centre)
    step = max(1, round(0.02 * c))
    return [c + k * step for k in range(-3, 4)]


def main() -> int:
    workers = sys.argv[1] if len(sys.argv) > 1 else "8"
    TRACES.mkdir(parents=True, exist_ok=True)
    for c in sorted(CONFIGS, key=lambda c: predict(c, n_ref_for(c))["g23_g25"]):
        p = predict(c, n_ref_for(c))
        drive(c.name, f"uf_{c.name.lower()}_pilot", workers, "--pilot", "--center",
              repr(p["g23_g25"]))
        a, w = crossings(c.name, f"uf_{c.name.lower()}_pilot", 5)
        ns = sorted(set(grid(a if a is not None else p["g23_g25"]))
                    | set(grid(w if w is not None else p["g24_g25"])))
        print(f"{c.name}: pilot crossings average {a}, every-sender {w} -> N {ns}", flush=True)
        drive(c.name, f"uf_{c.name.lower()}", workers, "--n", *map(str, ns), "--seeds", "30")
    n_out = round(predict(OUTLIER, n_ref_for(OUTLIER))["g23_g25"])
    drive("FOUT", "uf_fout", workers, "--n", str(n_out), "--seeds", "30")
    print("all U-F runs done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
