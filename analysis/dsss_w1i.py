#!/usr/bin/env python3
"""W1i: an adaptive preflight tunes the Pis' powers, then one long run at those powers, fixed.

predictions/W1i.md. W1h (F130) was void by a hair: its balance passed the gate at 1.433x and failed
the session's own A31 at 1.549x, drifting with no margin under the 1.5x rule. W1i keeps W1h's plan
and rule and adds margin. A rule fixed in advance (`next_powers`) moves the Pis' powers one rung
at a time, from short preflights, until the senders are within 1.25x. The long run then holds
those powers for every window: one radio configuration for all eight capacity points.

    python analysis/dsss_w1i.py --step DIR --powers 1:800,2:800,3:auto
        -> exit 0 TUNED, 4 RETRY (Pis too fast after a boot), 5 ADJUST (prints POWERS=...),
           3 STOP or NO-GO
    python analysis/dsss_w1i.py --score SESSION_DIR --powers 1:600,2:800,3:auto
        -> results/hw/channel24/<session>_windows.csv and results/raw/w1i_<session>.csv

Reused unchanged:
* W1h's plan (`plan_w1h.txt`) and gate (`dsss_w1h`, `prereg-W1h`);
* W1g's balance rule, crossings and predictions (`dsss_w1g`, `prereg-W1g`);
* W1f's reducer, node 4's rules, bracket and join checks (`dsss_w1f`, `prereg-W1f`);
* the preflight's seven checks (`hw_preflight`, at this commit).

New here: the ladder, the tuning rule, and V6 for any held power.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from collections.abc import Mapping
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dsss_w1h as w1h  # noqa: E402
import hw_preflight as pf  # noqa: E402

w1g, w1f, w1d = w1h.w1g, w1h.w1f, w1h.w1d
PLAN = w1h.PLAN                     # W1h's 52 windows, unchanged
LADDER: tuple[int | None, ...] = (None, 1000, 800, 600, 400)   # mBm; None = auto, the default
TUNE_TARGET = 1.25                  # the preflight's tuning target, with margin under V5's 1.5x
MAX_STEPS = 5
PIS = (1, 2, 3)
EXIT = {"TUNED": 0, "STOP": 3, "NO-GO": 3, "RETRY": 4, "ADJUST": 5}
Powers = Mapping[int, int | None]


def parse_powers(text: str) -> dict[int, int | None]:
    """'1:800,2:800,3:auto' -> {1: 800, 2: 800, 3: None}."""
    out: dict[int, int | None] = {}
    for kv in text.split(","):
        node, value = kv.split(":")
        out[int(node)] = None if value == "auto" else int(value)
    return out


def format_powers(powers: Powers) -> str:
    return ",".join(f"{n}:{'auto' if p is None else p}" for n, p in sorted(powers.items()))


def held(powers: Powers) -> dict[int, int]:
    """The Pis whose power a run holds (the ones not at auto)."""
    return {n: p for n, p in powers.items() if p is not None}


def _step(power: int | None, direction: int) -> int | None:
    i = LADDER.index(power) + direction
    return LADDER[min(max(i, 0), len(LADDER) - 1)]


def next_powers(losses: Mapping[int, float], powers: Powers) -> tuple[dict[int, int | None], str]:
    """One step of the registered tuning rule, from each sender's loss at G31.

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
        if new[s] != LADDER[-1]:
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
    """One tuning preflight: TUNED, RETRY, ADJUST (with the next powers), STOP or NO-GO."""
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


def _power_row(node: int, mbm: int, log: str) -> dict:
    return {"what": f"node{node} at {mbm / 100:g} dBm (V6)", "group": f"node{node} txpower.log",
            "measured": " | ".join(ln.strip() for ln in log.splitlines()), "predicted": "",
            "band_lo": "", "band_hi": "", "held": pf.power_check_at(log, mbm), "windows": ""}


def score(windows: list[dict], meta: dict, means: dict[int, float], logs: Mapping[int, str],
          held_powers: Mapping[int, int]) -> list[dict]:
    """W1g's score with V6 for every held Pi at its tuned power; everything else unchanged."""
    marks = w1f.sentinels(windows)
    joins = w1f.join_checks(meta)
    controls = [w["loss"] for w in windows if w1d.CONTROL.fullmatch(w["label"])
                and w["power_ok"] and w["node4_ok"] and "loss" in w]
    b = st.mean(controls) if controls else float("nan")
    background = {"what": "background", "group": "controls", "measured": round(b, 6),
                  "predicted": "", "band_lo": "", "band_hi": w1d.BACKGROUND_STOP,
                  "held": b <= w1d.BACKGROUND_STOP, "windows": len(controls)}
    setup = [w1g.balance_check(means)] + [_power_row(n, m, logs.get(n, ""))
                                          for n, m in sorted(held_powers.items())]
    valid = (len(marks) == 2 * w1f.N_BOARDS and all(m["held"] is True for m in marks)
             and background["held"] is True and all(j["held"] is True for j in joins + setup))
    scored = w1g._crossings(windows, b)
    if not valid:
        scored = [r | {"held": f"void (session): {r['held']}"} for r in scored]
    head = [{"what": "session", "group": "valid" if valid else "VOID", "measured": "",
             "predicted": "", "band_lo": "", "band_hi": "", "held": valid,
             "windows": len(windows)}]
    return head + joins + setup + marks + [background] + scored


def score_session(session: Path, powers: Powers) -> tuple[list[dict], list[dict]]:
    windows = w1f.apply_node4_rules(w1f.window_rows(session))
    logs = {n: (session / f"node{n}" / "txpower.log").read_text()
            for n in PIS if (session / f"node{n}" / "txpower.log").exists()}
    rows = score(windows, w1f.load_meta(session), w1g.sender_means(session, w1g.SPREAD_LABEL),
                 logs, held(powers))
    gate_rows, go = w1h.gate(session)
    balance = next(r for r in gate_rows if r["what"] == "gate: senders balanced")
    verdict = {"what": "gate (reported, not scored)", "group": "GO" if go else "ABORT",
               "measured": balance["measured"], "predicted": "", "band_lo": "",
               "band_hi": w1g.SPREAD_MAX, "held": go, "windows": balance["windows"]}
    return windows, [verdict] + rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--step", type=Path, metavar="PREFLIGHT_DIR")
    what.add_argument("--score", type=Path, metavar="SESSION_DIR")
    ap.add_argument("--powers", required=True, metavar="1:800,2:800,3:auto")
    args = ap.parse_args()
    powers = parse_powers(args.powers)
    if args.step is not None:
        verdict, new, rows = step(args.step, powers)
        w1f._write(args.step / "tune.csv", rows, "w1i_tune")
        for r in rows:
            print(f"  [{r['check']}] {'ok ' if r['held'] else 'NO '} {r['what']} | {r['group']} | "
                  f"{r['measured']} {('| ' + r['note']) if r.get('note') else ''}")
        print(f"{verdict} POWERS={format_powers(new)}")
        sys.exit(EXIT[verdict])
    windows, rows = score_session(args.score, powers)
    w1f._write(w1d.HW / f"{args.score.name}_windows.csv", windows, "w1i_windows")
    w1f._write(w1d.RAW / f"w1i_{args.score.name}.csv", rows, "w1i")
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
