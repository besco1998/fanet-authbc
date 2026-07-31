"""Run the NS-3 authbc-sat saturation matrix → results/raw/ns3_matrix.csv (P6b, docs/04 §3).

Sweeps N × mode × seed, saturated. Each run's channel goodput is parsed from its `.stats`
(never hand-copied). Frame payload = a real AUTHBC frame size (CBOR self-batch near b_max) so
Bianchi's L matches the MAC payload directly (PacketSocket → no IP/UDP headers).
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

from authbc.bench import provenance

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
from ns3_paths import ns3_root  # noqa: E402

NS3 = ns3_root()   # D4: pinned tree, override with AUTHBC_NS3 (ns3/ns3_paths.py)
RESULTS = REPO / "results" / "raw"

N_VALUES = (5, 10, 20, 35, 50)
MODES = ("unicast", "broadcast")


def _run_one(n: int, mode: str, seed: int, frame_size: int, sim_time: float, outdir: str) -> dict:
    prefix = f"{outdir}/{mode}_{n}_{seed}"
    arg = (f"authbc-sat --mode={mode} --nNodes={n} --seed={seed} "
           f"--frameSize={frame_size} --simTime={sim_time} --outPrefix={prefix}")
    subprocess.run(["./ns3", "run", arg], cwd=NS3, check=True, capture_output=True, text=True)
    d: dict[str, str] = {}
    for line in Path(prefix + ".stats").read_text().splitlines()[1:]:
        k, _, v = line.partition(",")
        d[k.strip()] = v.strip()
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="NS-3 saturation matrix")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--frameSize", type=int, default=1400)
    ap.add_argument("--simTime", type=float, default=10.0)
    # F28: the published bands were measured at 1400 B only, but the co-design operates at
    # 72-288 B where per-frame overhead dominates instead of payload. Allow a distinct output so
    # the small-frame validation is an added artifact rather than a replacement.
    ap.add_argument("--out", default="ns3_matrix.csv")
    args = ap.parse_args()

    if not (NS3 / "ns3").exists():
        raise SystemExit(f"NS-3 not built at {NS3} — see ns3/README.md")
    (NS3 / "scratch" / "authbc-sat.cc").write_bytes((REPO / "ns3" / "authbc-sat.cc").read_bytes())
    subprocess.run(["./ns3", "build", "authbc-sat"], cwd=NS3, check=True, capture_output=True)

    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as outdir:
        for n in N_VALUES:
            for mode in MODES:
                for seed in range(1, args.seeds + 1):
                    d = _run_one(n, mode, seed, args.frameSize, args.simTime, outdir)
                    rows.append({"N": n, "mode": mode, "seed": seed,
                                 "frameSize": args.frameSize, "simTime": args.simTime,
                                 "goodput_mbps": d["goodput_mbps"]})
            print(f"  N={n} done ({len(rows)} runs)")

    RESULTS.mkdir(parents=True, exist_ok=True)
    cfg = {"N": list(N_VALUES), "modes": list(MODES), "seeds": args.seeds,
           "frameSize": args.frameSize, "simTime": args.simTime}
    meta = {**provenance.env_block(), "run": args.out.replace(".csv", ""), "ns3_version": "3.41",
            "config_hash": provenance.config_hash(cfg)}
    fields = ["N", "mode", "seed", "frameSize", "simTime", "goodput_mbps"]
    path = RESULTS / args.out
    with path.open("w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
