#!/usr/bin/env python3
"""W1h: W1g's session, preceded on the same Blue 2 boot by a balance gate: plan, gate, score.

predictions/W1h.md. W1g (F128) was void: its senders were unbalanced (cause undetermined: Blue 2
was later found displaced, or the TP-Link differed between boots; F128 addendum), and the Pi 3
had drifted out of its rate band. W1h runs W1g's session unchanged, after four gate windows at
W1g's A31 line on the same Blue 2 boot and placement. No board can be reached during a session
(the Pis' only link is the ad-hoc cell, and node 4's kit takes Blue 2's own radio off the air;
W1h pilot), so the gate is read after the attempt: GO makes the attempt the session, ABORT
discards it unscored, and a new attempt starts.

    python analysis/dsss_w1h.py --plan          -> experiments/channel24/plan_w1h.txt
    python analysis/dsss_w1h.py --gate DIR      -> GO (exit 0) or ABORT (exit 3), DIR/gate.csv
    python analysis/dsss_w1h.py --score results/hw/channel24/<session>
        -> results/hw/channel24/<session>_windows.csv and results/raw/w1h_<session>.csv

Imported unchanged from `dsss_w1g` (registered at `prereg-W1g`) and through it `dsss_w1f`
(`prereg-W1f`): the capacity block, the score with its six validity conditions, the balance rule,
the power check, the scored predictions and bands. New here: the gate, whose windows reach
neither a capacity point nor the background (both match labels exactly).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dsss_w1g as w1g  # noqa: E402

w1f, w1d = w1g.w1f, w1g.w1d
PLAN = w1d.PLANS / "plan_w1h.txt"
GATE_LABEL = "G31"              # W1g's A31 line, relabelled: the calibration's rate
GATE_WINDOWS = w1f.WINDOWS_PER_POINT
GO, ABORT = 0, 3                # --gate's exit codes


def plan() -> list[str]:
    """R1-R4, G31 x4, then W1g's session after its rate checks, verbatim."""
    body = [ln for ln in w1g.plan() if not ln.startswith("#")]
    before, rest = body[:w1f.N_BOARDS], body[w1f.N_BOARDS:]
    a31 = next(ln for ln in rest if ln.split()[0] == w1g.SPREAD_LABEL)
    gate_line = GATE_LABEL + a31[len(w1g.SPREAD_LABEL):]
    return (["# nodes: 1,2,3",
             "# W1h: rate checks; the balance gate (W1g's A31, read after the attempt);"
             " W1g's capacity block and rate checks, verbatim."]
            + before + [gate_line] * GATE_WINDOWS + rest)


def gate(folder: Path) -> tuple[list[dict], bool]:
    """GO only if the rate checks before, node 4's join, the gate windows and the balance hold.

    Reads only the rate checks before and the gate windows, so the first eight windows alone and
    the whole attempt give the same verdict.
    """
    windows = w1f.apply_node4_rules(w1f.window_rows(folder))
    joins = w1f.join_checks(w1f.load_meta(folder))
    before = [m for m in w1f.sentinels(windows) if m["what"] == "rate check before"]
    mine = [w for w in windows if w["label"] == GATE_LABEL]
    usable = sum(1 for w in mine if w.get("usable"))
    windows_row = {"what": "gate: windows usable", "group": GATE_LABEL,
                   "measured": f"{usable}/{GATE_WINDOWS}", "predicted": "", "band_lo": "",
                   "band_hi": "", "held": usable == GATE_WINDOWS == len(mine), "windows": ""}
    balance = w1g.balance_check(w1g.sender_means(folder, GATE_LABEL)) | {
        "what": "gate: senders balanced", "group": GATE_LABEL}
    rows = joins + before + [windows_row, balance]
    go = len(before) == w1f.N_BOARDS and all(r["held"] is True for r in rows)
    return rows, go


def score(session: Path) -> tuple[list[dict], list[dict]]:
    """W1g's score, unchanged, on the session's own windows; the gate reported beside it."""
    windows = w1f.apply_node4_rules(w1f.window_rows(session))
    rows = w1g.score(windows, w1f.load_meta(session),
                     w1g.sender_means(session, w1g.SPREAD_LABEL), w1g._power_log(session))
    gate_rows, go = gate(session)
    balance = next(r for r in gate_rows if r["what"] == "gate: senders balanced")
    verdict = {"what": "gate (reported, not scored)", "group": "GO" if go else "ABORT",
               "measured": balance["measured"], "predicted": "", "band_lo": "",
               "band_hi": w1g.SPREAD_MAX, "held": go, "windows": balance["windows"]}
    return windows, [verdict] + rows


def _show(rows: list[dict]) -> None:
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--plan", action="store_true")
    what.add_argument("--gate", type=Path, metavar="ATTEMPT_DIR")
    what.add_argument("--score", type=Path, metavar="SESSION_DIR")
    args = ap.parse_args()
    if args.plan:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text("\n".join(plan()) + "\n")
        print(PLAN.read_text())
    elif args.gate is not None:
        rows, go = gate(args.gate)
        w1f._write(args.gate / "gate.csv", rows, "w1h_gate")
        _show(rows)
        print("GO" if go else "ABORT")
        sys.exit(GO if go else ABORT)
    else:
        windows, rows = score(args.score)
        w1f._write(w1d.HW / f"{args.score.name}_windows.csv", windows, "w1h_windows")
        w1f._write(w1d.RAW / f"w1h_{args.score.name}.csv", rows, "w1h")
        _show(rows)


if __name__ == "__main__":
    main()
