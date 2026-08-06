#!/usr/bin/env python3
"""Direction C — the frozen-phase artifact sweep (findings F32/F33). Generator for audit item S8.

**Why this file exists.** `results/raw/lora_phase_artifact_{30seed,eu_30seed}.csv` are the 300 runs
that Direction C's entire claim rests on, and until now **no committed code produced them**. They
could be read but not re-derived, which makes the central result of a would-be second paper
unreproducible. This is that generator, reconstructed from the artifacts' own `design=` headers.

**The question.** The ns-3 LoRaWAN module's `PeriodicSender` fires on an exact interval. Every
device here shares one period and LoRaWAN ALOHA has no backoff, so relative transmission phases are
frozen for a whole run: a pair that collides once collides on every transmission, and a pair that
misses never collides. Randomising the inter-transmission interval (`--txJitter`) breaks that. The
sweep contrasts the two and reports the **distribution**, because the frozen arm is bimodal.

⚠️ Read `F33` before quoting anything from this: the variance half of the original claim
generalised, the **mean-bias half did not**, and it was narrowed accordingly.

⚠️ The committed artifacts predate this generator, so re-running will not reproduce them
bit-for-bit — the RNG realisation differs. Compare distributions, not rows.

Analysis: `analysis/analyse_phase_artifact.py --csv <out>`
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from run_lora_capacity import run_one  # noqa: E402

from authbc.bench import provenance  # noqa: E402

# From the artifacts' `design=` headers: DR5, 218 B, appPeriod 36.378 s, 3600 s, ideal channel,
# radius 1000 m, aloha interference matrix. Only the gateway preset and node grid differ.
DR, PAYLOAD, PERIOD_S, SIM_S, RADIUS = 5, 218, 36.378, 3600.0, 1000.0
PRESETS = {
    "aloha": {"gw_region": "aloha", "nodes": (5, 20, 100)},   # 3 x 2 x 30 = 180 runs
    "eu": {"gw_region": "eu", "nodes": (20, 100)},            # 2 x 2 x 30 = 120 runs
}
JITTERS = (0.0, 1.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=sorted(PRESETS), default="aloha")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--out", default=None, help="default: lora_phase_artifact[_eu]_<seeds>seed.csv")
    a = ap.parse_args()

    preset = PRESETS[a.preset]
    suffix = "" if a.preset == "aloha" else "_eu"
    out_name = a.out or f"lora_phase_artifact{suffix}_{a.seeds}seed.csv"

    rows = []
    for n in preset["nodes"]:
        for jitter in JITTERS:
            for seed in range(1, a.seeds + 1):
                got = run_one(n, DR, PAYLOAD, PERIOD_S, SIM_S, seed,
                              gw_region=preset["gw_region"], channel_model="ideal",
                              radius_m=RADIUS, interference="aloha", tx_jitter_s=jitter)
                rows.append({"n_devices": n, "tx_jitter_s": jitter, "seed": seed,
                             "delivered_frac": got["delivered_frac"]})
            vals = [r["delivered_frac"] for r in rows[-a.seeds:]]
            label = "frozen" if jitter == 0 else "jittered"
            print(f"  N={n:<4} {label:<9} n={a.seeds}  mean={sum(vals) / len(vals):.4f}  "
                  f"[{min(vals):.4f}..{max(vals):.4f}]")

    path = REPO / "results" / "raw" / out_name
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": f"lora_phase_artifact_{a.preset}",
            "config_hash": provenance.config_hash(
                {"preset": a.preset, "nodes": list(preset["nodes"]), "jitters": list(JITTERS),
                 "seeds": a.seeds, "dr": DR, "payload": PAYLOAD, "period": PERIOD_S,
                 "sim": SIM_S, "radius": RADIUS})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    buf.write(f"# design=N in {list(preset['nodes'])} x tx_jitter in {list(JITTERS)} s x "
              f"{a.seeds} seeds; DR{DR}, {PAYLOAD} B, appPeriod {PERIOD_S} s, {SIM_S:.0f} s,\n")
    buf.write(f"#        {a.preset} preset, ideal channel, radius {RADIUS:.0f} m\n")
    buf.write("# stats=Levene (variance, robust to the bimodality) + Mann-Whitney U (location)\n")
    buf.write("# findings=F32 (variance inflation, generalised) and F33 (the mean-bias half did\n")
    buf.write("#          NOT generalise -- read that narrowing before quoting a mean shift)\n")
    w = csv.DictWriter(buf, fieldnames=["n_devices", "tx_jitter_s", "seed", "delivered_frac"])
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())
    print(f"\nwrote {path} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
