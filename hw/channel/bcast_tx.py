#!/usr/bin/env python3
"""Send sequence-numbered 802.11 broadcast UDP frames at a controlled rate.

Two schedules. The default sends strictly periodically, as the two-radio link test of August
2026 did. `--redraw` sends one frame per period at an instant drawn uniformly within it — the
traffic source the capacity simulations use (docs/NMAX_DIRECT_EXPECTATIONS.md). With several
transmitters the strictly periodic schedule freezes their relative phases for a whole window:
two radios' clocks drift by microseconds per second, so a window would sample one phase
configuration and say little about the mean. The contention experiment therefore uses
`--redraw` (docs/CONTENTION_HW_EXPECTATIONS.md).
"""
import argparse
import json
import random
import socket
import time


def send_offsets(n_frames: int, period_s: float, redraw: bool, seed: int) -> list[float]:
    """Seconds after the start at which each frame is offered."""
    if not redraw:
        return [k * period_s for k in range(n_frames)]
    rng = random.Random(seed)
    return [(k + rng.random()) * period_s for k in range(n_frames)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="10.0.0.255")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--bytes", type=int, default=1400)
    ap.add_argument("--rate", type=float, default=100.0, help="frames per second")
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", default="tx.json")
    ap.add_argument("--redraw", action="store_true",
                    help="one frame per period at a uniformly drawn instant within it")
    ap.add_argument("--seed", type=int, default=1, help="seed of the drawn instants")
    a = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    pad = b"x" * max(0, a.bytes - 10)
    period = 1.0 / a.rate
    offsets = send_offsets(int(a.seconds * a.rate), period, a.redraw, a.seed)
    sent = late = 0
    t0 = time.monotonic()
    deadline = t0 + a.seconds
    for offset in offsets:
        slack = t0 + offset - time.monotonic()
        if slack > 0:
            time.sleep(slack)
        elif slack < -period:
            late += 1                      # the schedule fell a whole period behind
        if time.monotonic() >= deadline:
            break
        s.sendto(f"{sent:<10}".encode() + pad, (a.dest, a.port))
        sent += 1
    elapsed = time.monotonic() - t0
    s.close()
    with open(a.out, "w") as fh:
        json.dump({"sent": sent, "elapsed_s": elapsed, "achieved_fps": sent / elapsed,
                   "bytes": a.bytes, "rate": a.rate, "redraw": a.redraw, "seed": a.seed,
                   "late": late}, fh)
    print(json.dumps({"sent": sent, "achieved_fps": round(sent / elapsed, 1), "late": late}))


if __name__ == "__main__":
    main()
