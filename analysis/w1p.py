#!/usr/bin/env python3
"""W1p — session 3 of the 2026-11-20 session plans: the contention window against slot and DIFS
(predictions/W1p.md; plans approved by Mohamed 2026-11-21, docs/DECISIONS.md).

The one-sender cycle at 2.4 GHz fits two settings (U-H, `analysis/uh.py`): σ 20 µs, DIFS 50 µs
with W = 4, 4 for the Pi 4s, and σ 9 µs, DIFS 28 µs with W = 12, 13. This session separates them.

* **Step 0, first: the receive-timestamp jitter of each board.** One board sends at 50 frames/s
  while the other two timestamp the same frames (`bcast_rx.py --timestamps`). Per receiver pair, a
  least-squares line t_k = a + b·t_i removes the two clocks' offset and drift; the residual
  variance is J_i² + J_k² if the boards' jitters are independent. Three senders give the three
  pair variances, so each board's J.
* **Primary: the saturated pair** (pi-A with pi-B, 600 frames/s offered, frame burst off). Each is
  the other's only sender, and a station that is transmitting cannot receive, so capture cannot
  rescue a collided frame at the partner. Measured as `contention_hw.saturated` does: a
  receiver's span of sequence numbers is what the sender put on air.
  * loss at the partner, and frames per second on air, per window;
  * a family is **consistent** if ns-3's value for it lies inside the measured 95 % interval over
    windows (t with n − 1 degrees of freedom) for both the loss and the rate.
* **Supporting: each board alone, saturated.** The gap after each frame (receive-time difference of
  consecutive sequence numbers, less T_f) has mean DIFS + σ(W − 1)/2 and standard deviation
  σ·√((W² − 1)/12) on the lattice DIFS + kσ. The two families share the mean by construction;
  the Pi 4s' standard deviations differ (22.4 µs against 31.1 and 33.7 µs), so the jitter must be
  known first.

    python analysis/w1p.py --predict   -> results/raw/w1p_predictions.csv (ns-3, 30 seeds)
    python analysis/w1p.py --plan      -> experiments/channel24/plan_w1p.txt
    python analysis/w1p.py --score results/hw/channel24/<session>  -> results/raw/w1p_<session>.csv
"""
from __future__ import annotations

import csv
import io
import math
import os
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

import uh  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

FRAME = uh.W1F_FRAME                  # ns-3 frameSize 173: the 145 B UDP frame, 1 864 µs on air
T_F_S = uc.airtime_s(phy.DSSS_1M, FRAME)
SAT_FPS = 600.0                       # offered per board; the medium carries about 450 alone
JITTER_FPS = 50.0
JITTER_S = 60                         # 3 000 frames per pair: see board_jitter_sq_se_us2
SIM_S = 20.0
SEEDS = range(1, 31)
PAIR = (0, 1)                         # pi-A and pi-B in uh.board_windows' order
OUT = REPO / "results" / "raw" / "w1p_predictions.csv"
T975 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306,
        10: 2.262, 12: 2.201, 15: 2.145, 20: 2.093}


def gap_moments_us(family: str, w: int) -> tuple[float, float]:
    """Mean and standard deviation of the gap after a frame, in µs, for a saturated sender alone:
    DIFS + kσ with k uniform on 0 … W − 1."""
    slot, difs = uh.FAMILIES[family]
    return 1e6 * (difs + slot * (w - 1) / 2), 1e6 * slot * math.sqrt((w * w - 1) / 12)


def _pair_run(job: tuple[str, int]) -> dict[str, Any]:
    family, seed = job
    import run_unified as ru
    from ns3_paths import ns3_root
    slot, _difs = uh.FAMILIES[family]
    w = [uh.board_windows(family)[i] for i in PAIR]
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "p"
        args = [str(exe), "--nNodes=2", f"--simTime={SIM_S}", f"--seed={seed}",
                f"--outPrefix={pre}", *ru.Cell(FRAME, SAT_FPS, "80211b", "DsssRate1Mbps").args(),
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
    loss = [1 - rx[s] / on_air[s] for s in (0, 1)]
    return {"family": family, "seed": seed, "loss": st.mean(loss),
            "air_fps": st.mean(on_air[s] / SIM_S for s in (0, 1))}


def predict(workers: int = 10) -> list[dict[str, Any]]:
    jobs = [(f, s) for f in uh.FAMILIES for s in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        runs = list(ex.map(_pair_run, jobs))
    rows = []
    for f in uh.FAMILIES:
        v = [r for r in runs if r["family"] == f]
        w = uh.board_windows(f)
        rows.append({
            "family": f, "w_pi_a": w[0], "w_pi_b": w[1], "w_pi3": w[2], "seeds": len(v),
            "pair_loss": st.mean(r["loss"] for r in v),
            "pair_loss_sd": st.stdev(r["loss"] for r in v),
            "pair_air_fps": st.mean(r["air_fps"] for r in v),
            "pair_air_fps_sd": st.stdev(r["air_fps"] for r in v),
            **{f"gap_mean_us_{b}": gap_moments_us(f, w[i])[0] for i, b in enumerate(BOARDS)},
            **{f"gap_sd_us_{b}": gap_moments_us(f, w[i])[1] for i, b in enumerate(BOARDS)}})
    return rows


BOARDS = ("pi_a", "pi_b", "pi3")


# ---- scoring (fixed before the session) ----------------------------------------------------

def _line_residuals(x: list[float], y: list[float]) -> list[float]:
    mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y, strict=True)) / sxx
    return [c - my - b * (a - mx) for a, c in zip(x, y, strict=True)]


def pair_variance_ns2(ts_i: dict[int, int], ts_k: dict[int, int]) -> dict[str, float]:
    """Two receivers' timestamps of the same frames ({seq: t_ns}): the residual variance of one
    clock against the other after a straight line, and its robust form (1.4826·MAD)²."""
    common = sorted(set(ts_i) & set(ts_k))
    if len(common) < 50:
        raise ValueError(f"only {len(common)} frames heard by both receivers")
    t0 = ts_i[common[0]]
    x = [float(ts_i[s] - t0) for s in common]
    y = [float(ts_k[s] - t0) for s in common]
    r = _line_residuals(x, y)
    med = st.median(r)
    mad = st.median(abs(v - med) for v in r)
    return {"frames": len(common), "var_ns2": sum(v * v for v in r) / (len(r) - 2),
            "robust_var_ns2": (1.4826 * mad) ** 2}


def board_jitter_us(v_ab: float, v_ac: float, v_bc: float) -> dict[str, float]:
    """Each board's jitter from the three pair variances (ns²), V_ik = J_i² + J_k². A negative
    square is reported as such (noise), never set to zero."""
    def j(sq: float) -> float:
        return math.copysign(math.sqrt(abs(sq)), sq) / 1e3
    return {"a": j((v_ab + v_ac - v_bc) / 2), "b": j((v_ab + v_bc - v_ac) / 2),
            "c": j((v_ac + v_bc - v_ab) / 2)}


def board_jitter_sq_se_us2(v_ab: float, v_ac: float, v_bc: float, frames: int) -> float:
    """The standard error of each J², in µs², for Gaussian residuals: Var(V̂) = 2V²/(n − 2) per
    pair, and J_i² = (±V ± V ± V)/2. A board's J² is a difference of the pair variances, so the
    smallest jitter is resolved only when this error is below its square (stated with W1p)."""
    return 0.5 * math.sqrt(sum(2 * v * v / (frames - 2) for v in (v_ab, v_ac, v_bc))) / 1e6


def interval(values: list[float]) -> tuple[float, float, float]:
    """Mean and its 95 % interval over windows (Student t, n − 1 degrees of freedom)."""
    n = len(values)
    m = st.mean(values)
    h = T975[n] * st.stdev(values) / math.sqrt(n)
    return m, m - h, m + h


def consistent(predicted_loss: float, predicted_fps: float, loss_windows: list[float],
               fps_windows: list[float]) -> bool:
    """The registered rule: inside the measured 95 % interval for both the loss and the rate."""
    _, lo, hi = interval(loss_windows)
    _, flo, fhi = interval(fps_windows)
    return lo <= predicted_loss <= hi and flo <= predicted_fps <= fhi


def gaps_us(ts: dict[int, int]) -> list[float]:
    """The gap after each frame in µs: receive-time differences of consecutive sequence numbers,
    less the frame's own time on air."""
    seqs = sorted(ts)
    return [(ts[b] - ts[a]) / 1e3 - 1e6 * T_F_S for a, b in zip(seqs, seqs[1:], strict=False)
            if b == a + 1]


def gap_summary(gaps: list[float], jitter_us: float) -> dict[str, float]:
    """Mean, raw and jitter-corrected standard deviation (two timestamps per gap: 2J²)."""
    sd = st.stdev(gaps)
    corr = sd * sd - 2 * jitter_us * jitter_us
    return {"gaps": len(gaps), "mean_us": st.mean(gaps), "sd_us": sd,
            "sd_corrected_us": math.copysign(math.sqrt(abs(corr)), corr),
            "p05_us": sorted(gaps)[len(gaps) // 20]}


PAIR_WINDOWS = 6
PLAN = REPO / "experiments" / "channel24" / "plan_w1p.txt"
PAYLOAD_UDP = 145
RATE_FPS = 600
NODES = (1, 2, 3)                     # pi-A, pi-B, the Pi 3


def plan() -> list[str]:
    """Step 0 first (each board alone at 50 frames/s, 60 s: the jitter, the kit check and the
    link backgrounds); the rate checks (each board alone, saturated: the gap distributions);
    the saturated pair six times; the rate checks again (the bracket, as W1e)."""
    jit = [f"J{n} {JITTER_FPS:g} {PAYLOAD_UDP} {n} {JITTER_S}" for n in NODES]
    checks = [f"R{n} {RATE_FPS} {PAYLOAD_UDP} {n} 25" for n in NODES]
    pair = [f"P {RATE_FPS} {PAYLOAD_UDP} 1,2 25"] * PAIR_WINDOWS
    return (["# nodes: 1,2,3", "# W1p: jitter first, rate checks, the saturated pair, rate checks"
             " (analysis/w1p.py)"] + jit + checks + pair + checks)


PER_MAC_SPREAD_DB = 2.0
PER_MAC_SEPARATION_DB = 4.0


def per_mac_accepted(readings: dict[int, list[dict[str, Any]]]) -> str:
    """The kit check at one receiver, from the step-0 windows (one peer alone in each).

    `readings[j]`: the readings taken while peer j sent alone, each {"any": dBm, "peers": {k: dBm}}.
    Accepted only if, for every peer, its per-peer readings in all windows lie within ±2 dB of
    their median and, in its own window, within 2 dB of the zero-address reading; and at least
    two peers differ by 4 dB or more, so that a reading tied to the address can be told from one
    that follows the last frame. Otherwise "not shown" (the fallback applies) or "rejected".
    """
    peers = sorted(readings)
    own: dict[int, float] = {}
    for j in peers:
        every = [r["peers"][j] for w in peers for r in readings[w]]
        mid = st.median(every)
        if any(abs(v - mid) > PER_MAC_SPREAD_DB for v in every):
            return "rejected"
        if any(abs(r["peers"][j] - r["any"]) > PER_MAC_SPREAD_DB for r in readings[j]):
            return "rejected"
        own[j] = st.median(r["any"] for r in readings[j])
    spread = max(own.values()) - min(own.values())
    return "accepted" if spread >= PER_MAC_SEPARATION_DB else "not shown"


MIN_ON_AIR = 5000
MIN_PAIR_WINDOWS = 5


def _predictions() -> dict[str, dict[str, str]]:
    with OUT.open() as fh:
        return {r["family"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


def _pair_window(rx: dict[int, dict[str, Any]]) -> tuple[float, float, int]:
    """One P window: (mean loss at the partner, mean frames/s on air, fewest frames on air)."""
    losses, fps, ons = [], [], []
    for s, r in ((1, 2), (2, 1)):
        g = rx[r]["by_source"][f"10.0.0.{s}"]
        on = g["max_seq"] - g["min_seq"] + 1
        losses.append(1 - g["received_unique"] / on)
        fps.append((on - 1) / g["span_s"])
        ons.append(on)
    return st.mean(losses), st.mean(fps), min(ons)


def score(session: Path) -> list[dict[str, Any]]:
    """W1p as registered: validity, step 0's jitter, the kit check, the pair rule, the gaps."""
    import dsss_three as w1d
    import hw_session as hs
    out: list[dict[str, Any]] = []
    windows = w1d.window_rows(session)
    files = w1d._files(session)
    tags = {w["window"]: w for w in windows}
    by_label: dict[str, list[str]] = {}
    for tag in sorted(tags, key=lambda x: int(x.split("_")[0])):
        by_label.setdefault(tags[tag]["label"], []).append(tag)
    # validity
    out.append({"what": "frame burst off on every board", "item": "", "measured": "",
                "predicted": "0 before and after", "held": hs.frameburst_off(session)})
    for label in ("R1", "R2", "R3"):
        for tag in by_label.get(label, []):
            c = tags[tag]["cycle_us"] * 1e-6
            out.append({"what": "rate check", "item": tag, "measured": round(1e6 * c, 1),
                        "predicted": "1900-2600 us",
                        "held": w1d.RATE_BAND_S[0] <= c <= w1d.RATE_BAND_S[1]})
    # step 0: the jitter, pair by pair (sender j's window gives the other two receivers' pair)
    v: dict[str, float] = {}
    vr: dict[str, float] = {}
    frames = []
    for j, pair in ((3, "ab"), (2, "ac"), (1, "bc")):
        tag = by_label[f"J{j}"][0]
        i, k = [n for n in NODES if n != j]
        got = pair_variance_ns2(hs.timestamps(session, i, tag)[j],
                                hs.timestamps(session, k, tag)[j])
        v[pair], vr[pair] = got["var_ns2"], got["robust_var_ns2"]
        frames.append(got["frames"])
    jit = board_jitter_us(v["ab"], v["ac"], v["bc"])
    jit_r = board_jitter_us(vr["ab"], vr["ac"], vr["bc"])
    se = board_jitter_sq_se_us2(v["ab"], v["ac"], v["bc"], min(frames))
    for n, b in zip(NODES, "abc", strict=True):
        out.append({"what": "timestamp jitter (us)", "item": f"node {n}",
                    "measured": round(jit[b], 2), "predicted": f"robust {jit_r[b]:.2f}; "
                    f"SE of J^2 {se:.2f} us^2", "held": "reported"})
    # the kit check at each receiver, on step 0's windows
    for r in NODES:
        readings: dict[int, list[dict[str, Any]]] = {}
        for j in NODES:
            if j == r:
                continue
            tag = by_label[f"J{j}"][0]
            readings[j] = [x for x in hs.rssi(session, r) if x["tag"] == tag]
        ok = all(x["any"] is not None and all(p is not None for p in x["peers"].values())
                 for rs in readings.values() for x in rs)
        verdict = per_mac_accepted(readings) if ok else "rejected (a read failed)"
        out.append({"what": "kit check: per-peer RSSI", "item": f"at node {r}", "measured": verdict,
                    "predicted": "accepted, or the fallback", "held": "reported"})
    # primary: the saturated pair
    loss_w, fps_w = [], []
    for tag in by_label.get("P", []):
        loss, fps, fewest = _pair_window(files[tag]["rx"])
        if tags[tag]["power_ok"] and fewest >= MIN_ON_AIR:
            loss_w.append(loss)
            fps_w.append(fps)
    out.append({"what": "usable pair windows", "item": "", "measured": len(loss_w),
                "predicted": f">= {MIN_PAIR_WINDOWS}", "held": len(loss_w) >= MIN_PAIR_WINDOWS})
    if len(loss_w) >= MIN_PAIR_WINDOWS:
        m, lo, hi = interval(loss_w)
        fm, flo, fhi = interval(fps_w)
        out.append({"what": "pair loss (95 % interval)", "item": "",
                    "measured": f"{m:.4f} ({lo:.4f}-{hi:.4f})", "predicted": "", "held": ""})
        out.append({"what": "pair frames/s on air (95 % interval)", "item": "",
                    "measured": f"{fm:.1f} ({flo:.1f}-{fhi:.1f})", "predicted": "", "held": ""})
        pred = _predictions()
        verdicts = {}
        for fam, p in pred.items():
            verdicts[fam] = consistent(float(p["pair_loss"]), float(p["pair_air_fps"]), loss_w,
                                       fps_w)
            out.append({"what": "family consistent", "item": fam,
                        "measured": f"{m:.4f}, {fm:.1f}/s",
                        "predicted": f"{float(p['pair_loss']):.4f}, "
                                     f"{float(p['pair_air_fps']):.1f}/s",
                        "held": verdicts[fam]})
        chosen = [f for f, ok in verdicts.items() if ok]
        out.append({"what": "family for W1r", "item": "", "measured":
                    chosen[0] if len(chosen) == 1 else "none (both reported)", "predicted": "",
                    "held": "reported"})
    # supporting: the gaps of each board alone, saturated, at each other receiver
    pred = _predictions()
    for j, b in zip(NODES, BOARDS, strict=True):
        tag = by_label[f"R{j}"][0]
        for r in NODES:
            if r == j:
                continue
            s = gap_summary(gaps_us(hs.timestamps(session, r, tag)[j]),
                            abs(jit["abc"[NODES.index(r)]]))
            out.append({"what": "gap after a frame (us)", "item": f"node {j} at node {r}",
                        "measured": f"mean {s['mean_us']:.1f}, sd {s['sd_us']:.1f}, corrected "
                                    f"{s['sd_corrected_us']:.1f}, p05 {s['p05_us']:.1f}",
                        "predicted": "; ".join(
                            f"{f}: {float(p[f'gap_mean_us_{b}']):.1f}, "
                            f"{float(p[f'gap_sd_us_{b}']):.1f}" for f, p in pred.items()),
                        "held": "reported"})
    return out


def main() -> None:
    if "--score" in sys.argv:
        session = Path(sys.argv[sys.argv.index("--score") + 1])
        rows = score(session)
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": f"w1p_{session.name}"}.items():
            buf.write(f"# {k}={v}\n")
        wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
        (REPO / "results" / "raw" / f"w1p_{session.name}.csv").write_text(buf.getvalue())
        print(buf.getvalue())
        return
    if "--plan" in sys.argv:
        lines = plan()
        PLAN.write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
        return
    if "--predict" in sys.argv:
        rows = predict()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "w1p_predictions",
                     "ns3": "3.48 (authbc-links-audit)", "seeds": "1-30", "sim_s": SIM_S,
                     "offered_fps": SAT_FPS, "frame_size": FRAME}.items():
            buf.write(f"# {k}={v}\n")
        wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
        OUT.write_text(buf.getvalue())
        print(buf.getvalue())


if __name__ == "__main__":
    main()
