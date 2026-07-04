"""E1–E3 experiment runners (docs/02 T1-T3, docs/04 §2). Frozen data + config-hash provenance.

Each runner returns tidy rows and is unit-tested; `main(--exp eN)` reads
`experiments/eN/config.yaml`, runs it, and writes `results/raw/eN_*.csv` with an env + config-hash
header (Law 7). E1 = overhead dominance (φ per encoding); E2 = batching cure (measured A vs the
T2 formula); E3 = loss frontier (measured V_B/V_D vs T3). Absolute sizes use the measured s_e and
g_a=64/96 (Mohamed's P1 decisions); the T1/T2/T3 FORMULAS are what the validations check.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean

import numpy as np
import yaml

from authbc.bench import framesizes, provenance, telemgen
from authbc.bench.stats import bootstrap_ci
from authbc.channel.airtime import DELTA_US, DIFS_US, MAC_HDR_B, T_PHY_US, tx_us
from authbc.encodings.registry import new_encoder
from authbc.placement.framer import H_F, M_MTU, b_max, b_max_inline

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "results" / "raw"
CI_SEED = 12345


def load_config(exp: str) -> dict:
    return yaml.safe_load((REPO / "experiments" / exp / "config.yaml").read_text())


def write_csv(name: str, rows: list[dict], config: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    meta = {**provenance.env_block(), "run": name, "config_hash": provenance.config_hash(config)}
    path = RESULTS / f"{name}.csv"
    with path.open("w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


# --------------------------------------------------------------------------- E1 (T1)
def run_e1(cfg: dict) -> list[dict]:
    """Per-encoding on-air bytes + inline auth fraction φ=g/(s+g) over seeds 1..30.

    Same seeds ⇒ same records across encodings (baseline fairness by construction).
    """
    g, n, seeds = cfg["g"], cfg["records_per_seed"], cfg["seeds"]
    rows: list[dict] = []
    for enc_name in cfg["encodings"]:
        sizes: list[int] = []
        for seed in seeds:
            enc = new_encoder(enc_name)  # one stateful encoder per (encoding, seed) stream
            sizes.extend(len(enc.encode(r)) for r in telemgen.samples(seed=seed, n=n))
        mean_s = mean(sizes)
        lo, hi = bootstrap_ci([float(x) for x in sizes], seed=CI_SEED, statistic=np.mean)
        rows.append({
            "encoding": enc_name, "placement": "A_inline", "g": g,
            "n_records": len(sizes), "mean_bytes": round(mean_s, 3),
            "ci_lo": round(lo, 3), "ci_hi": round(hi, 3),
            "phi_pct": round(100.0 * g / (mean_s + g), 2),
            "baseline": int(enc_name in cfg["baselines"]),
        })
    return rows


# --------------------------------------------------------------------------- E2 (T2)
def run_e2(cfg: dict) -> list[dict]:
    """Batching cure: per-record on-air bytes vs b for A/B × encodings × M, with amplification.

    A (self-batch, B) = M/(M−H_f−g_a) is the relaxed-floor formula; the discrete value at the
    integer b_max approaches it as M grows (small M shows a documented discretization gap).
    """
    sizes = framesizes.measured_sizes(seed=cfg["size_seed"], n=cfg["size_n"])
    g_a = cfg["g_a"]
    rows: list[dict] = []
    for m in cfg["mtu_values"]:
        for placement in cfg["placements"]:
            for enc in cfg["encodings"]:
                s = sizes[enc]
                bm = int(b_max(s, g_a, mtu=m) if placement == "B"
                         else b_max_inline(s, g_a, mtu=m))  # s is a float mean → floor to int
                if bm < 1:
                    continue  # a single record does not fit this MTU
                a_formula = m / (m - H_F - g_a) if placement == "B" else ""
                for b in range(1, bm + 1):
                    fb = framesizes.frame_bytes(placement, s, b)
                    per_rec = fb / b
                    phi_ov = 100.0 * (framesizes.auth_bytes(placement, b) + H_F) / fb
                    rows.append({
                        "mtu": m, "placement": placement, "encoding": enc, "s": round(s, 2),
                        "b": b, "b_max": bm, "frame_bytes": round(fb, 2),
                        "bytes_per_rec": round(per_rec, 3), "phi_overhead_pct": round(phi_ov, 2),
                        "A_at_b": round(per_rec / s, 4),
                        "A_formula": round(a_formula, 4) if a_formula != "" else "",
                        "is_bmax": int(b == bm),
                    })
    return rows


# --------------------------------------------------------------------------- E3 (T3)
def _airtime_multiframe(n_frames: int, total_payload_bytes: float) -> float:
    """Broadcast airtime for n frames carrying total_payload_bytes (excl. MAC hdr)."""
    fixed = n_frames * (T_PHY_US + DIFS_US + DELTA_US)
    return fixed + tx_us(total_payload_bytes + n_frames * MAC_HDR_B)


def run_e3(cfg: dict) -> list[dict]:
    """Loss frontier: measured V_B (flat 1−p) vs V_D ((1−p)^n) over b, p, seeds 1..30.

    V is a pure loss property (no tampering): a record is verifiable iff its self-batch frame
    (B) / all its block fragments (D) arrived — measured by seeded Bernoulli draws (the emulator's
    model, P3-validated). D's on-air model carries the signature ONCE (byte-optimal, T3 (ii)).
    """
    s = framesizes.measured_sizes(seed=cfg["size_seed"], n=cfg["size_n"])[cfg["encoding"]]
    g_a, n_blk, seeds, base = cfg["g_a"], cfg["blocks_per_seed"], cfg["seeds"], cfg["base_seed"]
    bmax_b = int(b_max(s, g_a, mtu=M_MTU))
    rows: list[dict] = []
    for p in cfg["p_values"]:
        for b in cfg["b_values"]:
            n_b = math.ceil(b / bmax_b)                       # B frames (loss-local)
            n_d = math.ceil((b * s + g_a + H_F) / M_MTU)      # D frames (block-level)
            bytes_b = (H_F * n_b + b * s + g_a * n_b) / b     # B: header+sig per frame
            bytes_d = (H_F * n_d + b * s + g_a) / b           # D: one sig for the block
            air_b = _airtime_multiframe(n_b, H_F * n_b + b * s + g_a * n_b)
            air_d = _airtime_multiframe(n_d, H_F * n_d + b * s + g_a)

            vb_by_seed, vd_by_seed = [], []
            for seed in seeds:
                rng = np.random.default_rng([base, b, int(round(p * 1000)), seed])  # per-config
                vb_by_seed.append(float((rng.random(n_blk) >= p).mean()))            # B: one frame
                vd_by_seed.append(float((rng.random((n_blk, n_d)) >= p).all(axis=1).mean()))
            vb, vd = float(mean(vb_by_seed)), float(mean(vd_by_seed))
            vb_ci = bootstrap_ci(vb_by_seed, seed=CI_SEED)
            vd_ci = bootstrap_ci(vd_by_seed, seed=CI_SEED)
            for plc, nf, bpr, vm, vci, air, vth in (
                ("B", n_b, bytes_b, vb, vb_ci, air_b, 1 - p),
                ("D", n_d, bytes_d, vd, vd_ci, air_d, (1 - p) ** n_d),
            ):
                rows.append({
                    "placement": plc, "p": p, "b": b, "s": round(s, 2), "n_frames": nf,
                    "bytes_per_rec": round(bpr, 3), "V_meas": round(vm, 5),
                    "V_ci_lo": round(vci[0], 5), "V_ci_hi": round(vci[1], 5),
                    "V_theory": round(vth, 5),
                    "goodput_mbps": round(vm * b * s * 8 / air, 4),  # bits/µs = Mbit/s
                })
    return rows


_RUNNERS = {
    "e1": (run_e1, "e1_dominance"),
    "e2": (run_e2, "e2_batching"),
    "e3": (run_e3, "e3_loss"),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="run an AUTHBC experiment → results/raw/")
    ap.add_argument("--exp", required=True, choices=sorted(_RUNNERS))
    args = ap.parse_args()
    runner, out_name = _RUNNERS[args.exp]
    cfg = load_config(args.exp)
    rows = runner(cfg)
    path = write_csv(out_name, rows, cfg)
    print(f"{args.exp}: wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
