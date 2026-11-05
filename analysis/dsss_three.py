#!/usr/bin/env python3
"""W1d: three ad-hoc radios at 2.4 GHz — the plans, the predictions and the score.

predictions/W1d.md. Only three of the five boards can join an ad-hoc cell (the BeagleBone Blues
have no IBSS, F120), and with three the capacity crossing lies in overload, so this campaign tests
the contention model, not the capacity ratio. Nodes: 1 = pi-A, 2 = pi-B (Pi 4, BCM4345/6),
3 = Pi 3 (BCM43430/1). 802.11b at 1 Mb/s, channel 11.

    python analysis/dsss_three.py --plan      -> experiments/channel24/plan_s0.txt, plan_s1.txt
    python analysis/dsss_three.py --predict   -> results/raw/w1d_predictions.csv
    python analysis/dsss_three.py --score results/hw/channel24/<session>
        -> results/hw/channel24/<session>_windows.csv and results/raw/w1d_<session>.csv

The contention predictions are W1c's registered rows for N = 2 and 3, unchanged (they were
registered before any board session). The model does not know which chip a station has, so a
mixed pair is predicted as the Pi 4 pair is.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_hardware as w1c  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw" / "channel24"
PLANS = REPO / "experiments" / "channel24"
PREDICTIONS = RAW / "w1d_predictions.csv"
BOARDS = {1: "pi-A (BCM4345/6)", 2: "pi-B (BCM4345/6)", 3: "Pi 3 (BCM43430/1)"}
BCM4345 = (1, 2)
GROUPS = {"AB": (1, 2), "AC": (1, 3), "BC": (2, 3), "ABC": (1, 2, 3)}
PAYLOAD_UDP = w1c.udp_payload(173)          # 145 B: the AUTHBC frame on air
RATE_CHECK_FPS = 600
CONTROL_FPS = 50
STANDARD_CYCLE_S = w1c.cycle_s(1e6, 173)    # 2 224 µs
RATE_BAND_S = (1.9e-3, 2.6e-3)
BACKGROUND_STOP = 0.01
BAND = {2: (0.6, 1.4), 3: (0.3, 1.4)}
MIN_USABLE = 3
# window labels: R<node> a rate check, B<node> a control, a group name (AB, AC, BC, ABC) contention.
# Matched exactly: "BC" is a pair, not a control.
RATE_CHECK = re.compile(r"R\d")
CONTROL = re.compile(r"B\d")


# ------------------------------------------------------------------------------- plans
def registered_contention() -> dict[int, list[tuple[float, int, float]]]:
    """W1c's rows: nodes -> [(occupancy, frames/s per board, model loss)], as registered."""
    out: dict[int, list[tuple[float, int, float]]] = {}
    with w1c.OUT.open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if r["what"] == "contention" and int(r["n"]) in (2, 3):
                out.setdefault(int(r["n"]), []).append(
                    (float(r["u"]), int(r["fps_per_board"]), float(r["model_loss"])))
    return out


def plan_s0() -> list[str]:
    lines = ["# nodes: 1,2,3", "# W1d S0: the rate check (each board alone, saturated), then"
             " one control window per board"]
    for node in BOARDS:
        lines += [f"R{node} {RATE_CHECK_FPS} {PAYLOAD_UDP} {node}"] * 2
    lines += [f"B{node} {CONTROL_FPS} {PAYLOAD_UDP} {node}" for node in BOARDS]
    return lines


def plan_s1() -> list[str]:
    lines = ["# nodes: 1,2,3", "# W1d S1: each pair and the trio at three occupancies, four"
             " windows each, a control window after every four"]
    reg = registered_contention()
    controls = 0
    for i in range(3):
        for name, nodes in GROUPS.items():
            _u, fps, _loss = sorted(reg[len(nodes)])[i]
            lines += [f"{name} {fps} {PAYLOAD_UDP} {','.join(map(str, nodes))}"] * 4
            node = 1 + controls % 3
            lines.append(f"B{node} {CONTROL_FPS} {PAYLOAD_UDP} {node}")
            controls += 1
    return lines


def write_plans() -> None:
    PLANS.mkdir(parents=True, exist_ok=True)
    (PLANS / "plan_s0.txt").write_text("\n".join(plan_s0()) + "\n")
    (PLANS / "plan_s1.txt").write_text("\n".join(plan_s1()) + "\n")


# ------------------------------------------------------------------------------- predictions
def predict() -> list[dict]:
    rows: list[dict] = []
    for node, board in BOARDS.items():
        rows.append({"what": "rate check", "group": board, "nodes": node, "u": "",
                     "fps_per_board": RATE_CHECK_FPS, "model_loss": "",
                     "band_lo": RATE_BAND_S[0], "band_hi": RATE_BAND_S[1],
                     "note": f"standard cycle {1e6 * STANDARD_CYCLE_S:.0f} us"
                             + ("; registered: shorter (F74's direction)" if node in BCM4345
                                else "; direction left open")})
    reg = registered_contention()
    for name, nodes in GROUPS.items():
        lo, hi = BAND[len(nodes)]
        for u, fps, loss in sorted(reg[len(nodes)]):
            rows.append({"what": "contention", "group": name,
                         "nodes": " ".join(map(str, nodes)), "u": u, "fps_per_board": fps,
                         "model_loss": loss, "band_lo": round(lo * loss, 5),
                         "band_hi": round(hi * loss, 5),
                         "note": "W1c's registered row" if name in ("AB", "ABC")
                                 else "W1c's N = 2 row (the model has no chip)"})
    return rows


# ------------------------------------------------------------------------------- scoring
def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _files(session: Path) -> dict[str, dict[str, dict[int, dict]]]:
    by: dict[str, dict[str, dict[int, dict]]] = {}
    for path in session.rglob("*_node*_*.json"):
        m = re.fullmatch(r"(tx|rx|ctr)_node(\d+)_(.+)\.json", path.name)
        if m:
            by.setdefault(m.group(3), {}).setdefault(m.group(1), {})[int(m.group(2))] = \
                _load(path)
    return by


def _undervoltage(before: str, after: str) -> bool:
    """A window is spoiled if a board was under-voltage at its end or became so during it."""
    b, a = int(before or "0x0", 16), int(after or "0x0", 16)
    return bool(a & 0x1) or bool((a & ~b) & 0x10000)


def window_rows(session: Path) -> list[dict]:
    rows = []
    for tag, parts in sorted(_files(session).items()):
        tx, rx, ctr = parts.get("tx", {}), parts.get("rx", {}), parts.get("ctr", {})
        label = tag.split("_")[1]
        senders = [int(s) for s in next(iter(ctr.values()))["senders"].split(",")]
        rate = float(tag.rsplit("_", 1)[1].removesuffix("fps"))
        power_ok = not any(_undervoltage(c.get("throttled_before", ""),
                                         c.get("throttled_after", "")) for c in ctr.values())
        row = {"window": tag, "label": label, "senders": ",".join(map(str, senders)),
               "rate_fps": rate, "power_ok": power_ok}
        if len(senders) == 1:
            s = senders[0]
            got = [rx[r]["by_source"].get(f"10.0.0.{s}") for r in rx if r != s]
            got = [g for g in got if g]
            sent = tx[s]["sent"]
            row |= {"sent": sent, "received_mean": st.mean(g["received_unique"] for g in got),
                    "loss": round(1 - st.mean(g["received_unique"] for g in got) / sent, 6)}
            if RATE_CHECK.fullmatch(label):
                cycles = [g["span_s"] / (g["max_seq"] - g["min_seq"]) for g in got
                          if g["max_seq"] > g["min_seq"]]
                row["cycle_us"] = round(1e6 * st.mean(cycles), 1)
        else:
            sent = {s: tx[s]["sent"] for s in senders}
            received = sum(rx[r]["by_source"].get(f"10.0.0.{s}", {}).get("received_unique", 0)
                           for s in senders for r in senders if r != s)
            row |= {"sent": sum(sent.values()),
                    "delivered_frac": round(received / (sum(sent.values())
                                                        * (len(senders) - 1)), 6),
                    "achieved_fps_min": round(min(tx[s]["achieved_fps"] for s in senders), 2),
                    "late_frames": sum(tx[s].get("late", 0) for s in senders),
                    "tx_dropped": sum(ctr[s]["tx_dropped"] for s in senders)}
            row["usable"] = (power_ok and row["tx_dropped"] == 0
                             and row["achieved_fps_min"] >= 0.98 * rate
                             and row["late_frames"] <= 0.01 * row["sent"])
        rows.append(row)
    return rows


def score(windows: list[dict]) -> list[dict]:
    out = []
    controls = [w["loss"] for w in windows if CONTROL.fullmatch(w["label"]) and w["power_ok"]]
    b = st.mean(controls) if controls else float("nan")
    out.append({"what": "background", "group": "controls", "measured": round(b, 6),
                "predicted": "", "band_lo": "", "band_hi": BACKGROUND_STOP,
                "held": b <= BACKGROUND_STOP, "windows": len(controls)})
    for node, board in BOARDS.items():
        cyc = [w["cycle_us"] for w in windows if w["label"] == f"R{node}" and "cycle_us" in w]
        c = st.mean(cyc) * 1e-6 if cyc else float("nan")
        out.append({"what": "rate check", "group": board, "measured": round(1e6 * c, 1),
                    "predicted": round(1e6 * STANDARD_CYCLE_S, 1),
                    "band_lo": 1e6 * RATE_BAND_S[0], "band_hi": 1e6 * RATE_BAND_S[1],
                    "held": RATE_BAND_S[0] <= c <= RATE_BAND_S[1], "windows": len(cyc)})
        if node in BCM4345 and cyc:
            out.append({"what": "spacing shorter than the standard", "group": board,
                        "measured": round(1e6 * c, 1),
                        "predicted": round(1e6 * STANDARD_CYCLE_S, 1),
                        "band_lo": "", "band_hi": "", "held": c < STANDARD_CYCLE_S,
                        "windows": len(cyc)})
    reg = {(r["group"], float(r["fps_per_board"])): r for r in predict()
           if r["what"] == "contention"}
    for (group, fps), r in sorted(reg.items()):
        mine = [w for w in windows if w["label"] == group and w["rate_fps"] == fps]
        good = [w for w in mine if w.get("usable")]
        loss = (st.mean(1 - w["delivered_frac"] for w in good) - b) if good else float("nan")
        scored = len(good) >= MIN_USABLE
        out.append({"what": "contention", "group": f"{group} at {fps:g}/s",
                    "measured": round(loss, 6) if good else "",
                    "predicted": float(r["model_loss"]), "band_lo": float(r["band_lo"]),
                    "band_hi": float(r["band_hi"]),
                    "held": (float(r["band_lo"]) <= loss <= float(r["band_hi"])) if scored
                    else "not scored (fewer than 3 usable windows)",
                    "windows": f"{len(good)}/{len(mine)}"})
    return out


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"boards": BOARDS, "groups": GROUPS, "payload_udp": PAYLOAD_UDP,
              "rate_band_s": RATE_BAND_S, "background_stop": BACKGROUND_STOP, "band": BAND,
              "min_usable": MIN_USABLE, "rate_check_fps": RATE_CHECK_FPS,
              "control_fps": CONTROL_FPS}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    fields = list(dict.fromkeys(k for r in rows for k in r))
    w = csv.DictWriter(buf, fieldnames=fields, restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--plan", action="store_true")
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", type=Path, metavar="SESSION_DIR")
    args = ap.parse_args()
    if args.plan:
        write_plans()
        print((PLANS / "plan_s1.txt").read_text())
    elif args.predict:
        rows = predict()
        _write(PREDICTIONS, rows, "w1d_predictions")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))
    else:
        windows = window_rows(args.score)
        _write(HW / f"{args.score.name}_windows.csv", windows, "w1d_windows")
        rows = score(windows)
        _write(RAW / f"w1d_{args.score.name}.csv", rows, "w1d")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
