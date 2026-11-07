#!/usr/bin/env python3
"""What a forged frame costs a receiver, and what stops it (revision A7; predictions/A7.md).

Written before any timing (the registration's harness). Every path below is one the unit tests
of `placement/admission.py` define; nothing here is a new receiver.

Part A, ``--part costs``: the time ONE frame takes on each path, with the bench's own timer
(`bench.timers.time_op`: warm-up, at least 10 000 operations and 200 ms, median and bootstrap
interval). An honest frame through each policy; the plan's worst-case forged frame (a real
sender, a newer sequence number, a well-formed signature by another key) through each policy;
what each cheap refusal costs; the HMAC check and an Ed25519 verification alone, for the batch
row, which is arithmetic: the frame's cost with its verification at 0.46 of a single one
(`hw/ed25519_batch`, measured on pi-B).

Part B, ``--part flood``: the plan's design. One receiver process, pinned to one core, reads a
local UDP socket (no radio) through `AdmissionReceiver`; a sender process on another core sends
the honest load (every sender at 12.5 frames/s, staggered) and forged frames at a set rate.
Honest V is honest frames accepted / honest frames sent; frames the kernel dropped at a full
socket count as lost, which is what an overloaded receiver does. The receiver's core share is
its CPU time over its wall time. Attacks:

    forged      the worst case, aimed round-robin at every sender, two frames ahead of it
    forged-one  the same frames, all naming one sender (an impostor of that sender)
    outsider    the worst case wrapped with a wrong group tag
    insider     the worst case wrapped with the right group tag (a member's key)

Loads: 124 senders (the registration) and 41, one core's share of 124 on the three cores 124
nodes need (F84) — added before any run, since one Python core cannot receive 124 senders even
unattacked (1550 frames/s at ~1.4 ms).

    python analysis/flood_cost.py --part costs     # results/hw/flood_cost.<host>.csv
    python analysis/flood_cost.py --part flood     # results/hw/flood_udp.<host>.csv
    python analysis/flood_cost.py --check          # seconds of each, any host: plumbing only
"""
from __future__ import annotations

import argparse
import csv
import io
import multiprocessing as mp
import os
import random
import socket
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.bench.stats import summarize  # noqa: E402
from authbc.bench.timers import time_op  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.placement.admission import AdmissionReceiver, GroupMac, Policy, Refused  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Received  # noqa: E402

B = 4                                   # records per frame: the design
FPS = 12.5                              # frames per second per sender at the adopted point
BATCH_VERIFY_FACTOR = 0.46              # hw/ed25519_batch on pi-B: batch-of-64 / single
CI_SEED = 20261022
RATES = (0, 250, 500, 750, 1000, 1500, 2000, 3000)
LOADS = (124, 41)
CONFIGS = (("none", "forged"), ("cheap", "forged"), ("cap", "forged-one"), ("cap", "forged"),
           ("mac", "outsider"), ("mac", "insider"))
DURATION_S = 15.0
RX_CPU, TX_CPU = 2, 3                   # pi-B has four cores; the parent stays on 0-1
ED = Ed25519Scheme()
SWARM_KEY = b"authbc A7 swarm key, 32 bytes.."
GROUP = GroupMac(SWARM_KEY)
WRONG = GroupMac(b"not the swarm key ............")


def _key(i: int) -> Any:
    return ED.keygen(seed=i.to_bytes(4, "big") * 8)


def build(senders: int, frames_each: int) -> tuple[dict[int, Any], list[list[bytes]],
                                                     list[list[bytes]]]:
    """Each sender's honest frames, and the same records signed by an attacker's key."""
    attacker, _ = ED.keygen(seed=b"\xa7" * 32)
    pks, honest, forged = {}, [], []
    for s in range(senders):
        sk, pk = _key(s + 1)
        pks[s + 1] = pk
        recs = leanframes.chained_records(1000 + s, frames_each * B, src=s + 1)
        groups = [recs[i:i + B] for i in range(0, len(recs), B)]
        honest.append([LeanSender(sk).frame(g) for g in groups])
        forged.append([LeanSender(attacker).frame(g) for g in groups])
    return pks, honest, forged


def policy(name: str) -> Policy:
    return {"none": Policy(), "cheap": Policy(cheap_checks=True),
            "cap": Policy(cheap_checks=True, rate_cap=FPS),
            "mac": Policy(group_mac=GROUP, cheap_checks=True)}[name]


# ------------------------------------------------------------------------------- part A: costs
class _Path:
    """Feeds frames to a receiver one per call, after `prime` (frames accepted first, so forged
    ones are 'newer' than the state they meet). Only a path whose frames change the receiver's
    state (accepted ones) needs a fresh receiver when the list wraps; the others cycle."""

    def __init__(self, make: Callable[[], Any], frames: list[bytes], prime: tuple[bytes, ...] = (),
                 *, stateful: bool = False, clock: bool = False) -> None:
        self._make, self._frames, self._prime = make, frames, list(prime)
        self._stateful, self._clock = stateful, clock
        self._reset()

    def _reset(self) -> None:
        self._rx, self._i = self._make(), 0
        for f in self._prime:
            self._take(f)

    def _take(self, frame: bytes) -> Received | Refused:
        if isinstance(self._rx, LeanReceiver):
            return self._rx.receive(frame)
        # a rate cap refills with time; every other path ignores it
        return self._rx.receive(frame, time.monotonic() if self._clock else 0.0)

    def __call__(self) -> int:
        if self._i == len(self._frames):
            if self._stateful:
                self._reset()
            self._i = 0
        got = self._take(self._frames[self._i])
        self._i += 1
        return len(got.receipt.value) if isinstance(got, Received) else len(got.value)


def cost_paths(frames_each: int = 260) -> dict[str, tuple[Callable[[], Any], str]]:
    """(path) -> (a call handling ONE frame, what that frame meets)."""
    pks, honest, forged = build(2, frames_each)
    h, f = honest[0], forged[0]
    pk = {1: pks[1], 2: pks[2]}

    def rx(p: Policy, keys: dict[int, Any] = pk) -> Callable[[], AdmissionReceiver]:
        return lambda: AdmissionReceiver(LeanReceiver(keys), p, frozenset(keys))

    member = [GROUP.wrap(x) for x in h]
    outsider = [WRONG.wrap(x) for x in f]
    rng = random.Random(CI_SEED)
    garbage = [rng.randbytes(len(x)) for x in h[:200]]
    _, verify_pk = _key(1)
    sig_msg, sig = h[1], ED.sign(_key(1)[0], h[1])
    return {
        "receiver_only": (_Path(lambda: LeanReceiver(pk), h, stateful=True),
                          "accepted, LeanReceiver alone"),
        "honest_none": (_Path(rx(Policy()), h, stateful=True), "accepted"),
        "honest_cheap": (_Path(rx(policy("cheap")), h, stateful=True), "accepted"),
        "honest_cap": (_Path(rx(Policy(cheap_checks=True, rate_cap=1e9)), h, stateful=True,
                             clock=True), "accepted"),
        "honest_mac": (_Path(rx(policy("mac")), member, stateful=True), "accepted"),
        # worst case: frames 1.. of the sender, signed by another key, after its frame 0
        "forged_none": (_Path(rx(Policy()), f[1:201], prime=tuple(h[:1])), "bad signature"),
        "forged_cheap": (_Path(rx(policy("cheap")), f[1:201], prime=tuple(h[:1])), "bad signature"),
        "forged_cap_refused": (_Path(rx(Policy(cheap_checks=True, rate_cap=FPS, burst=1.0)),
                                     f[2:202], prime=tuple(h[:1])), "refused: rate"),
        "insider_mac": (_Path(rx(policy("mac")), [GROUP.wrap(x) for x in f[1:201]],
                              prime=tuple(member[:1])), "bad signature"),
        "outsider_mac": (_Path(rx(policy("mac")), outsider[1:201]), "refused: mac"),
        "garbage_cheap": (_Path(rx(policy("cheap")), garbage), "refused: shape"),
        "replay_cheap": (_Path(rx(policy("cheap")), h[:200], prime=tuple(h[:200])),
                         "refused: seq window"),
        "unknown_cheap": (_Path(rx(policy("cheap"), {2: pk[2]}), h[:200]),
                          "refused: unknown sender"),
        "hmac_check": (lambda: len(GROUP.unwrap(member[0]) or b""), "tag check alone"),
        "ed25519_verify": (lambda: int(ED.verify(verify_pk, sig_msg, sig)),
                           f"one verification, {len(sig_msg)} B message"),
    }


def part_costs(check: bool) -> list[dict]:
    rows = []
    for path, (fn, meets) in cost_paths().items():
        floors = {"min_ops": 200, "min_total_ns": 50_000_000} if check else {}
        res = time_op(fn, batch=10, **floors)
        s = summarize(res.samples_ns, seed=CI_SEED)
        rows.append({"path": path, "meets": meets, "median_us": round(s.median / 1e3, 2),
                     "ci_lo_us": round(s.ci_lo / 1e3, 2), "ci_hi_us": round(s.ci_hi / 1e3, 2),
                     "n_ops": res.n_ops})
        print(f"{path:20s} {s.median / 1e3:9.2f} us  [{s.ci_lo / 1e3:.2f}, {s.ci_hi / 1e3:.2f}]"
              f"  {meets}", flush=True)
    by = {r["path"]: r["median_us"] for r in rows}
    batch = by["honest_cheap"] - by["ed25519_verify"] * (1 - BATCH_VERIFY_FACTOR)
    rows.append({"path": "honest_batch64_arith", "meets": "honest_cheap with its verification "
                 f"at {BATCH_VERIFY_FACTOR} of one (arithmetic, hw/ed25519_batch)",
                 "median_us": round(batch, 2), "ci_lo_us": "", "ci_hi_us": "", "n_ops": ""})
    return rows


# ------------------------------------------------------------------------------- part B: flood
def _udp_drops(port: int) -> int:
    """The kernel's drop count for the socket bound to `port` (/proc/net/udp, last column)."""
    for line in Path("/proc/net/udp").read_text().splitlines()[1:]:
        cols = line.split()
        if int(cols[1].split(":")[1], 16) == port:
            return int(cols[-1])
    return -1


def _receiver(pol: Policy, pks: dict[int, Any], ready: Any, done: Any, out: Any) -> None:
    try:
        os.sched_setaffinity(0, {RX_CPU})
    except (AttributeError, OSError):
        pass
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(0.05)
    port = sock.getsockname()[1]
    rx = AdmissionReceiver(LeanReceiver(pks), pol, frozenset(pks))
    counts: Counter[str] = Counter()
    ready.put(port)
    t0 = c0 = None
    while True:
        try:
            data = sock.recv(4096)
        except TimeoutError:
            if done.is_set():
                break
            continue
        if t0 is None:
            t0, c0 = time.monotonic(), time.process_time()
        got = rx.receive(data, time.monotonic())
        counts[got.receipt.value if isinstance(got, Received) else "refused_" + got.value] += 1
    t1, c1 = time.monotonic(), time.process_time()
    out.put({"counts": dict(counts), "rx_wall_s": (t1 - t0) if t0 else 0.0,
             "rx_cpu_s": (c1 - c0) if c0 is not None else 0.0, "kernel_drops": _udp_drops(port)})


def _schedule(senders: int, rate: float, duration: float) -> list[tuple[float, int, int]]:
    """(time, sender, frame index) for honest frames (index ≥ 0) and attack frames (index −1)."""
    ev = [((j + s / senders) / FPS, s, j) for s in range(senders)
          for j in range(int(duration * FPS))]
    if rate > 0:
        ev += [(k / rate, k, -1) for k in range(int(duration * rate))]
    return sorted(ev)


def _sender(port: int, events: list, honest: list, forged: list, attack: str,
            senders: int, out: Any) -> None:
    try:
        os.sched_setaffinity(0, {TX_CPU})
    except (AttributeError, OSError):
        pass
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = ("127.0.0.1", port)
    wrap = {"outsider": WRONG.wrap, "insider": GROUP.wrap}.get(attack)
    honest_wrap = GROUP.wrap if attack in ("outsider", "insider") else None
    sent: Counter[str] = Counter()
    start = time.monotonic() + 0.2
    for t, s, j in events:
        while time.monotonic() - start < t:
            pass
        if j >= 0:
            frame = honest[s][j]
            sock.sendto(honest_wrap(frame) if honest_wrap else frame, addr)
            sent["honest"] += 1
            continue
        target = 0 if attack == "forged-one" else s % senders
        ahead = min(int(t * FPS) + 2, len(forged[target]) - 1)   # two frames ahead of it
        frame = forged[target][ahead]
        sock.sendto(wrap(frame) if wrap else frame, addr)
        sent["attack"] += 1
    out.put({"honest_sent": sent["honest"], "attack_sent": sent["attack"],
             "tx_wall_s": time.monotonic() - start})


def flood_run(senders: int, pol_name: str, attack: str, rate: float, duration: float,
              built: tuple) -> dict:
    pks, honest, forged = built
    ctx = mp.get_context("fork")
    ready, done, rx_out, tx_out = ctx.Queue(), ctx.Event(), ctx.Queue(), ctx.Queue()
    rxp = ctx.Process(target=_receiver, args=(policy(pol_name), pks, ready, done, rx_out))
    rxp.start()
    port = ready.get(timeout=30)
    txp = ctx.Process(target=_sender, args=(port, _schedule(senders, rate, duration), honest,
                                            forged, attack, senders, tx_out))
    txp.start()
    tx = tx_out.get(timeout=duration * 4 + 60)
    txp.join()
    done.set()                         # the receiver drains its socket, then stops
    rx = rx_out.get(timeout=duration * 20 + 120)
    rxp.join()
    c = rx["counts"]
    honest_ok = c.get("accepted", 0)
    return {"senders": senders, "policy": pol_name, "attack": attack, "rate_offered": rate,
            "duration_s": duration, **tx,
            "attack_rate_sent": round(tx["attack_sent"] / tx["tx_wall_s"], 1),
            "received": sum(c.values()), "kernel_drops": rx["kernel_drops"],
            "honest_accepted": honest_ok,
            "honest_V": round(honest_ok / tx["honest_sent"], 4) if tx["honest_sent"] else "",
            "rx_cpu_s": round(rx["rx_cpu_s"], 3), "rx_wall_s": round(rx["rx_wall_s"], 3),
            "core_share": round(rx["rx_cpu_s"] / rx["rx_wall_s"], 4) if rx["rx_wall_s"] else 0,
            "counts": ";".join(f"{k}={v}" for k, v in sorted(c.items()))}


def part_flood(check: bool) -> list[dict]:
    loads, rates, duration = ((8,), (0, 500), 2.0) if check else (LOADS, RATES, DURATION_S)
    rows = []
    for senders in loads:
        built = build(senders, int(duration * FPS) + 4)
        for pol_name, attack in CONFIGS:
            for rate in rates:
                row = flood_run(senders, pol_name, attack, rate, duration, built)
                rows.append(row)
                print(f"{senders:4d} {pol_name:5s} {attack:10s} {rate:5.0f}/s  V {row['honest_V']}"
                      f"  core {row['core_share']}  drops {row['kernel_drops']}"
                      f"  sent {row['attack_rate_sent']}/s  {row['counts']}", flush=True)
                time.sleep(0.5 if check else 3.0)
    return rows


# ------------------------------------------------------------------------------- output
def _board() -> dict[str, str]:
    def run(*cmd: str) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=5).stdout.strip() or "NA"
        except (OSError, subprocess.SubprocessError):
            return "NA"
    return {"throttled": run("vcgencmd", "get_throttled"),
            "arm_clock": run("vcgencmd", "measure_clock", "arm")}


def write(rows: list[dict], name: str, config: dict, before: dict, check: bool) -> Path:
    host = socket.gethostname()
    out = REPO / "results" / "hw" / f"{name}.{host}{'.check' if check else ''}.csv"
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": name, "config_hash": provenance.config_hash(config),
            **{f"before_{k}": v for k, v in before.items()},
            **{f"after_{k}": v for k, v in _board().items()}}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(buf.getvalue())
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", choices=("costs", "flood"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    parts = ("costs", "flood") if args.check else (args.part,)
    if parts == (None,):
        ap.error("--part or --check")
    for part in parts:
        before = _board()
        config: dict[str, Any]
        if part == "costs":
            rows = part_costs(args.check)
            config = {"b": B, "batch_factor": BATCH_VERIFY_FACTOR}
        else:
            rows = part_flood(args.check)
            config = {"rates": RATES, "loads": LOADS, "configs": CONFIGS, "T": DURATION_S,
                      "cpus": (RX_CPU, TX_CPU)}
        print(write(rows, "flood_cost" if part == "costs" else "flood_udp", config, before,
                    args.check))


if __name__ == "__main__":
    main()
