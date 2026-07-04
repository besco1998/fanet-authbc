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
from pathlib import Path
from statistics import mean

import numpy as np
import yaml

from authbc.bench import framesizes, provenance, telemgen
from authbc.bench.stats import bootstrap_ci
from authbc.encodings.registry import new_encoder
from authbc.placement.framer import H_F, b_max, b_max_inline

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


_RUNNERS = {"e1": (run_e1, "e1_dominance"), "e2": (run_e2, "e2_batching")}


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
