#!/usr/bin/env python3
"""Count 802.11 broadcast UDP frames received, by sender and sequence number.

Counts what ARRIVES, and separately what was SENT (from the sender's own record), so the delivery
ratio is measured rather than inferred. Sequence numbers make loss and duplication distinguishable.
With several transmitters each sender is counted on its own, by source address; `--self` names
this node's address so that its own broadcasts, which the kernel hands back to it, are left out.
"""
import argparse
import json
import socket
import time


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", default="rx.json")
    ap.add_argument("--self", dest="own", default="", help="this node's address; not counted")
    a = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Enlarge the receive buffer before binding. At the top of the load sweep (1600 fps x 1400 B =
    # 2.2 MB/s) the default ~208 KB buffer holds under 0.1 s of traffic, so a scheduling hiccup in
    # this Python loop would drop frames that the radio actually delivered — receiver loss recorded
    # as channel loss. The granted size is reported so the caveat can be checked rather than
    # assumed: the kernel silently caps this at net.core.rmem_max.
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    except OSError:
        pass
    rcvbuf = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

    s.bind(("", a.port))
    s.settimeout(1.0)

    seen: dict[str, set[int]] = {}
    dups: dict[str, int] = {}
    heard: dict[str, list[float]] = {}      # sender -> [first arrival, last arrival]
    first = last = None
    deadline = time.monotonic() + a.seconds
    while time.monotonic() < deadline:
        try:
            d, (src, _port) = s.recvfrom(2048)
        except TimeoutError:
            continue
        if src == a.own:
            continue
        try:
            seq = int(d[:10].decode().strip())
        except Exception:
            continue
        got = seen.setdefault(src, set())
        if seq in got:
            dups[src] = dups.get(src, 0) + 1
        got.add(seq)
        now = time.monotonic()
        first = first if first is not None else now
        last = now
        heard.setdefault(src, [now, now])[1] = now

    s.close()
    by_source = {src: {"received_unique": len(got), "duplicates": dups.get(src, 0),
                       "min_seq": min(got), "max_seq": max(got),
                       "span_s": heard[src][1] - heard[src][0]}
                 for src, got in sorted(seen.items())}
    everything = [seq for got in seen.values() for seq in got]
    with open(a.out, "w") as fh:
        json.dump({"received_unique": len(everything), "duplicates": sum(dups.values()),
                   "min_seq": min(everything) if everything else -1,
                   "max_seq": max(everything) if everything else -1,
                   "span_s": (last - first) if first and last else 0.0,
                   "rcvbuf_bytes": rcvbuf, "self": a.own, "by_source": by_source}, fh)
    print(json.dumps({"received_unique": len(everything), "senders": len(seen),
                      "duplicates": sum(dups.values())}))


if __name__ == "__main__":
    main()
