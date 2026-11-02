#!/usr/bin/env python3
"""G27: which rule for a radio's own queued frames fits all three measurements of 2026-10-09.

predictions/G27.md. Each candidate rule (src/authbc/sim/dcf_own_queue.py) has one parameter per
frame-burst state, set from one measurement only: the gap a saturated sender leaves after its
frame (F74, F75; results/hw/channel/frame_spacing.csv). The rule is then screened against two
saturated senders (F76) and scored against the 36 windows below saturation (F73).

    python analysis/own_queue_rules.py --calibrate
        the parameters, and stage A: one simulated sender gives the gap of the closed form
        -> results/raw/g27_calibration.csv
    python analysis/own_queue_rules.py --defect
        F114: how much of the frozen model's loss is a station colliding with itself
        -> results/raw/g27_frozen_defect.csv
    python analysis/own_queue_rules.py --screen [--only R0]
        stage B, two saturated senders -> results/raw/g27_screen.csv
    python analysis/own_queue_rules.py --score [--only R0]
        stage C, the 36 windows -> results/raw/g27_windows.csv

Every band is computed here from the files on disk, by the rule the registration states.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from collections.abc import Iterator
from multiprocessing import Pool
from pathlib import Path

from scipy import stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "ns3"))

import contention_hw as hw  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_own_queue as oq  # noqa: E402
from authbc.sim import dcf_unsaturated as frozen  # noqa: E402

RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw" / "channel"
SPACING = HW / "frame_spacing.csv"
WINDOWS = {"on": ("contention_2nodes_windows.csv", "contention_2nodes_fb_on_repeat_windows.csv"),
           "off": ("contention_2nodes_fb_off_windows.csv",)}
SATURATED = {"on": "saturated_2nodes_fb_on.csv", "off": "saturated_2nodes_fb_off.csv"}

SEEDS = 30
SIM_S = 20.0
WARMUP_S = 1.0
STAGE_A_SEEDS = 10
ONE_SENDER_FPS = 900                # what the one-sender sessions offered beyond saturation
SATURATED_FPS = 400                 # what each board was offered in F76
LOADS = (124, 174, 211)             # F73, frames/s per board
STAGE_A_TOLERANCE_S = 1e-6
STANDARD_GAP_S = frozen.DIFS_S + (frozen.W0 - 1) / 2 * frozen.SLOT_S
CALIBRATIONS = ("mean", "lowest", "highest", "reading_B")   # the first decides; the rest inform


# ------------------------------------------------------------------------------------ the data
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def state_of(frame_burst: str) -> str:
    return "on" if frame_burst.startswith("on") else "off"


def measured_gaps_s() -> dict[str, dict[str, float]]:
    """The gap after a frame, per frame-burst state, read four ways.

    `mean`: every window on disk, as F74 reads it (frames on air are the sequence numbers the
    receiver spans). `lowest`, `highest`: the single windows. `reading_B`: the frames the receiver
    did not get never went on air, so the frames on air are the frames received.
    """
    ppdu = hw.airtime_s()
    out: dict[str, dict[str, float]] = {}
    for state in ("on", "off"):
        rows = [r for r in _rows(SPACING) if state_of(r["frame_burst"]) == state]
        gaps = [float(r["gap_after_frame_us"]) * 1e-6 for r in rows]
        b = [float(r["receiver_span_s"]) / (int(r["received"]) - 1) - ppdu for r in rows]
        out[state] = {"mean": st.mean(gaps), "lowest": min(gaps), "highest": max(gaps),
                      "reading_B": st.mean(b)}
    return out


def one_sender_loss_max() -> float:
    """The most a single saturated sender loses with nobody to collide with (frames spanned)."""
    return max(1.0 - int(r["received"]) / (int(r["frames_spanned"]) + 1)
               for r in _rows(SPACING))


def _interval(values: list[float]) -> tuple[float, float]:
    """Mean and the half-width of its 95 % t-interval."""
    n = len(values)
    return st.mean(values), float(stats.t.ppf(0.975, n - 1)) * st.stdev(values) / n ** 0.5


def saturated_bands() -> dict[str, dict[str, float]]:
    """Stage B's bands, from F76's files.

    The model has no loss but collisions, and a single saturated sender loses up to
    `one_sender_loss_max()` with nobody to collide with: the loss band reaches that far below the
    measured interval, and the rate band as far below in proportion (a frame never on air would
    still be counted on air).
    """
    allowance = one_sender_loss_max()
    out = {}
    for state, name in SATURATED.items():
        rows = _rows(HW / name)
        loss, half = _interval([float(r["loss"]) for r in rows])
        totals: dict[str, float] = {}
        for r in rows:
            totals[r["window"]] = totals.get(r["window"], 0.0) + float(r["air_fps"])
        rate, rhalf = _interval(list(totals.values()))
        out[state] = {"loss": loss, "loss_lo": loss - half - allowance, "loss_hi": loss + half,
                      "rate": rate, "rate_lo": (1 - allowance) * rate - rhalf,
                      "rate_hi": rate + rhalf, "windows": len(totals)}
    return out


def window_losses() -> dict[str, dict[int, list[float]]]:
    """F73's windows: loss per window, per state and rate; 'pooled' is all 36."""
    out: dict[str, dict[int, list[float]]] = {"on": {}, "off": {}, "pooled": {}}
    for state, names in WINDOWS.items():
        for name in names:
            for r in _rows(HW / name):
                rate, loss = int(r["rate_fps_per_node"]), 1.0 - float(r["delivered_frac"])
                out[state].setdefault(rate, []).append(loss)
                out["pooled"].setdefault(rate, []).append(loss)
    return out


def window_bands() -> dict[str, dict[int, tuple[float, float, float, int]]]:
    """Stage C's bands: mean, low, high and number of windows, per state and rate."""
    out: dict[str, dict[int, tuple[float, float, float, int]]] = {}
    for state, by_rate in window_losses().items():
        out[state] = {}
        for rate, v in sorted(by_rate.items()):
            m, half = _interval(v)
            out[state][rate] = (m, m - half, m + half, len(v))
    return out


# ------------------------------------------------------------------------------------ the rules
def closed_gap_s(rule: oq.OwnQueueRule) -> float:
    """The mean gap after a frame of one saturated sender, by the rule's own arithmetic."""
    contend = frozen.DIFS_S + (1 - rule.q_zero) * (rule.w_post - 1) / 2 * rule.slot_s
    return rule.q_burst * oq.SIFS_S + (1 - rule.q_burst) * contend


def candidates(gap_s: float) -> list[oq.OwnQueueRule]:
    """R1-R5, each with its one parameter set from `gap_s` (predictions/G27.md)."""
    backoff_s = gap_s - frozen.DIFS_S
    w = max(1, round(1 + 2 * backoff_s / frozen.SLOT_S))
    q_zero = min(1.0, max(0.0, 1 - backoff_s / (STANDARD_GAP_S - frozen.DIFS_S)))
    q_burst = min(0.99, max(0.0, (STANDARD_GAP_S - gap_s) / (STANDARD_GAP_S - oq.SIFS_S)))
    sigma = max(1e-9, backoff_s / ((frozen.W0 - 1) / 2))
    return [oq.OwnQueueRule("R1", w_post=w, w_defer=w),
            oq.OwnQueueRule("R2", q_zero=round(q_zero, 3)),
            oq.OwnQueueRule("R3", q_burst=round(q_burst, 3)),
            oq.OwnQueueRule("R4", w_post=w, w_defer=frozen.W0, redraw_on_defer=True),
            oq.OwnQueueRule("R5", slot_s=round(sigma, 9))]


def parameter(rule: oq.OwnQueueRule) -> str:
    return {"R0": "—", "R1": f"W={rule.w_post}", "R2": f"q={rule.q_zero}",
            "R3": f"q={rule.q_burst}", "R4": f"W={rule.w_post}",
            "R5": f"slot={1e6 * rule.slot_s:.2f}us"}[rule.name]


def parameter_sets(only: str | None = None) -> Iterator[tuple[str, str, oq.OwnQueueRule]]:
    """(state, calibration, rule) for every set that is run; R0 once per state."""
    gaps = measured_gaps_s()
    for state in ("on", "off"):
        if only in (None, "R0"):
            yield state, "—", oq.STANDARD
        for calibration in CALIBRATIONS:
            for rule in candidates(gaps[state][calibration]):
                if only in (None, rule.name):
                    yield state, calibration, rule


# ------------------------------------------------------------------------------------ the runs
def _saturated_job(job: tuple[oq.OwnQueueRule, int]) -> tuple[float, float]:
    rule, seed = job
    r = oq.run(2, SATURATED_FPS, hw.airtime_s(), rule=rule, seed=seed, sim_time_s=SIM_S,
               warmup_s=WARMUP_S, count_until_s=SIM_S)
    return r.loss, r.frames / (SIM_S - WARMUP_S)


def _window_job(job: tuple[oq.OwnQueueRule, int, int]) -> float:
    rule, fps, seed = job
    return oq.run(2, fps, hw.airtime_s(), rule=rule, seed=seed).delivered_frac


def calibrate() -> list[dict]:
    gaps = measured_gaps_s()
    rows = []
    for state in ("on", "off"):
        for calibration in CALIBRATIONS:
            for rule in [oq.STANDARD, *candidates(gaps[state][calibration])]:
                sim = oq.mean_gap_after_frame_s(rule, hw.airtime_s(), seeds=STAGE_A_SEEDS,
                                                sim_time_s=SIM_S, offered_fps=ONE_SENDER_FPS)
                closed = closed_gap_s(rule)
                rows.append({"state": state, "calibration": calibration, "rule": rule.name,
                             "parameter": parameter(rule),
                             "measured_gap_us": round(1e6 * gaps[state][calibration], 2),
                             "closed_form_gap_us": round(1e6 * closed, 2),
                             "simulated_gap_us": round(1e6 * sim, 2),
                             "stage_A_pass": abs(sim - closed) < STAGE_A_TOLERANCE_S})
    return rows


def screen(only: str | None, workers: int) -> list[dict]:
    bands = saturated_bands()
    sets = list(parameter_sets(only))
    jobs = [(rule, seed) for _s, _c, rule in sets for seed in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_saturated_job, jobs, chunksize=4)
    rows = []
    for k, (state, calibration, rule) in enumerate(sets):
        mine = got[k * SEEDS:(k + 1) * SEEDS]
        loss = [x for x, _ in mine]
        rate = [y for _, y in mine]
        b = bands[state]
        loss_ok = b["loss_lo"] <= st.mean(loss) <= b["loss_hi"]
        rate_ok = b["rate_lo"] <= st.mean(rate) <= b["rate_hi"]
        rows.append({"state": state, "calibration": calibration, "rule": rule.name,
                     "parameter": parameter(rule),
                     "model_loss": round(st.mean(loss), 5),
                     "model_loss_sd": round(st.stdev(loss), 5),
                     "band_loss_lo": round(b["loss_lo"], 5), "band_loss_hi": round(b["loss_hi"], 5),
                     "measured_loss": round(b["loss"], 5),
                     "model_rate_fps": round(st.mean(rate), 2),
                     "model_rate_sd": round(st.stdev(rate), 2),
                     "band_rate_lo": round(b["rate_lo"], 2), "band_rate_hi": round(b["rate_hi"], 2),
                     "measured_rate_fps": round(b["rate"], 2),
                     "loss_pass": loss_ok, "rate_pass": rate_ok,
                     "stage_B_pass": loss_ok and rate_ok})
    return rows


def score(only: str | None, workers: int) -> list[dict]:
    bands = window_bands()
    sets = list(parameter_sets(only))
    jobs = [(rule, fps, seed) for _s, _c, rule in sets for fps in LOADS
            for seed in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_window_job, jobs, chunksize=10)
    rows = []
    k = 0
    for state, calibration, rule in sets:
        for fps in LOADS:
            delivered = got[k:k + SEEDS]
            k += SEEDS
            loss = 1.0 - st.mean(delivered) + hw.LINK_LOSS
            m, lo, hi, n = bands[state][fps]
            rows.append({"state": state, "calibration": calibration, "rule": rule.name,
                         "parameter": parameter(rule), "rate_fps_per_node": fps,
                         "model_loss": round(loss, 5),
                         "model_loss_sd_between_seeds": round(st.pstdev(delivered), 5),
                         "measured_loss": round(m, 5), "band_lo": round(lo, 5),
                         "band_hi": round(hi, 5), "windows": n,
                         "inside": lo <= loss <= hi, "over_measured": round(loss / m, 3)})
    return rows + pooled(rows, bands["pooled"])


def pooled(rows: list[dict], band: dict[int, tuple[float, float, float, int]]) -> list[dict]:
    """All 36 windows, as F73 reads them: the model weighted by each state's windows (8 on, 4 off).

    Reported beside the per-state scores; a verdict is per state.
    """
    out = []
    by = {(r["state"], r["calibration"], r["rule"], r["rate_fps_per_node"]): r for r in rows}
    for (state, calibration, rule, fps), on in by.items():
        off = by.get(("off", calibration, rule, fps))
        if state != "on" or off is None:
            continue
        m, lo, hi, n = band[fps]
        loss = (on["windows"] * on["model_loss"] + off["windows"] * off["model_loss"]) / n
        out.append({**on, "state": "pooled",
                    "parameter": f"on {on['parameter']}; off {off['parameter']}",
                    "model_loss": round(loss, 5), "model_loss_sd_between_seeds": "",
                    "measured_loss": round(m, 5), "band_lo": round(lo, 5),
                    "band_hi": round(hi, 5), "windows": n, "inside": lo <= loss <= hi,
                    "over_measured": round(loss / m, 3)})
    return out


# ------------------------------------------------------------------------ F114, the defect
def _defect_points() -> list[tuple[str, int, float, float]]:
    import run_nmax_direct as drv

    air = hw.airtime_s()
    points = [(f"F73 2 boards {fps}/s", 2, float(fps), air) for fps in LOADS]
    points.append(("F76 2 boards saturated 400/s", 2, float(SATURATED_FPS), air))
    points += [(f"registered grid {n} boards {fps}/s", n, float(fps), air)
               for n, _u, fps in hw.grid() if n > 2]
    for cell, n in (("C", 35), ("C", 28), ("D", 124), ("D", 97)):
        c = drv.CELLS[cell]
        points.append((f"cell {cell} at N={n}", n, c.fps,
                       bianchi.t_broadcast(c.frame_bytes) - frozen.DIFS_S))
    return points


def _defect_job(job: tuple[int, float, float, int]) -> tuple[int, int, int, int, int]:
    n, fps, air, seed = job
    groups: list[list[int]] = []
    r = frozen.run(n, fps, air, seed=seed, on_send=groups.append)
    extra_frames = extra_lost = selfish = 0
    for g in groups:
        repeats = len(g) - len(set(g))
        if repeats:
            selfish += 1
            extra_frames += repeats
            # every repeat is a frame that was never sent and was counted lost; a group of one
            # station alone was no collision, so its genuine frame was counted lost as well
            extra_lost += repeats + (1 if len(set(g)) == 1 else 0)
    return r.frames, r.lost, selfish, extra_frames, extra_lost


def defect(workers: int) -> list[dict]:
    points = _defect_points()
    jobs = [(n, fps, air, seed) for _l, n, fps, air in points for seed in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_defect_job, jobs, chunksize=4)
    rows = []
    for k, (label, n, fps, _air) in enumerate(points):
        mine = got[k * SEEDS:(k + 1) * SEEDS]
        frames, lost, selfish, xf, xl = (sum(x[j] for x in mine) for j in range(5))
        loss = lost / frames
        corrected = (lost - xl) / (frames - xf)
        rows.append({"point": label, "nodes": n, "frames_per_s": fps, "frames": frames,
                     "lost": lost, "self_collision_groups": selfish,
                     "frames_lost_to_the_defect": xl,
                     "share_of_lost": round(xl / lost, 4) if lost else 0.0,
                     "loss": round(loss, 6), "loss_without_the_defect": round(corrected, 6),
                     "relative_change": round(corrected / loss - 1, 4) if loss else 0.0})
    return rows


# ------------------------------------------------------------------------------------ output
def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "sim_s": SIM_S, "warmup_s": WARMUP_S, "loads": LOADS,
              "saturated_fps": SATURATED_FPS, "one_sender_fps": ONE_SENDER_FPS,
              "stage_a_seeds": STAGE_A_SEEDS, "calibrations": CALIBRATIONS,
              "slot_s": frozen.SLOT_S, "difs_s": frozen.DIFS_S, "sifs_s": oq.SIFS_S,
              "w0": frozen.W0, "detect_s": frozen.DETECT_S, "link_loss": hw.LINK_LOSS}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--calibrate", "--defect", "--screen", "--score"):
        what.add_argument(flag, action="store_true")
    ap.add_argument("--only", choices=("R0", "R1", "R2", "R3", "R4", "R5"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, help="write here instead of results/raw")
    args = ap.parse_args()
    if args.calibrate:
        rows, name = calibrate(), "g27_calibration.csv"
    elif args.defect:
        rows, name = defect(args.workers), "g27_frozen_defect.csv"
    elif args.screen:
        rows, name = screen(args.only, args.workers), "g27_screen.csv"
    else:
        rows, name = score(args.only, args.workers), "g27_windows.csv"
    _write(args.out or RAW / name, rows, name.removesuffix(".csv"))
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items()))


if __name__ == "__main__":
    main()
