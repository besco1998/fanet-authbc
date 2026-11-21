#!/usr/bin/env python3
"""U-F2 runs (predictions/UF2.md), in the registered order.

1. **(a) and statistic 2,** per configuration: a pilot of 5 seeds (31–35) on seven node counts at
   ±5 % steps around the (G23)/(G22a) root; then 30 seeds (31–60) on the node counts of U-C2's
   rule around both pilot crossings, the average and the per-run worst sender, as U-F did. 20 s
   runs, the per-node files kept in `~/.cache/authbc_uf2_traces`.
2. **Statistic 1,** per configuration: at each node count of the registered grid, the placement
   of seed 61 written once (`--placementOnly`) and read by every run (`--positionsFile`); 30 run
   seeds (31–60) of the registered length; each run's per-node delivery appended to
   `results/raw/uf2_pooled_<config>_runs.csv`. Resumable.

    python ns3/run_uf2.py [workers]
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

import run_unified as ru  # noqa: E402
import uf2  # noqa: E402
from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402

RAW = REPO / "results" / "raw"


def drive(cell: str, stem: str, workers: str, *args: str) -> None:
    subprocess.run([sys.executable, str(REPO / "ns3" / "run_unified.py"), "--cells", cell,
                    "--stem", stem, "--trace", str(uf2.TRACES), "--trace-opts", "--workers",
                    workers, "--first-seed", str(uf2.SEEDS[0]), *args], check=True)


def pilot_crossings(name: str, stem: str) -> tuple[float | None, float | None]:
    by: dict[int, list[dict[str, str]]] = {}
    with (RAW / f"{stem}_runs.csv").open() as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            by.setdefault(int(r["n_nodes"]), []).append(r)
    avg = {n: sum(float(r["delivered_frac"]) for r in v) / len(v) for n, v in by.items()}
    worst = {n: sum(uf2.worst_of_run(name, n, int(r["seed"])) for r in v) / len(v)
             for n, v in by.items()}
    return interpolated_crossing(avg, 0.95), interpolated_crossing(worst, 0.95)


def grid(centre: float) -> list[int]:
    c = round(centre)
    step = max(1, round(0.02 * c))
    return [c + k * step for k in range(-3, 4)]


def _exe() -> tuple[str, dict[str, str]]:
    return (str(ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"),
            {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")})


def placement(c: uf2.UF2Config, n: int) -> Path:
    """The fixed placement of seed 61 at N = n, written once."""
    out = uf2.TRACES / "placements" / f"{c.name}_n{n}"
    path = Path(f"{out}_positions.csv")
    if not path.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        exe, env = _exe()
        ru.run_checked([exe, f"--nNodes={n}", f"--seed={uf2.PLACEMENT_SEED}",
                        f"--radiusM={c.radius_m}", "--pathLossExp=2", "--placementOnly=1",
                        f"--outPrefix={out}"], env)
    return path


def pooled_run(c: uf2.UF2Config, n: int, seed: int, run_s: float, pos: Path) -> list[dict]:
    exe, env = _exe()
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "p"
        ru.run_checked([exe, f"--nNodes={n}", f"--simTime={run_s}", f"--seed={seed}",
                        f"--outPrefix={pre}", *ru.CELLS[c.name].args(),
                        f"--positionsFile={pos}"], env)
        with Path(f"{pre}_nodes.csv").open() as fh:
            return [{"config": c.name, "n_nodes": n, "seed": seed, "node": r["node"],
                     "tx_frames": r["tx_frames"], "delivered_frac": r["delivered_frac"]}
                    for r in csv.DictReader(fh)]


def run_pooled(c: uf2.UF2Config, reg: dict[str, str], workers: int) -> None:
    path = RAW / f"uf2_pooled_{c.name.lower()}_runs.csv"
    done = set()
    if path.exists():
        with path.open() as fh:
            done = {(int(r["n_nodes"]), int(r["seed"])) for r in
                    csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    ns = [int(x) for x in reg["pooled_grid"].split()]
    run_s = float(reg["pooled_run_s"])
    todo = [(n, s) for n in ns for s in uf2.SEEDS if (n, s) not in done]
    pos = {n: placement(c, n) for n in ns}
    fields = ["config", "n_nodes", "seed", "node", "tx_frames", "delivered_frac"]
    if not path.exists():
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": f"uf2_pooled_{c.name.lower()}",
                     "run_s": run_s, "placement_seed": uf2.PLACEMENT_SEED}.items():
            buf.write(f"# {k}={v}\n")
        buf.write(",".join(fields) + "\n")
        path.write_text(buf.getvalue())
    print(f"{c.name}: pooled, {len(todo)} runs of {run_s:g} s to do", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(pooled_run, c, n, s, run_s, pos[n]) for n, s in todo]
        for k, f in enumerate(as_completed(futs), 1):
            with path.open("a") as fh:
                w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
                w.writerows(f.result())
            if k % 10 == 0 or k == len(futs):
                print(f"  {k}/{len(futs)} done", flush=True)


def main() -> int:
    workers = sys.argv[1] if len(sys.argv) > 1 else "10"
    uf2.TRACES.mkdir(parents=True, exist_ok=True)
    reg = uf2.registered()
    for c in uf2.CONFIGS:
        r = reg[c.name]
        drive(c.name, f"uf2_{c.name.lower()}_pilot", workers, "--pilot", "--center",
              r["g23_g22a_g25"])
        a, w = pilot_crossings(c.name, f"uf2_{c.name.lower()}_pilot")
        ns = sorted(set(grid(a if a is not None else float(r["g23_g22a_g25"])))
                    | set(grid(w if w is not None else float(r["g24a_root"]))))
        print(f"{c.name}: pilot crossings average {a}, worst {w} -> N {ns}", flush=True)
        drive(c.name, f"uf2_{c.name.lower()}", workers, "--n", *map(str, ns), "--seeds", "30")
    for c in sorted(uf2.CONFIGS, key=lambda c: c.standard != "80211a"):
        run_pooled(c, reg[c.name], int(workers))
    print("all U-F2 runs done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
