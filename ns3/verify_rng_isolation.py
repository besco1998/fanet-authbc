#!/usr/bin/env python3
"""Guard against the RNG-stream confound that F36/F37 found in the mobility scenario.

**The defect class.** ns-3 hands every new `RandomVariableStream` the next index from a global
counter. So any configuration option whose objects are constructed *before* the senders shifts every
sender's stream, changing the traffic realisation for reasons that have nothing to do with the
physics being studied. In the mobility scenario this produced a convincing 5-point "mobility
penalty" that was pure bookkeeping (F37).

**The invariant.** `sent` counts transmissions by end devices. None of the options swept below can
physically change how many packets a device *transmits* — they change propagation, gateway
configuration, or how collisions are resolved, all of which act on *reception*. So:

    for a fixed seed, `sent` must be identical across every value of these options.

If it is not, the option is displacing the sender RNG and any comparison across it is confounded.

⚠️ `txJitter` is deliberately NOT checked. It selects a different sender class entirely
(`JitteredSender` vs the module's `PeriodicSender`), so a different `sent` is expected and correct —
that comparison is handled distributionally across 30 seeds instead (F32/F33).

Run: `make verify-rng-isolation`
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

BASE = ("--nDevices=20 --dataRate=5 --payloadBytes=218 --appPeriod=36.6 "
        "--simulationTime=600 --radius=1000 --txJitter=1.0")

# (axis, [option strings]) — every value of an axis must yield the same `sent`.
AXES: list[tuple[str, list[str]]] = [
    ("channelModel (F25)", ["--channelModel=ideal", "--channelModel=shadowing"]),
    ("gwRegion (E9)", ["--gwRegion=aloha", "--gwRegion=eu"]),
    ("interferenceMatrix (A2)", ["--interferenceMatrix=aloha", "--interferenceMatrix=goursaud"]),
]
DEFAULTS = "--channelModel=ideal --gwRegion=aloha --interferenceMatrix=aloha"


def _run(scenario: str, opts: str, seed: int) -> dict[str, str]:
    ns3 = ns3_root()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "r"
        subprocess.run(
            ["./ns3", "run", f"{scenario} {BASE} --seed={seed} {opts} --outPrefix={prefix}"],
            cwd=ns3, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--scenario", default="authbc-lora-capacity")
    a = ap.parse_args()

    failures = []
    for axis, options in AXES:
        sents = {}
        for opt in options:
            # Hold the other axes at their defaults so only this one varies. The later flag wins in
            # ns-3's CommandLine, so appending the axis value after the defaults overrides it.
            got = _run(a.scenario, f"{DEFAULTS} {opt}", a.seed)
            sents[opt] = int(got["sent"])
        uniq = set(sents.values())
        ok = len(uniq) == 1
        print(f"{'PASS' if ok else 'FAIL'}  {axis:28s} sent={sents}")
        if not ok:
            failures.append(axis)

    if failures:
        raise SystemExit(
            "\nRNG ISOLATION VIOLATED on: " + ", ".join(failures) +
            "\nThese options change how many packets are SENT, which is physically impossible —\n"
            "they are displacing the sender RNG streams. Every published comparison across them\n"
            "is confounded. Pin the sender streams (see JitteredSender::PinStreams in\n"
            "authbc-lora-capacity-mobile.cc) before trusting any number from that axis.")
    print("\nAll axes isolated: `sent` is invariant, so cross-axis comparisons are not confounded.")


if __name__ == "__main__":
    main()
