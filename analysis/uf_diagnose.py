#!/usr/bin/env python3
"""U-F diagnostics, written after the scored outcome (`predictions/UF.md`). None of this is scored.

Each diagnostic answers why a registered prediction missed. None changes a registered value.

0. **The crossings' bootstrap intervals** (`authbc.bench.stats.interpolated_crossing_ci`, the
   plain percentile interval), reported beside the scored point values; the score uses the
   point values only, as registered.
1. **ns-3's capture share, without a model.**
   * Without fading, a station's MAC does not depend on the received powers: every pair is above
     carrier sense, and broadcast has no acknowledgement. So the share of frames that collide is
     the same as in the stored equal-power runs at the same cell, PHY and N:
     * 802.11b: U-D's `Pb1B` and `Pb1D`, 30 seeds;
     * 802.11a: U-C1's `C` and `D`, 10 seeds.
   * Then q̂ = 1 − (L_capture − ℓ̄)/L_no-capture, set beside the closed form's mean q.
   * With Rayleigh fading, a fade below the −82 dBm floor (at most 0.063 % of frames) also
     changes carrier sense. The same ratio is reported, marked as approximate.
2. **The split of the (G23) error** (configurations where ns-3's no-capture curve brackets ε′):
   * **the loss-curve term:** (G25)'s root at the model's ε′ against ns-3's no-capture curve
     crossed at the same ε′;
   * **the q term:** ns-3's no-capture curve crossed at the model's ε′ against the same curve at
     ε/(1 − q̂);
   * **the closure:** that last crossing against ns-3's capture crossing, which tests (G22) itself
     when q is right.
   * Crossings are linear between whole N, as the score's. The loss curve is convex, so the
     loss-curve term is also given through a quadratic in the three nearest points.
3. **The worst sender is the minimum of finite samples.** Per run:
   * the measured spread of senders' delivered fractions, against
     * the spread from geometry alone: (G22) per sender, with p_c the run's own;
     * that plus binomial noise: frames per sender n_j, sd (1 − q_j)·√(p_c(1 − p_c)/n_j);
   * the worst sender's delivery, measured and from 200 Monte Carlo draws of geometry plus noise.
   * (G24)'s ε_w is the geometry-alone minimum. A scored statistic that is the minimum of 20 s
     samples also carries the noise of that minimum.
4. **Capture on the actual collision events** (configurations without fading, where ns-3's rule
   is deterministic given the powers). The F runs are rerun with `--traceMac=1 --traceRx=2`. The
   traces observe only: each rerun's delivered fraction must equal the stored run's.
   * **The groups:** frames whose airtimes overlap, from the MAC trace's TX begin and end.
   * **Measured:** for every collided frame j and every receiver i ≠ j, whether i decoded it
     (the PHY's OK lines, by uid).
   * **ns-3's rule on the actual group:** a receiver transmitting during j decodes nothing
     (half-duplex). Otherwise it decodes j if j's power is at least θ times the sum of the
     overlapping frames' powers, with powers from ns-3's log-distance model.
   * **The two-frame closed form on the same events:** the registered q_ij at the receivers that
     are not transmitting, and 0 at those that are.
   * **The registered mean q:** the closed form averaged over the receivers i ∉ {j, m}. It omits
     that one of the N − 1 receivers is the colliding partner itself, which cannot receive.
     Unconditionally, q is smaller by the factor (N − 2)/(N − 1).
   * The power model is checked on frames that did not collide: the sniffer's signal against the
     model's power at that distance.
5. **The roots with that factor:** ε′(N) = (ε − ℓ̄)/(1 − q̄·(N − 2)/(N − 1)) inside the
   bisection on N, and likewise for ε_w. A corrected model, not a prediction: Mohamed's rule of
   2026-11-20 needs a fresh registered check on unseen points before it is used.

    python analysis/uf_diagnose.py            -> results/raw/uf_diagnose_{ci,q,split,worst,
                                                 events,corrected}.csv
    python analysis/uf_diagnose.py --events   -> the event check only (its reruns included)
"""
from __future__ import annotations

import csv
import io
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import uf  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402

RAW = REPO / "results" / "raw"
NO_CAPTURE = {("C", "80211b"): ("unified_d1", "Pb1B"), ("D", "80211b"): ("unified_d1", "Pb1D"),
              ("C", "80211a"): ("unified_c1", "C"), ("D", "80211a"): ("unified_c1", "D")}
MC_DRAWS = 200


def _losses(stem: str, cell: str) -> dict[int, list[float]]:
    by: dict[int, list[float]] = defaultdict(list)
    for r in csv.DictReader(ln for ln in (RAW / f"{stem}_runs.csv").open()
                            if not ln.startswith("#")):
        if r["cell"] == cell:
            by[int(r["n_nodes"])].append(1 - float(r["delivered_frac"]))
    return dict(by)


def _se(v: list[float]) -> float:
    return st.stdev(v) / math.sqrt(len(v))


def _crossing(curve: dict[int, float], target: float) -> float | None:
    """Linear interpolation of N where the loss curve reaches target (bracketed only)."""
    ns = sorted(curve)
    for a, b in zip(ns, ns[1:], strict=False):
        if curve[a] <= target <= curve[b]:
            return a + (target - curve[a]) / (curve[b] - curve[a]) * (b - a)
    return None


def _crossing_quadratic(curve: dict[int, float], target: float) -> float | None:
    """As `_crossing`, through a quadratic in the three grid points nearest the linear crossing:
    the loss curve is convex, so the chord reaches a loss at a smaller N than the curve does."""
    lin = _crossing(curve, target)
    if lin is None:
        return None
    ns = sorted(sorted(curve, key=lambda n: abs(n - lin))[:3])
    a, b, c = ns
    la, lb, lc = curve[a], curve[b], curve[c]
    # Newton's form through the three points, solved for the root nearest the linear crossing
    d1, d2 = (lb - la) / (b - a), ((lc - lb) / (c - b) - (lb - la) / (b - a)) / (c - a)
    x = lin
    for _ in range(50):
        f = la + d1 * (x - a) + d2 * (x - a) * (x - b) - target
        df = d1 + d2 * (2 * x - a - b)
        x -= f / df
    return x


def capture_share() -> list[dict[str, Any]]:
    reg = uf.registered()
    rows = []
    for c in uf.CONFIGS:
        stem, cell = NO_CAPTURE[(c.cell, c.standard)]
        noc, cap = _losses(stem, cell), _losses(f"uf_{c.name.lower()}", c.name)
        l_bar = uf.predict(c, uf.n_ref_for(c))["l_bar"]
        for n in sorted(set(noc) & set(cap)):
            lc, ln = st.mean(cap[n]), st.mean(noc[n])
            ratio = (lc - l_bar) / ln
            se = ratio * math.hypot(_se(cap[n]) / lc, _se(noc[n]) / ln)
            rows.append({"config": c.name, "n": n, "seeds_capture": len(cap[n]),
                         "seeds_no_capture": len(noc[n]), "q_hat": 1 - ratio, "q_hat_se": se,
                         "q_closed_form": reg[c.name]["q_bar"],
                         "approximate": int(c.fading)})
    return rows


def split(q_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reg = uf.registered()
    rows = []
    for c in uf.CONFIGS:
        stem, cell = NO_CAPTURE[(c.cell, c.standard)]
        noc = {n: st.mean(v) for n, v in _losses(stem, cell).items()}
        cap = {n: st.mean(v) for n, v in _losses(f"uf_{c.name.lower()}", c.name).items()}
        qs = [r for r in q_rows if r["config"] == c.name]
        if not qs:
            continue
        # q̂ at the overlapping N nearest the capture crossing, the most precise of the near ones
        meas = _crossing(cap, uf.EPS)
        if meas is None:
            continue
        near = min(qs, key=lambda r: abs(int(r["n"]) - meas))
        e_mod = reg[c.name]["eps_prime"]
        e_hat = (uf.EPS - uf.predict(c, uf.n_ref_for(c))["l_bar"]) / (1 - float(near["q_hat"]))
        g25 = pc.n_root_periodic(c.fps, c.tf_s, e_mod, c.access)
        at_mod, at_hat = _crossing(noc, e_mod), _crossing(noc, e_hat)
        if at_mod is None or at_hat is None:
            continue
        rows.append({"config": c.name, "q_hat_at_n": near["n"], "q_hat": near["q_hat"],
                     "eps_prime_model": e_mod, "eps_prime_measured_q": e_hat,
                     "g23_g25_root": g25, "ns3_no_capture_at_model_eps": at_mod,
                     "ns3_no_capture_at_measured_q_eps": at_hat, "ns3_capture_crossing": meas,
                     "total_err_pct": 100 * (g25 - meas) / meas,
                     "loss_curve_term_pct": 100 * (g25 - at_mod) / meas,
                     "q_term_pct": 100 * (at_mod - at_hat) / meas,
                     "closure_pct": 100 * (at_hat - meas) / meas,
                     "loss_curve_term_pct_quadratic":
                         100 * (g25 - (_crossing_quadratic(noc, e_mod) or float("nan"))) / meas})
    return rows


def _run(c: uf.FConfig, n: int, seed: int) -> tuple[list[float], list[float], list[float]]:
    tr = uf.TRACES
    with (tr / f"{c.name}_n{n}_s{seed}_positions.csv").open() as fh:
        pos = tuple((float(r["x_m"]), float(r["y_m"])) for r in csv.DictReader(fh))
    with (tr / f"{c.name}_n{n}_s{seed}_nodes.csv").open() as fh:
        nodes = list(csv.DictReader(fh))
    x = [float(r["delivered_frac"]) for r in nodes]
    frames = [int(r["tx_frames"]) for r in nodes]
    q, ell = uf.q_and_loss(c, pos)
    p_c = ((1 - st.mean(x)) - st.mean(ell)) / (1 - st.mean(q))
    mu = [1 - (p_c * (1 - qj) + lj) for qj, lj in zip(q, ell, strict=True)]
    sig = [(1 - qj) * math.sqrt(max(p_c * (1 - p_c), 0.0) / k)
           for qj, k in zip(q, frames, strict=True)]
    return x, mu, sig


def worst_sender(points: dict[str, list[int]]) -> list[dict[str, Any]]:
    rows = []
    for c in uf.CONFIGS:
        rng = random.Random(f"uf_diagnose:{c.name}")
        for n in points.get(c.name, []):
            vm, vg, vn, wm, wg, ws = [], [], [], [], [], []
            for seed in uf.SEEDS:
                x, mu, sig = _run(c, n, seed)
                vm.append(st.pvariance(x))
                vg.append(st.pvariance(mu))
                vn.append(st.mean(s * s for s in sig))
                wm.append(min(x))
                wg.append(min(mu))
                ws.append(st.mean(min(m + s * rng.gauss(0, 1) for m, s in zip(mu, sig, strict=True))
                                  for _ in range(MC_DRAWS)))
            rows.append({"config": c.name, "n": n, "seeds": len(wm),
                         "sd_measured": math.sqrt(st.mean(vm)),
                         "sd_geometry": math.sqrt(st.mean(vg)),
                         "sd_binomial": math.sqrt(st.mean(vn)),
                         "sd_geometry_plus_noise": math.sqrt(st.mean(vg) + st.mean(vn)),
                         "worst_measured": st.mean(wm), "worst_geometry": st.mean(wg),
                         "worst_geometry_plus_noise": st.mean(ws)})
    return rows


def _points() -> dict[str, list[int]]:
    """Per configuration, the two grid N nearest ns-3's every-sender crossing (or the lowest two
    when the grid does not bracket it)."""
    out = {}
    for c in uf.CONFIGS:
        _avg, worst, _s = uf._per_n(c.name)
        w = _crossing({n: 1 - v for n, v in worst.items()}, uf.EPS)
        ns = sorted(worst)
        out[c.name] = sorted(ns, key=lambda n: abs(n - w))[:2] if w is not None else ns[:2]
    return out


def _write(name: str, rows: list[dict[str, Any]]) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": f"uf_diagnose_{name}"}.items():
        buf.write(f"# {k}={v}\n")
    wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    (RAW / f"uf_diagnose_{name}.csv").write_text(buf.getvalue())


EVENT_TRACES = Path.home() / ".cache" / "authbc_ufdiag_traces"
# (configuration, N near its crossing, seeds 1..k): no fading only, where the rule is exact
EVENT_POINTS = (("FCBP2N", 10, 5), ("FCBP3N", 10, 5), ("FDBP2N", 33, 3), ("FDBP3N", 34, 3),
                ("FCAP2N", 39, 2), ("FCAP3N", 41, 2))


def _rerun(name: str, n: int, seed: int) -> Path:
    """The F run (name, n, seed) again with the MAC and reception traces; its delivered fraction
    must equal the stored run's, or the traces changed the simulation."""
    import os
    sys.path.insert(0, str(REPO / "ns3"))
    import run_unified as ru
    from ns3_paths import ns3_root
    EVENT_TRACES.mkdir(parents=True, exist_ok=True)
    pre = EVENT_TRACES / f"{name}_n{n}_s{seed}"
    if not Path(f"{pre}_rx.csv").exists():
        exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
        env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
        ru.run_checked([str(exe), f"--nNodes={n}", f"--simTime={ru.CELLS[name].sim_s}",
                        f"--seed={seed}", f"--outPrefix={pre}", *ru.CELLS[name].args(),
                        "--traceMac=1", "--traceRx=2"], env)
    got = dict(csv.reader(pre.with_suffix(".csv").read_text().splitlines()[1:]))["delivered_frac"]
    stored = [r["delivered_frac"] for r in csv.DictReader(
        ln for ln in (RAW / f"uf_{name.lower()}_runs.csv").open() if not ln.startswith("#"))
        if int(r["n_nodes"]) == n and int(r["seed"]) == seed]
    if stored != [got]:
        raise SystemExit(f"{pre}: delivered {got} against the stored {stored}: traces moved it")
    return pre


def _groups(pre: Path) -> list[list[tuple[int, int, int, str]]]:
    """Frames (begin_ns, end_ns, node, uid) in groups whose airtimes overlap."""
    frames: dict[str, list[int]] = {}
    with Path(f"{pre}_mac.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["kind"] == "B":
                frames[r["uid"]] = [int(r["node"]), int(r["t_ns"]), -1]
            elif r["kind"] == "F" and r["uid"] in frames:
                frames[r["uid"]][2] = int(r["t_ns"])
    fl = sorted((b, e, nd, u) for u, (nd, b, e) in frames.items() if e >= 0)
    groups: list[list[tuple[int, int, int, str]]] = []
    end = -1
    for f in fl:
        if groups and f[0] < end:
            groups[-1].append(f)
            end = max(end, f[1])
        else:
            groups.append([f])
            end = f[1]
    return groups


def events(name: str, n: int, seed: int) -> dict[str, Any]:
    from authbc.models import capture as cp
    c = next(x for x in uf.CONFIGS if x.name == name)
    pre = _rerun(name, n, seed)
    with Path(f"{pre}_positions.csv").open() as fh:
        pos = [(float(r["x_m"]), float(r["y_m"])) for r in csv.DictReader(fh)]
    dist = [[max(1.0, math.dist(a, b)) for b in pos] for a in pos]
    mw = [[10 ** (uf.rx_dbm(dist[i][j], c.alpha) / 10) for j in range(n)] for i in range(n)]
    ok, dev = set(), []
    groups = _groups(pre)
    solo = {g[0][3]: g[0][2] for g in groups if len(g) == 1}
    with Path(f"{pre}_rx.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["kind"] == "OK":
                ok.add((int(r["node"]), r["uid"]))
            elif r["kind"] == "PWR" and r["uid"] in solo:
                i, j = int(r["node"]), solo[r["uid"]]
                dev.append(float(r["value"].split(";")[0]) - uf.rx_dbm(dist[i][j], c.alpha))
    pairs = meas = rule = closed = 0
    multi = 0
    for g in groups:
        if len(g) < 2:
            continue
        busy = {x[2] for x in g}
        for b, e, j, u in g:
            over = [x for x in g if x[3] != u and x[0] < e and b < x[1]]
            multi += len(over) > 1
            for i in range(n):
                if i == j:
                    continue
                pairs += 1
                meas += (i, u) in ok
                if i in busy:
                    continue
                rule += mw[i][j] >= cp.THETA_NS3 * sum(mw[i][x[2]] for x in over)
                closed += cp.q_no_fading(cp.THETA_NS3, c.alpha, dist[i][j],
                                         [dist[i][m] for m in range(n) if m not in (i, j)])
    collided = sum(len(g) for g in groups if len(g) > 1)
    return {"config": name, "n": n, "seed": seed, "frames": sum(len(g) for g in groups),
            "collided_frames": collided, "collided_with_two_or_more": multi,
            "pairs": pairs, "q_measured": meas / pairs, "q_rule_on_groups": rule / pairs,
            "q_closed_form_on_events": closed / pairs,
            "q_registered_mean": uf.registered()[name]["q_bar"],
            "q_registered_times_factor": uf.registered()[name]["q_bar"] * (n - 2) / (n - 1),
            "power_dev_max_db": max(map(abs, dev)), "power_checks": len(dev)}


OUTLIER_SEEDS = (1, 2, 3, 4, 5)
TIE_NS = 4_000          # the preamble window: starts closer than this are one DCF slot's tie
SENSE_NS = 25_000       # beyond a slot plus CCA's reaction, a start means the frame was not sensed


def outlier(seed: int, n: int = 42) -> dict[str, Any]:
    """FOUT's node 0, frame by frame, from the MAC and reception traces of the stored run.

    Written before the traces were read (2026-11-21), what each quantity should show:
    * node 0's frames that overlap no other frame lose only to the link: their loss should equal
      ℓ_0 from the placement, 0.368 averaged over seeds;
    * if node 0's excess loss is collisions its neighbours could not sense, the share of its
      frames overlapped by another should lie far above p_c (0.0795), with most partners
      starting more than SENSE_NS from node 0's start, in either order.
    """
    pre = _rerun("FOUT", n, seed)
    with Path(f"{pre}_positions.csv").open() as fh:
        pos = tuple((float(r["x_m"]), float(r["y_m"])) for r in csv.DictReader(fh))
    _q, ell = uf.q_and_loss(uf.OUTLIER, pos)
    ok: dict[str, int] = defaultdict(int)
    with Path(f"{pre}_rx.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["kind"] == "OK":
                ok[r["uid"]] += 1
    k: dict[str, int] = defaultdict(int)
    got: dict[str, int] = defaultdict(int)
    others_overlapped = others = 0
    for g in _groups(pre):
        for b, e, nd, uid in g:
            hit = [x for x in g if x[3] != uid and x[0] < e and x[1] > b]
            if nd != 0:
                others += 1
                others_overlapped += bool(hit)
                continue
            if not hit:
                kind = "solo"
            elif any(abs(x[0] - b) < TIE_NS for x in hit):
                kind = "tie"
            elif all(x[0] > b for x in hit):
                kind = "others_started_during_0" if min(x[0] for x in hit) - b > SENSE_NS \
                    else "others_started_early_in_0"
            elif all(x[0] < b for x in hit):
                kind = "0_started_during_other" if b - max(x[0] for x in hit) > SENSE_NS \
                    else "0_started_early_in_other"
            else:
                kind = "both"
            k[kind] += 1
            got[kind] += ok[uid]
    total = sum(k.values())
    row: dict[str, Any] = {"seed": seed, "n": n, "node0_frames": total,
                           "l0_placement": ell[0],
                           "others_overlapped_share": others_overlapped / others}
    for kind in ("solo", "tie", "others_started_early_in_0", "others_started_during_0",
                 "0_started_early_in_other", "0_started_during_other", "both"):
        row[f"share_{kind}"] = k[kind] / total
        row[f"loss_{kind}"] = 1 - got[kind] / ((n - 1) * k[kind]) if k[kind] else float("nan")
    row["loss_all"] = 1 - sum(got.values()) / ((n - 1) * total)
    return row


def _pair_point(c: uf.FConfig) -> int:
    """The 30-seed grid N nearest ns-3's average crossing."""
    a = {r["config"]: r for r in _read_scored()}[c.name]["ns3_average_crossing"]
    curve = _losses(f"uf_{c.name.lower()}", c.name)
    return min((n for n, v in curve.items() if len(v) == 30), key=lambda n: abs(n - float(a)))


def _read_scored() -> list[dict[str, str]]:
    with (RAW / "uf_scored.csv").open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def pairs(name: str) -> dict[str, Any]:
    """The registered report (not scored): each pair's measured loss against (G22),
    p_c(ν)(1 − q_ij) + ℓ_ij, with p_c from (G25) at the run's N and q_ij, ℓ_ij from the run's own
    placement, pooled over the 30 seeds at the grid N nearest ns-3's average crossing.

    Written before it was computed (2026-11-21), what it should show if (G22) holds pair by pair:
    * the sd of the measured pair losses equals the sd of the predicted ones and the binomial
      noise of each pair's count, added in quadrature;
    * the mean of the predicted pair losses lies below the measured where (G23) failed
      optimistic (the 802.11b cell C configurations), by F138's factor and F140's curve;
    * the correlation across pairs is positive and is limited by the count noise.
    """
    from authbc.models import capture as cp
    c = next(x for x in uf.CONFIGS if x.name == name)
    n = _pair_point(c)
    p_c = pc.loss_periodic(n, c.fps, c.tf_s, c.access)
    meas, pred, noise = [], [], []
    for seed in range(1, 31):
        stem = uf.TRACES / f"{c.name}_n{n}_s{seed}"
        with Path(f"{stem}_positions.csv").open() as fh:
            pos = [(float(r["x_m"]), float(r["y_m"])) for r in csv.DictReader(fh)]
        d = [[max(1.0, math.dist(a, b)) for b in pos] for a in pos]
        with Path(f"{stem}_pairs.csv").open() as fh:
            for r in csv.DictReader(fh):
                j, i, k = int(r["src"]), int(r["rx"]), int(r["tx_frames"])
                others = [d[i][m] for m in range(n) if m not in (i, j)]
                if c.fading:
                    q = cp.q_rayleigh_pathloss(cp.THETA_NS3, c.alpha, d[i][j], others)
                    ell = uf.rayleigh_link_loss(uf.rx_dbm(d[i][j], c.alpha))
                else:
                    q, ell = cp.q_no_fading(cp.THETA_NS3, c.alpha, d[i][j], others), 0.0
                p = cp.loss_with_capture(p_c, q, ell)
                meas.append(1 - int(r["rx_frames"]) / k)
                pred.append(p)
                noise.append(p * (1 - p) / k)
    sd_pred = st.pstdev(pred)
    return {"config": name, "n": n, "pairs": len(meas), "p_c_g25": p_c,
            "mean_measured": st.mean(meas), "mean_predicted": st.mean(pred),
            "sd_measured": st.pstdev(meas), "sd_predicted": sd_pred,
            "sd_binomial": math.sqrt(st.mean(noise)),
            "sd_predicted_plus_noise": math.sqrt(sd_pred ** 2 + st.mean(noise)),
            "correlation": st.correlation(meas, pred) if sd_pred > 0 else float("nan")}


def _root(c: uf.FConfig, eps_of_n: Any) -> float:
    """N where (G25)'s loss reaches an N-dependent target, by bisection as n_root_periodic."""
    lo, hi = 2.0, 1.0 / (c.fps * c.tf_s) + 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        e = eps_of_n(mid)
        lo, hi = (mid, hi) if pc.loss_periodic(mid, c.fps, c.tf_s, c.access, p_fixed=e) < e \
            else (lo, mid)
    return lo


def corrected(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from authbc.models import capture as cp
    rows = []
    for c, s in zip(uf.CONFIGS, scored, strict=True):
        n_ref = uf.n_ref_for(c)
        per_seed = [uf.q_and_loss(c, uf.positions(n_ref, seed, c.radius_m)) for seed in uf.SEEDS]
        q_bar = st.mean(st.mean(q) for q, _l in per_seed)
        l_bar = st.mean(st.mean(ell) for _q, ell in per_seed)

        def e_avg(nn: float, q_bar: float = q_bar, l_bar: float = l_bar) -> float:
            return cp.eps_average(uf.EPS, l_bar, q_bar * (nn - 2) / (nn - 1))

        def e_worst(nn: float, per_seed: list[Any] = per_seed) -> float:
            f = (nn - 2) / (nn - 1)
            return st.mean(cp.eps_every_sender(uf.EPS, ell, [x * f for x in q])
                           for q, ell in per_seed)

        g23, g24 = _root(c, e_avg), _root(c, e_worst)
        a, w = s["ns3_average_crossing"], s["ns3_every_sender_crossing"]
        rows.append({"config": c.name, "g23_registered": s["g23_g25"], "g23_corrected": g23,
                     "ns3_average_crossing": a,
                     "g23_registered_err_pct": s["g23_err_pct"],
                     "g23_corrected_err_pct": 100 * (g23 - a) / a if a != "" else "",
                     "g24_registered": s["g24_g25"], "g24_corrected": g24,
                     "ns3_every_sender_crossing": w,
                     "g24_corrected_err_pct": 100 * (g24 - w) / w if w != "" else ""})
    return rows


def crossing_cis() -> list[dict[str, Any]]:
    from authbc.bench.stats import interpolated_crossing_ci
    rows = []
    for c in uf.CONFIGS:
        path = RAW / f"uf_{c.name.lower()}_runs.csv"
        runs = [r for r in csv.DictReader(ln for ln in path.open() if not ln.startswith("#"))]
        avg: dict[int, list[float]] = defaultdict(list)
        worst: dict[int, list[float]] = defaultdict(list)
        for r in runs:
            n = int(r["n_nodes"])
            avg[n].append(float(r["delivered_frac"]))
            with (uf.TRACES / f"{c.name}_n{n}_s{r['seed']}_nodes.csv").open() as fh:
                worst[n].append(min(float(x["delivered_frac"]) for x in csv.DictReader(fh)))
        out: dict[str, Any] = {"config": c.name}
        for key, per_n in (("average", avg), ("every_sender", worst)):
            full = {n: v for n, v in per_n.items() if len(v) >= 30}
            ci = interpolated_crossing_ci(full, threshold=1 - uf.EPS)
            out[f"{key}_lo"], out[f"{key}_hi"], out[f"{key}_bracketed"] = ci if ci else ("", "", 0)
        rows.append(out)
    return rows


def _show(rows: list[dict[str, Any]]) -> None:
    for r in rows:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


def main() -> None:
    if "--outlier" in sys.argv:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(len(OUTLIER_SEEDS)) as ex:
            o_rows = list(ex.map(outlier, OUTLIER_SEEDS))
        _write("outlier", o_rows)
        _show(o_rows)
        return
    if "--pairs" in sys.argv:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(8) as ex:
            p_rows = list(ex.map(pairs, [c.name for c in uf.CONFIGS]))
        _write("pairs", p_rows)
        _show(p_rows)
        return
    ev = [events(name, n, seed) for name, n, k in EVENT_POINTS for seed in range(1, k + 1)]
    _write("events", ev)
    _show(ev)
    if "--events" in sys.argv:
        return
    ci_rows = crossing_cis()
    _write("ci", ci_rows)
    _show(ci_rows)
    q_rows = capture_share()
    _write("q", q_rows)
    split_rows = split(q_rows)
    _write("split", split_rows)
    _show(split_rows)
    cor = corrected(uf.score())
    _write("corrected", cor)
    _show(cor)
    w_rows = worst_sender(_points())
    _write("worst", w_rows)
    _show(w_rows)


if __name__ == "__main__":
    main()
