"""P1 microbenchmark runner — parameter sizes + crypto timings (docs/04 §1, docs/06 §3).

Writes tidy CSVs to results/raw/ with a commented env-block header (provenance, Law 7):
  - p1_sizes.csv  : per-encoding mean±CI + max bytes, and φ=g/(s+g) at g=64.
  - p1_crypto.csv : per-scheme sign/verify median±CI (ns) on 200 B msgs; BLS aggregate /
                    aggregate_verify for b∈{2,4,8,16,32}.

Determinism: telemetry is seeded; the delta encoder is reused as ONE stateful instance across
the stream (a fresh-per-record encoder would emit all keyframes — the Law-6 pitfall caught in
the audit). Run via `make bench-micro` or `python -m authbc.bench.micro`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
from pathlib import Path
from statistics import mean

import numpy as np

from authbc.bench import provenance
from authbc.bench.stats import bootstrap_ci, summarize
from authbc.bench.timers import time_op
from authbc.crypto.registry import all_schemes, get_scheme
from authbc.encodings.registry import new_encoder

RESULTS = Path(__file__).resolve().parents[3] / "results" / "raw"
G_INLINE = 64  # inline per-record signature bytes for φ (Ed25519/ECDSA), docs/02 T1
MSG_BYTES = 200  # docs/04 §1
CI_SEED = 12345  # bootstrap RNG seed (reproducible CIs)
# prev_hash(32) + a delta-encoded record body(13) — what the chain actually hashes (D7)
CHAIN_MSG_BYTES = 45
BATCH_SIZES = (2, 4, 8, 16, 32)
BLS_CAP_NS = 2_500_000_000  # wall-time cap for ms-scale BLS ops


def _write_csv(path: Path, header_meta: dict, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        for k, v in header_meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _seed32(seed: int, tag: str) -> bytes:
    return hashlib.sha256(f"{seed}:{tag}".encode()).digest()


# --------------------------------------------------------------------------- sizes
def measure_sizes(seed: int, n: int) -> list[dict]:
    from authbc.bench import telemgen

    recs = telemgen.samples(seed=seed, n=n)
    rows: list[dict] = []
    for name in ("json", "cbor", "msgpack", "delta"):
        enc = new_encoder(name)  # ONE stateful instance across the stream
        sizes = [len(enc.encode(r)) for r in recs]
        mean_s = mean(sizes)
        lo, hi = bootstrap_ci([float(s) for s in sizes], seed=CI_SEED, statistic=np.mean)
        phi = 100 * G_INLINE / (mean_s + G_INLINE)
        base = {"encoding": name, "seed": seed, "n": n}
        rows.append({**base, "metric": "mean_bytes", "value": round(mean_s, 3),
                     "ci_lo": round(lo, 3), "ci_hi": round(hi, 3)})
        rows.append({**base, "metric": "max_bytes", "value": max(sizes), "ci_lo": "", "ci_hi": ""})
        rows.append({**base, "metric": "phi_pct_g64", "value": round(phi, 2),
                     "ci_lo": "", "ci_hi": ""})
    return rows


# --------------------------------------------------------------------------- crypto timings
def _time_row(scheme: str, op: str, fn, *, agg_b: str, expensive: bool,
              msg_bytes: int = MSG_BYTES) -> dict:
    """One timed row. `msg_bytes` MUST describe the input actually measured — the SHA-256 chain
    link hashes a 45 B record, not the 200 B crypto message, and a frozen artifact that misstates
    its own input is worse than no artifact (caught 2026-07-29 during D7)."""
    if expensive:
        # ms-scale ops: gather ~1 s of samples (hundreds–thousands) for a tight CI, capped at
        # BLS_CAP_NS so the slowest (agg_verify b=32, ~11 ms) still finishes quickly.
        res = time_op(fn, warmup=1000, reps=200, batch=1, min_ops=200,
                      min_total_ns=1_000_000_000, max_total_ns=BLS_CAP_NS)
    else:
        res = time_op(fn)  # production floors: ≥10k ops / ≥200 ms
    s = summarize(res.samples_ns, seed=CI_SEED)
    return {"scheme": scheme, "op": op, "agg_b": agg_b, "msg_bytes": msg_bytes,
            "median_ns": round(s.median, 1), "ci_lo_ns": round(s.ci_lo, 1),
            "ci_hi_ns": round(s.ci_hi, 1), "n_ops": res.n_ops, "checksum": res.checksum}


def measure_crypto(seed: int) -> list[dict]:
    rng = random.Random(seed)
    msg = bytes(rng.randrange(256) for _ in range(MSG_BYTES))
    rows: list[dict] = []
    for scheme in all_schemes():
        sk, pk = scheme.keygen(seed=_seed32(seed, scheme.name))
        sig = scheme.sign(sk, msg)
        exp = scheme.name == "bls"
        rows.append(_time_row(scheme.name, "sign", lambda sc=scheme, k=sk: sc.sign(k, msg),
                              agg_b="", expensive=exp))
        rows.append(_time_row(scheme.name, "verify",
                              lambda sc=scheme, p=pk, g=sig: sc.verify(p, msg, g),
                              agg_b="", expensive=exp))
    # SHA-256 chain link (item D7, 2026-07-29). Every record is hashed to form prev_hash — that
    # IS the ledger — but `models.energy` had no term for it, which is half of F14's measured 32 %
    # energy gap. Measured here so the model's input is a real per-platform figure rather than a
    # borrowed x86 number. The message is the RECORD-sized input the chain actually hashes
    # (prev_hash 32 B + a delta-encoded body), not the 200 B crypto message.
    chain_input = bytes(rng.randrange(256) for _ in range(CHAIN_MSG_BYTES))
    rows.append(_time_row("sha256", "chain_link",
                          lambda m=chain_input: hashlib.sha256(m).digest(), agg_b="",
                          expensive=False, msg_bytes=CHAIN_MSG_BYTES))

    # BLS cross-signer aggregation over distinct messages (AugScheme), b∈{2,4,8,16,32}
    bls = get_scheme("bls")
    for b in BATCH_SIZES:
        keys = [bls.keygen(seed=_seed32(seed, f"bls{b}_{i}")) for i in range(b)]
        msgs = [bytes(rng.randrange(256) for _ in range(MSG_BYTES)) for _ in range(b)]
        sigs = [bls.sign(sk, m) for (sk, _), m in zip(keys, msgs, strict=True)]
        pks = [pk for _, pk in keys]
        agg = bls.aggregate(sigs)
        rows.append(_time_row("bls", "aggregate", lambda s=sigs: bls.aggregate(s),
                              agg_b=str(b), expensive=True))
        rows.append(_time_row("bls", "agg_verify",
                              lambda p=pks, m=msgs, a=agg: bls.aggregate_verify(p, m, a),
                              agg_b=str(b), expensive=True))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="P1 microbenchmarks → results/raw/p1_*.csv")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n", type=int, default=10_000)
    args = ap.parse_args()

    env = provenance.env_block()
    size_meta = {**env, "run": "p1_sizes", "seed": args.seed, "n": args.n,
                 "config_hash": provenance.config_hash({"seed": args.seed, "n": args.n})}
    crypto_meta = {**env, "run": "p1_crypto", "seed": args.seed, "msg_bytes": MSG_BYTES,
                   "config_hash": provenance.config_hash({"seed": args.seed, "msg": MSG_BYTES})}

    print("measuring sizes …")
    size_rows = measure_sizes(args.seed, args.n)
    _write_csv(RESULTS / "p1_sizes.csv", size_meta,
               ["encoding", "seed", "n", "metric", "value", "ci_lo", "ci_hi"], size_rows)

    print("measuring crypto timings (BLS pairing ops are ms-scale) …")
    crypto_rows = measure_crypto(args.seed)
    _write_csv(RESULTS / "p1_crypto.csv", crypto_meta,
               ["scheme", "op", "agg_b", "msg_bytes", "median_ns", "ci_lo_ns", "ci_hi_ns",
                "n_ops", "checksum"], crypto_rows)
    print(f"wrote {RESULTS/'p1_sizes.csv'} and {RESULTS/'p1_crypto.csv'}")


if __name__ == "__main__":
    main()
