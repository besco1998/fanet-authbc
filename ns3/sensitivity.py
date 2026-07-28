"""Deployment-geometry sensitivity of the NS-3 broadcast channel → results/raw/ns3_sensitivity.csv.

The validation scenario (docs/04 §3) is deliberately idealised: co-located stations, one collision
domain, symmetric received powers — the conditions the analytic DCF models actually describe. This
driver asks the complementary question: **how far do those predictions travel to a real formation?**

It sweeps the `--realistic` scenario (Friis free-space at 5.18 GHz, area-uniform 3D spiral cluster
at 50–120 m altitude, optional Nakagami fading) across cluster radii and fading conditions, and
reports goodput relative to the controlled baseline at the same N, seeds and frame size.

What moves the answer is **spatial reuse**: once stations are far enough apart, concurrent
transmissions succeed at different receivers, which a single-collision-domain model cannot
represent by construction. That makes the controlled model a conservative LOWER bound — until the
cluster grows enough that path loss starts costing frames and hidden terminals appear, at which
point it becomes optimistic instead. This driver locates that crossover.
"""

from __future__ import annotations

import argparse
import csv
import statistics as st
import subprocess
import tempfile
from pathlib import Path

from authbc.bench import provenance

REPO = Path(__file__).resolve().parents[1]
NS3 = REPO / "ns3" / "ns-allinone-3.41" / "ns-3.41"
RESULTS = REPO / "results" / "raw"

# (label, extra NS-3 args) — the controlled baseline MUST be first; everything is relative to it.
SCENARIOS: tuple[tuple[str, str], ...] = (
    ("controlled", ""),
    ("realistic_50m", "--realistic=1 --clusterM=50"),
    ("realistic_150m", "--realistic=1 --clusterM=150"),
    ("realistic_300m", "--realistic=1 --clusterM=300"),
    ("realistic_500m", "--realistic=1 --clusterM=500"),
    ("realistic_150m_nakagami3", "--realistic=1 --clusterM=150 --nakagamiM=3"),
    ("realistic_150m_nakagami1", "--realistic=1 --clusterM=150 --nakagamiM=1"),
)
FIELDS = ["scenario", "N", "frameSize", "simTime", "seeds", "goodput_mbps_median",
          "goodput_mbps_min", "goodput_mbps_max", "delta_vs_controlled_pct"]


def _run(label: str, args: str, n: int, seeds: int, frame: int, sim_t: float,
         outdir: str) -> list[float]:
    out: list[float] = []
    for seed in range(1, seeds + 1):
        prefix = f"{outdir}/{label}_{seed}"
        cmd = (f"authbc-sat --mode=broadcast --nNodes={n} --seed={seed} --frameSize={frame} "
               f"--simTime={sim_t} {args} --outPrefix={prefix}")
        subprocess.run(["./ns3", "run", cmd], cwd=NS3, check=True, capture_output=True, text=True)
        stats = dict(line.split(",", 1)
                     for line in Path(prefix + ".stats").read_text().splitlines()[1:])
        out.append(float(stats["goodput_mbps"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="NS-3 deployment-geometry sensitivity")
    ap.add_argument("--nNodes", type=int, default=20)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--frameSize", type=int, default=1400)
    ap.add_argument("--simTime", type=float, default=10.0)
    args = ap.parse_args()

    if not (NS3 / "ns3").exists():
        raise SystemExit(f"NS-3 not built at {NS3} — see ns3/README.md")
    (NS3 / "scratch" / "authbc-sat.cc").write_bytes((REPO / "ns3" / "authbc-sat.cc").read_bytes())
    subprocess.run(["./ns3", "build", "authbc-sat"], cwd=NS3, check=True, capture_output=True)

    rows: list[dict] = []
    baseline: float | None = None
    with tempfile.TemporaryDirectory() as outdir:
        for label, extra in SCENARIOS:
            vals = _run(label, extra, args.nNodes, args.seeds, args.frameSize,
                        args.simTime, outdir)
            med = st.median(vals)
            if baseline is None:
                baseline = med
            rows.append({
                "scenario": label, "N": args.nNodes, "frameSize": args.frameSize,
                "simTime": args.simTime, "seeds": args.seeds,
                "goodput_mbps_median": round(med, 4),
                "goodput_mbps_min": round(min(vals), 4),
                "goodput_mbps_max": round(max(vals), 4),
                "delta_vs_controlled_pct": round(100 * (med - baseline) / baseline, 2),
            })
            print(f"  {label:<26} {med:8.4f} Mb/s  "
                  f"{rows[-1]['delta_vs_controlled_pct']:+7.2f}%")

    RESULTS.mkdir(parents=True, exist_ok=True)
    cfg = {"scenarios": [s for s, _ in SCENARIOS], "N": args.nNodes, "seeds": args.seeds,
           "frameSize": args.frameSize, "simTime": args.simTime}
    meta = {**provenance.env_block(), "run": "ns3_sensitivity", "ns3_version": "3.41",
            "config_hash": provenance.config_hash(cfg)}
    path = RESULTS / "ns3_sensitivity.csv"
    with path.open("w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} scenarios)")


if __name__ == "__main__":
    main()
