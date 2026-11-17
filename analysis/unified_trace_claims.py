#!/usr/bin/env python3
"""Three claims of the unified model tested on stored traces, no new runs (task of 2026-11-17,
work package A5; the model: docs/revision/2026-11-17_unified_model_spec.md).

Each claim's criterion was fixed before its numbers were computed:

1. **Age of information.** Under independent frame loss p, the share of peak ages above the
   deadline is p^⌊(D_max − S)·Λ/b⌋, S being the delivery offset after a frame's last record
   (`t_after_ms`). Held if the prediction lies inside the exact 95 % binomial interval of every
   measured share (`aoi_under_loss.csv`).
2. **Mean access delay** ≈ ρ·[T/(2(1 − ρ)) + (W − 1)σ/2], ρ = (N − 1)·f·T_f, against ns-3's mean
   delay less the frame's own airtime and DIFS (`ns3_delay.csv`, `access_delay_ms`). Held if within
   max(10 %, 5 µs) at every load. The registration was defective: it defined ρ with T_f and left T
   undefined. Mohamed (2026-11-17): T is the medium holding time T_f + DIFS, as in (M16), in ρ
   too. Both readings are reported (see `access_delay`); neither is adopted after the fact.
3. **Verifiability under bursty loss:** V = (1 − p)(1 − (1 − α)^r)/(r·α), α = P(lost | the frame
   before arrived), fitted by counting transitions in the trace itself. Held if inside the trace's
   own 95 % interval, for ns-3's per-link traces (`verifiability_margin_trace.csv`) and for W3a's
   on-air traces through the real decoder.

    python analysis/unified_trace_claims.py      -> results/raw/unified_trace_claims.csv
"""
from __future__ import annotations

import csv
import io
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import bootstrap_ci  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "unified_trace_claims.csv"
W3A = REPO / "results" / "hw" / "channel24" / "w3a_2026-11-06"
DELAY_REL, DELAY_ABS_MS = 0.10, 0.005
REFS = (1, 2, 4)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def clopper_pearson(k: int, n: int, ci: float = 0.95) -> tuple[float, float]:
    a = (1 - ci) / 2
    lo = 0.0 if k == 0 else float(beta_dist.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1 - a, k + 1, n - k))
    return lo, hi


def aoi() -> list[dict]:
    out = []
    for r in _rows(RAW / "aoi_under_loss.csv"):
        p, b, lam = float(r["p"]), int(r["batch"]), float(r["lambda_rec_per_s"])
        k = math.floor((float(r["d_max_ms"]) - float(r["t_after_ms"])) * lam / b / 1000)
        pred = p ** k if p > 0 else 0.0
        n = int(r["updates"])
        hits = round(float(r["share_peak_over_dmax"]) * n)
        lo, hi = clopper_pearson(hits, n)
        out.append({"claim": "aoi_tail", "case": f"b={b} p={p:g}", "predicted": pred,
                    "measured": float(r["share_peak_over_dmax"]), "lo": round(lo, 6),
                    "hi": round(hi, 6), "extra": f"k={k} updates={n} exceedances={hits}",
                    "held": lo <= pred <= hi})
    return out


def access_delay() -> list[dict]:
    """Two rows per load: the claim as registered, and (M16), the reading Mohamed says was meant.

    Registered (2026-11-17, defective): ρ = ν·T_f and T undefined, read T = T_f; measured as the
    file's `access_delay_ms` (mean delay − `model_non_fill_ms`, 490.2–504.8 µs). (M16) of the
    model document: T = T_f + DIFS, the medium holding time, in ρ = ν·T as well; measured as the
    mean delay − (T_f + DIFS), T_f = 456 µs for 288 B by the PHY formula (`airtime_s`). Rows whose
    delivered fraction is below 0.95 are outside the formula's range (the queue drops frames
    there) and decide nothing. The 99th percentile is ns-3's alone. Neither reading is adopted
    after the fact (Mohamed, 2026-11-17): the item is recorded as failed as registered.
    """
    acc, out = uc.A80211A, []
    backoff = (acc.w - 1) * acc.slot_s / 2

    def formula(rho: float, t: float) -> float:
        """ρ·[T/(2(1 − ρ)) + (W − 1)σ/2], in ms."""
        return 1e3 * rho * (t / (2 * (1 - rho)) + backoff)

    for r in _rows(RAW / "ns3_delay.csv"):
        n, f = int(r["n_nodes"]), float(r["frames_per_s"])
        tf = uc.airtime_s(phy.OFDM_20MHZ_6M, int(r["frame_bytes"]))
        t_hold = tf + acc.difs_s
        nu = (n - 1) * f

        in_range = float(r["delivered_frac"]) >= 0.95
        meas_file = float(r["access_delay_ms"])
        meas_hold = float(r["delay_mean_ms"]) - 1e3 * t_hold
        p99 = float(r["delay_p99_ms"]) - 1e3 * t_hold
        for claim, pred, meas, how in (
                ("access_delay_registered", formula(nu * tf, tf), meas_file,
                 "rho=nu*Tf, T=Tf; measured = access_delay_ms (delay - model_non_fill)"),
                ("access_delay_M16", formula(nu * t_hold, t_hold), meas_hold,
                 "rho=nu*(Tf+DIFS), T=Tf+DIFS; measured = delay - (Tf+DIFS)")):
            tol = max(DELAY_REL * meas, DELAY_ABS_MS)
            extra = (f"{how}; delivered {r['delivered_frac']}; p99 access (ns-3) {p99:.4f} ms")
            if claim == "access_delay_M16":
                ok = abs(pred - meas_file) <= max(DELAY_REL * meas_file, DELAY_ABS_MS)
                extra += (f"; vs access_delay_ms {100 * (pred - meas_file) / meas_file:+.1f}% "
                          f"({'within' if ok else 'outside'} tolerance)")
            out.append({"claim": claim, "case": f"N={n} f={f:g} rho_Tf={nu * tf:.3f}",
                        "predicted": round(pred, 5), "measured": round(meas, 5),
                        "lo": round(meas - tol, 5), "hi": round(meas + tol, 5), "extra": extra,
                        "held": (abs(pred - meas) <= tol) if in_range else "out_of_range"})
    return out


def alpha_hat(masks: list[np.ndarray]) -> tuple[float, float]:
    """(p̂, α̂): the loss share, and P(lost | the frame before arrived) counted in the traces."""
    lost = sum(int(m.sum()) for m in masks)
    total = sum(len(m) for m in masks)
    after_ok = sum(int((~m[:-1]).sum()) for m in masks)
    ok_then_lost = sum(int(((~m[:-1]) & m[1:]).sum()) for m in masks)
    return lost / total, ok_then_lost / after_ok


def v_gilbert(p: float, alpha: float, r: int) -> float:
    return (1 - p) if alpha == 0 else (1 - p) * (1 - (1 - alpha) ** r) / (r * alpha)


def ns3_traces() -> list[dict]:
    import verifiability_margin as vm
    groups = vm.read_trace_dir(RAW / "ns3_spatial_a3trace_traces")
    out = []
    for r in _rows(RAW / "verifiability_margin_trace.csv"):
        masks = [m for run in groups[r["group"]] for m in run]
        p, a = alpha_hat(masks)
        ref = int(r["ref_interval"])
        pred = v_gilbert(p, a, ref)
        lo, hi = float(r["V_ci_lo"]), float(r["V_ci_hi"])
        out.append({"claim": "v_gilbert_ns3", "case": f"{r['group']} b={r['batch']} r={ref}",
                    "predicted": round(pred, 5), "measured": float(r["V_trace"]), "lo": lo,
                    "hi": hi, "extra": f"p={p:.5f} alpha={a:.5f} iid={float(r['V_iid']):.5f}",
                    "held": lo <= pred <= hi})
    return out


def w3a_traces() -> list[dict]:
    import w3a_loss
    out = []
    for power in sorted(p.name for p in W3A.iterdir() if p.is_dir() and p.name.startswith("p")):
        masks_by, _missing = w3a_loss.traces(W3A / power)      # each power folder is a session
        for (label, rx), masks in sorted(masks_by.items()):
            p, a = alpha_hat(masks)
            for ref in REFS:
                v = w3a_loss.v_through_decoder(masks, ref)
                lo, hi = bootstrap_ci(v, seed=1, statistic=np.mean)
                pred = v_gilbert(p, a, ref)
                out.append({"claim": "v_gilbert_w3a", "case": f"{power} {label} rx{rx} r={ref}",
                            "predicted": round(pred, 5), "measured": round(st.mean(v), 5),
                            "lo": round(lo, 5), "hi": round(hi, 5),
                            "extra": f"p={p:.5f} alpha={a:.5f} windows={len(masks)}",
                            "held": lo <= pred <= hi})
    return out


def main() -> None:
    rows = aoi() + access_delay() + ns3_traces() + w3a_traces()
    buf = io.StringIO()
    config = {"delay_rel": DELAY_REL, "delay_abs_ms": DELAY_ABS_MS, "refs": REFS}
    for k, v in {**provenance.env_block(), "run": "unified_trace_claims",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    by: dict[str, list[bool]] = {}
    for r in rows:
        if isinstance(r["held"], bool):                  # out-of-range rows decide nothing
            by.setdefault(r["claim"], []).append(r["held"])
        print(f"{r['claim']:18s} {r['case']:38s} pred {r['predicted']!s:>10} meas "
              f"{r['measured']!s:>9} [{r['lo']}, {r['hi']}] "
              f"{r['held'] if isinstance(r['held'], str) else ('held' if r['held'] else 'FAILED')}"
              f"  {r['extra']}")
    for c, v in by.items():
        print(f"== {c}: {sum(v)}/{len(v)} held")


if __name__ == "__main__":
    main()
