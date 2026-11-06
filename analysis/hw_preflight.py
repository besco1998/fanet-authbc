#!/usr/bin/env python3
"""The preflight before every long hardware run: six windows, six mechanical checks, GO or not.

hw/channel/README.md §"Preflight before every long run". No board can be reached during a session
(F129), so a long run's faults show only when it ends. A three-minute run on the same setup checks
the parameters first:
1. every Pi broadcasts at 1 Mb/s: its rate check in band and channel-limited (a Pi in its first
   ad-hoc session after a boot sends at 6 Mb/s and is limited by its own offered rate; F129);
2. the TP-Link at 1 Mb/s: `rate_ctl` fixed at join, its rate check in band;
3. pi-B held at 8 dBm, then back to auto;
4. node 4 in the Pis' cell with every Pi reached, and Blue 2 on one boot throughout;
5. no Pi under-voltage;
6. the senders within 1.5x of each other at W1g's A31 line (two G31 windows).

The preflight is never scored. It decides only whether a long run starts; the long run's own
registered conditions still decide its validity.

    python analysis/hw_preflight.py --plan        -> experiments/channel24/plan_preflight.txt
    python analysis/hw_preflight.py --check DIR   -> DIR/preflight.csv; exit 0 GO, 3 NO-GO,
                                                     4 RETRY (once)

Reused unchanged: the reducer, node 4's rules, the bracket and the join checks (`dsss_w1f`,
`prereg-W1f`); the per-sender loss, the balance rule and the power check (`dsss_w1g`, `prereg-W1g`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dsss_w1g as w1g  # noqa: E402

w1f, w1d = w1g.w1f, w1g.w1d
PLAN = w1d.PLANS / "plan_preflight.txt"
GATE_LABEL = "G31"
GATE_WINDOWS = 2
SENDER_LIMITED = 0.98           # achieved >= 98 % of the offered rate: the sender, not the channel
PIS = (1, 2, 3)
EXIT = {"GO": 0, "NO-GO": 3, "RETRY": 4}


def plan() -> list[str]:
    """R1-R4 as every session's bracket, then two windows of W1g's A31 line relabelled G31."""
    body = [ln for ln in w1g.plan() if not ln.startswith("#")]
    a31 = next(ln for ln in body if ln.split()[0] == w1g.SPREAD_LABEL)
    return (["# nodes: 1,2,3",
             "# Preflight (hw/channel/README.md): rate checks, then the balance at W1g's A31 line."]
            + body[:w1f.N_BOARDS] + [GATE_LABEL + a31[len(w1g.SPREAD_LABEL):]] * GATE_WINDOWS)


def _windows() -> list[str]:
    return [ln for ln in plan() if not ln.startswith("#")]


def _row(check: int, what: str, group: str, measured: object, held: bool, note: str = "") -> dict:
    return {"check": check, "what": what, "group": group, "measured": measured, "held": held,
            "note": note}


def _achieved(folder: Path) -> dict[str, float]:
    """Each rate check's achieved send rate, by window tag."""
    out = {}
    for tag, parts in w1d._files(folder).items():
        tx = parts.get("tx", {})
        if w1d.RATE_CHECK.fullmatch(tag.split("_")[1]) and len(tx) == 1:
            out[tag] = next(iter(tx.values()))["achieved_fps"]
    return out


def _rate_rows(windows: list[dict], achieved: dict[str, float]) -> list[dict]:
    lo, hi = (1e6 * x for x in w1d.RATE_BAND_S)
    rows = []
    for node in (*PIS, w1f.TPLINK):
        mine = [w for w in windows if w["label"] == f"R{node}" and "cycle_us" in w]
        if not mine:
            rows.append(_row(1 if node in PIS else 2, "rate check", w1f.BOARDS[node], "",
                             False, "missing"))
            continue
        w = mine[0]
        limited = achieved.get(w["window"], 0.0) >= SENDER_LIMITED * w["rate_fps"]
        held = lo <= w["cycle_us"] <= hi and not (node in PIS and limited)
        note = ("sender-limited: faster than 1 Mb/s (F129)" if node in PIS and limited
                else "" if held else f"outside {lo:.0f}-{hi:.0f} us")
        rows.append(_row(1 if node in PIS else 2, "rate check", w1f.BOARDS[node], w["cycle_us"],
                         held, note))
    return rows


def check(folder: Path) -> tuple[list[dict], str]:
    """The six checks, then GO, NO-GO, or RETRY (only the Pis at 6 Mb/s, everything else fine)."""
    windows = w1f.apply_node4_rules(w1f.window_rows(folder))
    meta = w1f.load_meta(folder)
    joined, rate_fixed = w1f.join_checks(meta)
    rows = _rate_rows(windows, _achieved(folder))
    rows.append(_row(2, "rate_ctl at join", "TP-Link", rate_fixed["group"],
                     rate_fixed["held"] is True))
    power = w1g.power_check(w1g._power_log(folder))
    rows.append(_row(3, "pi-B at 8 dBm, then auto", "node2 txpower.log", power["measured"],
                     power["held"] is True))
    rows.append(_row(4, "node 4 in the Pis' cell", joined["group"], joined["measured"],
                     joined["held"] is True))
    boots = {b for w in windows for b in (w.get("boot_before", ""), w.get("boot_after", ""))}
    n_complete, n_planned = sum(1 for w in windows if w.get("complete")), len(_windows())
    rows.append(_row(4, "Blue 2 on one boot, every window complete", ",".join(sorted(boots)),
                     f"{n_complete}/{n_planned}",
                     len(boots) == 1 and "" not in boots and n_complete == n_planned))
    rows.append(_row(5, "no Pi under-voltage", "all windows",
                     sum(1 for w in windows if not w["power_ok"]),
                     bool(windows) and all(w["power_ok"] for w in windows)))
    balance = w1g.balance_check(w1g.sender_means(folder, GATE_LABEL))
    gate = [w for w in windows if w["label"] == GATE_LABEL and w.get("usable")]
    rows.append(_row(6, "senders within 1.5x", GATE_LABEL, balance["measured"],
                     balance["held"] is True and len(gate) == GATE_WINDOWS,
                     f"{balance['windows']}; usable {len(gate)}/{GATE_WINDOWS}"))
    if all(r["held"] for r in rows):
        return rows, "GO"
    pis = [r for r in rows if r["check"] == 1]
    fast = len(pis) == len(PIS) and all("sender-limited" in r["note"] for r in pis)
    others = all(r["held"] for r in rows if r["check"] in (2, 3, 4, 5))
    return rows, "RETRY" if fast and others else "NO-GO"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--plan", action="store_true")
    what.add_argument("--check", type=Path, metavar="RUN_DIR")
    args = ap.parse_args()
    if args.plan:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text("\n".join(plan()) + "\n")
        print(PLAN.read_text())
        return
    rows, verdict = check(args.check)
    w1f._write(args.check / "preflight.csv", rows, "hw_preflight")
    for r in rows:
        print(f"  [{r['check']}] {'ok ' if r['held'] else 'NO '} {r['what']} | {r['group']} | "
              f"{r['measured']} {('| ' + r['note']) if r['note'] else ''}")
    print(verdict)
    sys.exit(EXIT[verdict])


if __name__ == "__main__":
    main()
