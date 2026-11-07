#!/usr/bin/env python3
"""W1g: four radios, balanced, the grid moved to bracket both crossings: plan, predictions, score.

predictions/W1g.md. In W1f (F127) loss depended on the sender: the stronger radio won collisions
(capture), every point lay above the model, and the per-record curve did not fall to 0.95 inside
its grid, so the ratio was not measured. Making the senders equal cannot remove capture with these
radios (calibration, `results/hw/channel24/w1g_cal_2026-11-06/`). So W1g keeps the balanced setup
(the TP-Link at 90 cm, pi-B at 8 dBm) and moves the grid to bracket both crossings below overload,
to measure the ratio on real radios with capture present and stated.

    python analysis/dsss_w1g.py --plan        -> experiments/channel24/plan_w1g.txt
    python analysis/dsss_w1g.py --predict [W] -> results/raw/w1g_predictions.csv
    python analysis/dsss_w1g.py --score results/hw/channel24/<session>
        -> results/hw/channel24/<session>_windows.csv and results/raw/w1g_<session>.csv

Imported unchanged from `dsss_w1f` (registered at `prereg-W1f`): the four-board mapping, the
reducer and node 4's rules, the bracket, the join checks, the crossing interpolation. The scored
crossings, bands and ratio are W1f's registered values, copied without change. New here: the grid,
the balance rule (V5) and the power check (V6).
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_campaign as w1b  # noqa: E402
import dsss_w1f as w1f  # noqa: E402

from authbc.bench.stats import interpolated_crossing_ci  # noqa: E402

w1d, w1c = w1f.w1d, w1f.w1c
PLAN = w1d.PLANS / "plan_w1g.txt"
PREDICTIONS = w1d.RAW / "w1g_predictions.csv"
NEQ_GRID = {"AUTHBC": (29, 30, 31, 32), "per-record": (9, 9.25, 9.5, 9.75)}
SPREAD_LABEL = "A31"            # the calibration's rate (125 frames/s per board)
SPREAD_MAX = 1.5                # PROTOCOL.md's rule: every sender within 1.5x of every other
PI_B, PI_B_MBM = 2, 800         # pi-B held at 8 dBm through the windows (calibration run 3)
SET_LINE = re.compile(rf"set {PI_B_MBM}: txpower {PI_B_MBM / 100:.2f} dBm")


def points() -> list[tuple[str, float]]:
    """The capacity points in session order: the designs alternate, each in ascending load."""
    a, p = list(NEQ_GRID["AUTHBC"]), list(NEQ_GRID["per-record"])
    pairs = zip((("AUTHBC", n) for n in a), (("per-record", n) for n in p), strict=True)
    return [pt for pair in pairs for pt in pair]


def plan() -> list[str]:
    everyone = ",".join(map(str, w1f.BOARDS))
    rate_checks = [f"R{n} {w1d.RATE_CHECK_FPS} {w1d.PAYLOAD_UDP} {n}" for n in w1f.BOARDS]
    body: list[str] = []
    for k, (design, neq) in enumerate(points()):
        line = (f"{w1f.label(design, neq)} {w1f._rate(w1f.board_rate(design, neq))} "
                f"{w1f.payload(design)} {everyone}")
        body += [line] * w1f.WINDOWS_PER_POINT
        node = 1 + k % w1f.N_BOARDS
        body.append(f"B{node} {w1d.CONTROL_FPS} {w1d.PAYLOAD_UDP} {node}")
    return (["# nodes: 1,2,3",
             "# W1g: rate checks; the capacity points, the designs alternating, moved to bracket"
             " both crossings; rate checks. Balanced: TP-Link at 90 cm, pi-B at 8 dBm."]
            + rate_checks + body + rate_checks)


# ------------------------------------------------------------------------------- predictions
def _w1f_registered_rows() -> list[dict]:
    with w1f.PREDICTIONS.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                if r["what"] in ("crossing", "ratio")]


def predict(workers: int, seeds: int = w1f.SEEDS) -> list[dict]:
    """The model at this grid (reported), and W1f's registered crossings and ratio (scored)."""
    rows: list[dict] = []
    jobs = [(w1f.N_BOARDS, w1f.board_rate(d, n), w1c.DESIGNS[d][0], s)
            for d, n in points() for s in range(1, seeds + 1)]
    with Pool(workers) as pool:
        got = pool.map(w1f._job, jobs, chunksize=4)
    by: dict[tuple[int, float, int], list[float]] = {}
    for n, f, mac, v in got:
        by.setdefault((n, f, mac), []).append(v)
    for d, neq in sorted(points()):
        f = w1f.board_rate(d, neq)
        v = st.mean(by[(w1f.N_BOARDS, f, w1c.DESIGNS[d][0])])
        rows.append({"what": "capacity-equivalent (model, reported)", "design": d,
                     "n": w1f.N_BOARDS, "n_eq": neq, "fps_per_board": round(f, 3),
                     "udp_payload": w1f.payload(d),
                     "offered_load": round(w1f.offered_load(d, neq), 4), "model": round(v, 5),
                     "band_lo": "", "band_hi": "", "note": w1f.label(d, neq)})
    for r in _w1f_registered_rows():
        rows.append({k: r[k] for k in ("what", "design", "n", "n_eq", "fps_per_board",
                                       "udp_payload", "offered_load", "model", "band_lo",
                                       "band_hi")}
                    | {"note": "W1f's registered prediction and band, unchanged"})
    return rows


def registered() -> dict[str, dict]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        return {f"{r['what']}:{r['design']}": r
                for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                if r["what"] in ("crossing", "ratio")}


# ------------------------------------------------------------------------------- scoring
def sender_means(session: Path, label: str) -> dict[int, float]:
    """Each sender's frames' loss, averaged over the other three receivers and the windows."""
    per: dict[int, list[float]] = {}
    for tag, parts in w1d._files(session).items():
        if tag.split("_")[1] != label:
            continue
        tx, rx = parts.get("tx", {}), parts.get("rx", {})
        for s in w1f.BOARDS:
            if s not in tx or not all(r in rx for r in w1f.BOARDS if r != s):
                continue
            got = [rx[r]["by_source"].get(f"10.0.0.{s}", {}).get("received_unique", 0)
                   for r in w1f.BOARDS if r != s]
            per.setdefault(s, []).append(1 - st.mean(got) / tx[s]["sent"])
    return {s: st.mean(v) for s, v in sorted(per.items())}


def balance_check(means: dict[int, float]) -> dict:
    complete = len(means) == w1f.N_BOARDS and min(means.values(), default=0) > 0
    spread = max(means.values()) / min(means.values()) if complete else float("nan")
    return {"what": "senders balanced (V5)", "group": SPREAD_LABEL,
            "measured": round(spread, 3) if complete else "",
            "predicted": "", "band_lo": "", "band_hi": SPREAD_MAX,
            "held": complete and spread <= SPREAD_MAX,
            "windows": " ".join(f"{w1f.BOARDS[s].split()[0]}={100 * m:.2f}%"
                                for s, m in means.items())}


def power_check(log: str) -> dict:
    """V6: pi-B was held at 8 dBm (read back) and returned to auto."""
    m = SET_LINE.search(log)
    held = m is not None and "auto:" in log[m.end():]
    return {"what": "pi-B at 8 dBm (V6)", "group": "node2 txpower.log",
            "measured": " | ".join(ln.strip() for ln in log.splitlines()), "predicted": "",
            "band_lo": "", "band_hi": "", "held": held, "windows": ""}


def _crossings(windows: list[dict], b: float) -> list[dict]:
    reg = registered()
    rows, x = [], {}
    for design, grid in NEQ_GRID.items():
        curve: dict[float, float] = {}
        per_n: dict[float, list[float]] = {}
        for neq in grid:
            mine = [w for w in windows if w["label"] == w1f.label(design, neq)]
            good = [w for w in mine if w.get("usable")]
            v = [w["delivered_frac"] / (1 - b) for w in good]
            if len(good) >= w1d.MIN_USABLE:
                curve[neq], per_n[neq] = st.mean(v), v
            rows.append({"what": "capacity-equivalent", "group": w1f.label(design, neq),
                         "measured": round(st.mean(v), 5) if v else "", "predicted": "",
                         "band_lo": "", "band_hi": "",
                         "held": "scored" if len(good) >= w1d.MIN_USABLE
                         else "not scored (fewer than 3 usable windows)",
                         "windows": f"{len(good)}/{len(mine)}"})
        xs = w1f._crossing(curve) if len(curve) >= 2 else None
        equal = len({len(v) for v in per_n.values()}) == 1
        ci = (interpolated_crossing_ci(per_n, threshold=w1b.V_TARGET)
              if len(per_n) >= 2 and equal else None)
        r = reg[f"crossing:{design}"]
        x[design] = xs
        rows.append({"what": "crossing", "group": design,
                     "measured": round(xs, 3) if xs is not None else "",
                     "predicted": float(r["n_eq"]), "band_lo": float(r["band_lo"]),
                     "band_hi": float(r["band_hi"]),
                     "held": (float(r["band_lo"]) <= xs <= float(r["band_hi"]))
                     if xs is not None else "not determined (the curve does not cross 0.95 "
                                            "inside the grid)",
                     "windows": f"95% CI {ci[0]:.2f}-{ci[1]:.2f} ({ci[2]:.0%} bracketed)"
                     if ci else ""})
    r = reg["ratio:AUTHBC/per-record"]
    xa, xp = x["AUTHBC"], x["per-record"]
    ratio = xa / xp if xa is not None and xp is not None else None
    rows.append({"what": "ratio", "group": "AUTHBC/per-record",
                 "measured": round(ratio, 4) if ratio is not None else "",
                 "predicted": float(r["n_eq"]), "band_lo": float(r["band_lo"]),
                 "band_hi": float(r["band_hi"]),
                 "held": (float(r["band_lo"]) <= ratio <= float(r["band_hi"]))
                 if ratio is not None else "not determined", "windows": ""})
    return rows


def score(windows: list[dict], meta: dict, means: dict[int, float], power_log: str) -> list[dict]:
    """W1g-1 the bracket, W1g-2 the background, W1g-3/4 the crossings, W1g-5 the ratio.

    Valid only if V1-V4 (as W1f) hold and the senders were balanced (V5) with pi-B at 8 dBm (V6).
    Otherwise every scored row is marked void.
    """
    marks = w1f.sentinels(windows)
    joins = w1f.join_checks(meta)
    controls = [w["loss"] for w in windows if w1d.CONTROL.fullmatch(w["label"])
                and w["power_ok"] and w["node4_ok"] and "loss" in w]
    b = st.mean(controls) if controls else float("nan")
    background = {"what": "background", "group": "controls", "measured": round(b, 6),
                  "predicted": "", "band_lo": "", "band_hi": w1d.BACKGROUND_STOP,
                  "held": b <= w1d.BACKGROUND_STOP, "windows": len(controls)}
    setup = [balance_check(means), power_check(power_log)]
    valid = (len(marks) == 2 * w1f.N_BOARDS and all(m["held"] is True for m in marks)
             and background["held"] is True and all(j["held"] is True for j in joins + setup))
    scored = _crossings(windows, b)
    if not valid:
        scored = [r | {"held": f"void (session): {r['held']}"} for r in scored]
    head = [{"what": "session", "group": "valid" if valid else "VOID", "measured": "",
             "predicted": "", "band_lo": "", "band_hi": "", "held": valid,
             "windows": len(windows)}]
    return head + joins + setup + marks + [background] + scored


def _power_log(session: Path) -> str:
    path = session / f"node{PI_B}" / "txpower.log"
    return path.read_text() if path.exists() else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--plan", action="store_true")
    what.add_argument("--predict", type=int, nargs="?", const=4, metavar="WORKERS")
    what.add_argument("--score", type=Path, metavar="SESSION_DIR")
    args = ap.parse_args()
    if args.plan:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text("\n".join(plan()) + "\n")
        print(PLAN.read_text())
    elif args.predict is not None:
        rows = predict(args.predict)
        w1f._write(PREDICTIONS, rows, "w1g_predictions")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))
    else:
        windows = w1f.apply_node4_rules(w1f.window_rows(args.score))
        w1f._write(w1d.HW / f"{args.score.name}_windows.csv", windows, "w1g_windows")
        rows = score(windows, w1f.load_meta(args.score), sender_means(args.score, SPREAD_LABEL),
                     _power_log(args.score))
        w1f._write(w1d.RAW / f"w1g_{args.score.name}.csv", rows, "w1g")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
