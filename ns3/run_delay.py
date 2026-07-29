#!/usr/bin/env python3
"""D3/C1 — measure DCF delivery delay against offered load, and find where D(b) stops holding.

`models.energy.freshness_delay_s` omits channel-access delay entirely (docs/OPEN_ITEMS C1). The
thesis claims D(b) is "a lower bound, credible only at low U" — this quantifies "low".

Sweeps per-node offered frame rate at fixed N, in the same single collision domain the Bianchi
comparison uses, and records the delivery-delay distribution plus the delivered fraction. The
model's own prediction (airtime + M/M/1 queueing, i.e. everything except fill time) is computed
alongside so the two are directly comparable.

Writes results/raw/ns3_delay.csv.
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NS3 = REPO / "ns3" / "ns-allinone-3.41" / "ns-3.41"
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import bianchi, optimizer  # noqa: E402
from authbc.models.energy import EnergyConfig, Placement, queueing_delay_s  # noqa: E402

H_F, G_A, S_DELTA, BATCH = 44, 64, 45.0, 4
FRAME_BYTES = H_F + G_A + int(BATCH * S_DELTA)     # 288 B, the optimized frame


def run_one(n_nodes: int, fps: float, seed: int, sim_time: float) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "d"
        cmd = (f"authbc-delay --nNodes={n_nodes} --framesPerSec={fps} "
               f"--frameSize={FRAME_BYTES} --simTime={sim_time} --seed={seed} "
               f"--outPrefix={prefix}")
        subprocess.run(["./ns3", "run", cmd], cwd=NS3, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = dict(csv.reader((prefix.with_suffix(".csv")).read_text().splitlines()[1:]))
    return {k: float(v) for k, v in rows.items()}


def model_non_fill_delay_ms(n_nodes: int, fps: float) -> float:
    """What D(b) predicts for everything EXCEPT fill time: airtime + M/M/1 queueing.

    Fill time (b/Λ) is excluded because it is an application property, identical in the simulator
    and the model; the question is only whether the CHANNEL terms are right.
    """
    cfg = EnergyConfig(placement=Placement.B, batch=BATCH, record_bytes=S_DELTA,
                       auth_bytes=G_A, frame_hdr_bytes=H_F, n_frames=1)
    lam = fps * BATCH
    return (bianchi.t_broadcast(FRAME_BYTES) + queueing_delay_s(cfg, lam)) * 1e3


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-nodes", type=int, default=50)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--sim-time", type=float, default=20.0)
    ap.add_argument("--rates", type=float, nargs="+",
                    default=[1, 2, 3, 5, 7, 8, 9, 10, 12])
    args = ap.parse_args()

    out_rows = []
    for fps in args.rates:
        per_seed = [run_one(args.n_nodes, fps, s, args.sim_time)
                    for s in range(1, args.seeds + 1)]
        util = optimizer.channel_utilisation(args.n_nodes, fps * BATCH, BATCH, FRAME_BYTES)
        def mean(key: str, rows: list[dict[str, float]] = per_seed) -> float:
            return sum(r[key] for r in rows) / len(rows)

        predicted = model_non_fill_delay_ms(args.n_nodes, fps)
        measured = mean("delay_mean_ms")
        out_rows.append({
            "n_nodes": args.n_nodes, "frames_per_s": fps,
            "lambda_rec_per_s": round(fps * BATCH, 2), "frame_bytes": FRAME_BYTES,
            "channel_util": round(util, 4),
            "delivered_frac": round(mean("delivered_frac"), 5),
            "delay_mean_ms": round(measured, 4),
            "delay_p50_ms": round(mean("delay_p50_ms"), 4),
            "delay_p95_ms": round(mean("delay_p95_ms"), 4),
            "delay_p99_ms": round(mean("delay_p99_ms"), 4),
            "delay_max_ms": round(mean("delay_max_ms"), 4),
            "model_non_fill_ms": round(predicted, 4),
            "access_delay_ms": round(measured - predicted, 4),
            "pct_of_250ms_budget": round(100.0 * measured / 250.0, 3),
            "seeds": args.seeds,
        })
        print(f"  fps={fps:<5} U={util:.3f}  delivered={mean('delivered_frac'):.4f}  "
              f"mean={measured:8.3f} ms  p95={mean('delay_p95_ms'):8.3f}  "
              f"model={predicted:.3f}  access={measured - predicted:+8.3f} ms")

    path = REPO / "results" / "raw" / "ns3_delay.csv"
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "ns3_delay",
            "config_hash": provenance.config_hash(
                {"n": args.n_nodes, "seeds": args.seeds, "t": args.sim_time,
                 "rates": args.rates, "frame": FRAME_BYTES})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)
    path.write_text(buf.getvalue())
    print(f"\nwrote {path} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
