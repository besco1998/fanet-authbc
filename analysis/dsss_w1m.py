#!/usr/bin/env python3
"""W1m: sessions at W1j's registered powers; re-tuned on W1j's 1 dB grid only after a balance NO-GO.

predictions/W1m.md. W1l met a NO-GO on balance alone (1.769x) at W1j's powers, after the
square was rebuilt. Mohamed: "use the same power rules as session 1 and 2 registered". So each
session starts as W1j and W1k ran it: pi-A 600, pi-B auto, the Pi 3 1100 mBm, set, read back and
returned to auto by `set_txpower_window.sh`, a preflight at W1k's 1.5x, W1j's score.

Only a preflight that fails on balance alone starts a tuning. The tuning rule is W1i's
(`dsss_w1i.next_powers`, prereg-W1i), word for word, with its target (1.25x) and floor (400 mBm),
on the grid W1j chose its powers from: 1 dB steps. W1i's 2 dB ladder has no rung at 1100 mBm, so
it cannot start from W1j's powers at all.

    python analysis/dsss_w1m.py --step DIR --powers 1:600,2:auto,3:1100
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

import dsss_w1i as w1i  # noqa: E402

pf, w1g, w1f = w1i.pf, w1i.w1g, w1i.w1f
PLAN = w1i.PLAN
score_session = w1i.score_session
# auto on top, then 14 ... 4 dBm: W1j's powers (6 and 11 dBm) and the 10 / 12 dBm it tried are on it
GRID: tuple[int | None, ...] = (None, *range(1400, 399, -100))
TUNE_TARGET = w1i.TUNE_TARGET
MAX_STEPS = 6
PIS = w1i.PIS
EXIT = w1i.EXIT
Powers = w1i.Powers
format_powers, held, parse_powers = w1i.format_powers, w1i.held, w1i.parse_powers


def _step(power: int | None, direction: int) -> int | None:
    i = GRID.index(power) + direction
    return GRID[min(max(i, 0), len(GRID) - 1)]


def next_powers(losses: Mapping[int, float], powers: Powers) -> tuple[dict[int, int | None], str]:
    """W1i's rule (`dsss_w1i.next_powers`) on GRID; the rung, not the logic, is what changes.

    1. every Pi too strong (loss below L_max / 1.25) goes down one rung, if above the floor;
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
        if new[s] != GRID[-1]:
            new[s] = _step(new[s], +1)
            moves.append(f"node{s} down to {format_powers({s: new[s]}).split(':')[1]}")
    raise_: set[int] = set()
    if w1f.TPLINK in strong:
        raise_ |= {s for s in PIS if s not in strong and powers[s] is not None}
    if weakest in PIS and powers[weakest] is not None:
        raise_.add(weakest)
    for s in sorted(raise_):
        new[s] = _step(new[s], -1)
        moves.append(f"node{s} up to {format_powers({s: new[s]}).split(':')[1]}")
    if not moves:
        return new, "STOP: no knob can move (the strong senders are at the floor or the TP-Link)"
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
    w1f._write(args.step / "tune.csv", rows, "w1m_tune")
    for r in rows:
        print(f"  [{r['check']}] {'ok ' if r['held'] else 'NO '} {r['what']} | {r['group']} | "
              f"{r['measured']} {('| ' + r['note']) if r.get('note') else ''}")
    print(f"{verdict} POWERS={format_powers(new)}")
    sys.exit(EXIT[verdict])


if __name__ == "__main__":
    main()
