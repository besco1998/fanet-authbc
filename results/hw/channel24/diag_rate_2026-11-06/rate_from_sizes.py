#!/usr/bin/env python3
"""The broadcast PHY rate of each sender, from two frame sizes (diagnostic, 2026-11-06).

Each Pi sends alone, saturated, once with 145 B and once with 1000 B of UDP payload. The cycle
between frames is read at the receivers, as W1d's rate check does: span / sequence range. The
fixed costs (preamble, DIFS, backoff) are the same at both sizes, so the difference is the 855
extra bytes on air: rate = 855 * 8 / (cycle_1000 - cycle_145).

    python3 -I rate_from_sizes.py <session dir with node1..node3>
"""
import glob
import json
import os
import statistics as st
import sys

D = sys.argv[1]
SMALL, LARGE = 145, 1000


def load(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


cycles: dict[tuple[int, int], float] = {}
for path in sorted(glob.glob(os.path.join(D, "node1", "ctr_node1_*.json"))):
    tag = os.path.basename(path)[len("ctr_node1_"):-len(".json")]
    ctr = load(path)
    s, size = int(ctr["senders"]), int(ctr["bytes"])
    tx = load(os.path.join(D, f"node{s}", f"tx_node{s}_{tag}.json"))
    got = [load(os.path.join(D, f"node{r}", f"rx_node{r}_{tag}.json"))["by_source"]
           .get(f"10.0.0.{s}", {}) for r in (1, 2, 3) if r != s]
    cyc = 1e6 * st.mean(g["span_s"] / (g["max_seq"] - g["min_seq"]) for g in got)
    cycles[(s, size)] = cyc
    print(f"{tag}: sender {s}, {size} B, sent {tx['sent']} at {tx['achieved_fps']:.1f}/s, "
          f"received {[g['received_unique'] for g in got]}, cycle {cyc:.1f} us")
for s in (1, 2, 3):
    if (s, SMALL) in cycles and (s, LARGE) in cycles:
        diff = cycles[(s, LARGE)] - cycles[(s, SMALL)]
        print(f"node {s}: {cycles[(s, SMALL)]:.1f} / {cycles[(s, LARGE)]:.1f} us, "
              f"difference {diff:.1f} us -> {(LARGE - SMALL) * 8 / diff:.2f} Mb/s")
