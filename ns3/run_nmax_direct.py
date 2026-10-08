#!/usr/bin/env python3
"""Direct search for the 802.11 N_max at V >= 0.95, with a bootstrap interval (review 4.8).

Every other 802.11 capacity figure at this threshold applies ONE load ceiling (U = 2.435), measured
at N = 50 with a 288 B frame, to every configuration. This driver does not use that ceiling at all:
it simulates each configuration at its own frame size and frame rate over a grid of N, and reads
the crossing off the simulated delivery — the treatment the LoRa arm has had since F28.

Predictions and the decision rule were committed before the first run, and each later stage's
before its own runs: `docs/NMAX_DIRECT_EXPECTATIONS.md`.

Writes two files:
  results/raw/ns3_nmax_direct_runs.csv   one row per (cell, source, N, seed) — raw simulator output
  results/raw/ns3_nmax_direct.csv        per-(cell, source, N) dispersion, then one CROSSING row
                                         per (cell, source); a source is (jitter, rate offset)

The summary is a pure function of the runs file (`summarise`), so it can be rebuilt and checked on
a machine without NS-3: `--summarise-only`, and `tests/test_nmax_direct.py`.

Runs are launched as the built scenario binary, several at a time. `--verify` first checks that
launching the binary directly returns exactly what the documented `./ns3 run` entry returns.
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import (  # noqa: E402
    crossing_point,
    interpolated_crossing,
    interpolated_crossing_ci,
    threshold_crossing_ci,
)
from authbc.models import bianchi, optimizer  # noqa: E402

RAW = REPO / "results" / "raw"
V_TARGET = 0.95
PER_RUN_SHARE = 0.95          # per-run criterion: this share of runs must individually meet V
BOOTSTRAP_SEED = 12345


@dataclass(frozen=True)
class Cell:
    """One configuration: what is put on air, how often, and what the single ceiling predicts."""

    label: str
    frame_bytes: int      # results/raw/design_ladder.csv, rounded to the whole byte ns-3 needs
    batch: int            # records per frame
    lam: float            # records/s per node
    model_n: int          # N_max by the load ceiling U <= 2.435 (design_ladder.csv, n_max_v95)

    @property
    def fps(self) -> float:
        return self.lam / self.batch


CELLS: dict[str, Cell] = {
    # --- adopted operating point (50 rec/s, 100 ms): the six cells registered before any run ---
    "A": Cell("first/inline-1", 174, 1, 50.0, 31),
    "B": Cell("first/batch-delta", 300, 4, 50.0, 97),
    "C": Cell("lean/inline-1", 146, 1, 50.0, 34),
    "D": Cell("lean/batch-delta", 173, 4, 50.0, 142),
    "E": Cell("first/inline-b", 565, 4, 50.0, 49),
    "F": Cell("lean/inline-b", 372, 4, 50.0, 80),
    # --- adopted point, the rungs stage 1 left out (held out: predicted before they were run) ---
    "G": Cell("first/batch-cbor", 373, 4, 50.0, 79),
    "H": Cell("lean/batch-keys", 218, 4, 50.0, 123),
    "I": Cell("first/batch-delta-published", 288, 4, 50.0, 100),
    # --- relaxed operating point (20 rec/s, 250 ms), also held out ---
    "RA": Cell("first/inline-1", 174, 1, 20.0, 88),
    "RB": Cell("first/batch-delta", 300, 4, 20.0, 208),
    "RC": Cell("lean/inline-1", 146, 1, 20.0, 101),
    "RD": Cell("lean/batch-delta", 173, 4, 20.0, 269),
    "RE": Cell("first/inline-b", 565, 4, 20.0, 140),
    "RF": Cell("lean/inline-b", 372, 4, 20.0, 185),
    "RG": Cell("first/batch-cbor", 373, 4, 20.0, 184),
    "RH": Cell("lean/batch-keys", 218, 4, 20.0, 243),
    "RI": Cell("first/batch-delta-published", 288, 4, 20.0, 213),
    # --- the classical stream-signing schemes of results/raw/stream_baselines.csv: the lean
    #     one-record frame with each scheme's authenticator, one frame per record (follow-up F3).
    #     EMSS adds one signature packet per hundred, simulated as 50.5 frames/s of one size. ---
    "SM": Cell("stream/mavlink2", 94, 1, 50.0, 44),
    "ST": Cell("stream/tesla", 106, 1, 50.0, 41),
    "SG": Cell("stream/gennaro-rohatgi", 114, 1, 50.0, 39),
    "SE": Cell("stream/emss", 146, 1, 50.5, 34),
    "SW": Cell("stream/wong-lam-tree", 211, 1, 50.0, 28),
}


def default_grid(model_n: int) -> list[int]:
    """Six node counts spanning roughly ±20 % of the model's value."""
    step = max(1, round(model_n * 0.08))
    return [model_n + k * step for k in (-3, -2, -1, 0, 1, 2)]


def one_period_ms(fps: float) -> float:
    """One sending period in ms, as the scenario's own guard will accept it.

    The scenario aborts if ``txJitterMs * 1e-3 > 1.0 / framesPerSec``. For some rates the two
    sides of that comparison round differently and 1000/fps fails it by one unit in the last
    place (116 frames/s was the first found, on 2026-10-09: the run stopped with SIGABRT). The
    jitter is stepped down until the guard holds, which for every rate used before that date
    changes nothing.
    """
    period = 1000.0 / fps
    while period * 1e-3 > 1.0 / fps:
        period = math.nextafter(period, 0.0)
    return period


def source_of(spec: str, fps: float) -> tuple[float, float]:
    """A traffic-source spec as (jitter in ms, rate offset in ppm).

    ``J`` or ``J/S``. J is the per-frame send jitter: a number of milliseconds, or ``period`` for
    one full sending period; 0 is the published strictly periodic source. S, if given, offsets
    each node's rate by up to ±S ppm so that relative phases sweep during the run.
    """
    jitter, _, skew = spec.partition("/")
    return (one_period_ms(fps) if jitter == "period" else float(jitter)), float(skew or 0.0)


def read_plan(path: Path) -> list[tuple[str, str, list[int]]]:
    """A run plan: one `cell source n1 n2 ...` per line (source as `--source`); `#` comments.

    One process then holds every result in memory from start to finish, so a long campaign is
    written by a single writer and cannot lose rows to a second invocation re-reading a file
    that something else (a commit hook stashing the working tree) had momentarily reverted.
    """
    plan = []
    for line in path.read_text().splitlines():
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        cell, source, *ns = fields
        if cell not in CELLS or not ns:
            raise SystemExit(f"bad plan line: {line!r}")
        plan.append((cell, source, [int(n) for n in ns]))
    return plan


def plan_of(runs: list[dict]) -> list[tuple[str, str, list[int]]]:
    """The plan that reproduces a runs file: every (cell, source) on file with its node counts.

    Runs are independent and seeded by (cell, N, seed), so the order they were made in is not
    part of the result; this is the whole of what has to be kept to run the campaign again.
    """
    points: dict[tuple[int, float, float], set[int]] = {}
    for r in runs:
        _, jitter, skew, n, _ = _run_key(r)
        points.setdefault((list(CELLS).index(r["cell"]), jitter, skew), set()).add(n)
    plan = []
    for (cell_index, jitter, skew), ns in sorted(points.items()):
        cell = list(CELLS)[cell_index]
        one_period = provenance.as_written(1000.0 / CELLS[cell].fps)
        spec = "period" if jitter == one_period else f"{jitter:g}"
        plan.append((cell, spec + (f"/{skew:g}" if skew else ""), sorted(ns)))
    return plan


def render_plan(plan: list[tuple[str, str, list[int]]]) -> str:
    """A plan as the text `read_plan` reads."""
    head = ("# Every node count simulated for results/raw/ns3_nmax_direct_runs.csv, 30 seeds.\n"
            "# cell  source  N ...   source: send jitter in ms (`period` = one sending period),\n"
            "#                       then /S for a rate offset of up to ±S ppm; 0 = strictly\n"
            "#                       periodic.\n"
            "# Written by `run_nmax_direct.py --write-plan`; the registrations that decided each\n"
            "# stage are in docs/NMAX_DIRECT_EXPECTATIONS.md.\n")
    return head + "".join(f"{cell} {spec} {' '.join(map(str, ns))}\n" for cell, spec, ns in plan)


def _binary() -> tuple[Path, Path]:
    root = ns3_root()
    return root, root / "build" / "scratch" / "ns3.48-authbc-delay-optimized"


def scenario_args(frame_bytes: int, fps: float, n_nodes: int, seed: int, sim_time: float,
                  prefix: Path, *, jitter_ms: float = 0.0, skew_ppm: float = 0.0,
                  cw_min: int = 0) -> list[str]:
    """Command-line arguments of one run. An option at its default is left out, so the
    published scenario is invoked exactly as it always was."""
    args = [f"--nNodes={n_nodes}", f"--framesPerSec={fps}", f"--frameSize={frame_bytes}",
            f"--simTime={sim_time}", f"--seed={seed}", f"--outPrefix={prefix}"]
    if jitter_ms > 0.0:
        args.append(f"--txJitterMs={jitter_ms!r}")
    if skew_ppm > 0.0:
        args.append(f"--txSkewPpm={skew_ppm!r}")
    if cw_min > 0:
        args.append(f"--cwMin={cw_min}")
    return args


def run_one(frame_bytes: int, fps: float, n_nodes: int, seed: int, sim_time: float,
            *, jitter_ms: float = 0.0, skew_ppm: float = 0.0, cw_min: int = 0,
            via_ns3: bool = False) -> dict[str, float]:
    root, binary = _binary()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "d"
        args = scenario_args(frame_bytes, fps, n_nodes, seed, sim_time, prefix,
                             jitter_ms=jitter_ms, skew_ppm=skew_ppm, cw_min=cw_min)
        if via_ns3:
            cmd = ["./ns3", "run", "authbc-delay " + " ".join(args)]
            env = None
        else:
            cmd = [str(binary), *args]
            env = {**os.environ, "LD_LIBRARY_PATH": str(root / "build" / "lib")}
        subprocess.run(cmd, cwd=root, check=True, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    return {k: float(v) for k, v in rows.items()}


def verify(sim_time: float) -> None:
    """The directly-launched binary must return exactly what `./ns3 run` returns."""
    a = run_one(288, 12.5, 20, 1, sim_time, via_ns3=True)
    b = run_one(288, 12.5, 20, 1, sim_time, via_ns3=False)
    if a != b:
        raise SystemExit(f"VERIFY FAILED: ./ns3 run and the binary disagree\n  {a}\n  {b}")
    c = run_one(288, 12.5, 20, 1, sim_time, via_ns3=False)
    if b != c:
        raise SystemExit("VERIFY FAILED: the same seed gave two different results")
    print(f"verify: ./ns3 run == direct binary == repeat (delivered {b['delivered_frac']})")


def read_runs(path: Path) -> list[dict[str, str]]:
    """The raw runs. Rows written before a source option existed did not use it: it reads as 0."""
    if not path.exists():
        return []
    rows = list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))
    for r in rows:
        r["jitter_ms"] = r.get("jitter_ms") or "0"
        r["skew_ppm"] = r.get("skew_ppm") or "0"
    return rows


def _run_key(r: dict[str, str]) -> tuple[str, float, float, int, int]:
    return (r["cell"], float(r["jitter_ms"]), float(r["skew_ppm"]), int(r["n_nodes"]),
            int(r["seed"]))


def pending(plan: list[tuple[str, str, list[int]]], done: set[tuple], seeds: int,
            first_seed: int = 1) -> list[tuple[str, float, float, int, int]]:
    """The runs a plan still needs, as (cell, jitter, rate offset, N, seed); `done` is updated.

    Seeds run from `first_seed`; a range that starts above the reported sample's is a fresh
    sample. Runs on file are keyed by the jitter as it was written, not as computed (F56).
    """
    todo = []
    for cell, spec, ns in plan:
        jitter, skew = source_of(spec, CELLS[cell].fps)
        for n in ns:
            for seed in range(first_seed, first_seed + seeds):
                filed = (cell, provenance.as_written(jitter), provenance.as_written(skew),
                         n, seed)
                if filed not in done:
                    todo.append((cell, jitter, skew, n, seed))
                    done.add(filed)                   # a plan may name a point twice
    return todo


def _write(path: Path, rows: list[dict], run: str, config: dict) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def _per_run_crossing(per_n: dict[int, list[float]]) -> int:
    """Largest N at which PER_RUN_SHARE of the runs individually meet V, same first-failure rule."""
    share = {n: sum(x >= V_TARGET for x in v) / len(v) for n, v in per_n.items()}
    return crossing_point(share, PER_RUN_SHARE)


def summarise(runs: list[dict[str, str]], seeds: int) -> list[dict]:
    """Per-(cell, source, N) dispersion rows, then one CROSSING row per (cell, source).

    A source is a (jitter, rate offset) pair. A node count enters only once all ``seeds`` runs
    are on file, so a half-finished sweep can be summarised without a short sample being compared
    against the threshold.
    """
    groups: dict[tuple[str, float, float], dict[int, list[float]]] = {}
    for r in runs:
        cell, jitter, skew, n, _ = _run_key(r)
        groups.setdefault((cell, jitter, skew), {}).setdefault(n, []).append(
            float(r["delivered_frac"]))
    out: list[dict] = []
    for cell, jitter, skew in sorted(groups, key=lambda k: (list(CELLS).index(k[0]), *k[1:])):
        c = CELLS[cell]
        per_n = {n: v for n, v in groups[(cell, jitter, skew)].items() if len(v) == seeds}
        if not per_n:
            continue
        head = {"cell": cell, "config": c.label, "frame_bytes": c.frame_bytes, "batch": c.batch,
                "lambda_rec_per_s": c.lam, "jitter_ms": f"{jitter:g}", "skew_ppm": f"{skew:g}"}
        frame_s = bianchi.t_broadcast(c.frame_bytes)
        for n in sorted(per_n):
            v = per_n[n]
            out.append({
                **head, "n_nodes": n, "delivered_mean": round(mean(v), 5),
                "delivered_min": round(min(v), 5), "delivered_max": round(max(v), 5),
                "delivered_stdev": round(stdev(v), 5),
                "seeds_failing_v": sum(x < V_TARGET for x in v), "seeds": len(v),
                "model_util": round(
                    optimizer.channel_utilisation(n, c.lam, c.batch, c.frame_bytes), 4),
                "airtime_occupancy": round(n * c.fps * frame_s, 4),
            })
        means = {n: mean(v) for n, v in per_n.items()}
        grid = sorted(per_n)
        n_max = crossing_point(means, V_TARGET)
        ci = threshold_crossing_ci(per_n, threshold=V_TARGET, seed=BOOTSTRAP_SEED)
        interp = interpolated_crossing(means, V_TARGET)
        interp_ci = interpolated_crossing_ci(per_n, threshold=V_TARGET, seed=BOOTSTRAP_SEED)
        row = {
            **head, "n_nodes": "CROSSING", "seeds": seeds,
            # the estimate is the SAMPLE's crossing; the bootstrap supplies only the interval
            "n_max_mean": n_max, "n_max_ci_lo": ci.ci_lo, "n_max_ci_hi": ci.ci_hi,
            "n_max_per_run": _per_run_crossing(per_n), "model_n_max": c.model_n,
            "deviation_pct": round(100.0 * (n_max - c.model_n) / c.model_n, 1),
            "grid": " ".join(map(str, grid)),
            "bracketed": int(grid[0] <= n_max < grid[-1]),
        }
        if interp is not None and interp_ci is not None:
            row |= {"n_cross_interp": round(interp, 2),
                    "n_cross_interp_lo": round(interp_ci[0], 2),
                    "n_cross_interp_hi": round(interp_ci[1], 2),
                    "interp_share_bracketed": round(interp_ci[2], 4),
                    "deviation_interp_pct": round(100.0 * (interp - c.model_n) / c.model_n, 1)}
        out.append(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path,
                    help="file of `cell source n1 n2 ...` lines, run in order by this one process")
    ap.add_argument("--cells", nargs="+", default=list("ABCDEF"), choices=list(CELLS))
    ap.add_argument("--n", type=int, nargs="+",
                    help="explicit node counts (one cell only); default: a grid round the model")
    ap.add_argument("--source", default="0",
                    help="traffic source as J or J/S: per-frame jitter J in ms (or 'period'), "
                         "optional rate offset S in ppm; 0 = the published strictly periodic "
                         "source (default)")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--first-seed", type=int, default=1,
                    help="number of the first seed (default 1); a later range is a fresh sample")
    ap.add_argument("--out-stem", default="ns3_nmax_direct",
                    help="results/raw/<stem>_runs.csv and <stem>.csv. A fresh-seed campaign "
                         "takes its own stem, so that every reported point keeps exactly "
                         "--seeds runs, numbered from 1")
    ap.add_argument("--cw-min", type=int, default=0,
                    help="minimum contention window given to the scenario (0 = the standard's, "
                         "the default). Needs its own --out-stem: one file, one window")
    ap.add_argument("--no-summary", action="store_true",
                    help="write the runs only (for a campaign whose analysis is its own script)")
    ap.add_argument("--sim-time", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--verify", action="store_true", help="check binary == ./ns3 run, then exit")
    ap.add_argument("--summarise-only", action="store_true")
    ap.add_argument("--write-plan", type=Path,
                    help="write the plan that reproduces the runs on file, then exit")
    args = ap.parse_args()
    if args.verify:
        verify(args.sim_time)
        return
    if args.write_plan:
        runs_on_file = read_runs(RAW / f"{args.out_stem}_runs.csv")
        args.write_plan.write_text(render_plan(plan_of(runs_on_file)))
        return
    if args.n and len(args.cells) != 1:
        raise SystemExit("--n applies to exactly one cell")
    if args.cw_min and args.out_stem == "ns3_nmax_direct":
        raise SystemExit("--cw-min changes the scenario: give it an --out-stem of its own")
    plan = read_plan(args.plan) if args.plan else [
        (cell, args.source, args.n or default_grid(CELLS[cell].model_n)) for cell in args.cells]

    runs_path = RAW / f"{args.out_stem}_runs.csv"
    runs = read_runs(runs_path)
    done = {_run_key(r) for r in runs}
    on_file = len(done)
    todo = [] if args.summarise_only else pending(plan, done, args.seeds, args.first_seed)
    print(f"{on_file} runs on file, {len(todo)} to do, {args.workers} at a time", flush=True)

    def job(t: tuple[str, float, float, int, int]) -> dict:
        cell, jitter, skew, n, seed = t
        c = CELLS[cell]
        r = run_one(c.frame_bytes, c.fps, n, seed, args.sim_time, jitter_ms=jitter,
                    skew_ppm=skew, cw_min=args.cw_min)
        return {"cell": cell, "frame_bytes": c.frame_bytes, "frames_per_s": c.fps, "n_nodes": n,
                "seed": seed, "sim_time_s": args.sim_time,
                "tx_frames": int(r["tx_frames"]), "rx_frames": int(r["rx_frames"]),
                "delivered_frac": r["delivered_frac"], "delay_mean_ms": r["delay_mean_ms"],
                "delay_p99_ms": r["delay_p99_ms"], "delay_max_ms": r["delay_max_ms"],
                "jitter_ms": f"{jitter:g}", "skew_ppm": f"{skew:g}"}

    config = {"seeds": args.seeds, "t": args.sim_time,
              "cells": {k: vars(c) for k, c in CELLS.items()}}
    if args.first_seed != 1:                    # absent by default: the reported sample's hash
        config["first_seed"] = args.first_seed
    if args.cw_min:
        config["cw_min"] = args.cw_min
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(job, todo), 1):
            runs.append({k: str(v) for k, v in row.items()})
            if i % 30 == 0 or i == len(todo):       # checkpoint: a long sweep must survive a kill
                runs.sort(key=lambda r: (list(CELLS).index(r["cell"]), *_run_key(r)[1:]))
                _write(runs_path, runs, f"{args.out_stem}_runs", config)
                print(f"  {i}/{len(todo)} done", flush=True)

    if args.no_summary:
        return
    summary = summarise(runs, args.seeds)
    _write(RAW / f"{args.out_stem}.csv", summary, args.out_stem, config)
    for r in summary:
        if r["n_nodes"] == "CROSSING":
            interp = (f"  interp {r['n_cross_interp']} [{r['n_cross_interp_lo']}, "
                      f"{r['n_cross_interp_hi']}]" if "n_cross_interp" in r else "")
            print(f"  {r['cell']:<2} {r['config']:<28} jitter {r['jitter_ms']:>4} ms "
                  f"skew {r['skew_ppm']:>5} ppm  "
                  f"N_max = {r['n_max_mean']} [{r['n_max_ci_lo']}, {r['n_max_ci_hi']}]{interp}  "
                  f"per-run {r['n_max_per_run']}  model {r['model_n_max']} "
                  f"({r['deviation_pct']:+.1f} %)  "
                  f"{'' if r['bracketed'] else '⚠️ NOT BRACKETED by the grid'}")


if __name__ == "__main__":
    main()
