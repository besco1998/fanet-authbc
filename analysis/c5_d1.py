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
    python analysis/c5_d1.py --score  -> results/raw/c5_d1_scored.csv
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


def all_crossings(means: dict[int, float], level: float = 1 - EPS) -> list[float]:
    """Every straight-line crossing of `level` by the mean curve, downward or upward."""
    ns = sorted(means)
    out = []
    for lo, hi in zip(ns, ns[1:], strict=False):
        a, b = means[lo] - level, means[hi] - level
        if a == 0:
            out.append(float(lo))
        elif a * b < 0:
            out.append(lo + a / (a - b) * (hi - lo))
    return out


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))]


def score() -> None:
    """The registered rule: the best batch in the sweep, and its capacity, against the
    registration. The crossing is the driver's (the first downward one); every crossing of the
    mean curve is reported beside it, since a flat curve can cross 0.95 more than once."""
    pred = {int(r["b"]): r for r in _rows(OUT) if r["in_sweep"] == "True"}
    rows: list[dict[str, object]] = []
    measured: dict[int, float] = {}
    for b in SWEEP:
        runs = _rows(OUT.with_name(f"c5_d1_b{b}_runs.csv"))
        by: dict[int, list[float]] = {}
        for r in runs:
            by.setdefault(int(r["n_nodes"]), []).append(float(r["delivered_frac"]))
        means = {n: sum(v) / len(v) for n, v in by.items()}
        summary = {r["n_nodes"]: r for r in _rows(OUT.with_name(f"c5_d1_b{b}.csv"))}
        cross = summary["CROSSING@0.95"]
        first = float(cross["delivered_mean"]) if cross["delivered_mean"] else None
        every = all_crossings(means)
        p = float(pred[b]["capacity_root"]) if pred[b]["capacity_root"] else None
        if first is not None:
            measured[b] = first
        rows.append({"b": b, "seeds": cross["seeds"], "node_counts": " ".join(map(str, sorted(by))),
                     "ns3_crossing": "" if first is None else first,
                     "ci_lo": cross["delivered_min"], "ci_hi": cross["delivered_max"],
                     "bracketed": cross["delivered_stdev"],
                     "every_crossing": " ".join(f"{x:.3f}" for x in every),
                     "min_mean_delivered": round(min(means.values()), 6),
                     "predicted_root": "" if p is None else p,
                     "err_pct_first": "" if p is None or first is None
                     else round(100 * (p - first) / first, 2),
                     "err_pct_last": "" if p is None or not every
                     else round(100 * (p - every[-1]) / every[-1], 2)})
    best = max(measured, key=lambda b: measured[b])
    best_pred = max((b for b in SWEEP if pred[b]["capacity_root"]),
                    key=lambda b: float(pred[b]["capacity_root"]))
    step = abs(SWEEP.index(best) - SWEEP.index(best_pred))
    err = 100 * (float(pred[best]["capacity_root"]) - measured[best]) / measured[best]
    verdict = "held" if step <= 1 and abs(err) <= 5.0 else "failed"
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "c5_d1_scored",
                 "config_hash": provenance.config_hash({"sweep": SWEEP, "eps": EPS})}.items():
        buf.write(f"# {k}={v}\n")
    buf.write(f"# measured best batch b={best} ({measured[best]:.3f}); registered b={best_pred}; "
              f"{step} sweep step(s) apart; capacity error at the measured best {err:+.2f} %; "
              f"verdict {verdict}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.with_name("c5_d1_scored.csv").write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


def main() -> None:
    if sys.argv[1] == "--score":
        score()
        return
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
