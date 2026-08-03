#!/usr/bin/env python3
"""Send sequence-numbered 802.11 broadcast UDP frames at a controlled rate."""
import argparse
import json
import socket
import time

ap = argparse.ArgumentParser()
ap.add_argument("--dest", default="10.0.0.255")
ap.add_argument("--port", type=int, default=9999)
ap.add_argument("--bytes", type=int, default=1400)
ap.add_argument("--rate", type=float, default=100.0, help="frames per second")
ap.add_argument("--seconds", type=float, default=60.0)
ap.add_argument("--out", default="tx.json")
a = ap.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
pad = b"x" * max(0, a.bytes - 10)
period = 1.0 / a.rate
sent = 0
t0 = time.monotonic()
deadline = t0 + a.seconds
nxt = t0
while time.monotonic() < deadline:
    s.sendto(f"{sent:<10}".encode() + pad, (a.dest, a.port))
    sent += 1
    nxt += period
    slack = nxt - time.monotonic()
    if slack > 0:
        time.sleep(slack)
elapsed = time.monotonic() - t0
s.close()
json.dump({"sent": sent, "elapsed_s": elapsed, "achieved_fps": sent / elapsed,
           "bytes": a.bytes}, open(a.out, "w"))
print(json.dumps({"sent": sent, "achieved_fps": round(sent / elapsed, 1)}))
