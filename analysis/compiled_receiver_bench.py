#!/usr/bin/env python3
"""The compiled receiver against the Python one, on one board (revisions A8 and A13).

Written before any timing (predictions/A8.md, A13.md). The frames are the identity gate's
(`analysis/rust_identity.py`: ten seeded streams of 1 000 four-record frames, key seed bytes
0..31); the first sixteen are checked against the golden vectors before anything is timed, so
both receivers time the frames whose bytes the gate proved identical.

    compiled  `authbc-rx bench` (decode + rebuild + verify per frame; decode + rebuild alone;
              Ed25519 in batches of 64 per frame) and `authbc-rx lazy` (A13: the 8 B group tag
              and decode, then batches of 64), each run INVOCATIONS times; a run's figure is
              the median over its repetitions, the row gives the median and range of the runs.
    Python    `LeanReceiver.receive` on the same frames with the bench's timer (time_op: warm-up,
              ≥ 10 000 frames, median and bootstrap interval); a fresh receiver per stream,
              since the ten streams share a sender and sequence numbers.

Nodes per core by Eq. (4): one core's second over the per-frame cost, at 12.5 frames/s a node.

    python analysis/compiled_receiver_bench.py      # results/hw/compiled_receiver.<host>.csv
    python analysis/compiled_receiver_bench.py --check     # one short run each: plumbing only
"""
from __future__ import annotations

import argparse
import csv
import io
import socket
import statistics as st
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import rust_identity as rid  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.bench.stats import summarize  # noqa: E402
from authbc.bench.timers import time_op  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt  # noqa: E402

FPS = 12.5
INVOCATIONS = 5
REPS = 20
STREAMS, PER_STREAM = 10, 1000


def identity_frames() -> tuple[list[bytes], str, object]:
    sk, pk = Ed25519Scheme().keygen(seed=rid.SEED)
    frames: list[bytes] = []
    for seed in range(1, STREAMS + 1):
        recs = leanframes.chained_records(seed, PER_STREAM * rid.BATCH)
        sender = LeanSender(sk)
        frames += [sender.frame(recs[i:i + rid.BATCH]) for i in range(0, len(recs), rid.BATCH)]
    golden = rid.read_frames((rid.VECTORS / "frames.bin").read_bytes())
    if frames[:len(golden)] != golden:
        raise SystemExit("these are not the identity gate's frames")
    return frames, pk.public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), pk


class _Streams:
    """One frame per call through `LeanReceiver`; a fresh receiver at every stream's start."""

    def __init__(self, frames: list[bytes], pk: object) -> None:
        self._frames, self._pk, self._i = frames, pk, 0
        self._rx = LeanReceiver({leanframes.CONVENTION_SRC: pk})

    def __call__(self) -> int:
        if self._i % PER_STREAM == 0:
            self._rx = LeanReceiver({leanframes.CONVENTION_SRC: self._pk})
            self._i %= len(self._frames)
        got = self._rx.receive(self._frames[self._i])
        self._i += 1
        if got.receipt is not Receipt.ACCEPTED:
            raise RuntimeError(f"frame {self._i - 1} not accepted: {got.receipt}")
        return len(got.records)


def run_rx(exe: Path, cmd: str, path: Path, pk_hex: str, invocations: int, reps: int
           ) -> list[dict[str, float]]:
    out = []
    for _ in range(invocations):
        text = subprocess.run([str(exe), cmd, str(path), pk_hex, str(reps)], check=True,
                              capture_output=True, text=True).stdout
        out.append({k: float(v) for k, v in (ln.split(",") for ln in text.split())})
    return out


def rows_of(impl: str, runs: list[dict[str, float]], reps: int) -> list[dict]:
    return [{"impl": impl, "metric": m, "median_ns": st.median(r[m] for r in runs),
             "lo_ns": min(r[m] for r in runs), "hi_ns": max(r[m] for r in runs),
             "n": f"{len(runs)} runs x {reps} reps x {int(runs[0]['frames'])} frames"}
            for m in runs[0] if m != "frames"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", type=Path, default=rid.EXE)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    inv, reps = (1, 1) if args.check else (INVOCATIONS, REPS)
    floors = {"min_ops": 200, "min_total_ns": 50_000_000} if args.check else {}
    frames, pk_hex, pk = identity_frames()
    rows: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "frames.bin"
        path.write_bytes(rid.frames_file(frames))
        rows += rows_of("rust", run_rx(args.exe, "bench", path, pk_hex, inv, reps), reps)
        rows += rows_of("rust", run_rx(args.exe, "lazy", path, pk_hex, inv, reps), reps)
    res = time_op(_Streams(frames, pk), batch=10, **floors)
    s = summarize(res.samples_ns, seed=20261022)
    rows.append({"impl": "python", "metric": "receive_ns_per_frame", "median_ns": s.median,
                 "lo_ns": s.ci_lo, "hi_ns": s.ci_hi,
                 "n": f"{res.n_ops} frames (bootstrap 95 % interval)"})
    by = {(r["impl"], r["metric"]): r["median_ns"] for r in rows}
    rust_batch = (by[("rust", "decode_rebuild_ns_per_frame")]
                  + by[("rust", "batch64_verify_ns_per_frame")])
    derived = {
        "python_over_rust_receive": by[("python", "receive_ns_per_frame")]
        / by[("rust", "receive_ns_per_frame")],
        "nodes_per_core_python": 1e9 / (by[("python", "receive_ns_per_frame")] * FPS),
        "nodes_per_core_rust": 1e9 / (by[("rust", "receive_ns_per_frame")] * FPS),
        "nodes_per_core_rust_batch64": 1e9 / (rust_batch * FPS),
        "nodes_per_core_lazy": 1e9 / ((by[("rust", "tier1_tag_decode_ns_per_frame")]
                                       + by[("rust", "tier2_batch64_ns_per_frame")]) * FPS),
        "verify_share_of_receive": 1 - by[("rust", "decode_rebuild_ns_per_frame")]
        / by[("rust", "receive_ns_per_frame")],
        "batch64_over_single_verify": by[("rust", "batch64_verify_ns_per_frame")]
        / (by[("rust", "receive_ns_per_frame")] - by[("rust", "decode_rebuild_ns_per_frame")]),
    }
    rows += [{"impl": "derived", "metric": k, "median_ns": round(v, 4), "lo_ns": "", "hi_ns": "",
              "n": "Eq. (4)" if k.startswith("nodes") else ""} for k, v in derived.items()]
    for r in rows:
        if isinstance(r["median_ns"], float) and r["impl"] != "derived":
            r["median_ns"], r["lo_ns"], r["hi_ns"] = (round(r[k], 1) for k in
                                                      ("median_ns", "lo_ns", "hi_ns"))
    out = REPO / "results" / "hw" / (f"compiled_receiver.{socket.gethostname()}"
                                     f"{'.check' if args.check else ''}.csv")
    buf = io.StringIO()
    rustc = subprocess.run([str(Path.home() / ".cargo" / "bin" / "rustc"), "--version"],
                           capture_output=True, text=True).stdout.strip() or "NA"
    for k, v in {**provenance.env_block(), "run": "compiled_receiver", "rustc": rustc,
                 "config_hash": provenance.config_hash({"inv": INVOCATIONS, "reps": REPS,
                                                        "streams": STREAMS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(buf.getvalue())
    for r in rows:
        print(r)
    print(out)


if __name__ == "__main__":
    main()
