#!/usr/bin/env python3
"""W1s — the last board session of this phase (Mohamed, 2026-11-23; predictions/W1s.md): three
parts in one session with a fixed end, the boards in W1q's 1 m triangle throughout.

**A. W1q's gradual capture curve, checked on steps W1q did not use.** The reading under test is
the halfway RSSI reading alone (W1q, "Seen after scoring"). The curve is W1q's steps that pass
Mohamed's criterion, each sender's single-sender loss ≤ 1 % at every receiver (steps 0, 3 and 6;
10 and 15 fail it), as a piecewise-linear q_A(Δ), q_B(Δ) with no fitted parameter. A new step
holds if each sender's q lies within the curve's range over its measured Δ ± 1.5 dB, widened by
±0.02. A step with Δ < 0 is read on the mirrored curve (the stronger sender on q_A's branch, the
weaker on q_B's), the hypothesis that capture follows the power difference, not the sender.

**B. The contention window, re-derived once** from the 2026-11-22 rate checks (frame burst off),
both families, and one test: the saturated pi-A + pi-B pair at 345 B of UDP payload, a length no
2.4 GHz session has used. W1p's rule: a family is consistent if inside the measured 95 % interval
for both the loss and the rate. If neither is, the window is not identifiable without a frame
sniffer (Mohamed, 2026-11-23).

**C. The Pi 3's extra time per frame**, fixed per frame or a wider backoff, from the gaps of each
board alone and saturated, at the receiver that hears both (pi-B). With gap = DIFS + g₀ + kσ, k
uniform on 0 … W − 1, median − IQR = DIFS + g₀; between boards DIFS cancels.

    python analysis/w1s.py --predict   -> results/raw/w1s_predictions.csv,
                                          experiments/channel24/plan_w1s.txt
    python analysis/w1s.py --score results/hw/channel24/<session>
    python analysis/w1s.py --known145  -> results/raw/w1s_known145.csv (the disclosure only)
"""
from __future__ import annotations

import csv
import io
import os
import re
import statistics as st
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "ns3"))

import dsss_three as w1d  # noqa: E402
import hw_session as hs  # noqa: E402
import uh  # noqa: E402
import w1p  # noqa: E402
import w1q  # noqa: E402

from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

PI_A, PI_B, PI_3 = 1, 2, 3
HW = REPO / "results" / "hw" / "channel24"
OUT = REPO / "results" / "raw" / "w1s_predictions.csv"
PLAN = w1d.PLANS / "plan_w1s.txt"

# ---- A. the capture curve -------------------------------------------------------------------
W1Q = HW / "w1q_2026-11-22"
LINK_MAX = 0.01                 # Mohamed: a step enters, or is scored, only at or below this
DELTA_TOL_DB = 1.5              # W1q's step tolerance
Q_WIDEN = 0.02                  # W1q's typical window-to-window range
P0_MBM = 1500
A_STEPS = (("15", 1500, 1500), ("13", 1300, 1500), ("11", 1100, 1500), ("10", 1000, 1500))
ANCHOR = "15"
NEG = ("N", 1500, 1800)         # pi-B raised to 18 dBm, pi-A at 15: the negative side
NEG_READBACK_DBM = 18.0
POWER_A = {d: pa for d, pa, _ in A_STEPS}
MIN_SCORED_STEPS = 2

# ---- B. the window --------------------------------------------------------------------------
# The in-session rate checks of 2026-11-22 (frame burst off), before and after: W1p, W1q, W1r.
CYCLE_SESSIONS = ("w1p_2026-11-22", "w1q_2026-11-22", "w1r_2026-11-22")
T_F_145 = uc.airtime_s(phy.DSSS_1M, uh.W1F_FRAME)     # the frame the cycles were measured with
PAYLOAD_B = 345
FRAME_B = PAYLOAD_B + (uh.W1F_FRAME - w1d.PAYLOAD_UDP)   # ns-3 frameSize: + IP and UDP, 373
SAT_FPS = 600
SIM_S = 20.0
SEEDS = range(1, 31)
PAIR_WINDOWS = 6
MIN_ON_AIR_B = 2500             # about 3 000 frames per sender in a 25 s window at 345 B
CHOICES = ("mean", "min", "max")    # "mean" is the registered one; min and max are reported

# ---- C. the Pi 3's timing ------------------------------------------------------------------
NEGATIVE_GAP_MAX = 0.05


# ============================================================================== A
def single_losses(files: dict[str, Any], tags: dict[str, list[str]], d: str
                  ) -> dict[str, float]:
    """Each sender's loss at every other receiver, alone at 50 frames/s, in step d's windows."""
    a, b = tags[f"A{d}"][0], tags[f"B{d}"][0]
    la = w1q.losses(files[a]["rx"], PI_A, files[a]["tx"][PI_A]["sent"])
    lb = w1q.losses(files[b]["rx"], PI_B, files[b]["tx"][PI_B]["sent"])
    return {**{f"A at {r}": v for r, v in la.items()}, **{f"B at {r}": v for r, v in lb.items()}}


def _session_parts(session: Path) -> tuple[dict, dict[str, list[str]], dict[str, bool]]:
    windows = w1d.window_rows(session)
    files = w1d._files(session)
    tags: dict[str, list[str]] = {}
    for w in sorted(windows, key=lambda x: int(x["window"].split("_")[0])):
        tags.setdefault(w["label"], []).append(w["window"])
    return files, tags, {w["window"]: w["power_ok"] for w in windows}


def measure_step(session: Path, d: str) -> dict[str, Any]:
    """Δ from the halfway readings alone, q of each sender at the Pi 3, the worst link."""
    files, tags, power_ok = _session_parts(session)
    mid = [x for x in hs.rssi(session, PI_3) if x["when"] == "mid"]
    s = w1q._step(files, tags, power_ok, d, PI_3, PI_A, PI_B, mid, False, ("A", "B", "C"))
    links = single_losses(files, tags, d)
    return {"step": d, "delta_db": s["sir_db"], "rssi_a": s["rssi_1"], "rssi_b": s["rssi_2"],
            "q_a": st.mean(s["q_1"]), "q_b": st.mean(s["q_2"]), "q_a_w": s["q_1"],
            "q_b_w": s["q_2"], "worst_link": max(links.values()), "links": links}


def curve_points(session: Path = W1Q) -> list[dict[str, Any]]:
    """W1q's steps with the halfway reading, each marked whether it enters the curve."""
    out = []
    for d in w1q.STEPS_DB:
        m = measure_step(session, str(d))
        m["enters"] = m["worst_link"] <= LINK_MAX
        out.append(m)
    return out


def _lin(pts: list[tuple[float, float]], x: float) -> float:
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError(f"{x} outside the curve's span {pts[0][0]}…{pts[-1][0]}")


def curve_band(points: list[tuple[float, float, float]], delta_db: float,
               tol: float = DELTA_TOL_DB, widen: float = Q_WIDEN
               ) -> dict[str, tuple[float, float]] | None:
    """The range of each sender's q over Δ ± tol, from the curve's (Δ, q_A, q_B) points, widened.
    Δ < 0 is read on the mirror: q_B on q_A's branch at |Δ|, q_A on q_B's. None outside the span."""
    pts = sorted(points)
    x = abs(delta_db)
    lo_x, hi_x = max(x - tol, pts[0][0]), min(x + tol, pts[-1][0])
    if x < pts[0][0] or x > pts[-1][0]:
        return None
    xs = [lo_x, hi_x] + [p[0] for p in pts if lo_x < p[0] < hi_x]
    branch = {}
    for k, name in ((1, "own"), (2, "other")):
        vals = [_lin([(p[0], p[k]) for p in pts], v) for v in xs]
        branch[name] = (min(vals) - widen, max(vals) + widen)
    if delta_db >= 0:
        return {"q_a": branch["own"], "q_b": branch["other"]}
    return {"q_a": branch["other"], "q_b": branch["own"]}


def readback_dbm(session: Path, node: int, asked_mbm: int) -> float | None:
    """The power the driver read back after `asked_mbm` was set on `node` (its session log)."""
    log = (hs.node_dirs(session)[node] / "session.log").read_text()
    m = re.search(rf"txpower asked {asked_mbm}:\s*txpower ([0-9.]+) dBm", log)
    return float(m.group(1)) if m else None


def score_a(session: Path, curve: list[tuple[float, float, float]]) -> list[dict[str, Any]]:
    out = []
    scored = held = 0
    _, tags, _ = _session_parts(session)
    for d, *_ in [*A_STEPS, NEG]:
        item = (f"pi-A {POWER_A[d] / 100:g} dBm" if d != NEG[0] else "pi-B 18 dBm, pi-A 15 dBm")
        if not all(f"{x}{d}" in tags for x in "ABC"):
            # a chip stop (chip_check.sh) can end a board's windows early
            out.append({"what": "A: step", "item": item, "measured": "no windows",
                        "predicted": "", "held": "not run"})
            continue
        m = measure_step(session, d)
        meas = (f"Δ {m['delta_db']:+.1f} dB; q_A {m['q_a']:.3f}, q_B {m['q_b']:.3f}; "
                f"worst single-sender loss {100 * m['worst_link']:.2f} %")
        if d == ANCHOR:
            out.append({"what": "A: anchor (W1q's 0 dB step again)", "item": item,
                        "measured": meas, "predicted": f"W1q: Δ {curve_anchor(curve)}",
                        "held": "reported (drift)"})
            continue
        if d == NEG[0]:
            rb = readback_dbm(session, PI_B, NEG[2])
            if rb != NEG_READBACK_DBM:
                out.append({"what": "A: negative step", "item": item, "measured":
                            f"pi-B read back {rb} dBm", "predicted": "18.00 dBm",
                            "held": "dropped: the curve covers Δ ≥ 0 only"})
                continue
        if m["worst_link"] > LINK_MAX:
            out.append({"what": "A: step", "item": item, "measured": meas,
                        "predicted": "single-sender loss ≤ 1 %", "held": "not scored (link)"})
            continue
        band = curve_band(curve, m["delta_db"])
        if band is None:
            out.append({"what": "A: step", "item": item, "measured": meas,
                        "predicted": "|Δ| within the curve's span", "held": "not scored (span)"})
            continue
        ok_a = band["q_a"][0] <= m["q_a"] <= band["q_a"][1]
        ok_b = band["q_b"][0] <= m["q_b"] <= band["q_b"][1]
        scored += 1
        held += ok_a and ok_b
        out.append({"what": "A: step", "item": item, "measured": meas,
                    "predicted": f"q_A {band['q_a'][0]:.3f}–{band['q_a'][1]:.3f}, "
                                 f"q_B {band['q_b'][0]:.3f}–{band['q_b'][1]:.3f}"
                                 + (" (mirrored)" if m["delta_db"] < 0 else ""),
                    "held": ok_a and ok_b})
    used = scored >= MIN_SCORED_STEPS and held == scored
    out.append({"what": "A: the curve", "item": f"{held} of {scored} scored steps held",
                "measured": "", "predicted": f"every scored step, at least {MIN_SCORED_STEPS}",
                "held": "used" if used else "not used: the thesis states W1q's scored result"})
    return out


def curve_anchor(curve: list[tuple[float, float, float]]) -> str:
    top = max(curve)
    return f"{top[0]:+.1f} dB, q_A {top[1]:.3f}, q_B {top[2]:.3f}"


# ============================================================================== B
def day_cycles_us() -> dict[int, list[float]]:
    """Every board's in-session rate checks of 2026-11-22, in session order."""
    out: dict[int, list[float]] = {1: [], 2: [], 3: []}
    for name in CYCLE_SESSIONS:
        for w in w1d.window_rows(HW / name):
            if w1d.RATE_CHECK.fullmatch(w["label"]):
                out[int(w["label"][1])].append(w["cycle_us"])
    return out


def windows_from(cycles_us: list[float], family: str) -> list[int]:
    """W per board from its one-sender cycle at 145 B: cycle = T_f + DIFS + σ(W − 1)/2."""
    slot, difs = uh.FAMILIES[family]
    return [round(1 + 2 * (c * 1e-6 - T_F_145 - difs) / slot) for c in cycles_us]


def chosen_cycles(choice: str) -> list[float]:
    c = day_cycles_us()
    if choice == "mean":
        return [st.mean(c[n]) for n in (1, 2, 3)]
    return [(min if choice == "min" else max)(c[n]) for n in (1, 2, 3)]


def _pair_run(job: tuple[str, str, int] | tuple[str, str, int, int]) -> dict[str, Any]:
    family, choice, seed = job[:3]
    frame = job[3] if len(job) == 4 else FRAME_B
    import run_unified as ru
    from ns3_paths import ns3_root
    slot, _ = uh.FAMILIES[family]
    w = windows_from(chosen_cycles(choice), family)[:2]
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "p"
        args = [str(exe), "--nNodes=2", f"--simTime={SIM_S}", f"--seed={seed}",
                f"--outPrefix={pre}", *ru.Cell(frame, SAT_FPS, "80211b", "DsssRate1Mbps").args(),
                f"--cwMinList={w[0] - 1},{w[1] - 1}", "--traceMac=1", "--perPair=1"]
        if slot != 20e-6:
            args.append(f"--slotUs={round(slot * 1e6)}")
        ru.run_checked(args, env)
        on_air = {0: 0, 1: 0}
        with Path(f"{pre}_mac.csv").open() as fh:
            for r in csv.DictReader(fh):
                if r["kind"] == "B":
                    on_air[int(r["node"])] += 1
        with Path(f"{pre}_pairs.csv").open() as fh:
            rx = {int(r["src"]): int(r["rx_frames"]) for r in csv.DictReader(fh)}
    return {"family": family, "choice": choice, "seed": seed,
            "loss": st.mean(1 - rx[s] / on_air[s] for s in (0, 1)),
            "air_fps": st.mean(on_air[s] / SIM_S for s in (0, 1))}


def predict_b(workers: int = 10) -> list[dict[str, Any]]:
    jobs = [(f, c, s) for f in uh.FAMILIES for c in CHOICES for s in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        runs = list(ex.map(_pair_run, jobs))
    rows = []
    for f in uh.FAMILIES:
        for c in CHOICES:
            v = [r for r in runs if r["family"] == f and r["choice"] == c]
            w = windows_from(chosen_cycles(c), f)
            rows.append({"part": "B", "family": f, "cycles": c,
                         "cycle_us": "/".join(f"{x:.1f}" for x in chosen_cycles(c)),
                         "w_pi_a": w[0], "w_pi_b": w[1], "w_pi3": w[2], "seeds": len(v),
                         "pair_loss": st.mean(r["loss"] for r in v),
                         "pair_loss_sd": st.stdev(r["loss"] for r in v),
                         "pair_air_fps": st.mean(r["air_fps"] for r in v),
                         "pair_air_fps_sd": st.stdev(r["air_fps"] for r in v),
                         "registered": c == "mean"})
    return rows


def known_145(workers: int = 10) -> list[dict[str, Any]]:
    """For the disclosure only: the registered windows at W1p's 145 B, where W1p measured the pair
    (0.1029 at 262.7 frames/s). Not a prediction; nothing in the rule uses it."""
    jobs = [(f, "mean", s, uh.W1F_FRAME) for f in uh.FAMILIES for s in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        runs = list(ex.map(_pair_run, jobs))
    return [{"family": f, "frame_size": uh.W1F_FRAME, "seeds": len(v),
             "pair_loss": st.mean(r["loss"] for r in v),
             "pair_loss_sd": st.stdev(r["loss"] for r in v),
             "pair_air_fps": st.mean(r["air_fps"] for r in v)}
            for f in uh.FAMILIES for v in [[r for r in runs if r["family"] == f]]]


def bracketed(m_loss: float, m_fps: float, a: dict[str, float], b: dict[str, float]) -> bool:
    """The measured mean loss and rate each lie between the two families' predictions."""
    return (min(a["loss"], b["loss"]) <= m_loss <= max(a["loss"], b["loss"])
            and min(a["fps"], b["fps"]) <= m_fps <= max(a["fps"], b["fps"]))


def score_b(session: Path, pred: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    files, tags, power_ok = _session_parts(session)
    loss_w, fps_w = [], []
    for tag in tags.get("P", []):
        loss, fps, fewest = w1p._pair_window(files[tag]["rx"])
        if power_ok[tag] and fewest >= MIN_ON_AIR_B:
            loss_w.append(loss)
            fps_w.append(fps)
    out: list[dict[str, Any]] = [{"what": "B: usable pair windows", "item": "345 B",
                                  "measured": len(loss_w), "predicted": f">= {PAIR_WINDOWS - 1}",
                                  "held": len(loss_w) >= PAIR_WINDOWS - 1}]
    for d in ("NA", "NB"):
        if d in tags:
            s = PI_A if d == "NA" else PI_B
            t = tags[d][0]
            lo = w1q.losses(files[t]["rx"], s, files[t]["tx"][s]["sent"])
            out.append({"what": "B: link alone at 50/s", "item": f"node {s}", "measured":
                        ", ".join(f"at {r}: {100 * v:.2f} %" for r, v in sorted(lo.items())),
                        "predicted": "", "held": "reported"})
    if len(loss_w) < PAIR_WINDOWS - 1:
        return out
    m, lo_, hi_ = w1p.interval(loss_w)
    fm, flo, fhi = w1p.interval(fps_w)
    out.append({"what": "B: pair (95 % interval)", "item": "", "measured":
                f"loss {m:.4f} ({lo_:.4f}-{hi_:.4f}); {fm:.1f} ({flo:.1f}-{fhi:.1f}) frames/s",
                "predicted": "", "held": ""})
    ok = {}
    for fam, p in pred.items():
        ok[fam] = w1p.consistent(p["loss"], p["fps"], loss_w, fps_w)
        out.append({"what": "B: family consistent", "item": fam,
                    "measured": f"{m:.4f}, {fm:.1f}/s",
                    "predicted": f"{p['loss']:.4f}, {p['fps']:.1f}/s", "held": ok[fam]})
    fams = list(pred)
    verdict = ([f for f in fams if ok[f]][0] if sum(ok.values()) == 1 else
               "both consistent: not separated" if all(ok.values()) else
               "neither: the window is not identifiable without a frame sniffer; "
               + ("the hardware lies between the two settings"
                  if bracketed(m, fm, pred[fams[0]], pred[fams[1]])
                  else "the hardware is NOT between the two settings"))
    out.append({"what": "B: the window", "item": "", "measured": verdict, "predicted": "",
                "held": "reported"})
    return out


# ============================================================================== C
def iqr(v: list[float]) -> float:
    q = st.quantiles(v, n=4)
    return q[2] - q[0]


def fixed_part_us(gaps: list[float]) -> float:
    """median − IQR: DIFS plus any fixed per-frame time, under a uniform backoff."""
    return st.median(gaps) - iqr(gaps)


def timing_verdict(d_us: float, c_us: float) -> str:
    if c_us <= 0:
        return "unresolved: no extra time to explain"
    if d_us >= 2 * c_us / 3:
        return "fixed per frame: the hypothesis is supported"
    if d_us <= c_us / 3:
        return "backoff: the hypothesis is rejected"
    return "unresolved: an unexplained property of the BCM43430"


def board_gaps(session: Path, sender: int, receiver: int) -> list[float]:
    """Gaps after each frame of `sender` alone and saturated, at `receiver`, over the R and S
    windows, pooled."""
    _, tags, power_ok = _session_parts(session)
    out: list[float] = []
    for label in (f"R{sender}", f"S{sender}"):
        for tag in tags.get(label, []):
            if power_ok[tag]:
                out += w1p.gaps_us(hs.timestamps(session, receiver, tag).get(sender, {}))
    return out


def score_c(session: Path) -> list[dict[str, Any]]:
    windows = w1d.window_rows(session)
    cyc = {n: [w["cycle_us"] for w in windows if w["label"] == f"R{n}"] for n in (1, 2, 3)}
    out = []
    for slow, ref, at in ((PI_3, PI_A, PI_B), (PI_3, PI_B, PI_A)):
        g3, gr = board_gaps(session, slow, at), board_gaps(session, ref, at)
        if len(g3) < 4 or len(gr) < 4 or not cyc[slow] or not cyc[ref]:
            out.append({"what": "C: the Pi 3's fixed time", "item": f"against node {ref}",
                        "measured": "no windows", "predicted": "", "held": "not run"})
            continue
        neg = max(sum(1 for x in g if x < 0) / len(g) for g in (g3, gr))
        d = fixed_part_us(g3) - fixed_part_us(gr)
        c = st.mean(cyc[slow]) - st.mean(cyc[ref])
        primary = ref == PI_A
        if neg >= NEGATIVE_GAP_MAX:
            verdict = "unresolved: the timestamps cannot resolve it (an unexplained property " \
                      "of the BCM43430)"
        else:
            verdict = timing_verdict(d, c)
        out.append({"what": "C: the Pi 3's fixed time" + (" (primary)" if primary else
                                                          " (reported)"),
                    "item": f"against node {ref}, at node {at}",
                    "measured": f"d {d:.1f} us; c {c:.1f} us; median/IQR Pi 3 "
                                f"{st.median(g3):.1f}/{iqr(g3):.1f}, node {ref} "
                                f"{st.median(gr):.1f}/{iqr(gr):.1f}; negative gaps "
                                f"{100 * neg:.1f} %",
                    "predicted": "d >= 2c/3 fixed; d <= c/3 backoff",
                    "held": verdict if primary else "reported"})
    return out


# ============================================================================== the session
def plan() -> list[str]:
    pay = w1d.PAYLOAD_UDP
    checks = [f"R{n} {SAT_FPS} {pay} {n} 25" for n in (1, 2, 3)]
    lines = ["# nodes: 1,2,3", "# W1s: A the capture curve on unseen steps, B the saturated pair at"
             " 345 B, C the boards alone (analysis/w1s.py)"] + checks
    for d, pa, pb in A_STEPS:
        p = f"{PI_A}:{pa}" + (f",{PI_B}:{pb}" if d == ANCHOR else "")
        lines += [f"A{d} 50 {pay} {PI_A} 25 {p}", f"B{d} 50 {pay} {PI_B} 25"]
        lines += [f"C{d} {SAT_FPS} {pay} {PI_A},{PI_B} 25"] * 3
    d, pa, pb = NEG
    lines += [f"A{d} 50 {pay} {PI_A} 25 {PI_A}:{pa},{PI_B}:{pb}", f"B{d} 50 {pay} {PI_B} 25"]
    lines += [f"C{d} {SAT_FPS} {pay} {PI_A},{PI_B} 25"] * 3
    lines += [f"NA 50 {PAYLOAD_B} {PI_A} 25 {PI_B}:{P0_MBM}", f"NB 50 {PAYLOAD_B} {PI_B} 25"]
    lines += [f"P {SAT_FPS} {PAYLOAD_B} {PI_A},{PI_B} 25"] * PAIR_WINDOWS
    lines += [f"S{n} {SAT_FPS} {pay} {n} 25" for n in (1, 2, 3)]
    return lines + checks


def _predictions() -> tuple[list[tuple[float, float, float]], dict[str, dict[str, float]]]:
    with OUT.open() as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    curve = [(float(r["delta_db"]), float(r["q_a"]), float(r["q_b"])) for r in rows
             if r["part"] == "A" and r["enters"] == "True"]
    pred = {r["family"]: {"loss": float(r["pair_loss"]), "fps": float(r["pair_air_fps"])}
            for r in rows if r["part"] == "B" and r["registered"] == "True"}
    return curve, pred


def score(session: Path) -> list[dict[str, Any]]:
    missing = [n for n in (1, 2, 3) if not (session / f"node{n}" / "session.log").is_file()]
    out: list[dict[str, Any]] = [{"what": "boards with files", "item": "", "measured":
                                  f"{3 - len(missing)} of 3", "predicted": "3",
                                  "held": not missing}]
    if missing:
        return out
    stops = {n: re.findall(r"chip down before window (\d+)",
                           (session / f"node{n}" / "session.log").read_text()) for n in (1, 2, 3)}
    out.append({"what": "chip stops", "item": "", "measured": {n: s for n, s in stops.items() if s}
                or "none", "predicted": "none", "held": not any(stops.values())})
    out.append({"what": "frame burst off on every board", "item": "", "measured": "",
                "predicted": "0 before and after", "held": hs.frameburst_off(session)})
    for w in w1d.window_rows(session):
        if w1d.RATE_CHECK.fullmatch(w["label"]):
            c = w["cycle_us"] * 1e-6
            out.append({"what": "rate check", "item": w["window"], "measured": w["cycle_us"],
                        "predicted": "1900-2600 us",
                        "held": w1d.RATE_BAND_S[0] <= c <= w1d.RATE_BAND_S[1]})
    curve, pred = _predictions()
    return out + score_a(session, curve) + score_b(session, pred) + score_c(session)


def _write(rows: list[dict[str, Any]], path: Path, run: str) -> str:
    from authbc.bench import provenance
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run}.items():
        buf.write(f"# {k}={v}\n")
    wr = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                        lineterminator="\n", restval="")
    wr.writeheader()
    wr.writerows(rows)
    path.write_text(buf.getvalue())
    return buf.getvalue()


def main() -> None:
    if "--score" in sys.argv:
        session = Path(sys.argv[sys.argv.index("--score") + 1])
        print(_write(score(session), REPO / "results" / "raw" / f"w1s_{session.name}.csv",
                     f"w1s_{session.name}"))
        return
    if "--known145" in sys.argv:
        print(_write(known_145(), REPO / "results" / "raw" / "w1s_known145.csv",
                     "w1s_known145"))
        return
    if "--predict" in sys.argv:
        rows: list[dict[str, Any]] = []
        for m in curve_points():
            rows.append({"part": "A", "step": m["step"], "delta_db": m["delta_db"],
                         "q_a": round(m["q_a"], 6), "q_b": round(m["q_b"], 6),
                         "worst_link": round(m["worst_link"], 6), "enters": m["enters"]})
        rows += predict_b()
        print(_write(rows, OUT, "w1s_predictions"))
        lines = plan()
        PLAN.write_text("\n".join(lines) + "\n")
        print(f"plan: {len(lines) - 2} windows")


if __name__ == "__main__":
    main()
