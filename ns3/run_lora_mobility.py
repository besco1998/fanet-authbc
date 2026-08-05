#!/usr/bin/env python3
"""E20 / phase M2 — does node mobility change the LoRa capacity result? (docs/MOBILITY_PLAN.md)

Runs `authbc-lora-capacity-mobile` across mobility models, speeds and BOTH collision matrices,
at the project's 30-seed floor, and reports the **distribution** rather than a mean.

⚠️ Why both matrices, and why that is the whole point (finding F36). Under `aloha` the same-SF
diagonal is +inf, so any co-SF overlap is fatal *regardless of received power* — and power is the
only channel through which position can act. Mobility therefore cannot change delivery at all, for
any model, at any speed, provided nodes stay in range. That is a structural property, and the
`aloha` arm here exists to demonstrate it at scale rather than to measure anything. `goursaud`
(6 dB capture, and the module's own default) restores the power dependence, so it is the only arm
in which a mobility number means something.

⚠️ Two verified properties of the scenario, both re-checked by `--verify` before any sweep:
  1. `--pinStreams=false --speed=0` reproduces the frozen `authbc-lora-capacity.cc` bit-identically
     (porting correctness).
  2. With pinning on, every `aloha` configuration returns the SAME delivered fraction (clean
     attribution — the RNG-stream confound is gone).
They are mutually exclusive by construction, which is why pinning is a flag and not a constant.

Writes results/raw/lora_mobility.csv.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

# Fixed across every arm so the only variables are mobility model, speed and collision matrix.
BASE = ("--nDevices=20 --dataRate=5 --payloadBytes=218 --appPeriod=36.6 "
        "--simulationTime=600 --gwRegion=aloha --channelModel=ideal --radius=1000 "
        "--txJitter=1.0")


def run_one(*, matrix: str, model: str, speed: float, seed: int, pin: bool = True) -> dict:
    ns3 = ns3_root()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "m"
        cmd = (f"authbc-lora-capacity-mobile {BASE} --interferenceMatrix={matrix} "
               f"--mobilityModel={model} --speed={speed} --seed={seed} "
               f"--pinStreams={'true' if pin else 'false'} --outPrefix={prefix}")
        subprocess.run(["./ns3", "run", cmd], cwd=ns3, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    out: dict[str, float | str] = {}
    for k, v in rows.items():
        try:
            out[k] = float(v)
        except ValueError:
            out[k] = v
    return out


def verify() -> None:
    """Both scenario properties, checked before any sweep is trusted (Law 6)."""
    ns3 = ns3_root()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s"
        static_cmd = (f"authbc-lora-capacity {BASE} --seed=7 --interferenceMatrix=aloha "
                      f"--outPrefix={p}")
        subprocess.run(["./ns3", "run", static_cmd], cwd=ns3, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        frozen = dict(csv.reader(p.with_suffix(".csv").read_text().splitlines()[1:]))

    unpinned = run_one(matrix="aloha", model="static", speed=0, seed=7, pin=False)
    same = (int(float(frozen["sent"])) == int(unpinned["sent"])
            and int(float(frozen["received"])) == int(unpinned["received"]))
    print(f"property 1 (porting): frozen sent/recv "
          f"{frozen['sent']}/{frozen['received']} vs mobile "
          f"{int(unpinned['sent'])}/{int(unpinned['received'])} -> "
          f"{'PASS' if same else 'FAIL'}")
    if not same:
        raise SystemExit("property 1 FAILED — the mobile scenario no longer reproduces the frozen "
                         "static one; fix that before trusting any mobility number")

    vals = {}
    for model, speed in (("static", 0), ("gaussmarkov", 5), ("gaussmarkov", 20), ("rwp", 20)):
        r = run_one(matrix="aloha", model=model, speed=speed, seed=7)
        vals[f"{model}@{speed}"] = r["delivered_frac"]
    uniq = set(vals.values())
    print(f"property 2 (attribution): aloha configs -> {vals} -> "
          f"{'PASS' if len(uniq) == 1 else 'FAIL'}")
    if len(uniq) != 1:
        raise SystemExit("property 2 FAILED — aloha delivery varies with mobility, which is "
                         "structurally impossible; the RNG-stream confound is back")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--aloha-seeds", type=int, default=5,
                    help="the aloha arm demonstrates an exact structural property, so it needs "
                         "far fewer seeds than the goursaud arm that actually measures something")
    ap.add_argument("--out", default="lora_mobility.csv")
    ap.add_argument("--verify", action="store_true", help="run the two property checks and exit")
    a = ap.parse_args()

    if a.verify:
        verify()
        return

    verify()
    arms = [("static", 0.0), ("gaussmarkov", 5.0), ("gaussmarkov", 20.0), ("rwp", 20.0)]
    rows = []
    for matrix in ("goursaud", "aloha"):
        n_seeds = a.seeds if matrix == "goursaud" else a.aloha_seeds
        for model, speed in arms:
            got = [run_one(matrix=matrix, model=model, speed=speed, seed=s)
                   for s in range(1, n_seeds + 1)]
            d = [g["delivered_frac"] for g in got]
            rows.append({
                "matrix": matrix, "mobility_model": model, "speed_mps": speed,
                "seeds": n_seeds,
                "delivered_mean": round(st.mean(d), 6),
                "delivered_min": round(min(d), 6),
                "delivered_max": round(max(d), 6),
                "delivered_stdev": round(st.stdev(d), 6) if len(d) > 1 else 0.0,
                "mean_displacement_m": round(st.mean([g["mean_displacement_m"] for g in got]), 1),
                "max_displacement_m": round(max(g["max_displacement_m"] for g in got), 1),
            })
            r = rows[-1]
            print(f"{matrix:9s} {model:12s} v={speed:<5} n={n_seeds:<3} "
                  f"mean={r['delivered_mean']:.6f} "
                  f"[{r['delivered_min']:.6f}, {r['delivered_max']:.6f}] "
                  f"sd={r['delivered_stdev']:.6f} disp={r['mean_displacement_m']} m")

    out = REPO / "results" / "raw" / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "lora_mobility",
            "config_hash": provenance.config_hash(
                {"arms": [[m, s] for m, s in arms], "seeds": a.seeds,
                 "aloha_seeds": a.aloha_seeds, "base": BASE})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    buf.write("# E20/M2 mobility sweep. The aloha arm demonstrates the F36 structural invariance\n")
    buf.write("# (mobility cannot act without capture); goursaud is the only arm in which a\n")
    buf.write("# mobility number is meaningful. Sender RNG streams are pinned in both.\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    print(f"\nwrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
