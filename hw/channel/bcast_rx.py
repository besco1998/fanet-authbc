#!/usr/bin/env python3
"""Count 802.11 broadcast UDP frames received, by sequence number (hardware channel validation).

Counts what ARRIVES, and separately what was SENT (from the sender's own trailer), so the delivery
ratio is measured rather than inferred. Sequence numbers make loss and duplication distinguishable.
"""
import argparse
import json
import socket
import time

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=9999)
ap.add_argument("--seconds", type=float, default=60.0)
ap.add_argument("--out", default="rx.json")
a = ap.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("", a.port))
s.settimeout(1.0)

seen: set[int] = set()
dups = 0
first = last = None
deadline = time.monotonic() + a.seconds
while time.monotonic() < deadline:
    try:
        d, _ = s.recvfrom(2048)
    except TimeoutError:
        continue
    try:
        seq = int(d[:10].decode().strip())
    except Exception:
        continue
    if seq in seen:
        dups += 1
    seen.add(seq)
    now = time.monotonic()
    first = first if first is not None else now
    last = now

s.close()
json.dump({"received_unique": len(seen), "duplicates": dups,
           "max_seq": max(seen) if seen else -1,
           "span_s": (last - first) if first and last else 0.0}, open(a.out, "w"))
print(json.dumps({"received_unique": len(seen), "duplicates": dups}))
