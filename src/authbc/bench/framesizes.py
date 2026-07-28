"""Frame-size model → results/raw/framesizes.csv (SYNC-3, docs/02 T2, docs/04 §2 E2).

The e-axis analytical size model (Mohamed's decision): a frame carrying b records encoded with
encoding e costs `frame_bytes = H_f + b·s_e + auth(placement, b)`, using the REAL measured
per-encoding record size s_e (P1 encoders) and per-placement auth bytes. This is what NS-3 needs
as frame-size parameters; the authenticated substrate stays the frozen canonical CBOR (P2).

Auth bytes per placement (Ed25519 sig 64 B; BLS agg 96 B — Mohamed's g_a=96 decision):
  A inline: b·64 (a sig per record)      B self-batch: 64 (one sig)
  C relay:  96 + 2·b (agg + src ids)     D block: 64 + 6 (sig + block_id/frag_idx/frag_total)
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

from authbc.bench import provenance, telemgen
from authbc.encodings.registry import new_encoder
from authbc.placement.framer import H_F, M_MTU

RESULTS = Path(__file__).resolve().parents[3] / "results" / "raw"
ENCODINGS = ("json", "cbor", "msgpack", "delta")
PLACEMENTS = ("A", "B", "C", "D")
B_VALUES = (1, 2, 4, 8, 16, 32)


def auth_bytes(placement: str, b: int) -> int:
    return {"A": 64 * b, "B": 64, "C": 96 + 2 * b, "D": 64 + 6}[placement]


def frame_bytes(placement: str, s: float, b: int) -> float:
    return H_F + b * s + auth_bytes(placement, b)


def amplification(placement: str, s: float, b: int) -> float:
    """On-air bytes per record ÷ payload bytes = (frame_bytes/b) / s (T2's A when b=b_max)."""
    return (frame_bytes(placement, s, b) / b) / s


# The single sampling protocol for record sizes, shared by E1 and every downstream experiment
# (audit F4). docs/02 §8 requires ≥30 seeded repetitions with a bootstrap CI, so the 30×1000 form
# is the standard and single-seed sampling is gone: it produced a 4.1 % disagreement (cbor 68.94 B
# single-seed vs 66.25 B over 30 seeds) because the telemetry generator random-walks, so one long
# stream drifts to larger magnitudes than the average of thirty short ones.
SIZE_SEEDS: tuple[int, ...] = tuple(range(1, 31))
RECORDS_PER_SEED: int = 1000


def size_samples(seeds: tuple[int, ...] = SIZE_SEEDS,
                 records_per_seed: int = RECORDS_PER_SEED) -> dict[str, list[int]]:
    """Raw per-record encoded sizes per encoding, pooled over *seeds*.

    ONE stateful encoder per (encoding, seed) stream — a fresh-per-record encoder would make delta
    emit all keyframes (the P1b pitfall), and a single encoder spanning seeds would carry state
    across unrelated streams. E1 computes its mean and bootstrap CI from exactly this.
    """
    out: dict[str, list[int]] = {}
    for name in ENCODINGS:
        sizes: list[int] = []
        for seed in seeds:
            enc = new_encoder(name)
            sizes.extend(len(enc.encode(r))
                         for r in telemgen.samples(seed=seed, n=records_per_seed))
        out[name] = sizes
    return out


def measured_sizes(seeds: tuple[int, ...] = SIZE_SEEDS,
                   records_per_seed: int = RECORDS_PER_SEED) -> dict[str, float]:
    """Mean per-encoding record size s_e over the standard 30-seed protocol (audit F4)."""
    return {k: mean(v) for k, v in size_samples(seeds, records_per_seed).items()}


def build_rows(sizes: dict[str, float]) -> list[dict]:
    rows: list[dict] = []
    for placement in PLACEMENTS:
        for enc in ENCODINGS:
            s = sizes[enc]
            for b in B_VALUES:
                fb = frame_bytes(placement, s, b)
                rows.append({
                    "placement": placement, "encoding": enc, "b": b,
                    "s_e": round(s, 2), "auth_bytes": auth_bytes(placement, b),
                    "frame_bytes": round(fb, 2), "bytes_per_rec": round(fb / b, 2),
                    "amplification": round(amplification(placement, s, b), 4),
                    "feasible": int(fb <= M_MTU),
                })
    return rows


def main() -> None:
    sizes = measured_sizes()
    rows = build_rows(sizes)
    RESULTS.mkdir(parents=True, exist_ok=True)
    cfg = {"sizes": {k: round(v, 3) for k, v in sizes.items()}}
    meta = {**provenance.env_block(), "run": "framesizes", "mtu": M_MTU, "h_f": H_F,
            "config_hash": provenance.config_hash(cfg)}
    path = RESULTS / "framesizes.csv"
    with path.open("w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows); s_e = {({k: round(v,1) for k,v in sizes.items()})}")


if __name__ == "__main__":
    main()
