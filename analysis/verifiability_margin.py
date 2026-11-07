#!/usr/bin/env python3
"""Revision A3 — how much margin the design has against its verifiability target.

The paper's design meets V ≥ 0.95 at p = 0.05 with no margin (0.952, [0.947, 0.957]), and under
length-dependent loss it misses (0.947). This sweeps the codec-in-the-loop harness of the loss
table (`frame_experiments.run_loss_codec`, E10) over what the plan asks:

    p ∈ {0.01, 0.02, 0.03, 0.05, 0.08} × b ∈ {1, 2, 3, 4} × r ∈ {1, 2, 4}
    loss: independent; Gilbert–Elliott with the same mean and bursts of 2, 4, 8 frames;
          length-dependent (the bit error rate that loses the one-record frame with p)

and scores each cell against ε ∈ {0.05, 0.08, 0.10} (V ≥ 1 − ε). ε changes the target, not the
run, so it is applied here and not simulated. A frame counts only if `LeanReceiver` decodes,
verifies and stores it. Registration: `predictions/A3.md`.

    python analysis/verifiability_margin.py --run      # results/raw/verifiability_margin.csv

Part 2 replaces the loss process by ns-3's: per-link success sequences of A1's spatial runs
(`ns3/run_spatial.py --trace-links 50`), replayed frame by frame through the same codec. V is
averaged over a run's links and its interval bootstrapped over runs, not links: the links of one
run share one channel.

    python analysis/verifiability_margin.py --traces results/raw/ns3_spatial_<stem>_traces
                                                     # results/raw/verifiability_margin_trace.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.bench.frame_experiments import _length_loss_probs, _loss_mask  # noqa: E402
from authbc.bench.stats import bootstrap_ci  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.models import frame as frame_model  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt  # noqa: E402

OUT = REPO / "results" / "raw" / "verifiability_margin.csv"
OUT_TRACE = REPO / "results" / "raw" / "verifiability_margin_trace.csv"
P_VALUES: tuple[float, ...] = (0.01, 0.02, 0.03, 0.05, 0.08)
EPSILONS: tuple[float, ...] = (0.05, 0.08, 0.10)
BATCHES: tuple[int, ...] = (1, 2, 3, 4)
REF_INTERVALS: tuple[int, ...] = (1, 2, 4)
# (name, Gilbert mean burst in frames; None = independent; "ber" = length-dependent)
MODELS: tuple[tuple[str, float | None], ...] = (
    ("iid", None), ("gilbert2", 2.0), ("gilbert4", 4.0), ("gilbert8", 8.0), ("ber", None))
SEEDS: tuple[int, ...] = tuple(range(1, 31))
FRAMES_PER_SEED = 240           # a multiple of every r; 7 200 frames per cell, as E10
BASE_SEED = 7272
CI_SEED = 20261019


def theory(model: str, burst: float | None, p: float, r: int) -> float | None:
    """Eq. (3) for independent loss, its Gilbert form for bursts; None where the frame's own
    length sets its loss (the measured per-frame probabilities are averaged instead)."""
    if model == "iid":
        return frame_model.verifiability(p, r)
    if burst is not None:
        return frame_model.verifiability_gilbert(p, burst, r)
    return None


def cell(job: tuple[int, int]) -> list[dict]:
    batch, ref = job
    sk, pk = Ed25519Scheme().keygen(seed=bytes(range(32)))
    streams = []
    for seed in SEEDS:
        recs = leanframes.chained_records(seed, FRAMES_PER_SEED * batch)
        sender = LeanSender(sk, ref_interval=ref)
        streams.append([sender.frame(recs[i:i + batch]) for i in range(0, len(recs), batch)])
    frame_bytes = st.mean(len(f) for s in streams for f in s)
    one_record = leanframes.lean_frame_sizes(1).mean
    rows = []
    for k, (model, burst) in enumerate(MODELS):
        for p in P_VALUES:
            v_seed, p_seen = [], []
            th_ber = []
            for seed, frames in zip(SEEDS, streams, strict=True):
                rng = np.random.default_rng([BASE_SEED, k, batch, ref, int(round(p * 1e6)), seed])
                if model == "ber":
                    q = _length_loss_probs(frames, p, one_record)
                    lost = rng.random(len(frames)) < q
                    th_ber.append(frame_model.verifiability_per_frame(list(q), ref))
                    p_seen.append(float(np.mean(q)))
                else:
                    lost = _loss_mask(rng, len(frames), p, "iid" if burst is None else "gilbert",
                                      burst or 1.0)
                    p_seen.append(p)
                rx = LeanReceiver({leanframes.CONVENTION_SRC: pk})
                for data, gone in zip(frames, lost, strict=True):
                    if not gone:
                        rx.receive(data)
                odd = {x: c for x, c in rx.counters.items()
                       if c and x not in (Receipt.ACCEPTED, Receipt.DESYNC)}
                if odd:
                    raise RuntimeError(f"a loss-only link produced {odd}")
                v_seed.append(rx.counters[Receipt.ACCEPTED] / len(frames))
            lo, hi = bootstrap_ci(v_seed, seed=CI_SEED, statistic=np.mean)
            th = theory(model, burst, p, ref)
            v = st.mean(v_seed)
            row = {"loss_model": model, "p": p, "p_frame": round(st.mean(p_seen), 5),
                   "batch": batch, "ref_interval": ref, "frame_bytes": round(frame_bytes, 3),
                   "bytes_per_rec": round(frame_bytes / batch, 3),
                   "V_meas": round(v, 5), "V_ci_lo": round(lo, 5), "V_ci_hi": round(hi, 5),
                   "V_theory": round(th if th is not None else st.mean(th_ber), 5),
                   "frames": len(SEEDS) * FRAMES_PER_SEED}
            for eps in EPSILONS:
                row[f"meets_eps{eps:g}"] = int(v >= 1 - eps)
                row[f"margin_eps{eps:g}"] = round(v - (1 - eps), 5)
            rows.append(row)
    return rows


# --------------------------------------------------------------------------- part 2: ns-3 traces
def read_traces(path: Path) -> list[np.ndarray]:
    """One run's traced links as lost-frame masks, each in the order its source sent."""
    rows = csv.DictReader(path.read_text().splitlines())
    return [np.frombuffer(r["got"].encode(), dtype=np.uint8) == ord("0") for r in rows]


def burst_stats(masks: list[np.ndarray]) -> tuple[int, int]:
    """(frames lost, runs of consecutive lost frames) over all masks; their ratio is the mean
    burst."""
    lost = bursts = 0
    for m in masks:
        edges = np.diff(np.concatenate(([0], m.astype(np.int8), [0])))
        lost += int(m.sum())
        bursts += int((edges == 1).sum())
    return lost, bursts


def v_of_masks(frames: list[bytes], pk: object, masks: list[np.ndarray]) -> list[float]:
    """V of each mask: the frames the real receiver decodes, verifies and stores, over those sent.
    `frames` is one sender's stream, at least as long as every mask."""
    out = []
    for lost in masks:
        if len(lost) > len(frames):
            raise ValueError(f"a trace of {len(lost)} frames, a stream of {len(frames)}")
        rx = LeanReceiver({leanframes.CONVENTION_SRC: pk})
        for data, gone in zip(frames, lost, strict=False):
            if not gone:
                rx.receive(data)
        odd = {x: c for x, c in rx.counters.items()
               if c and x not in (Receipt.ACCEPTED, Receipt.DESYNC)}
        if odd:
            raise RuntimeError(f"a loss-only link produced {odd}")
        out.append(rx.counters[Receipt.ACCEPTED] / len(lost))
    return out


def trace_cell(job: tuple[int, int, dict[str, list[list[np.ndarray]]]]) -> list[dict]:
    """Every group of runs through frames of `batch` records with one reference per `ref`."""
    batch, ref, groups = job
    sk, pk = Ed25519Scheme().keygen(seed=bytes(range(32)))
    longest = max(len(m) for runs in groups.values() for run in runs for m in run)
    recs = leanframes.chained_records(1, longest * batch)
    sender = LeanSender(sk, ref_interval=ref)
    frames = [sender.frame(recs[i:i + batch]) for i in range(0, len(recs), batch)]
    rows = []
    for label, runs in groups.items():
        v_run = [st.mean(v_of_masks(frames, pk, run)) for run in runs]
        masks = [m for run in runs for m in run]
        lost, bursts = burst_stats(masks)
        p_hat = lost / sum(len(m) for m in masks)
        lo, hi = bootstrap_ci(v_run, seed=CI_SEED, statistic=np.mean)
        v = st.mean(v_run)
        v_iid = frame_model.verifiability(p_hat, ref)
        v_g8 = frame_model.verifiability_gilbert(p_hat, 8.0, ref)
        row = {"group": label, "runs": len(runs), "links": len(masks), "batch": batch,
               "ref_interval": ref, "p_hat": round(p_hat, 5),
               "mean_burst": round(lost / bursts, 3) if bursts else "",
               "V_trace": round(v, 5), "V_ci_lo": round(lo, 5), "V_ci_hi": round(hi, 5),
               "V_iid": round(v_iid, 5), "V_gilbert8": round(v_g8, 5),
               "between_iid_and_gilbert8": int(min(v_iid, v_g8) <= v <= max(v_iid, v_g8))}
        for eps in EPSILONS:
            row[f"meets_eps{eps:g}"] = int(v >= 1 - eps)
            row[f"margin_eps{eps:g}"] = round(v - (1 - eps), 5)
        rows.append(row)
    return rows


def read_trace_dir(trace_dir: Path) -> dict[str, list[list[np.ndarray]]]:
    """Runs grouped by (scenario, configuration, node count): `<scen>.<cfg>.<n>.<seed>.csv`."""
    groups: dict[str, list[list[np.ndarray]]] = {}
    for f in sorted(trace_dir.glob("*.csv"), key=lambda f: (f.stem.rsplit(".", 1)[0],
                                                             int(f.stem.rsplit(".", 1)[1]))):
        groups.setdefault(f.stem.rsplit(".", 1)[0], []).append(read_traces(f))
    if not groups:
        raise SystemExit(f"no traces in {trace_dir}")
    return groups


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true", help="part 1: the synthetic loss processes")
    mode.add_argument("--traces", type=Path, help="part 2: a directory of ns-3 link traces")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if args.traces:
        main_traces(args.traces, args.workers)
        return
    jobs = [(b, r) for b in BATCHES for r in REF_INTERVALS]
    with Pool(args.workers) as pool:
        rows = [row for part in pool.map(cell, jobs) for row in part]
    buf = io.StringIO()
    config = {"p": P_VALUES, "eps": EPSILONS, "b": BATCHES, "r": REF_INTERVALS,
              "models": MODELS, "seeds": SEEDS, "frames": FRAMES_PER_SEED, "base": BASE_SEED}
    for k, v in {**provenance.env_block(), "run": "verifiability_margin",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    print(f"{len(rows)} cells -> {OUT}")


def main_traces(trace_dir: Path, workers: int) -> None:
    groups = read_trace_dir(trace_dir)
    with Pool(workers) as pool:
        rows = [row for part in pool.map(trace_cell, [(b, r, groups) for b in BATCHES
                                                      for r in REF_INTERVALS]) for row in part]
    buf = io.StringIO()
    config = {"traces": trace_dir.name, "eps": EPSILONS, "b": BATCHES, "r": REF_INTERVALS,
              "ci": CI_SEED}
    for k, v in {**provenance.env_block(), "run": "verifiability_margin_trace",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT_TRACE.write_text(buf.getvalue())
    print(f"{len(rows)} cells -> {OUT_TRACE}")


if __name__ == "__main__":
    main()
