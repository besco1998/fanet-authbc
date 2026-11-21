#!/usr/bin/env python3
"""U-F2: the fresh checks Mohamed set after U-F (2026-11-21, F (a) and (b); `predictions/UF2.md`).

**(a) (G23) with (G22a).** The capture share averaged over receivers is q̄·(N − 2)/(N − 1)
(F138; the model document §8.1). Registered on placements and seeds never used (31–60; U-F used
1–30), at configurations whose root lies at occupancy ≤ 0.78, where (G25) was checked (U-G25).

**(b) The every-sender criterion, two labelled statistics** (§8.3):
* **statistic 1, (G24) with (G22a):** each sender's delivery pooled over all 30 run seeds and the
  whole run, on one fixed placement per node count (placement seed 61, read back through the
  twin's `--positionsFile`), against the long-run worst sender max_j p_j of that placement;
* **statistic 2, (G24a):** the worst sender per 20 s run, against E[max_j p̂_j] computed exactly
  from independent binomial counts at the predicted p_j (`capture.worst_window_loss`), on (a)'s
  own runs and placements. The z_N closed form is reported beside it.

Per sender, p_j = p_c(N)(1 − q_j·(N − 2)/(N − 1)) + ℓ_j (G22, G22a), with p_c from (G25) at N,
and q_j, ℓ_j the sender's means over its receivers (`uf.q_and_loss`, ns-3's 4 dB window rule).

**The pooled statistic's residual noise** (stated before any run): the worst of N pooled senders
reads below the long-run worst by about z_N·√(p(1 − p)/M) in loss, M frames per sender pooled,
which moves the crossing by about z_N·√((1 − ε)/(ε M)) of N. Each configuration's run length is
chosen so that this is at most RESIDUAL (2 %, two fifths of the tolerance).

    python analysis/uf2.py --predict    -> results/raw/uf2_predictions.csv and the tables
    python analysis/uf2.py --markdown   -> the registration's tables, from that file
    python analysis/uf2.py --scan       -> stored CSV rows at a cell's (bytes, frames/s)
    python analysis/uf2.py --score      -> results/raw/uf2_scored.csv
"""
from __future__ import annotations

import math
import statistics as st
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import uf  # noqa: E402

from authbc.models import capture as cp  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

EPS = 0.05
SEEDS = range(31, 61)
PLACEMENT_SEED = 61
RUN_S = 20.0                      # (a) and statistic 2: one window per run
RESIDUAL = 0.02
MAX_OCCUPANCY = 0.78
TOL = 0.05


@dataclass(frozen=True)
class UF2Config:
    standard: str
    frame_bytes: int
    fps: float
    alpha: int
    fading: bool

    @property
    def name(self) -> str:
        return (f"E{'A' if self.standard == '80211a' else 'B'}{self.frame_bytes}F{self.fps:g}"
                f"P{self.alpha}{'R' if self.fading else 'N'}")

    @property
    def radius_m(self) -> float:
        return uf.RADIUS_M[self.alpha]

    @property
    def access(self) -> uc.Access:
        return uc.A80211B if self.standard == "80211b" else uc.A80211A

    @property
    def tf_s(self) -> float:
        ph = phy.DSSS_1M if self.standard == "80211b" else phy.OFDM_20MHZ_6M
        return uc.airtime_s(ph, self.frame_bytes)


CELLS = (("80211b", 100, 12.5), ("80211b", 100, 10.0), ("80211a", 400, 100.0),
         ("80211a", 700, 50.0))
GEOMETRIES = ((3, True), (2, False))
CONFIGS = [UF2Config(s, b, f, a, fad) for s, b, f in CELLS for a, fad in GEOMETRIES]


def _root(c: UF2Config, eps_of_n: Any) -> float:
    """N where (G25)'s loss reaches an N-dependent target, by bisection (as uf_diagnose._root)."""
    lo, hi = 2.0, 1.0 / (c.fps * c.tf_s) + 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        e = eps_of_n(mid)
        lo, hi = (mid, hi) if pc.loss_periodic(mid, c.fps, c.tf_s, c.access, p_fixed=e) < e \
            else (lo, mid)
    return lo


def _poisson_root(c: UF2Config, eps_of_n: Any) -> float:
    lo, hi = 2.0, 1.0 / (c.fps * c.tf_s) + 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        e = eps_of_n(mid)
        lo, hi = (mid, hi) if uc.loss((mid - 1) * c.fps, c.tf_s, c.access, p_fixed=e) < e \
            else (lo, mid)
    return lo


def n_ref_for(c: UF2Config) -> int:
    """U-F's reference N for the placements: 1.3 × the no-capture (G25) root."""
    return max(4, round(pc.n_root_periodic(c.fps, c.tf_s, EPS, c.access) * 1.3))


@cache
def _geometry(c: UF2Config, n: int, seed: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    q, ell = uf.q_and_loss(c, uf.positions(n, seed, c.radius_m))   # type: ignore[arg-type]
    return tuple(q), tuple(ell)


def predict_a(c: UF2Config) -> dict[str, float]:
    """(a): q̄ and ℓ̄ over the run seeds' placements at N_ref, and the roots."""
    n_ref = n_ref_for(c)
    geo = [_geometry(c, n_ref, s) for s in SEEDS]
    q_bar = st.mean(st.mean(q) for q, _l in geo)
    l_bar = st.mean(st.mean(ell) for _q, ell in geo)

    def with_factor(nn: float) -> float:
        return cp.eps_average(EPS, l_bar, q_bar * cp.half_duplex_factor(nn))

    def without(_nn: float) -> float:
        return cp.eps_average(EPS, l_bar, q_bar)

    root = _root(c, with_factor)
    return {"n_ref": n_ref, "q_bar": q_bar, "l_bar": l_bar, "g23_g22a_g25": root,
            "occupancy": root * c.fps * c.tf_s, "g23_g25_no_factor": _root(c, without),
            "g23_g22a_poisson": _poisson_root(c, with_factor),
            "no_capture_g25": pc.n_root_periodic(c.fps, c.tf_s, EPS, c.access)}


def p_senders(c: UF2Config, n: int, seed: int) -> list[float]:
    """Each sender's predicted loss at N = n on placement `seed`: (G22) with (G22a), p_c (G25)."""
    q, ell = _geometry(c, n, seed)
    f = cp.half_duplex_factor(n)
    p_c = pc.loss_periodic(n, c.fps, c.tf_s, c.access)
    return [min(1.0, p_c * (1 - qj * f) + lj) for qj, lj in zip(q, ell, strict=True)]


def _crossing(curve: dict[int, float]) -> float | None:
    """Where a loss curve (by N) crosses ε, linearly between whole N."""
    ns = sorted(curve)
    for a, b in zip(ns, ns[1:], strict=False):
        if curve[a] <= EPS < curve[b]:
            return a + (EPS - curve[a]) / (curve[b] - curve[a]) * (b - a)
    return None


def _span(c: UF2Config, low: float, high: float) -> range:
    r = predict_a(c)["g23_g22a_g25"]
    return range(max(4, math.floor(low * r)), math.ceil(high * r) + 1)


def predict_stat2(c: UF2Config) -> dict[str, Any]:
    """(G24a): E[max_j p̂_j] per N, averaged over the run seeds' placements, and its root."""
    m = round(c.fps * RUN_S)
    exact, normal = {}, {}
    for n in _span(c, 0.6, 1.1):
        ps = [p_senders(c, n, s) for s in SEEDS]
        exact[n] = st.mean(cp.worst_window_loss(p, m) for p in ps)
        normal[n] = st.mean(cp.worst_window_loss_normal(st.mean(p), n, m) for p in ps)
    return {"frames_per_window": m, "g24a_root": _crossing(exact),
            "g24a_normal_root": _crossing(normal), "curve": exact}


def predict_stat1(c: UF2Config) -> dict[str, Any]:
    """(G24) with (G22a) on the fixed placement per N: the long-run worst sender, its root, the
    run grid, and the run length that brings the pooled residual to RESIDUAL."""
    curve = {n: max(p_senders(c, n, PLACEMENT_SEED)) for n in _span(c, 0.6, 1.1)}
    root = _crossing(curve)
    if root is None:
        raise SystemExit(f"{c.name}: the long-run worst sender does not cross ε in the span")
    centre = round(root)
    step = max(1, round(0.03 * centre))
    grid = [centre + k * step for k in range(-4, 5)]
    z = cp.z_n(centre)
    frames = z * z * (1 - EPS) / (EPS * RESIDUAL ** 2)        # pooled frames per sender
    run_s = 10 * math.ceil(frames / (len(SEEDS) * c.fps) / 10)
    pooled = len(SEEDS) * c.fps * run_s
    return {"g24_root": root, "grid": grid, "run_s": run_s, "pooled_frames": pooled,
            "residual_pct": 100 * z * math.sqrt((1 - EPS) / (EPS * pooled))}


def scan() -> list[tuple[str, str, int, float]]:
    import ug25
    saved = ug25.CELLS
    ug25.CELLS = {f"{s}_{b}_{f:g}": ug25.G25Cell(s, b, f) for s, b, f in CELLS}
    try:
        return ug25.scan_prior()
    finally:
        ug25.CELLS = saved


OUT = REPO / "results" / "raw" / "uf2_predictions.csv"


def predict() -> list[dict[str, Any]]:
    """Every registered value, one row per configuration (written once, at registration)."""
    rows = []
    for c in CONFIGS:
        a = predict_a(c)
        s2 = predict_stat2(c)
        s1 = predict_stat1(c)
        rows.append({"config": c.name, "standard": c.standard, "frame_bytes": c.frame_bytes,
                     "fps": c.fps, "alpha": c.alpha, "fading": int(c.fading), **a,
                     "g24a_root": s2["g24a_root"], "g24a_normal_root": s2["g24a_normal_root"],
                     "frames_per_window": s2["frames_per_window"], "g24_root": s1["g24_root"],
                     "pooled_grid": " ".join(map(str, s1["grid"])), "pooled_run_s": s1["run_s"],
                     "pooled_frames": s1["pooled_frames"], "residual_pct": s1["residual_pct"]})
    return rows


def registered() -> dict[str, dict[str, str]]:
    import csv
    with OUT.open() as fh:
        return {r["config"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


def markdown() -> str:
    a_lines = ["| config | PHY | frame, frames/s | α | fading | N_ref | mean q | mean ℓ | "
               "**(G23), (G22a), (G25) root** | occupancy there | without the factor | "
               "Poisson, with the factor | no capture |", "|" + "---|" * 13]
    b_lines = ["| config | **(G24a) root, exact** | z_N closed form | frames per window | "
               "**(G24) root, fixed placement** | its grid | run length (s) | "
               "pooled frames per sender | residual |", "|" + "---|" * 9]
    for name, r in registered().items():
        f = float
        grid = r["pooled_grid"].split()
        a_lines.append(
            f"| {name} | {r['standard']} | {r['frame_bytes']} B, {f(r['fps']):g} | {r['alpha']} | "
            f"{'Rayleigh' if r['fading'] == '1' else 'none'} | {r['n_ref']} | "
            f"{f(r['q_bar']):.4f} | {f(r['l_bar']):.5f} | **{f(r['g23_g22a_g25']):.2f}** | "
            f"{f(r['occupancy']):.3f} | {f(r['g23_g25_no_factor']):.2f} | "
            f"{f(r['g23_g22a_poisson']):.2f} | {f(r['no_capture_g25']):.2f} |")
        b_lines.append(
            f"| {name} | **{f(r['g24a_root']):.2f}** | {f(r['g24a_normal_root']):.2f} | "
            f"{r['frames_per_window']} | **{f(r['g24_root']):.2f}** | "
            f"{grid[0]}–{grid[-1]} step {int(grid[1]) - int(grid[0])} | {r['pooled_run_s']} | "
            f"{f(r['pooled_frames']):.0f} | {f(r['residual_pct']):.2f} % |")
    return "\n".join(a_lines) + "\n\n" + "\n".join(b_lines)


TRACES = Path.home() / ".cache" / "authbc_uf2_traces"


def _crossing_of(curve: dict[int, float], level: float = 1 - EPS) -> float | None:
    from authbc.bench.stats import interpolated_crossing
    return interpolated_crossing(curve, level)


def _runs(stem: str) -> list[dict[str, str]]:
    import csv
    path = REPO / "results" / "raw" / f"{stem}_runs.csv"
    with path.open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def worst_of_run(name: str, n: int, seed: int) -> float:
    import csv
    with (TRACES / f"{name}_n{n}_s{seed}_nodes.csv").open() as fh:
        return min(float(r["delivered_frac"]) for r in csv.DictReader(fh))


def score() -> list[dict[str, Any]]:
    """(a), statistic 2 and statistic 1, each ±5 % on the crossing, with its side."""
    reg = registered()
    rows = []
    for c in CONFIGS:
        r = reg[c.name]
        by: dict[int, list[dict[str, str]]] = {}
        for x in _runs(f"uf2_{c.name.lower()}"):
            by.setdefault(int(x["n_nodes"]), []).append(x)
        by = {n: v for n, v in by.items() if len(v) == len(SEEDS)}
        avg = {n: st.mean(float(x["delivered_frac"]) for x in v) for n, v in by.items()}
        worst = {n: st.mean(worst_of_run(c.name, n, int(x["seed"])) for x in v)
                 for n, v in by.items()}
        pooled = pooled_worst(c)
        for what, measured, pred in (("(a) (G23) with (G22a)", _crossing_of(avg),
                                      float(r["g23_g22a_g25"])),
                                     ("statistic 2, (G24a)", _crossing_of(worst),
                                      float(r["g24a_root"])),
                                     ("statistic 1, (G24) pooled", _crossing_of(pooled),
                                      float(r["g24_root"]))):
            err = (pred - measured) / measured if measured else None
            rows.append({"config": c.name, "claim": what, "ns3_crossing": measured or "",
                         "predicted": pred, "err_pct": 100 * err if err is not None else "",
                         "held": int(err is not None and abs(err) <= TOL),
                         "side": "" if err is None or abs(err) <= TOL else
                         ("optimistic" if err > 0 else "conservative"),
                         "grid": " ".join(map(str, sorted(by if what != "statistic 1, (G24) "
                                                          "pooled" else pooled)))})
    return rows


def pooled_worst(c: UF2Config) -> dict[int, float]:
    """Statistic 1: per N, the worst sender's delivery pooled over all runs (frames-weighted)."""
    sent: dict[tuple[int, int], float] = {}
    got: dict[tuple[int, int], float] = {}
    seeds: dict[int, set[int]] = {}
    for x in _runs(f"uf2_pooled_{c.name.lower()}"):
        key = (int(x["n_nodes"]), int(x["node"]))
        tx = float(x["tx_frames"])
        sent[key] = sent.get(key, 0.0) + tx
        got[key] = got.get(key, 0.0) + tx * float(x["delivered_frac"])
        seeds.setdefault(int(x["n_nodes"]), set()).add(int(x["seed"]))
    out = {}
    for n, s in seeds.items():
        if len(s) == len(SEEDS):
            out[n] = min(got[(n, j)] / sent[(n, j)] for j in range(n))
    return out


def main() -> None:
    import csv
    import io
    if "--scan" in sys.argv:
        hits = scan()
        print(f"{len(hits)} stored rows at a cell's (bytes, frames/s)")
        for h in hits:
            print("  ", h)
        return
    if "--predict" in sys.argv:
        from authbc.bench import provenance
        rows = predict()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "uf2_predictions"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        OUT.write_text(buf.getvalue())
        print(markdown())
        return
    if "--markdown" in sys.argv:
        print(markdown())
        return
    if "--score" in sys.argv:
        from authbc.bench import provenance
        rows = score()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "uf2_scored"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        (REPO / "results" / "raw" / "uf2_scored.csv").write_text(buf.getvalue())
        for r in rows:
            print(r)
        return
    for c in CONFIGS:
        print(c.name, predict_a(c))


if __name__ == "__main__":
    main()
