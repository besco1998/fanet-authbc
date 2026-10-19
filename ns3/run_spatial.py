#!/usr/bin/env python3
"""Runs of the spatial scenario (revision A1; `ns3/authbc-spatial.cc`, `predictions/A1.md`).

A plan file names the runs, one line each:

    <scenario> <config> <N> [<N> ...]

`scenario` is a key of SCENARIOS (layout and its geometry), `config` a key of CONFIGS (the
frame and its rate; the three lean rungs the plan asks for). Every (scenario, config, N) runs
`--seeds` seeds numbered from 1. Results go to `results/raw/ns3_spatial_<stem>_runs.csv`, one
row per run, written by this one process with a checkpoint every 30 runs; a second invocation
skips what is on file. The d_ref sweep is a plan of its own over the `pair` layout.

    python ns3/run_spatial.py --plan experiments/spatial/<plan>.txt --stem <stem> --workers 12
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"


@dataclass(frozen=True)
class Config:
    """A frame on air and its rate: ladder rows 5, 6 and 8 at the adopted point."""

    label: str
    frame_bytes: int
    frames_per_s: float


CONFIGS: dict[str, Config] = {
    "base": Config("lean/inline-1 (row 5)", 146, 50.0),
    "inline4": Config("lean/inline-b (row 6)", 372, 12.5),
    "design": Config("lean/batch-delta (row 8)", 173, 12.5),
}

# d_ref is filled in once the pair sweep has measured it (predictions/A1.md records the value
# and the commit). The scenarios below that need it read it from here.
D_REF_M: float = 0.0


@dataclass(frozen=True)
class Scenario:
    layout: str
    args: tuple[tuple[str, str], ...] = ()


def scenarios(d_ref: float) -> dict[str, Scenario]:
    """Every scenario of A1, with the neighbour distance passed to the ones that count it."""
    ref = (("dRefM", f"{d_ref:g}"),)
    out = {
        "fixed": Scenario("point"),                       # must reproduce the published crossings
        "s3-v0": Scenario("group", ref + (("speedMps", "0"),)),
        "s3-v5": Scenario("group", ref + (("speedMps", "5"),)),
        "s3-v15": Scenario("group", ref + (("speedMps", "15"),)),
        "s2": Scenario("clusters", ref + (("separationM", f"{2 * d_ref:g}"),
                                          ("clusterRadiusM", "20"), ("pairs", "1"))),
    }
    for r in (100, 300, 600, 1000):
        out[f"s1-r{r}"] = Scenario("disc", ref + (("radiusM", str(r)),))
    for d in range(150, 405, 5):                          # the isolated link, for d_ref
        out[f"pair-{d}"] = Scenario("pair", (("pairDistanceM", str(d)),))
    return out


def binary() -> tuple[Path, Path]:
    root = ns3_root()
    return root, root / "build" / "scratch" / "ns3.48-authbc-spatial-optimized"


def run_one(scenario: Scenario, cfg: Config, n: int, seed: int, sim_time: float
            ) -> tuple[dict[str, float], str]:
    """One run: the scenario's key/value summary, and its per-pair file if it wrote one."""
    root, exe = binary()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "s"
        args = [f"--layout={scenario.layout}", f"--nNodes={n}",
                f"--frameSize={cfg.frame_bytes}", f"--framesPerSec={cfg.frames_per_s!r}",
                f"--simTime={sim_time!r}", f"--seed={seed}", f"--outPrefix={prefix}",
                *(f"--{k}={v}" for k, v in scenario.args)]
        subprocess.run([str(exe), *args], cwd=root, check=True,
                       env={**os.environ, "LD_LIBRARY_PATH": str(root / "build" / "lib")},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
        pairs = Path(f"{prefix}_pairs.csv")
        pair_text = pairs.read_text() if pairs.exists() else ""
    return {k: float(v) for k, v in rows.items()}, pair_text


def read_plan(path: Path, known: dict[str, Scenario]) -> list[tuple[str, str, list[int]]]:
    plan = []
    for line in path.read_text().splitlines():
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        scen, cfg, *ns = fields
        if scen not in known or cfg not in CONFIGS or not ns:
            raise SystemExit(f"bad plan line: {line!r}")
        plan.append((scen, cfg, [int(x) for x in ns]))
    return plan


def read_runs(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def _key(r: dict[str, str]) -> tuple[str, str, int, int]:
    return r["scenario"], r["config"], int(r["n_nodes"]), int(r["seed"])


def write(path: Path, rows: list[dict], run: str, config: dict) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--stem", required=True)
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--sim-time", type=float, default=20.0)
    ap.add_argument("--d-ref", type=float, default=D_REF_M,
                    help="neighbour distance in m (the measured d_ref)")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    known = scenarios(args.d_ref)
    plan = read_plan(args.plan, known)
    needs_ref = any(dict(known[s].args).get("dRefM") for s, _, _ in plan)
    if needs_ref and args.d_ref <= 0:
        raise SystemExit("this plan counts neighbours: give the measured --d-ref")
    path = RAW / f"ns3_spatial_{args.stem}_runs.csv"
    pair_dir = RAW / f"ns3_spatial_{args.stem}_pairs"
    runs = read_runs(path)
    done = {_key(r) for r in runs}
    todo = [(s, c, n, seed) for s, c, ns in plan for n in ns
            for seed in range(1, args.seeds + 1) if (s, c, n, seed) not in done]
    print(f"{len(runs)} runs on file, {len(todo)} to do, {args.workers} at a time", flush=True)
    config = {"seeds": args.seeds, "t": args.sim_time, "d_ref": args.d_ref,
              "configs": {k: asdict(v) for k, v in CONFIGS.items()},
              "scenarios": {s: asdict(known[s]) for s, _, _ in plan}}

    def job(t: tuple[str, str, int, int]) -> dict:
        scen, cfg, n, seed = t
        got, pairs = run_one(known[scen], CONFIGS[cfg], n, seed, args.sim_time)
        if pairs:
            pair_dir.mkdir(exist_ok=True)
            (pair_dir / f"{scen}.{cfg}.{n}.{seed}.csv").write_text(pairs)
        return {"scenario": scen, "config": cfg, "frame_bytes": CONFIGS[cfg].frame_bytes,
                "frames_per_s": CONFIGS[cfg].frames_per_s, "n_nodes": n, "seed": seed,
                **{k: (int(v) if v.is_integer() else v) for k, v in got.items()
                   if k not in ("nNodes", "frameSize", "framesPerSec", "seed")}}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(job, todo), 1):
            runs.append({k: str(v) for k, v in row.items()})
            if i % 30 == 0 or i == len(todo):
                runs.sort(key=_key)
                write(path, runs, f"ns3_spatial_{args.stem}_runs", config)
                print(f"  {i}/{len(todo)} done", flush=True)


if __name__ == "__main__":
    main()
