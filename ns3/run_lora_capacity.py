#!/usr/bin/env python3
"""D2 — the LoRa multi-node capacity envelope, by simulation (docs/02 §9).

The LoRa arm is otherwise analytical, and deliberately so: time on air comes from the SX1276
formula and the sustainable rate from the EU868 duty cycle, both deterministic, so simulating them
would be circular. Exactly one quantity resists that treatment, and it is the one the 802.11 arm
already reports — **how many nodes can share the channel**. LoRaWAN uplinks are pure ALOHA, so N
devices collide and the delivered fraction falls with N. The duty cycle says what ONE node may
legally send; it says nothing about fifty.

This sweeps N at a fixed data rate and AUTHBC frame size, and reports the largest N whose delivered
fraction still satisfies **V ≥ 1−ε** — the identical criterion behind the 802.11 envelope
(docs/02 §6b), so the two arms are directly comparable.

⚠️ **The frame size is the module's limit, not our model's.** The NS-3 LoRaWAN module enforces
RP002-1.0.3 **Table 12** (repeater-compatible, 222 B at DR4-6); `models/lora.py` uses **Table 13**
(non-repeater, 242 B) and documents that choice. At DR5 that caps the per-frame batch at b=6
(218 B) where our model reports b=7 (231 B). We simulate what the module accepts and say so, rather
than quietly reconciling two defensible readings of the same standard.

Writes results/raw/lora_capacity.csv.
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
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import lora  # noqa: E402

H_F, G_A, CHAIN, S_DELTA = 44, 64, 32, 13.0   # measured H_f (B1); per-frame chaining (F5)
MODULE_MAX_PAYLOAD = 222                      # RP002 Table 12, what the module enforces


def frame_for(dr: int, max_payload: int) -> tuple[int, int]:
    """(batch, frame bytes) — the largest AUTHBC frame that fits *max_payload* at this DR."""
    usable = max_payload - H_F - G_A - CHAIN
    b = int(usable // S_DELTA)
    return b, H_F + G_A + CHAIN + int(b * S_DELTA)


def run_one(n: int, dr: int, payload: int, period_s: float, sim_s: float, seed: int) -> dict:
    ns3 = ns3_root()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "c"
        cmd = (f"authbc-lora-capacity --nDevices={n} --dataRate={dr} "
               f"--payloadBytes={payload} --appPeriod={period_s} "
               f"--simulationTime={sim_s} --seed={seed} --outPrefix={prefix}")
        subprocess.run(["./ns3", "run", cmd], cwd=ns3, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    return {k: float(v) for k, v in rows.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-rate", type=int, default=5)
    ap.add_argument("--nodes", type=int, nargs="+",
                    default=[5, 10, 20, 35, 50, 75, 100, 150, 200, 300])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--sim-time", type=float, default=3600.0)
    ap.add_argument("--epsilon", type=float, default=0.05, help="V >= 1-eps (T3)")
    args = ap.parse_args()

    b, payload = frame_for(args.data_rate, MODULE_MAX_PAYLOAD)
    toa = lora.frame_time_on_air_s(payload, args.data_rate)
    period = lora.duty_cycle_interval_s(toa)
    print(f"DR{args.data_rate}: b={b}, frame={payload} B (module limit {MODULE_MAX_PAYLOAD} B), "
          f"ToA={toa * 1e3:.1f} ms, duty interval={period:.1f} s")
    print(f"acceptance: delivered >= {1 - args.epsilon:.2f} (V >= 1-eps), stated in advance\n")

    out_rows = []
    n_max = 0
    for n in args.nodes:
        per_seed = [run_one(n, args.data_rate, payload, period, args.sim_time, s)
                    for s in range(1, args.seeds + 1)]
        delivered = sum(r["delivered_frac"] for r in per_seed) / len(per_seed)
        sent = sum(r["sent"] for r in per_seed) / len(per_seed)
        ok = delivered >= 1 - args.epsilon
        if ok:
            n_max = n
        out_rows.append({
            "n_devices": n, "data_rate": args.data_rate, "batch": b,
            "payload_bytes": payload, "app_period_s": round(period, 3),
            "sent_mean": round(sent, 1), "delivered_frac": round(delivered, 5),
            "implied_p_loss": round(1 - delivered, 5),
            "meets_v": int(ok), "seeds": args.seeds,
            # Λ a node can sustain, and what the whole neighbourhood then carries
            "lambda_rec_per_s": round(b / period, 5),
            "aggregate_rec_per_s": round(n * b / period, 4),
        })
        print(f"  N={n:<4} delivered={delivered:.4f}  "
              f"{'OK' if ok else 'FAILS V>=0.95'}")

    print(f"\n  N_max (V >= {1 - args.epsilon:.2f}) = {n_max}")
    path = REPO / "results" / "raw" / "lora_capacity.csv"
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "lora_capacity",
            "config_hash": provenance.config_hash(
                {"dr": args.data_rate, "nodes": args.nodes, "seeds": args.seeds,
                 "t": args.sim_time, "payload": payload})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)
    path.write_text(buf.getvalue())
    print(f"wrote {path} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
