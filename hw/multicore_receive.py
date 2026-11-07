#!/usr/bin/env python3
"""Frames a second the lean receiver handles on K cores at once (hw/BENCH_SESSION.md; audit F84).

One core of the interpreted prototype serves 57 nodes, and 124 nodes need 2.2 cores — by
arithmetic from one core's time. This measures whether the board's cores deliver that when
they run together: K worker processes, one per core, each a `LeanReceiver` fed real frames of
its own senders from memory, started together and stopped at the same instant.

What it is not: there is no radio and no dispatcher. A frame reaches its worker for free here;
in a deployed receiver the kernel or a parent process would have to hand each sender's frames
to one worker. So this is what the cores deliver to the receive path, not the path from a
socket. Senders are independent in the receiver (state is per sender), which is why the work
divides by sender at all.

    python hw/multicore_receive.py                 # K = 1 2 3 4, 30 s each
    python hw/multicore_receive.py --check         # x86 self-test, one second per K

Writes results/hw/multicore_receive.<host>.csv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import multiprocessing as mp
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.crypto.registry import get_scheme  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt  # noqa: E402

BATCH = 4                       # records per frame: the design
RECORDS = 4000                  # 1000 distinct frames per stream, as authbc.bench.micro times
FRAMES_PER_NODE_S = 50.0 / BATCH        # 12.5: what one neighbour sends at the adopted point
PAUSE_S = 20.0                  # between runs, for the board to cool


def _vcgencmd(what: str) -> str:
    try:
        return subprocess.run(["vcgencmd", what], capture_output=True, text=True,
                              timeout=5).stdout.strip() or "NA"
    except (OSError, subprocess.SubprocessError):
        return "NA"


def _device() -> dict[str, str]:
    def read(path: str) -> str:
        try:
            return Path(path).read_text().replace("\0", "").strip()
        except OSError:
            return "NA"
    return {"device_model": read("/proc/device-tree/model"), "device_host": socket.gethostname(),
            "device_governor": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            "device_cores": str(os.cpu_count())}


def stream(seed: int) -> tuple[list[bytes], int, Any]:
    """A real stream of frames: chained records, delta coded, signed. (frames, src, key).

    The stream `authbc.bench.micro` times one frame of, key included, so that one worker here
    is that benchmark run as a loop."""
    scheme = get_scheme("ed25519")
    sk, pk = scheme.keygen(seed=hashlib.sha256(f"{seed}:lean".encode()).digest())
    recs = leanframes.chained_records(seed, RECORDS)
    groups = [recs[i:i + BATCH] for i in range(0, len(recs) - BATCH + 1, BATCH)]
    sender = LeanSender(sk)
    return [sender.frame(g) for g in groups], recs[0].src, pk


def work(core: int, seed: int, ready: Any, go: Any, seconds: float, out: Any) -> None:
    """One core: receive frames for `seconds` once every worker is ready. Reports its count."""
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {core})
    frames, src, pk = stream(seed)
    keys = {src: pk}
    rx = LeanReceiver(keys)
    ready.wait()
    go.wait()
    done = i = 0
    start = time.monotonic()
    stop = start + seconds
    while time.monotonic() < stop:
        if i == len(frames):                 # a receiver refuses a sequence number it has seen
            i, rx = 0, LeanReceiver(keys)
        if rx.receive(frames[i]).receipt is not Receipt.ACCEPTED:
            raise RuntimeError("a valid frame was not accepted")
        i += 1
        done += 1
    out.put((core, done, time.monotonic() - start))


def run(workers: int, seconds: float, seed: int) -> dict:
    ctx = mp.get_context("fork")
    ready, go, out = ctx.Barrier(workers + 1), ctx.Event(), ctx.Queue()
    procs = [ctx.Process(target=work, args=(core, seed, ready, go, seconds, out))
             for core in range(workers)]
    before = {"temp": _vcgencmd("measure_temp"), "throttled": _vcgencmd("get_throttled")}
    for p in procs:
        p.start()
    ready.wait()                             # every worker has built its frames
    go.set()
    results = [out.get() for _ in procs]
    for p in procs:
        p.join()
    after = {"temp": _vcgencmd("measure_temp"), "throttled": _vcgencmd("get_throttled")}
    rates = sorted(n / t for _, n, t in results)
    total = sum(rates)
    return {"workers": workers, "seconds": seconds, "frames": sum(n for _, n, _t in results),
            "frames_per_s": round(total, 2), "worker_min_fps": round(rates[0], 2),
            "worker_max_fps": round(rates[-1], 2),
            "nodes_served": 1 + int(total // FRAMES_PER_NODE_S),
            "temp_before": before["temp"], "temp_after": after["temp"],
            "throttled_before": before["throttled"], "throttled_after": after["throttled"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, nargs="+", default=[1, 2, 3, 4])
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--check", action="store_true", help="one second per run, nothing written")
    args = ap.parse_args()
    seconds = 1.0 if args.check else args.seconds
    rows = []
    for k, workers in enumerate(args.workers):
        if k and not args.check:
            time.sleep(PAUSE_S)
        rows.append(run(workers, seconds, args.seed))
        print({key: rows[-1][key] for key in ("workers", "frames_per_s", "nodes_served",
                                              "temp_after", "throttled_after")}, flush=True)
    base = rows[0]["frames_per_s"] / rows[0]["workers"]
    for r in rows:
        r["times_one_core"] = round(r["frames_per_s"] / base, 3)
    if args.check:
        print("OK: multicore_receive.py --check ran", len(rows), "runs")
        return
    buf = io.StringIO()
    meta = {**_device(), "run_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            **provenance.env_block(), "run": "multicore_receive", "seed": args.seed,
            "batch": BATCH, "frames_per_node_s": FRAMES_PER_NODE_S, "pause_s": PAUSE_S}
    for key, value in meta.items():
        buf.write(f"# {key}={value}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out = REPO / "results" / "hw" / f"multicore_receive.{socket.gethostname()}.csv"
    out.write_text(buf.getvalue())
    print(f"DONE wrote {out}", flush=True)


if __name__ == "__main__":
    main()
