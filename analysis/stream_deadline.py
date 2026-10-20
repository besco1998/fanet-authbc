#!/usr/bin/env python3
"""Revision A10 — the stream-signing schemes, implemented and run on ns-3 traces
(predictions/A10.md).

Table 5 of the paper places MAVLink 2, TESLA, Gennaro–Rohatgi, EMSS and the Wong–Lam tree by
their frame sizes and counts a delivered frame as a verified record — an upper bound for the
schemes that make a receiver wait. Here each scheme is a sender and a receiver with real keys
(`authbc.placement.stream_schemes`), and the published ns-3 scenario (`ns3/authbc-links.cc`,
identical to the published one at its defaults) records, for 20 sender→receiver pairs per run,
which frames arrived and when. A record counts as VERIFIED IN TIME if the receiver could
authenticate it within D_max = 100 ms of the record being taken.

Timing, the same for every scheme: a record is taken when its frame is sent, or — for a scheme
that makes records wait for a batch at the sender (Wong–Lam, the TESLA batch) — one record period
earlier for each record after it in the batch; a frame arrives 1 ms after it is sent; verifying
adds one Ed25519 verification (0.26 ms) where a signature is checked.

Because broadcast has no feedback, what a frame carries does not change which frames arrive, so
running the schemes on traces of frames of their own size and rate is the same as running them
inside ns-3. That is the substitution stated in docs/revision/EXECUTION_PLAN.md.

    python ns3/run_links.py --plan experiments/stream-deadline/plan.txt --stem stream_deadline \
        --trace stream_deadline
    python analysis/stream_deadline.py --score     # results/raw/stream_deadline.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing, interpolated_crossing_ci  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.placement import stream_schemes as ss  # noqa: E402

RAW = REPO / "results" / "raw"
D_MAX_MS = 100.0
ARRIVAL_MS = 1.0
VERIFY_MS = 0.26
RECORD_MS = 20.0
PAYLOAD = 82               # the lean one-record frame without its signature
_ED = Ed25519Scheme()
SK, PK = _ED.keygen(seed=b"\x0a" * 32)


def _payload(i: int) -> bytes:
    return i.to_bytes(4, "big") * (PAYLOAD // 4) + bytes(PAYLOAD % 4)


def tesla_in_time(got: list[int], sent: list[float], interval_ms: float, delay: int,
                  batch: int = 1) -> tuple[int, int]:
    """(records verified within D_max, records sent) for TESLA on one traced link."""
    keys = ss.tesla_chain(b"link", int(max(sent) // interval_ms) + delay + 4)
    t0 = sent[0] - 1e-6
    tx = ss.TeslaSender(keys, interval_ms, delay, t0_ms=t0)
    rx = ss.TeslaReceiver(keys[0], interval_ms, delay, PAYLOAD, t0_ms=t0)
    taken: dict[bytes, float] = {}
    in_time = 0
    for i, (g, t) in enumerate(zip(got, sent, strict=True)):
        body = _payload(i)
        taken[body] = t - (batch - 1) * RECORD_MS          # the oldest record of the frame
        packet = tx.packet(body, t)
        if not g:
            continue
        for done in rx.receive(packet, t + ARRIVAL_MS):
            # each frame holds `batch` records, taken RECORD_MS apart before its send time
            oldest = taken[done]
            for k in range(batch):
                in_time += (t + ARRIVAL_MS) - (oldest + k * RECORD_MS) <= D_MAX_MS
    return in_time, len(sent) * batch


def emss_in_time(got: list[int], sent: list[float], period: int) -> tuple[int, int]:
    """For EMSS the trace's frames are data and signature packets in the order sent."""
    tx, rx = ss.EmssSender(SK, period), ss.EmssReceiver(PK, PAYLOAD)
    taken: dict[bytes, float] = {}
    in_time = records = 0
    stream: list[tuple[bytes, bytes | None]] = []
    i = 0
    while len(stream) < len(sent):
        body = _payload(i)
        for pkt in tx.packets(body):
            stream.append((pkt, body if pkt[:1] == b"D" else None))
        i += 1
    for (pkt, body), g, t in zip(stream, got, sent, strict=False):
        if body is not None:
            taken[body] = t
            records += 1
        if g:
            for done in rx.receive(pkt):
                in_time += (t + ARRIVAL_MS + VERIFY_MS) - taken[done] <= D_MAX_MS
    return in_time, records


def wong_lam_in_time(got: list[int], sent: list[float]) -> tuple[int, int]:
    """Blocks of four: the sender holds each record until its block is full."""
    in_time = 0
    n = len(sent) - len(sent) % 4
    for b0 in range(0, n, 4):
        packets = ss.wong_lam_block([_payload(b0 + k) for k in range(4)], SK)
        for k in range(4):
            if got[b0 + k] and ss.wong_lam_verify(packets[k], PK, PAYLOAD) is not None:
                taken = sent[b0] - 3 * RECORD_MS + k * RECORD_MS
                in_time += (sent[b0 + k] + ARRIVAL_MS + VERIFY_MS) - taken <= D_MAX_MS
    return in_time, n


def gennaro_rohatgi_in_time(got: list[int], sent: list[float]) -> tuple[int, int]:
    """Each packet carries the digest of the next; one signature at the start of the stream:
    a packet authenticates only if every packet before it arrived."""
    first_loss = got.index(0) if 0 in got else len(got)
    return first_loss, len(sent)


def alone_in_time(got: list[int], sent: list[float]) -> tuple[int, int]:
    """A frame that verifies on arrival (MAVLink 2's tag, a signature per record)."""
    return sum(got), len(sent)


# cell -> (ns-3 cell of run_links.CELLS, list of (variant, evaluator))
VARIANTS = {
    "mavlink2": lambda g, s: alone_in_time(g, s),
    "gennaro-rohatgi": lambda g, s: gennaro_rohatgi_in_time(g, s),
    "wong-lam": lambda g, s: wong_lam_in_time(g, s),
    "tesla-I10-d1": lambda g, s: tesla_in_time(g, s, 10.0, 1),
    "tesla-I10-d2": lambda g, s: tesla_in_time(g, s, 10.0, 2),
    "tesla-I20-d1": lambda g, s: tesla_in_time(g, s, 20.0, 1),
    "tesla-I20-d2": lambda g, s: tesla_in_time(g, s, 20.0, 2),
    "tesla-I50-d1": lambda g, s: tesla_in_time(g, s, 50.0, 1),
    "tesla-I50-d2": lambda g, s: tesla_in_time(g, s, 50.0, 2),
    "tesla-batch4": lambda g, s: tesla_in_time(g, s, 80.0, 1, batch=4),
    "emss-k4": lambda g, s: emss_in_time(g, s, 4),
    "emss-k8": lambda g, s: emss_in_time(g, s, 8),
    "emss-k16": lambda g, s: emss_in_time(g, s, 16),
    "emss-k100": lambda g, s: emss_in_time(g, s, 100),
}
# which variants run on which simulated frame
ON_CELL = {
    "LSM": ("mavlink2",), "LSG": ("gennaro-rohatgi",), "LSW": ("wong-lam",),
    "LST": ("tesla-I10-d1", "tesla-I10-d2", "tesla-I20-d1", "tesla-I20-d2", "tesla-I50-d1",
            "tesla-I50-d2"),
    "LTB": ("tesla-batch4",), "LE4": ("emss-k4",), "LE8": ("emss-k8",),
    "LE16": ("emss-k16",), "LSE": ("emss-k100",),
}


def per_run(trace_text: str, cell: str) -> dict[str, float]:
    """Deadline-aware V of every variant that runs on this cell, from one run's traces."""
    rows = list(csv.DictReader(io.StringIO(trace_text)))
    out: dict[str, float] = {}
    for variant in ON_CELL[cell]:
        ok = total = 0
        for r in rows:
            got = [int(c) for c in r["got"]]
            sent = [float(x) for x in r["sent_ms"].split()]
            a, b = VARIANTS[variant](got, sent)
            ok, total = ok + a, total + b
        out[f"v_in_time:{variant}"] = round(ok / total, 6) if total else float("nan")
    return out


def score() -> list[dict]:
    path = RAW / "ns3_links_stream_deadline_runs.csv"
    with path.open(encoding="utf-8") as fh:
        runs = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    out = []
    for cell, variants in ON_CELL.items():
        mine = [r for r in runs if r["cell"] == cell]
        if not mine:
            continue
        delivery: dict[int, list[float]] = {}
        for r in mine:
            delivery.setdefault(int(r["n_nodes"]), []).append(float(r["delivered_frac"]))
        delivery = {n: v for n, v in delivery.items() if len(v) == 30}
        dx = interpolated_crossing({n: st.mean(v) for n, v in delivery.items()}, 0.95)
        dci = interpolated_crossing_ci(delivery, threshold=0.95, seed=20261020)
        for variant in variants:
            per_n: dict[int, list[float]] = {}
            for r in mine:
                per_n.setdefault(int(r["n_nodes"]), []).append(float(r[f"v_in_time:{variant}"]))
            per_n = {n: v for n, v in per_n.items() if len(v) == 30}
            means = {n: st.mean(v) for n, v in per_n.items()}
            vx = interpolated_crossing(means, 0.95)
            out.append({"cell": cell, "variant": variant,
                        "delivery_crossing": "" if dx is None else round(dx, 2),
                        "delivery_ci": "" if dci is None else f"{dci[0]:.2f}-{dci[1]:.2f}",
                        "in_time_crossing": "" if vx is None else round(vx, 2),
                        "in_time_v_by_n": " ".join(f"{n}:{means[n]:.4f}" for n in sorted(means)),
                        "delivery_by_n": " ".join(f"{n}:{st.mean(delivery[n]):.4f}"
                                                  for n in sorted(delivery))})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--score", action="store_true", required=True)
    ap.parse_args()
    rows = score()
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "stream_deadline",
                 "config_hash": provenance.config_hash({"d_max": D_MAX_MS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    (RAW / "stream_deadline.csv").write_text(buf.getvalue())
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
