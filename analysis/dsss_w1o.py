#!/usr/bin/env python3
"""W1o: W1n's series with floors on the tuning: pi-A at least 500, the Pi 3 at least 1100 mBm.

predictions/W1o.md. W1n's session 3 ended on check 7. The tuning had lowered pi-A to 4 dBm and the
Pi 3 to 10 dBm, and node 4 then received only 95.2 % and 76.7 % of their frames alone. At pi-A
5-6 dBm and the Pi 3 11 dBm, node 4 received 98.46-100 % in every W1n run. Mohamed chose
"Series with power floors", and that a STOP at the floors ends the series, as in W1n.

So the rule is W1m's (`dsss_w1m.next_powers`) on its 1 dB grid, word for word but for one test: a
Pi goes down only while above its own floor, not the grid's. pi-B keeps the grid's 400 mBm.

    python analysis/dsss_w1o.py --step DIR --powers 1:600,2:auto,3:1100
        -> exit 0 TUNED, 4 RETRY, 5 ADJUST (prints POWERS=...), 3 STOP or NO-GO

Scoring is W1j's, unchanged: `dsss_w1i.py --score SESSION --powers <that session's powers>`.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dsss_w1m as w1m  # noqa: E402

pf, w1g, w1f = w1m.pf, w1m.w1g, w1m.w1f
PLAN, score_session = w1m.PLAN, w1m.score_session
GRID, TUNE_TARGET, PIS, EXIT, Powers = w1m.GRID, w1m.TUNE_TARGET, w1m.PIS, w1m.EXIT, w1m.Powers
format_powers, held, parse_powers = w1m.format_powers, w1m.held, w1m.parse_powers
# the lowest powers at which node 4 still heard each Pi alone at >= 98.46 % in W1n
FLOORS: dict[int, int] = {1: 500, 2: GRID[-1], 3: 1100}


def _above_floor(node: int, power: int | None) -> bool:
    floor = FLOORS[node]
    return GRID.index(power) < GRID.index(floor)


def next_powers(losses: Mapping[int, float], powers: Powers) -> tuple[dict[int, int | None], str]:
    """W1m's rule (`dsss_w1m.next_powers`) with each Pi's own floor in place of the grid's.

    1. every Pi too strong (loss below L_max / 1.25) goes down one rung, if above its floor;
    2. if the TP-Link is too strong, every held Pi that is not goes up one rung;
    3. the weakest sender, if a held Pi below auto, goes up one rung.
    BALANCED if already within 1.25x; STOP if no knob can move.
    """
    new = dict(powers)
    if max(losses.values()) <= TUNE_TARGET * min(losses.values()):
        return new, "BALANCED"
    l_max = max(losses.values())
    weakest = max(losses, key=lambda s: losses[s])
    strong = {s for s, v in losses.items() if v < l_max / TUNE_TARGET}
    moves = []
    for s in sorted(strong & set(PIS)):
        if _above_floor(s, new[s]):
            new[s] = w1m._step(new[s], +1)
            moves.append(f"node{s} down to {format_powers({s: new[s]}).split(':')[1]}")
    raise_: set[int] = set()
    if w1f.TPLINK in strong:
        raise_ |= {s for s in PIS if s not in strong and powers[s] is not None}
    if weakest in PIS and powers[weakest] is not None:
        raise_.add(weakest)
    for s in sorted(raise_):
        new[s] = w1m._step(new[s], -1)
        moves.append(f"node{s} up to {format_powers({s: new[s]}).split(':')[1]}")
    if not moves:
        return new, "STOP: no knob can move (the strong senders are at their floors or the TP-Link)"
    return new, "ADJUST: " + "; ".join(moves)


def step(folder: Path, powers: Powers) -> tuple[str, dict[int, int | None], list[dict]]:
    """One tuning step from a preflight's files: TUNED, RETRY, ADJUST, STOP or NO-GO."""
    rows, verdict = pf.check(folder, held(powers), spread_max=TUNE_TARGET)
    if verdict == "GO":
        return "TUNED", dict(powers), rows
    if verdict == "RETRY":
        return "RETRY", dict(powers), rows
    if any(not r["held"] for r in rows if r["check"] != 6):
        return "NO-GO", dict(powers), rows
    new, action = next_powers(w1g.sender_means(folder, pf.GATE_LABEL), powers)
    return ("STOP" if action.startswith("STOP") else "ADJUST"), new, rows + [
        {"check": "tune", "what": action, "group": format_powers(new), "measured": "",
         "held": not action.startswith("STOP"), "note": ""}]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", type=Path, required=True, metavar="PREFLIGHT_DIR")
    ap.add_argument("--powers", required=True, metavar="1:600,2:auto,3:1100")
    args = ap.parse_args()
    verdict, new, rows = step(args.step, parse_powers(args.powers))
    w1f._write(args.step / "tune.csv", rows, "w1o_tune")
    for r in rows:
        print(f"  [{r['check']}] {'ok ' if r['held'] else 'NO '} {r['what']} | {r['group']} | "
              f"{r['measured']} {('| ' + r['note']) if r.get('note') else ''}")
    print(f"{verdict} POWERS={format_powers(new)}")
    sys.exit(EXIT[verdict])


if __name__ == "__main__":
    main()
