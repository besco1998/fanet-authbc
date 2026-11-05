#!/usr/bin/env python3
"""W1f: four ad-hoc radios at 2.4 GHz — the capacity ratio on hardware: plan, predictions, score.

predictions/W1f.md. With three radios the capacity crossing lies in overload (F120); the fourth
station is the TP-Link TL-WN722N on BeagleBone Blue 2, driven by the community driver with its
rate fixed at 1 Mb/s (F125), which saturates at the Pis' pace and joins their cell. Nodes:
1 = pi-A, 2 = pi-B (BCM4345/6), 3 = Pi 3 (BCM43430/1), 4 = the TP-Link (RTL8188EUS).

    python analysis/dsss_w1f.py --plan        -> experiments/channel24/plan_w1f.txt
    python analysis/dsss_w1f.py --predict [W] -> results/raw/w1f_predictions.csv
    python analysis/dsss_w1f.py --score results/hw/channel24/<session>
        -> results/hw/channel24/<session>_windows.csv and results/raw/w1f_<session>.csv

Imported unchanged: W1c's model and designs (`dsss_hardware`), W1d's per-window reducer, payload,
rate band and usable-window rule (`dsss_three`), and W1c's registered N = 4 contention rows. New
here: A12's mapping inverted for four boards, the four-board predictions, and the rules that the
fourth station needs (its files present, its boot ID unchanged, its BSSID not its own cell, its
rate fixed). Node 4 joins 40 s before the first window, after the Pis' early peer check, so the
plan's header names only nodes 1-3.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import statistics as st
import sys
import tempfile
from collections.abc import Mapping
from multiprocessing import Pool
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_campaign as w1b  # noqa: E402
import dsss_hardware as w1c  # noqa: E402
import dsss_three as w1d  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing, interpolated_crossing_ci  # noqa: E402
from authbc.models.phy import DSSS_1M  # noqa: E402
from authbc.sim import dcf_own_queue as oq  # noqa: E402

PLAN = w1d.PLANS / "plan_w1f.txt"
PREDICTIONS = w1d.RAW / "w1f_predictions.csv"
BOARDS = {1: "pi-A (BCM4345/6)", 2: "pi-B (BCM4345/6)", 3: "Pi 3 (BCM43430/1)",
          4: "TP-Link on Blue 2 (RTL8188EUS)"}
TPLINK = 4
N_BOARDS = len(BOARDS)
GROUP = "ABCD"
NEQ_GRID = {"AUTHBC": (24, 27, 29, 30, 31, 32), "per-record": (7, 8, 8.5, 9, 9.5)}
LABEL = {"AUTHBC": "A", "per-record": "P"}
MANY_NODE_GRID = {"AUTHBC": tuple(range(26, 35)), "per-record": tuple(range(7, 12))}
WINDOWS_PER_POINT = 4
CROSSING_BAND = 0.10
RATIO_FLOOR = 2.5
OWN_CELL = "02:11:87:"          # the driver's own-cell BSSID (rtl8188eus core/rtw_mlme.c l. 518)
RATE_FIXED = "FIXED CCK_1M"     # what rate_ctl reads when 1 Mb/s is fixed (core/rtw_debug.c)
SEEDS = w1c.SEEDS


# ------------------------------------------------------------------------------- the mapping
def board_rate(design: str, neq: float) -> float:
    """A12's mapping inverted for four boards: each contends with the load of `neq` - 1 nodes."""
    return (neq - 1) * w1c.DESIGNS[design][1] / (N_BOARDS - 1)


def offered_load(design: str, neq: float) -> float:
    return N_BOARDS * board_rate(design, neq) * DSSS_1M.t_broadcast(w1c.DESIGNS[design][0])


def payload(design: str) -> int:
    return w1c.udp_payload(w1c.DESIGNS[design][0])


def points() -> list[tuple[str, float]]:
    """The capacity points in session order: the designs alternate, each in ascending load."""
    a, p = list(NEQ_GRID["AUTHBC"]), list(NEQ_GRID["per-record"])
    out: list[tuple[str, float]] = []
    while a or p:
        if a:
            out.append(("AUTHBC", a.pop(0)))
        if p:
            out.append(("per-record", p.pop(0)))
    return out


def label(design: str, neq: float) -> str:
    return f"{LABEL[design]}{neq:g}"


def _rate(f: float) -> str:
    return f"{f:.3f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------------------- plan
def registered_contention() -> list[tuple[float, int, float]]:
    """W1c's N = 4 rows, as registered: [(occupancy, frames/s per board, model loss)]."""
    with w1c.OUT.open(encoding="utf-8") as fh:
        return sorted((float(r["u"]), int(r["fps_per_board"]), float(r["model_loss"]))
                      for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                      if r["what"] == "contention" and int(r["n"]) == N_BOARDS)


def plan() -> list[str]:
    everyone = ",".join(map(str, BOARDS))
    rate_checks = [f"R{n} {w1d.RATE_CHECK_FPS} {w1d.PAYLOAD_UDP} {n}" for n in BOARDS]
    body: list[str] = []

    def control() -> str:
        node = 1 + len([ln for ln in body if ln.startswith("B")]) % N_BOARDS
        return f"B{node} {w1d.CONTROL_FPS} {w1d.PAYLOAD_UDP} {node}"

    for _u, fps, _loss in registered_contention():
        body += [f"{GROUP} {fps} {w1d.PAYLOAD_UDP} {everyone}"] * WINDOWS_PER_POINT
        body.append(control())
    for design, neq in points():
        line = f"{label(design, neq)} {_rate(board_rate(design, neq))} {payload(design)} {everyone}"
        body += [line] * WINDOWS_PER_POINT
        body.append(control())
    return (["# nodes: 1,2,3",
             "# W1f: rate checks; N = 4 contention; the capacity-equivalent points, the designs"
             " alternating; rate checks. Node 4 joins later and is not in the Pis' peer check."]
            + rate_checks + body + rate_checks)


# ------------------------------------------------------------------------------- predictions
def _crossing(curve: Mapping[Any, float]) -> float | None:
    """W1c's interpolation at V = 0.95. The per-record grid has fractional N_eq (8.5, 9.5); the
    shared function is annotated for integer N but its arithmetic is the same on floats."""
    return interpolated_crossing(curve, w1b.V_TARGET)


def _job(job: tuple[int, float, int, int]) -> tuple[int, float, int, float]:
    n, fps, mac, seed = job
    r = oq.run(n, fps, w1b.airtime_s(mac), rule=w1b.RULE, seed=seed, difs_s=DSSS_1M.difs_s)
    return n, fps, mac, r.delivered_frac


def predict(workers: int, seeds: int = SEEDS) -> list[dict]:
    rows: list[dict] = []
    for when in ("before", "after"):
        for board in BOARDS.values():
            rows.append({"what": f"rate check {when}", "design": board, "n": 1, "n_eq": "",
                         "fps_per_board": w1d.RATE_CHECK_FPS, "udp_payload": w1d.PAYLOAD_UDP,
                         "offered_load": "", "model": "", "band_lo": w1d.RATE_BAND_S[0],
                         "band_hi": w1d.RATE_BAND_S[1],
                         "note": "every one in the band, or the session is void"})
    for u, fps, loss in registered_contention():
        rows.append({"what": "contention", "design": GROUP, "n": N_BOARDS, "n_eq": "",
                     "fps_per_board": fps, "udp_payload": w1d.PAYLOAD_UDP,
                     "offered_load": round(N_BOARDS * fps * DSSS_1M.t_broadcast(173), 4),
                     "model": loss, "band_lo": round(0.3 * loss, 5),
                     "band_hi": round(1.4 * loss, 5), "note": f"W1c's registered row (u={u})"})
    jobs = [(N_BOARDS, board_rate(d, neq), w1c.DESIGNS[d][0], s)
            for d, neq in points() for s in range(1, seeds + 1)]
    jobs += [(n, w1c.DESIGNS[d][1], w1c.DESIGNS[d][0], s)
             for d, grid in MANY_NODE_GRID.items() for n in grid for s in range(1, seeds + 1)]
    with Pool(workers) as pool:
        got = pool.map(_job, jobs, chunksize=4)
    by: dict[tuple[int, float, int], list[float]] = {}
    for n, f, mac, v in got:
        by.setdefault((n, f, mac), []).append(v)
    curves: dict[str, dict[float, float]] = {}
    for d, neq in sorted(points()):
        f = board_rate(d, neq)
        v = st.mean(by[(N_BOARDS, f, w1c.DESIGNS[d][0])])
        curves.setdefault(d, {})[neq] = v
        rows.append({"what": "capacity-equivalent", "design": d, "n": N_BOARDS, "n_eq": neq,
                     "fps_per_board": round(f, 3), "udp_payload": payload(d),
                     "offered_load": round(offered_load(d, neq), 4), "model": round(v, 5),
                     "band_lo": "", "band_hi": "", "note": label(d, neq)})
    x = {d: _crossing(c) for d, c in curves.items()}
    for d, xd in x.items():
        if xd is None:
            raise SystemExit(f"the {d} grid does not bracket its crossing")
        rows.append({"what": "crossing", "design": d, "n": N_BOARDS, "n_eq": round(xd, 3),
                     "fps_per_board": "", "udp_payload": "", "offered_load":
                     round(offered_load(d, xd), 4), "model": "",
                     "band_lo": round((1 - CROSSING_BAND) * xd, 3),
                     "band_hi": round((1 + CROSSING_BAND) * xd, 3), "note": "four boards"})
    xa, xp = x["AUTHBC"], x["per-record"]
    assert xa is not None and xp is not None
    ratio = xa / xp
    rows.append({"what": "ratio", "design": "AUTHBC/per-record", "n": N_BOARDS,
                 "n_eq": round(ratio, 4), "fps_per_board": "", "udp_payload": "",
                 "offered_load": "", "model": "",
                 "band_lo": round(max((1 - CROSSING_BAND) * ratio, RATIO_FLOOR), 4),
                 "band_hi": round((1 + CROSSING_BAND) * ratio, 4),
                 "note": f"within +-10 % and above {RATIO_FLOOR}"})
    for d, grid in MANY_NODE_GRID.items():
        c = {n: st.mean(by[(n, w1c.DESIGNS[d][1], w1c.DESIGNS[d][0])]) for n in grid}
        xm = _crossing(c)
        rows.append({"what": "many-node crossing (reported)", "design": d, "n": "N_eq",
                     "n_eq": round(xm, 3) if xm is not None else "",
                     "fps_per_board": w1c.DESIGNS[d][1], "udp_payload": payload(d),
                     "offered_load": "", "model": "", "band_lo": "", "band_hi": "",
                     "note": "N_eq real nodes at the design's rate; not scored"})
    return rows


def registered() -> dict[str, dict]:
    """The committed predictions, keyed by 'what' (and design, for crossings and contention)."""
    with PREDICTIONS.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    out: dict[str, dict] = {}
    for r in rows:
        if r["what"] in ("crossing", "ratio"):
            out[f"{r['what']}:{r['design']}"] = r
        elif r["what"] == "contention":
            out[f"contention:{r['fps_per_board']}"] = r
    return out


# ------------------------------------------------------------------------------- scoring
def _complete(parts: dict[str, dict[int, dict]], senders: list[int], nodes: set[int]) -> bool:
    """Every node received and counted the window, and every sender's send record is there."""
    return (nodes <= set(parts.get("rx", {})) and nodes <= set(parts.get("ctr", {}))
            and set(senders) <= set(parts.get("tx", {})))


def window_rows(session: Path, nodes: set[int] | None = None) -> list[dict]:
    """W1d's reducer on the complete windows; incomplete ones listed as unusable, not reduced.

    W1d's reducer is registered and unchanged; it expects every file of a window to exist, so it
    is run on a view of the session holding only complete windows.
    """
    nodes = set(BOARDS) if nodes is None else nodes
    by = w1d._files(session)
    complete: list[str] = []
    missing: list[str] = []
    for tag, parts in sorted(by.items()):
        ctr = parts.get("ctr", {})
        senders = [int(s) for s in next(iter(ctr.values()))["senders"].split(",")] if ctr else []
        (complete if ctr and _complete(parts, senders, nodes) else missing).append(tag)
    with tempfile.TemporaryDirectory() as tmp:
        for path in session.rglob("*_node*_*.json"):
            if any(path.name.endswith(f"_{t}.json") for t in complete):
                link = Path(tmp) / path.parent.name / path.name
                link.parent.mkdir(exist_ok=True)
                link.symlink_to(path.resolve())
        rows = w1d.window_rows(Path(tmp)) if complete else []
    meta = {tag: by[tag].get("ctr", {}).get(TPLINK, {}) for tag in by}
    for r in rows:
        r["complete"] = True
        r |= _node4(meta[r["window"]])
    for tag in missing:
        r = {"window": tag, "label": tag.split("_")[1], "rate_fps":
             float(tag.rsplit("_", 1)[1].removesuffix("fps")), "power_ok": True,
             "complete": False, "usable": False}
        rows.append(r | _node4(meta[tag]))
    return sorted(rows, key=_index)


def _node4(ctr: dict) -> dict:
    return {"boot_before": ctr.get("boot_before", ""), "boot_after": ctr.get("boot_after", ""),
            "bssid": ctr.get("bssid", ""), "rate_ctl": ctr.get("rate_ctl", "")}


def _index(w: dict) -> int:
    return int(w["window"].split("_")[0])


def apply_node4_rules(windows: list[dict]) -> list[dict]:
    """A window counts only with node 4 on its first boot, in the Pis' cell, at 1 Mb/s fixed."""
    boots = [w["boot_before"] for w in windows if w["boot_before"]]
    session_boot = boots[0] if boots else ""
    out = []
    for w in windows:
        ok = (w["complete"] and w["boot_before"] == w["boot_after"] == session_boot != ""
              and not w["bssid"].lower().startswith(OWN_CELL) and w["bssid"] != ""
              and w["rate_ctl"].startswith(RATE_FIXED))
        w = w | {"node4_ok": ok}
        if "usable" in w:
            w["usable"] = bool(w["usable"]) and ok
        out.append(w)
    return out


def sentinels(windows: list[dict]) -> list[dict]:
    rates = [w for w in windows if w1d.RATE_CHECK.fullmatch(w["label"])]
    first = min((_index(w) for w in windows if not w1d.RATE_CHECK.fullmatch(w["label"])),
                default=0)
    out = []
    for w in rates:
        c = w.get("cycle_us", float("nan")) * 1e-6
        out.append({"what": f"rate check {'before' if _index(w) < first else 'after'}",
                    "group": BOARDS[int(w["label"][1:])], "measured": w.get("cycle_us", ""),
                    "predicted": round(1e6 * w1d.STANDARD_CYCLE_S, 1),
                    "band_lo": 1e6 * w1d.RATE_BAND_S[0], "band_hi": 1e6 * w1d.RATE_BAND_S[1],
                    "held": bool(w["power_ok"] and w["node4_ok"])
                    and w1d.RATE_BAND_S[0] <= c <= w1d.RATE_BAND_S[1], "windows": 1})
    return out


def join_checks(meta: dict) -> list[dict]:
    """V3 and V4 at join: node 4 in the Pis' cell (not its own), all three Pis reached, 1 Mb/s."""
    bssid = meta.get("bssid", "")
    reached = sorted(meta.get("peers_reachable", []))
    return [{"what": "node 4 joined the Pis' cell", "group": bssid or "no join record",
             "measured": f"reached {reached}", "predicted": "", "band_lo": "", "band_hi": "",
             "held": bool(bssid) and not bssid.lower().startswith(OWN_CELL)
             and reached == [1, 2, 3], "windows": ""},
            {"what": "node 4 rate fixed at join", "group": meta.get("rate_ctl", ""),
             "measured": "", "predicted": RATE_FIXED, "band_lo": "", "band_hi": "",
             "held": meta.get("rate_ctl", "").startswith(RATE_FIXED), "windows": ""}]


def _crossing_rows(windows: list[dict], b: float) -> tuple[list[dict], dict[str, float | None]]:
    reg = registered()
    rows, x = [], {}
    for design in NEQ_GRID:
        curve: dict[float, float] = {}
        per_n: dict[float, list[float]] = {}
        for neq in NEQ_GRID[design]:
            mine = [w for w in windows if w["label"] == label(design, neq)]
            good = [w for w in mine if w.get("usable")]
            v = [w["delivered_frac"] / (1 - b) for w in good]
            if len(good) >= w1d.MIN_USABLE:
                curve[neq], per_n[neq] = st.mean(v), v
            rows.append({"what": "capacity-equivalent", "group": label(design, neq),
                         "measured": round(st.mean(v), 5) if v else "", "predicted": "",
                         "band_lo": "", "band_hi": "",
                         "held": "scored" if len(good) >= w1d.MIN_USABLE
                         else "not scored (fewer than 3 usable windows)",
                         "windows": f"{len(good)}/{len(mine)}"})
        xs = _crossing(curve) if len(curve) >= 2 else None
        # Reported, not scored. The bootstrap resamples every point equally, so it needs the same
        # number of usable windows at each; with fewer at any point it is not computed.
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
                     if ci else "CI not computed (unequal usable windows per point)"
                     if per_n and not equal else ""})
    r = reg["ratio:AUTHBC/per-record"]
    xa, xp = x["AUTHBC"], x["per-record"]
    ratio = xa / xp if xa is not None and xp is not None else None
    rows.append({"what": "ratio", "group": "AUTHBC/per-record",
                 "measured": round(ratio, 4) if ratio is not None else "",
                 "predicted": float(r["n_eq"]), "band_lo": float(r["band_lo"]),
                 "band_hi": float(r["band_hi"]),
                 "held": (float(r["band_lo"]) <= ratio <= float(r["band_hi"]))
                 if ratio is not None else "not determined", "windows": ""})
    return rows, x


def score(windows: list[dict], meta: dict) -> list[dict]:
    """W1f-1 the bracket, W1f-2 the background, W1f-3 contention, W1f-4 crossings, W1f-5 ratio.

    Valid only if all eight rate checks are present and in the band, the background holds, and
    node 4 joined the Pis' cell at 1 Mb/s fixed (V1-V4). Otherwise every scored row is marked void.
    """
    marks = sentinels(windows)
    joins = join_checks(meta)
    controls = [w["loss"] for w in windows if w1d.CONTROL.fullmatch(w["label"])
                and w["power_ok"] and w["node4_ok"] and "loss" in w]
    b = st.mean(controls) if controls else float("nan")
    background = {"what": "background", "group": "controls", "measured": round(b, 6),
                  "predicted": "", "band_lo": "", "band_hi": w1d.BACKGROUND_STOP,
                  "held": b <= w1d.BACKGROUND_STOP, "windows": len(controls)}
    valid = (len(marks) == 2 * N_BOARDS and all(m["held"] is True for m in marks)
             and background["held"] is True and all(j["held"] is True for j in joins))
    scored: list[dict] = []
    reg = registered()
    for _u, fps, _loss in registered_contention():
        r = reg[f"contention:{fps}"]
        mine = [w for w in windows if w["label"] == GROUP and w["rate_fps"] == fps]
        good = [w for w in mine if w.get("usable")]
        loss = (st.mean(1 - w["delivered_frac"] for w in good) - b) if good else float("nan")
        enough = len(good) >= w1d.MIN_USABLE
        scored.append({"what": "contention", "group": f"{GROUP} at {fps}/s",
                       "measured": round(loss, 6) if good else "",
                       "predicted": float(r["model"]), "band_lo": float(r["band_lo"]),
                       "band_hi": float(r["band_hi"]),
                       "held": (float(r["band_lo"]) <= loss <= float(r["band_hi"])) if enough
                       else "not scored (fewer than 3 usable windows)",
                       "windows": f"{len(good)}/{len(mine)}"})
    crossing_rows, _x = _crossing_rows(windows, b)
    scored += crossing_rows
    head = [{"what": "session", "group": "valid" if valid else "VOID", "measured": "",
             "predicted": "", "band_lo": "", "band_hi": "", "held": valid,
             "windows": len(windows)}]
    if not valid:
        scored = [r | {"held": f"void (session): {r['held']}"} for r in scored]
    return head + joins + marks + [background] + scored


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"boards": BOARDS, "neq_grid": NEQ_GRID, "many_node_grid": MANY_NODE_GRID,
              "seeds": SEEDS, "windows_per_point": WINDOWS_PER_POINT,
              "crossing_band": CROSSING_BAND, "ratio_floor": RATIO_FLOOR, "own_cell": OWN_CELL,
              "rate_fixed": RATE_FIXED, "rate_band_s": w1d.RATE_BAND_S,
              "background_stop": w1d.BACKGROUND_STOP, "min_usable": w1d.MIN_USABLE}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    fields = list(dict.fromkeys(k for r in rows for k in r))
    w = csv.DictWriter(buf, fieldnames=fields, restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue())


def load_meta(session: Path) -> dict:
    path = next(iter(session.rglob("meta_node4_join.json")), None)
    return json.loads(path.read_text()) if path else {}


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
        _write(PREDICTIONS, rows, "w1f_predictions")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))
    else:
        windows = apply_node4_rules(window_rows(args.score))
        _write(w1d.HW / f"{args.score.name}_windows.csv", windows, "w1f_windows")
        rows = score(windows, load_meta(args.score))
        _write(w1d.RAW / f"w1f_{args.score.name}.csv", rows, "w1f")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
