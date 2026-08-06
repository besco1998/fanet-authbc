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
from statistics import stdev

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import threshold_crossing_ci  # noqa: E402
from authbc.models import lora  # noqa: E402

H_F, G_A, CHAIN, S_DELTA = 44, 64, 32, 13.0   # measured H_f (B1); per-frame chaining (F5)
MODULE_MAX_PAYLOAD = 222                      # RP002 Table 12, what the module enforces


def frame_for(dr: int, max_payload: int) -> tuple[int, int]:
    """(batch, frame bytes) — the largest AUTHBC frame that fits *max_payload* at this DR."""
    usable = max_payload - H_F - G_A - CHAIN
    b = int(usable // S_DELTA)
    return b, H_F + G_A + CHAIN + int(b * S_DELTA)


def run_one(n: int, dr: int, payload: int, period_s: float, sim_s: float, seed: int,
            *, gw_region: str = "aloha", channel_model: str = "ideal",
            radius_m: float = 1000.0, interference: str = "aloha",
            tx_jitter_s: float = 0.0) -> dict:
    """One NS-3 run.

    ``gw_region``     "aloha" = 1 channel / 1 demodulation path (an ad hoc PEER, F21);
                      "eu"    = 3 channels / 8 paths (a GATEWAY — a different question, E9).
    ``channel_model`` "ideal" = LogDistance only, all loss is collisions;
                      "shadowing" = + correlated shadowing, the honest air-to-air model (E12).
    ``interference``  collision matrix. "aloha" has +inf on the same-SF diagonal, i.e. any
                      co-SF overlap is fatal and there is **no capture**; "goursaud" uses a 6 dB
                      same-SF threshold, so the stronger frame survives. We force one SF, so this
                      choice decides whether capture exists at all (audit finding F26).
    ``tx_jitter_s``   one-sided inter-transmission jitter (E13). 0 keeps the exact period, whose
                      frozen relative phases make delivery bimodal. Only ever delays, so the 1 %
                      duty cycle is preserved (mean interval becomes T + jitter/2).
    ``radius_m``      devices are uniform in a disc of this radius; the gateway sits at its centre,
                      so link distances span 0..radius with mean 2/3 radius — not a fixed
                      point-to-point range like the hardware references.
    """
    ns3 = ns3_root()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "c"
        cmd = (f"authbc-lora-capacity --nDevices={n} --dataRate={dr} "
               f"--payloadBytes={payload} --appPeriod={period_s} "
               f"--simulationTime={sim_s} --seed={seed} --outPrefix={prefix} "
               f"--gwRegion={gw_region} --channelModel={channel_model} --radius={radius_m} "
               f"--interferenceMatrix={interference} --txJitter={tx_jitter_s}")
        subprocess.run(["./ns3", "run", cmd], cwd=ns3, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    # The scenario also emits provenance strings (gw_region, channel_model), so coerce only what
    # is numeric rather than assuming every field is.
    out: dict[str, float | str] = {}
    for k, v in rows.items():
        try:
            out[k] = float(v)
        except ValueError:
            out[k] = v
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-rate", type=int, default=5)
    ap.add_argument("--nodes", type=int, nargs="+",
                    default=[5, 10, 20, 35, 50, 75, 100, 150, 200, 300])
    # E13/F26: 3 seeds gave N_max=5 purely by luck — the distribution is wide and the threshold
    # crossing is a knife edge. 30 is the floor for a defensible mean here.
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--sim-time", type=float, default=3600.0)
    ap.add_argument("--epsilon", type=float, default=0.05, help="V >= 1-eps (T3)")
    ap.add_argument("--gw-region", choices=("aloha", "eu"), default="aloha",
                    help="aloha = 1 ch/1 demod path (ad hoc peer); eu = 3 ch/8 paths (gateway)")
    ap.add_argument("--channel-model", choices=("ideal", "shadowing"), default="ideal",
                    help="ideal = LogDistance only; shadowing = + correlated shadowing (E12)")
    ap.add_argument("--radius", type=float, default=1000.0, help="deployment disc radius (m)")
    # E13: real LoRaWAN Class A randomises transmission timing; the module's sender does not.
    # 1 s is ~2.7 % of the duty interval, one-sided, so duty stays at 0.9865 % (< 1 %).
    ap.add_argument("--tx-jitter", type=float, default=1.0,
                    help="one-sided inter-transmission jitter (s); 0 = exact period (E13)")
    ap.add_argument("--interference", choices=("aloha", "goursaud"), default="aloha",
                    help="aloha = no capture (co-SF overlap always fatal); goursaud = 6 dB capture")
    ap.add_argument("--out", default="lora_capacity.csv",
                    help="output CSV under results/raw/ (use a distinct name for variant runs)")
    args = ap.parse_args()

    b, payload = frame_for(args.data_rate, MODULE_MAX_PAYLOAD)
    toa = lora.frame_time_on_air_s(payload, args.data_rate)
    period = lora.duty_cycle_interval_s(toa)
    print(f"DR{args.data_rate}: b={b}, frame={payload} B (module limit {MODULE_MAX_PAYLOAD} B), "
          f"ToA={toa * 1e3:.1f} ms, duty interval={period:.1f} s")
    print(f"acceptance: delivered >= {1 - args.epsilon:.2f} (V >= 1-eps), stated in advance\n")

    out_rows = []
    n_max = 0
    failed_yet = False
    # Kept for the bootstrap: a threshold crossing needs the per-seed sample, not the summary.
    per_seed_delivered: dict[int, list[float]] = {}
    n_max_strict = 0
    strict_failed_yet = False
    for n in args.nodes:
        per_seed = [run_one(n, args.data_rate, payload, period, args.sim_time, s,
                            gw_region=args.gw_region, channel_model=args.channel_model,
                            radius_m=args.radius, interference=args.interference,
                            tx_jitter_s=args.tx_jitter)
                    for s in range(1, args.seeds + 1)]
        vals = sorted(float(r["delivered_frac"]) for r in per_seed)
        delivered = sum(vals) / len(vals)
        sent = sum(float(r["sent"]) for r in per_seed) / len(per_seed)
        per_seed_delivered[n] = list(vals)
        ok = delivered >= 1 - args.epsilon
        # ⚠️ Two different questions, and the project previously answered only the first.
        #   `ok`        : does the MEAN across seeds meet V?           (a throughput-like reading)
        #   `ok_strict` : do at least 95 % of individual runs meet V?  (a reliability reading)
        # V is a verifiability target, so the strict form is the operationally meaningful one. At
        # N=3 the mean passes (0.9598) while 9 of 30 seeds fail — the two disagree, and reporting
        # only the mean overstates what the network guarantees.
        seed_pass_frac = sum(1 for v in vals if v >= 1 - args.epsilon) / len(vals)
        ok_strict = seed_pass_frac >= 0.95
        # F26/A4: N_max is the largest N for which EVERY smaller N also passes. Taking the last
        # passing N (the previous behaviour) would silently report a higher capacity than the data
        # supports the moment the curve is non-monotone — and F26/A1 shows it is noisy enough to be.
        if ok and not failed_yet:
            n_max = n
        elif not ok:
            failed_yet = True
        if ok_strict and not strict_failed_yet:
            n_max_strict = n
        elif not ok_strict:
            strict_failed_yet = True
        out_rows.append({
            "n_devices": n, "data_rate": args.data_rate, "batch": b,
            "payload_bytes": payload, "app_period_s": round(period, 3),
            "sent_mean": round(sent, 1), "delivered_frac": round(delivered, 5),
            "implied_p_loss": round(1 - delivered, 5),
            # F26/A5: the mean alone hid a bimodal distribution with sigma ~0.21. Report the spread
            # so a knife-edge threshold crossing is visible in the artifact itself.
            "delivered_min": round(vals[0], 5), "delivered_max": round(vals[-1], 5),
            "delivered_stdev": round(stdev(vals), 5) if len(vals) > 1 else 0.0,
            "seeds_failing_v": sum(1 for v in vals if v < 1 - args.epsilon),
            "seed_pass_frac": round(seed_pass_frac, 4),
            "meets_v": int(ok), "meets_v_strict": int(ok_strict), "seeds": args.seeds,
            # Λ a node can sustain, and what the whole neighbourhood then carries
            "lambda_rec_per_s": round(b / period, 5),
            "aggregate_rec_per_s": round(n * b / period, 4),
        })
        print(f"  N={n:<4} delivered={delivered:.4f} "
              f"[{vals[0]:.4f}..{vals[-1]:.4f}] "
              f"{sum(1 for v in vals if v < 1 - args.epsilon)}/{len(vals)} seeds fail  "
              f"{'OK' if ok else 'FAILS V>=0.95'}")

    crossing = threshold_crossing_ci(per_seed_delivered, threshold=1 - args.epsilon,
                                     resamples=10_000, seed=0)
    print(f"\n  N_max (mean V >= {1 - args.epsilon:.2f})            = {n_max}")
    print(f"  N_max 95 % bootstrap CI                = [{crossing.ci_lo}, {crossing.ci_hi}]"
          f"{'   <-- KNIFE EDGE, do not quote bare' if crossing.is_knife_edge else ''}")
    print(f"  bootstrap distribution                 = "
          f"{ {k: round(v, 3) for k, v in sorted(crossing.distribution.items())} }")
    print(f"  N_max (>= 95 % of individual runs)     = {n_max_strict}"
          f"{'   <-- DISAGREES with the mean criterion' if n_max_strict != n_max else ''}")
    path = REPO / "results" / "raw" / args.out
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "lora_capacity",
            "n_max_mean_criterion": n_max,
            "n_max_ci95": f"[{crossing.ci_lo},{crossing.ci_hi}]",
            "n_max_is_knife_edge": int(crossing.is_knife_edge),
            "n_max_strict_criterion": n_max_strict,
            "config_hash": provenance.config_hash(
                # ⚠️ Must include EVERY parameter that distinguishes a variant run. It used to
                # cover only {dr, nodes, seeds, t, payload}, so lora_capacity_shadow500.csv,
                # _shadow1000.csv and _repro.csv all carried the SAME hash despite different
                # radii and channel models — a hash that cannot tell its own runs apart.
                {"dr": args.data_rate, "nodes": args.nodes, "seeds": args.seeds,
                 "t": args.sim_time, "payload": payload,
                 "gw_region": args.gw_region, "channel_model": args.channel_model,
                 "radius": args.radius, "interference": args.interference,
                 "tx_jitter": args.tx_jitter, "epsilon": args.epsilon})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)
    path.write_text(buf.getvalue())
    print(f"wrote {path} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
