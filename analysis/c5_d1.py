#!/usr/bin/env python3
"""C5, setting D1 — the registered predictions (docs/prompts/CAPTURE_PROMPT.md §8.2–8.3; the
model: docs/revision/2026-11-17_unified_model_spec.md, `authbc.models.unified_capacity`).

802.11a at 48 Mb/s, constant received power (ns-3's published detection model), the lean format
ℓ(b) = 137 + 9b at Λ = 200 records/s, ε = 5 %:
1. PER(ℓ) from ns-3's own error-rate model (TableBasedErrorRateModel, by `ns3/authbc-per.cc`);
2. the collision budget ε_c(b) = 1 − (1 − ε)/(1 − PER(ℓ(b)));
3. the capacity: the root of p_c(ν) = ε_c(b), ν = (N − 1)·Λ/b (the law is out of its range: every
   frame is shorter than 2τ0); none where ε_c(b) ≤ 0 (the frame alone misses the target);
4. the best batch, over the sweep and over every integer b ≤ 32;
5. the cross-check (G19): b_opt = β[√(1 + Β₀/(e₁β)) − 1], with its inputs as the prompt defines
   them, none fitted.

    python analysis/c5_d1.py -77.17   -> results/raw/c5_d1_predictions.csv
"""
from __future__ import annotations

import csv
import io
import math
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

OUT = REPO / "results" / "raw" / "c5_d1_predictions.csv"
EPS = 0.05
LAMBDA = 200.0
SWEEP = (1, 2, 4, 8, 16, 32)
MODE = "OfdmRate48Mbps"
PHY48 = phy.ofdm_20mhz(48)


def length(b: int) -> int:
    return 137 + 9 * b


def per_table(dbm: float, batches: tuple[int, ...]) -> dict[int, float]:
    """PER(ℓ(b)) from ns-3's TableBasedErrorRateModel at a fixed received power."""
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-per-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    out = subprocess.run([str(exe), f"--mode={MODE}", f"--rxPowerDbm={dbm}",
                          "--sizes=" + ",".join(str(length(b)) for b in batches)],
                         check=True, env=env, capture_output=True, text=True).stdout
    by_len = {int(r["app_bytes"]): float(r["per"]) for r in csv.DictReader(io.StringIO(out))}
    return {b: by_len[length(b)] for b in batches}


def eps_c(per: float, eps: float = EPS) -> float:
    """The collision budget left after the loss to noise."""
    return 1.0 - (1.0 - eps) / (1.0 - per)


def capacity(b: int, per: float) -> float | None:
    """The root of p_c(ν) = ε_c(b); None when the frame alone misses the target."""
    e = eps_c(per)
    if e <= 0:
        return None
    return uc.n_root(LAMBDA / b, uc.airtime_s(PHY48, length(b)), e)


def big_b(eps: float) -> float:
    """Β(ε) = ρ*(ε)/κ(ε), κ = 1 − ε/2 (G6)."""
    return uc.dcf_constants(eps)[0] / (1 - eps / 2)


def g19(per1: float, per2: float, eps: float = EPS) -> dict[str, float]:
    """(G19) with the prompt's inputs: the secant airtime between b = 1 and b = 32, τ̂ at ε, the
    per-record noise slope s from b = 1 to b = 2, Β₀ at the extrapolated b = 0, and
    e₁ = (1 − ε)·s·dΒ/dε."""
    t1, t32 = uc.airtime_s(PHY48, length(1)), uc.airtime_s(PHY48, length(32))
    psi_t = (t32 - t1) / 31
    phi_t = t1 - psi_t
    tau0 = uc.dcf_constants(eps)[1]
    tau_hat = tau0 / (1 - eps / 2) - uc.A80211A.delta_s
    phi, psi = phi_t + tau_hat, psi_t
    beta = phi / psi
    s = per2 - per1
    per0 = per1 - s
    b0 = big_b(eps_c(per0, eps))
    h = 1e-4
    e1 = (1 - eps) * s * (big_b(eps + h) - big_b(eps - h)) / (2 * h)
    b_opt = beta * (math.sqrt(1 + b0 / (e1 * beta)) - 1)
    return {"phi_t_us": phi_t * 1e6, "psi_t_us": psi_t * 1e6, "tau_hat_us": tau_hat * 1e6,
            "beta": beta, "s": s, "per0": per0, "B0": b0, "e1": e1, "b_opt": b_opt}


def main() -> None:
    dbm = float(sys.argv[1])
    every = tuple(range(1, 33))
    per = per_table(dbm, every)
    caps = {b: capacity(b, per[b]) for b in every}
    feasible = {b: c for b, c in caps.items() if c is not None}
    best_sweep = max((b for b in SWEEP if caps[b] is not None), key=lambda b: caps[b] or 0)
    best_int = max(feasible, key=lambda b: feasible[b])
    cross = g19(per[1], per[2])
    rows = [{"b": b, "app_bytes": length(b), "frames_per_s": LAMBDA / b,
             "tf_us": round(uc.airtime_s(PHY48, length(b)) * 1e6, 3),
             "per": round(per[b], 6), "eps_c": round(eps_c(per[b]), 6),
             "capacity_root": "" if caps[b] is None else round(caps[b], 3),
             "in_sweep": b in SWEEP} for b in every]
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "c5_d1_predictions",
                 "config_hash": provenance.config_hash({"dbm": dbm, "eps": EPS,
                                                        "lambda": LAMBDA, "mode": MODE})}.items():
        buf.write(f"# {k}={v}\n")
    buf.write(f"# rx_power_dbm={dbm}\n")
    buf.write(f"# best batch in the sweep: b={best_sweep}, capacity {caps[best_sweep]:.3f}\n")
    buf.write(f"# best integer batch 1..32: b={best_int}, capacity {feasible[best_int]:.3f}\n")
    buf.write("# G19: " + " ".join(f"{k}={v:.6g}" for k, v in cross.items()) + "\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
