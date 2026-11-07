#!/usr/bin/env python3
"""W1f, reported and not scored: loss of each ordered (sender, receiver) pair in a window label.

Reads the session's raw files only. A collision without capture loses every frame involved at
every receiver, so equal senders at equal rates lose alike; loss that depends on the sender and
not on the receiver means collisions are won by particular senders (capture by the stronger one).
    python sender_receiver.py <session_dir> <label> [<rate>]   e.g. ... A32   or   ... ABCD 111
"""
import glob
import json
import os
import re
import sys

S, LAB = sys.argv[1], sys.argv[2]
RATE = sys.argv[3] if len(sys.argv) > 3 else None
NAMES = {1: "pi-A", 2: "pi-B", 3: "Pi 3", 4: "TP-Link"}


def load(kind, node, tag):
    with open(os.path.join(S, f"node{node}", f"{kind}_node{node}_{tag}.json")) as fh:
        return json.load(fh)


tags = sorted({m.group(1) for p in glob.glob(os.path.join(S, "node*", "*_node*_*.json"))
               if (m := re.fullmatch(r"(?:tx|rx|ctr)_node\d_(.+)\.json", os.path.basename(p)))
               and m.group(1).split("_")[1] == LAB
               and (RATE is None or m.group(1).endswith(f"_{RATE}fps"))})
loss: dict[tuple[int, int], list[float]] = {}
for t in tags:
    for s in NAMES:
        sent = load("tx", s, t)["sent"]
        for r in NAMES:
            if r != s:
                got = load("rx", r, t)["by_source"].get(f"10.0.0.{s}", {}).get("received_unique", 0)
                loss.setdefault((s, r), []).append(1 - got / sent)
where = f" at {RATE}/s" if RATE else ""
print(f"{LAB}{where}: {len(tags)} windows; loss % (sender rows, receiver columns)")
print("sender,receiver," + ",".join(NAMES[r] for r in NAMES) + ",sender mean")
for s in NAMES:
    cells = [f"{100 * sum(loss[(s, r)]) / len(loss[(s, r)]):.2f}" if r != s else "" for r in NAMES]
    mean = sum(sum(loss[(s, r)]) / len(loss[(s, r)]) for r in NAMES if r != s) / 3
    print(f"{NAMES[s]}," + ",".join(cells) + f",{100 * mean:.2f}")
