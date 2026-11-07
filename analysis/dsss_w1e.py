#!/usr/bin/env python3
"""W1e: three ad-hoc radios side by side at 2.4 GHz, the session bracketed by rate checks.

predictions/W1e.md. W1d's S0 failed its rate check for the Pi 3 and stopped the campaign (F121).
Repeated with the Pi 3 beside the Pi 4s and one Blue unplugged, the Pi 3 kept the 1 Mb/s band; the
cause of S0's failure was outside it and is confounded (F122). A sender that is made to defer
loses nothing: only a single-sender rate check sees it. So W1e runs W1d's contention windows
between two rate checks, one per board before and one per board after, and the session counts
only if all six lie in the band.

Everything else is W1d's, imported unchanged from `dsss_three` (registered at `prereg-W1d`):
the boards and groups, W1c's model rows, the bands, the usable-window rule, the background, and
the per-window reducer.

    python analysis/dsss_w1e.py --plan      -> experiments/channel24/plan_w1e.txt
    python analysis/dsss_w1e.py --predict   -> results/raw/w1e_predictions.csv
    python analysis/dsss_w1e.py --score results/hw/channel24/<session>
        -> results/hw/channel24/<session>_windows.csv and results/raw/w1e_<session>.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dsss_three as w1d  # noqa: E402

PLAN = w1d.PLANS / "plan_w1e.txt"
PREDICTIONS = w1d.RAW / "w1e_predictions.csv"


def _rate_checks() -> list[str]:
    return [f"R{node} {w1d.RATE_CHECK_FPS} {w1d.PAYLOAD_UDP} {node}" for node in w1d.BOARDS]


def plan() -> list[str]:
    """One rate check per board, W1d's sixty contention and control windows, one per board again."""
    body = [ln for ln in w1d.plan_s1() if not ln.startswith("#")]
    return (["# nodes: 1,2,3",
             "# W1e: a rate check per board, W1d's S1 windows unchanged, a rate check per board"]
            + _rate_checks() + body + _rate_checks())


def predict() -> list[dict]:
    """W1d's rows (W1c's model rows for the contention points), and the six sentinels' band."""
    rows = [r for r in w1d.predict() if r["what"] == "contention"]
    for when in ("before", "after"):
        for node, board in w1d.BOARDS.items():
            rows.append({"what": f"rate check {when}", "group": board, "nodes": node, "u": "",
                         "fps_per_board": w1d.RATE_CHECK_FPS, "model_loss": "",
                         "band_lo": w1d.RATE_BAND_S[0], "band_hi": w1d.RATE_BAND_S[1],
                         "note": "every one in the band, or the session is void"})
    return rows


def _index(window: dict) -> int:
    return int(window["window"].split("_")[0])


def sentinels(windows: list[dict]) -> list[dict]:
    """The rate-check windows, each with its own verdict; 'before' and 'after' by position."""
    rates = sorted((w for w in windows if w1d.RATE_CHECK.fullmatch(w["label"])), key=_index)
    middle = sorted(_index(w) for w in windows if not w1d.RATE_CHECK.fullmatch(w["label"]))
    first = middle[0] if middle else 0
    out = []
    for w in rates:
        node = int(w["label"][1:])
        c = w.get("cycle_us", float("nan")) * 1e-6
        out.append({"what": f"rate check {'before' if _index(w) < first else 'after'}",
                    "group": w1d.BOARDS[node], "measured": w.get("cycle_us", ""),
                    "predicted": round(1e6 * w1d.STANDARD_CYCLE_S, 1),
                    "band_lo": 1e6 * w1d.RATE_BAND_S[0], "band_hi": 1e6 * w1d.RATE_BAND_S[1],
                    "held": bool(w["power_ok"]) and w1d.RATE_BAND_S[0] <= c <= w1d.RATE_BAND_S[1],
                    "windows": 1})
    return out


def score(windows: list[dict]) -> list[dict]:
    """W1e-1 the six sentinels, W1e-2 the background, W1e-3 the twelve contention points.

    The session is valid only if W1e-1 and W1e-2 both hold, with all six sentinels present.
    Otherwise the contention rows are still reported, but marked void.
    """
    marks = sentinels(windows)
    base = w1d.score(windows)
    background = next(r for r in base if r["what"] == "background")
    valid = (len(marks) == 2 * len(w1d.BOARDS) and all(m["held"] is True for m in marks)
             and background["held"] is True)
    out = [{"what": "session", "group": "valid" if valid else "VOID", "measured": "",
            "predicted": "", "band_lo": "", "band_hi": "", "held": valid,
            "windows": len(windows)}]
    out += marks + [background]
    for r in base:
        if r["what"] == "contention":
            out.append(r if valid else r | {"held": f"void (session): {r['held']}"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--plan", action="store_true")
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", type=Path, metavar="SESSION_DIR")
    args = ap.parse_args()
    if args.plan:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text("\n".join(plan()) + "\n")
        print(PLAN.read_text())
    elif args.predict:
        rows = predict()
        w1d._write(PREDICTIONS, rows, "w1e_predictions")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))
    else:
        windows = w1d.window_rows(args.score)
        w1d._write(w1d.HW / f"{args.score.name}_windows.csv", windows, "w1e_windows")
        rows = score(windows)
        w1d._write(w1d.RAW / f"w1e_{args.score.name}.csv", rows, "w1e")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
