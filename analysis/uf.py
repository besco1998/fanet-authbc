#!/usr/bin/env python3
"""U-F: capacity with capture and geometry (work package F of `docs/prompts/NEXT_PHASE_PROMPT.md`).

**The configurations:**
* cells C (146 B at 50 frames/s) and D (173 B at 12.5 frames/s);
* 802.11a 6 Mb/s and 802.11b 1 Mb/s;
* path-loss exponent α = 2 and 3, with and without Nakagami m = 1 fading per frame;
* nodes uniform in a disc;
* ns-3's own receiver rule, the 4 µs preamble window with θ = 4 dB (`predictions/UCAP.md`,
  `UCAP2.md`), with no frame-capture model: it never acts on DCF ties.

**The channel:**
* every node transmits at 40 dBm; ns-3's log-distance model with reference loss 46.6777 dB at
  1 m (distances below 1 m clamped to it, as ns-3 does);
* the radius is the largest whole metre at which the longest possible pair (2R) still receives
  −50 dBm on average: 32 dB above the −82 dBm detection floor. Then Rayleigh fades below the floor
  with probability 1 − exp(−10^−3.2) = 0.063 % < 0.1 %, and every pair is within carrier sense;
* α = 2: R = 73 m. α = 3: R = 13 m.

**The predictions** (`authbc.models.capture`), from the placements the runs will use (the twin's
`--placementOnly`):
* q_ij: the mean over the other stations m of the probability that receiver i decodes j's frame
  colliding with m's. Rayleigh: 1/(1 + θ(d_ij/d_im)^α); no fading: 1{d_im > θ^(1/α)·d_ij};
  θ = 10^0.4;
* ℓ_ij: 0 without fading; with Rayleigh, 1 − exp(−10^((−82 − P̄_ij)/10));
* ε′ = (ε − mean ℓ)/(1 − mean q) (G23); ε_w = min_j (ε − ℓ_j)/(1 − q_j) (G24), with q_j and ℓ_j
  the sender's means over its receivers;
* the capacities: the roots of (G25) and of the Poisson (G5) at ε′ and at ε_w.

    python analysis/uf.py --radius     -> the radius check
    python analysis/uf.py --markdown   -> the registration's table
    python analysis/uf.py --outlier    -> the outlier node's own predicted loss
"""
from __future__ import annotations

import csv
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.models import capture as cp  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

EPS = 0.05
TX_DBM = 40.0
REF_LOSS_DB = 46.6777
FLOOR_DBM = -82.0
MIN_MEAN_DBM = -50.0                  # 32 dB above the floor at the longest pair
SEEDS = range(1, 31)
RADIUS_M = {2: 73.0, 3: 13.0}


def rx_dbm(d_m: float, alpha: float) -> float:
    return TX_DBM - REF_LOSS_DB - 10 * alpha * math.log10(max(d_m, 1.0))


def largest_radius(alpha: float) -> float:
    """The largest whole-metre R at which a pair 2R apart still receives MIN_MEAN_DBM on average."""
    two_r = 10 ** ((TX_DBM - REF_LOSS_DB - MIN_MEAN_DBM) / (10 * alpha))
    return math.floor(two_r / 2)


def rayleigh_link_loss(mean_dbm: float) -> float:
    return 1 - math.exp(-10 ** ((FLOOR_DBM - mean_dbm) / 10))


@dataclass(frozen=True)
class FConfig:
    cell: str            # "C" or "D"
    standard: str
    alpha: int
    fading: bool

    @property
    def name(self) -> str:
        return (f"F{self.cell}{'A' if self.standard == '80211a' else 'B'}"
                f"P{self.alpha}{'R' if self.fading else 'N'}")

    @property
    def frame_bytes(self) -> int:
        return 146 if self.cell == "C" else 173

    @property
    def fps(self) -> float:
        return 50.0 if self.cell == "C" else 12.5

    @property
    def radius_m(self) -> float:
        return RADIUS_M[self.alpha]

    @property
    def access(self) -> uc.Access:
        return uc.A80211B if self.standard == "80211b" else uc.A80211A

    @property
    def tf_s(self) -> float:
        ph = phy.DSSS_1M if self.standard == "80211b" else phy.OFDM_20MHZ_6M
        return uc.airtime_s(ph, self.frame_bytes)


CONFIGS = [FConfig(c, s, a, f) for c in ("C", "D") for s in ("80211a", "80211b")
           for a in (2, 3) for f in (False, True)]


@cache
def positions(n: int, seed: int, radius: float) -> tuple[tuple[float, float], ...]:
    """The placement a run of the twin with this N, seed and radius uses (--placementOnly)."""
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "p"
        subprocess.run([str(exe), f"--nNodes={n}", f"--seed={seed}", f"--radiusM={radius}",
                        "--pathLossExp=2", "--placementOnly=1", f"--outPrefix={pre}"],
                       env=env, check=True, capture_output=True)
        with open(f"{pre}_positions.csv") as fh:
            return tuple((float(r["x_m"]), float(r["y_m"])) for r in csv.DictReader(fh))


def q_and_loss(c: FConfig, pos: tuple[tuple[float, float], ...]) -> tuple[list[float],
                                                                           list[float]]:
    """Per sender j: q_j and ℓ_j, the means over its receivers of q_ij and ℓ_ij."""
    n = len(pos)
    d = [[max(1.0, math.dist(pos[a], pos[b])) for b in range(n)] for a in range(n)]
    q_by_sender, l_by_sender = [], []
    for j in range(n):
        qs, ls = [], []
        for i in range(n):
            if i == j:
                continue
            others = [d[i][m] for m in range(n) if m not in (i, j)]
            if c.fading:
                qs.append(cp.q_rayleigh_pathloss(cp.THETA_NS3, c.alpha, d[i][j], others))
                ls.append(rayleigh_link_loss(rx_dbm(d[i][j], c.alpha)))
            else:
                qs.append(cp.q_no_fading(cp.THETA_NS3, c.alpha, d[i][j], others))
                ls.append(0.0)
        q_by_sender.append(sum(qs) / len(qs))
        l_by_sender.append(sum(ls) / len(ls))
    return q_by_sender, l_by_sender


def predict(c: FConfig, n_ref: int) -> dict[str, float]:
    """ε′ and ε_w averaged over the placement seeds at N = n_ref, and the four capacities."""
    eps_p, eps_w, q_bar, l_bar = [], [], [], []
    for seed in SEEDS:
        q, ell = q_and_loss(c, positions(n_ref, seed, c.radius_m))
        qm, lm = sum(q) / len(q), sum(ell) / len(ell)
        q_bar.append(qm)
        l_bar.append(lm)
        eps_p.append(cp.eps_average(EPS, lm, qm))
        eps_w.append(cp.eps_every_sender(EPS, ell, q))
    e1, e2 = sum(eps_p) / len(eps_p), sum(eps_w) / len(eps_w)
    acc, f, tf = c.access, c.fps, c.tf_s
    return {"n_ref": n_ref, "q_bar": sum(q_bar) / len(q_bar), "l_bar": sum(l_bar) / len(l_bar),
            "eps_prime": e1, "eps_w": e2,
            "g23_g25": pc.n_root_periodic(f, tf, e1, acc), "g23_poisson": uc.n_root(f, tf, e1, acc),
            "g24_g25": pc.n_root_periodic(f, tf, e2, acc), "g24_poisson": uc.n_root(f, tf, e2, acc),
            "no_capture_g25": pc.n_root_periodic(f, tf, EPS, acc)}


OUTLIER = FConfig("C", "80211a", 3, True)
OUTLIER_M = 250.0       # node 0 at (250 m, 0): every link ≈ −79 dBm mean, 3 dB over the floor


def outlier_prediction(n: int) -> dict[str, float]:
    """Node 0's own loss at N = n by (G22): p_c(ν)(1 − q_0) + ℓ_0, p_c from (G25)'s loss at n."""
    acc, f, tf = OUTLIER.access, OUTLIER.fps, OUTLIER.tf_s
    p_c = pc.loss_periodic(n, f, tf, acc)
    q0s, l0s = [], []
    for seed in SEEDS:
        pos = list(positions(n, seed, OUTLIER.radius_m))
        pos[0] = (OUTLIER_M, 0.0)
        q, ell = q_and_loss(OUTLIER, tuple(pos))
        q0s.append(q[0])
        l0s.append(ell[0])
    q0, l0 = sum(q0s) / len(q0s), sum(l0s) / len(l0s)
    return {"n": n, "p_c": p_c, "q_0": q0, "l_0": l0,
            "loss_0": cp.loss_with_capture(p_c, q0, l0),
            "eps_w_0": (EPS - l0) / (1 - q0)}


def n_ref_for(c: FConfig) -> int:
    """The reference N for a configuration's placements: 1.3 × its no-capture (G25) root."""
    return max(4, round(pc.n_root_periodic(c.fps, c.tf_s, EPS, c.access) * 1.3))


def markdown() -> str:
    lines = ["| config | cell | PHY | α | fading | R (m) | N_ref | mean q | mean ℓ | ε′ | ε_w | "
             "**(G23), (G25) root** | (G23), Poisson | **(G24), (G25) root** | (G24), Poisson | "
             "no capture, (G25) |", "|" + "---|" * 16]
    for c in CONFIGS:
        p = predict(c, n_ref_for(c))
        lines.append(
            f"| {c.name} | {c.cell} | {c.standard} | {c.alpha} | "
            f"{'Rayleigh' if c.fading else 'none'} | {c.radius_m:g} | {p['n_ref']:.0f} | "
            f"{p['q_bar']:.4f} | {p['l_bar']:.5f} | {p['eps_prime']:.4f} | {p['eps_w']:.4f} | "
            f"**{p['g23_g25']:.2f}** | {p['g23_poisson']:.2f} | **{p['g24_g25']:.2f}** | "
            f"{p['g24_poisson']:.2f} | {p['no_capture_g25']:.2f} |")
    return "\n".join(lines)


def main() -> None:
    if "--markdown" in sys.argv:
        print(markdown())
        return
    if "--outlier" in sys.argv:
        n = round(predict(OUTLIER, n_ref_for(OUTLIER))["g23_g25"])
        print({k: round(v, 5) for k, v in outlier_prediction(n).items()})
        return
    if "--radius" in sys.argv:
        for alpha in (2, 3):
            r = largest_radius(alpha)
            frac_clamped = 1 / r ** 2          # P(two uniform points in the disc within 1 m) ≈ 1/R²
            print(f"alpha {alpha}: R = {r:.0f} m; rx at 2R = {rx_dbm(2 * r, alpha):.2f} dBm; "
                  f"Rayleigh l at 2R = {rayleigh_link_loss(rx_dbm(2 * r, alpha)) * 100:.4f} %; "
                  f"pairs within 1 m ≈ {frac_clamped * 100:.2f} %")
        return
    for c in CONFIGS:
        no_cap = pc.n_root_periodic(c.fps, c.tf_s, EPS, c.access)
        p = predict(c, max(4, round(no_cap * 1.3)))
        print(c.name, {k: round(v, 4) for k, v in p.items()})


if __name__ == "__main__":
    main()
