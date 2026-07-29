"""Measure NS-3's DCF slot statistics directly → results/raw/ns3_dcf_residual.csv.

Answers the P6/P7 open question "why does NS-3 broadcast beat the no-ACK Bianchi prediction by 14×
at N=50?" by instrumenting the access process instead of inferring from goodput (docs/audits/p7.md).

For each run it reports what Bianchi's model predicts internally and what NS-3 actually does:
  busy_per_s        virtual-slot rate — tests the model's channel-time arithmetic
  mean_multiplicity transmissions per busy period — tests the model's access rate
  p_s_measured      P(exactly one transmitter | busy) — the quantity the 14× gap lives in
  p_s_independent   what p_s would be for INDEPENDENT stations at that same mean multiplicity;
                    the difference from p_s_measured is exactly the decoupling-assumption error
  winner_*          whether the next transmitter comes from the previous busy period (the
                    post-transmission head start) versus a uniformly random station
  p_succ_after_*    success rate split by whether the previous busy period collided
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

from authbc.bench import provenance
from authbc.sim import dcf_trace as dt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
from ns3_paths import ns3_root  # noqa: E402

NS3 = ns3_root()   # D4: pinned tree, override with AUTHBC_NS3 (ns3/ns3_paths.py)
RESULTS = REPO / "results" / "raw"

N_VALUES = (5, 10, 20, 35, 50)
# Discard the first and last 0.5 s of offered traffic so every busy period analysed is in the
# saturated steady state (sources run [1, simTime+1]).
GUARD_S = 0.5

FIELDS = [
    "N", "mode", "seed", "frameSize", "simTime", "goodput_mbps", "goodput_window_mbps",
    "window_s", "busy_periods", "busy_per_s", "transmissions", "mean_multiplicity",
    "p_s_measured", "p_s_independent", "tau_matched", "idle_slots_per_busy",
    "winner_participant_frac", "winner_uniform_frac", "winner_enrichment",
    "winner_pairs", "p_succ_after_collision", "p_succ_after_success",
    "rx_ok_node0", "rx_drop_node0",
]


def _run_one(n: int, mode: str, seed: int, frame_size: int, sim_time: float,
             outdir: str, equal_power: bool) -> dict[str, str | float | int]:
    prefix = f"{outdir}/{mode}_{n}_{seed}"
    arg = (f"authbc-dcf-trace --mode={mode} --nNodes={n} --seed={seed} "
           f"--frameSize={frame_size} --simTime={sim_time} "
           f"--equalPower={int(equal_power)} --outPrefix={prefix}")
    subprocess.run(["./ns3", "run", arg], cwd=NS3, check=True, capture_output=True, text=True)

    stats: dict[str, str] = {}
    for line in Path(prefix + ".stats").read_text().splitlines()[1:]:
        k, _, v = line.partition(",")
        stats[k.strip()] = v.strip()

    with Path(prefix + ".tx.csv").open() as fh:
        periods = dt.busy_periods(dt.parse_tx_events(fh))
    lo = int((1.0 + GUARD_S) * 1e9)
    hi = int((sim_time + 1.0 - GUARD_S) * 1e9)
    window = dt.within(periods, lo, hi)
    span_s = (hi - lo) / 1e9

    mean_mult = dt.mean_multiplicity(window)
    hs = dt.winner_was_participant(window, n)
    successes = sum(1 for p in window if p.is_success)
    # Idle backoff slots between busy periods, from the gaps: (gap − DIFS) / slot. Bianchi puts
    # this at ~0.002 per busy period at N=50; the real process spends ~0.74 (audit A2).
    difs_ns, slot_ns = 34_000, 9_000
    gaps = dt.deferral_gaps(window)
    idle = sum(round((g - difs_ns) / slot_ns) for g, _, _ in gaps) / len(gaps) if gaps else 0.0
    return {
        "N": n, "mode": mode, "seed": seed, "frameSize": frame_size, "simTime": sim_time,
        # `goodput_mbps` is the scenario's own PacketSink figure over [1, simTime+1] — the number
        # the frozen matrix carries. `goodput_window_mbps` is derived from the SAME busy periods as
        # every other column here, so the row is internally consistent: p_s × busy_per_s × 8L must
        # reproduce it exactly. Comparing a model against a mixed-window row was audit finding A11.
        "goodput_mbps": stats["goodput_mbps"],
        "goodput_window_mbps": round(successes * 8.0 * frame_size / span_s / 1e6, 6),
        "window_s": span_s,
        "busy_periods": len(window),
        "busy_per_s": round(len(window) / span_s, 3),
        "transmissions": sum(p.multiplicity for p in window),
        "mean_multiplicity": round(mean_mult, 5),
        "p_s_measured": round(dt.measured_p_success(window), 6),
        "p_s_independent": round(dt.matched_binomial_p_success(n, mean_mult), 6),
        "tau_matched": round(dt.tau_matching_mean(n, mean_mult), 6),
        "idle_slots_per_busy": round(idle, 5),
        "winner_participant_frac": round(hs.observed_fraction, 6),
        "winner_uniform_frac": round(hs.expected_fraction, 6),
        "winner_enrichment": round(hs.enrichment, 4),
        "winner_pairs": hs.transitions,
        "p_succ_after_collision": round(hs.p_success_after_collision, 6),
        "p_succ_after_success": round(hs.p_success_after_success, 6),
        "rx_ok_node0": stats["rx_ok_node0"],
        "rx_drop_node0": stats["rx_drop_node0"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="NS-3 DCF slot-statistics measurement")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--frameSize", type=int, default=1400)
    ap.add_argument("--simTime", type=float, default=10.0)
    ap.add_argument("--modes", nargs="+", default=["broadcast", "unicast"])
    ap.add_argument("--equalPower", action="store_true",
                    help="constant path loss on every link (Bianchi's symmetric-station premise)")
    args = ap.parse_args()

    if not (NS3 / "ns3").exists():
        raise SystemExit(f"NS-3 not built at {NS3} — see ns3/README.md")
    (NS3 / "scratch" / "authbc-dcf-trace.cc").write_bytes(
        (REPO / "ns3" / "authbc-dcf-trace.cc").read_bytes())
    subprocess.run(["./ns3", "build", "authbc-dcf-trace"], cwd=NS3, check=True, capture_output=True)

    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as outdir:
        for n in N_VALUES:
            for mode in args.modes:
                for seed in range(1, args.seeds + 1):
                    rows.append(_run_one(n, mode, seed, args.frameSize, args.simTime,
                                         outdir, args.equalPower))
            print(f"  N={n} done ({len(rows)} runs)")

    RESULTS.mkdir(parents=True, exist_ok=True)
    cfg = {"N": list(N_VALUES), "modes": args.modes, "seeds": args.seeds,
           "frameSize": args.frameSize, "simTime": args.simTime,
           "guard_s": GUARD_S, "equalPower": args.equalPower}
    meta = {**provenance.env_block(), "run": "ns3_dcf_residual", "ns3_version": "3.41",
            "config_hash": provenance.config_hash(cfg)}
    path = RESULTS / "ns3_dcf_residual.csv"
    with path.open("w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
