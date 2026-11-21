#!/usr/bin/env python3
"""W1r — session 2 of the 2026-11-20 session plans: W1e's contention windows again, frame burst
off, side by side (predictions/W1r.md; approved by Mohamed 2026-11-21, docs/DECISIONS.md).

W1e (2026-11-05) ran at the driver's default, frame burst on (F75), and U-H could not reproduce it
(`uh.flags`: 1.4–9.3 % chance that a board holds two frames). This session repeats W1e's groups
with frame burst off, so ns-3, which has no frame burst for broadcast, can be compared.

* **The windows:** W1e's (`dsss_w1e.plan`, W1d's groups AB, AC, BC and ABC at occupancy 0.50, 0.70
  and 0.85, four windows each, a control window after every four, a rate check per board before
  and after). **Each window is sized** (Mohamed, 2026-11-21) so that every sender's expected lost
  frames are at least 25 under the lowest prediction of any candidate: the sender sends for
  seconds − 3, so seconds = max(25, 3 + 25 / (f · p_min)), rounded up to 5 s.
* **The loss, as W1d defined it** (`dsss_three.window_rows`, registered): a group's frames received
  by the group's other members, over frames sent times (n − 1). The silent third board is not a
  receiver of a pair. So at N = 2 capture cannot occur, and only the trio has two capture ends.
* **ns-3,** 30 seeds × 100 s per cell: the two slot/DIFS families of U-H with each board's window
  from its one-sender cycle (`uh.board_windows`), equal power, and for the trio also the assumed
  channel (Rayleigh per frame, ns-3's capture model). W1p's registered rule picks the family.
* **Closed forms,** reported, at the standard's W = 32: (G5), (G25), and the finite-station form
  where Mohamed accepted it (N = 3, u ≤ 0.5).

    python analysis/w1r.py --predict
        -> results/raw/w1r_predictions.csv and experiments/channel24/plan_w1r.txt
    python analysis/w1r.py --score results/hw/channel24/<session> --family <W1p's choice | none>
"""
from __future__ import annotations

import csv
import io
import math
import os
import statistics as st
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "ns3"))

import dsss_three as w1d  # noqa: E402
import uh  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import finite_station as fs  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

FRAME = uh.W1F_FRAME                 # ns-3 frameSize 173: the 145 B UDP frame
SIM_S = 100.0
SEEDS = range(1, 31)
MIN_LOST = 25                        # Mohamed, 2026-11-21: per sender, per window
WINDOWS_PER_POINT = 4
OUT = REPO / "results" / "raw" / "w1r_predictions.csv"
PLAN = w1d.PLANS / "plan_w1r.txt"
CAPTURE = {"equal": (), "rayleigh_capture": ("--nakagamiM=1", "--captureMarginDb=5")}


def points() -> list[tuple[str, tuple[int, ...], float, int]]:
    """(group, nodes, occupancy, frames/s per board) in W1d's order."""
    reg = w1d.registered_contention()
    out = []
    for i in range(3):
        for name, nodes in w1d.GROUPS.items():
            u, fps, _loss = sorted(reg[len(nodes)])[i]
            out.append((name, nodes, u, fps))
    return out


def _run(job: tuple[str, str, tuple[int, ...], int, int]) -> dict[str, Any]:
    family, end, nodes, fps, seed = job
    import run_unified as ru
    from ns3_paths import ns3_root
    slot, _difs = uh.FAMILIES[family]
    w = [uh.board_windows(family)[k - 1] for k in nodes]
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "r"
        args = [str(exe), f"--nNodes={len(nodes)}", f"--simTime={SIM_S}", f"--seed={seed}",
                f"--outPrefix={pre}", *ru.Cell(FRAME, float(fps), "80211b", "DsssRate1Mbps").args(),
                "--cwMinList=" + ",".join(str(x - 1) for x in w), "--perNode=1", *CAPTURE[end]]
        if slot != 20e-6:
            args.append(f"--slotUs={round(slot * 1e6)}")
        ru.run_checked(args, env)
        with Path(f"{pre}_nodes.csv").open() as fh:
            per = [1 - float(r["delivered_frac"]) for r in csv.DictReader(fh)]
        total = dict(csv.reader(pre.with_suffix(".csv").read_text().splitlines()[1:]))
    return {"family": family, "end": end, "nodes": nodes, "fps": fps, "seed": seed,
            "loss": 1 - float(total["delivered_frac"]), "per_sender": per}


def _closed(n: int, fps: int) -> dict[str, float | str]:
    tf = uc.airtime_s(phy.DSSS_1M, FRAME)
    acc = uc.A80211B
    u = n * fps * tf
    finite = fs.loss(n, float(fps), tf, acc) if (3 <= n <= 5 and u <= 0.5 + 1e-9) else ""
    return {"g5_w32": uc.loss((n - 1) * fps, tf, acc),
            "g25_w32": pc.loss_periodic(n, float(fps), tf, acc), "finite_w32": finite}


def seconds_for(fps: int, p_min: float) -> int:
    """The window length that gives each sender MIN_LOST expected lost frames at p_min."""
    need = 3 + MIN_LOST / (fps * p_min)
    return max(25, 5 * math.ceil(need / 5))


def predict(workers: int = 10) -> list[dict[str, Any]]:
    jobs = [(f, e, nodes, fps, s) for f in uh.FAMILIES for (_g, nodes, _u, fps) in points()
            for e in (CAPTURE if len(nodes) == 3 else ("equal",)) for s in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        runs = list(ex.map(_run, jobs))
    rows = []
    for g, nodes, u, fps in points():
        row: dict[str, Any] = {"group": g, "nodes": ",".join(map(str, nodes)), "u": u,
                               "fps_per_board": fps}
        low = math.inf
        for f in uh.FAMILIES:
            for e in (CAPTURE if len(nodes) == 3 else ("equal",)):
                v = [r for r in runs if (r["family"], r["end"], r["nodes"], r["fps"])
                     == (f, e, nodes, fps)]
                key = f"{f}_{e}"
                row[f"ns3_{key}"] = st.mean(r["loss"] for r in v)
                row[f"ns3_{key}_se"] = st.stdev(r["loss"] for r in v) / math.sqrt(len(v))
                per = [st.mean(r["per_sender"][k] for r in v) for k in range(len(nodes))]
                row[f"ns3_{key}_per_sender"] = " ".join(f"{p:.5f}" for p in per)
                low = min(low, *per)
        row |= _closed(len(nodes), fps)
        row["p_min"] = low
        row["seconds"] = seconds_for(fps, low)
        row["expected_lost_min"] = fps * (row["seconds"] - 3) * low
        rows.append(row)
    return rows


def plan(rows: list[dict[str, Any]]) -> list[str]:
    """W1e's windows with W1r's lengths: rate checks, the sized contention windows and controls."""
    sec = {(r["group"], int(r["fps_per_board"])): int(r["seconds"]) for r in rows}
    checks = [f"R{n} {w1d.RATE_CHECK_FPS} {w1d.PAYLOAD_UDP} {n} 25" for n in w1d.BOARDS]
    body = []
    for ln in w1d.plan_s1():
        if ln.startswith("#"):
            continue
        label, fps, payload, senders = ln.split()
        s = sec.get((label, int(fps)), 25)
        body.append(f"{label} {fps} {payload} {senders} {s}")
    return (["# nodes: 1,2,3", "# W1r: W1e's windows, frame burst off, each contention window"
             " sized for >= 25 expected lost frames per sender (analysis/w1r.py)"]
            + checks + body + checks)


def board_seconds(lines: list[str]) -> int:
    """The plan's length on the boards: each window's seconds plus the runner's 5 s gap."""
    return sum(int(ln.split()[4]) + 5 for ln in lines if not ln.startswith("#"))


MIN_USABLE = 3
T975 = {3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}       # Student t, 97.5 %, by windows (n − 1 df)


def _predictions() -> dict[tuple[str, int], dict[str, str]]:
    with OUT.open() as fh:
        return {(r["group"], int(r["fps_per_board"])): r for r in csv.DictReader(
            ln for ln in fh if not ln.startswith("#"))}


def _lost_per_sender(files: dict[str, Any], tag: str, nodes: list[int]) -> int:
    """The fewest lost frames of any sender in the window, counted at the group's receivers
    (sent × (n − 1) less receptions, over n − 1)."""
    rx, tx = files[tag]["rx"], files[tag]["tx"]
    out = []
    for s in nodes:
        got = sum(rx[r]["by_source"].get(f"10.0.0.{s}", {}).get("received_unique", 0)
                  for r in nodes if r != s)
        out.append((tx[s]["sent"] * (len(nodes) - 1) - got) / (len(nodes) - 1))
    return round(min(out))


def score(session: Path, family: str | None) -> list[dict[str, Any]]:
    """W1r as registered. `family`: W1p's choice, or None when W1p chose none (or both), and then
    every point is reported against both and nothing is scored."""
    import hw_session as hs
    windows = w1d.window_rows(session)
    files = w1d._files(session)
    out: list[dict[str, Any]] = [{"what": "frame burst off on every board", "item": "",
                                  "measured": "", "predicted": "0 before and after",
                                  "held": hs.frameburst_off(session)}]
    for w in windows:
        if w["label"] in ("R1", "R2", "R3"):
            c = w["cycle_us"] * 1e-6
            out.append({"what": "rate check", "item": w["window"], "measured": w["cycle_us"],
                        "predicted": "1900-2600 us",
                        "held": w1d.RATE_BAND_S[0] <= c <= w1d.RATE_BAND_S[1]})
    controls = [w["loss"] for w in windows if w1d.CONTROL.fullmatch(w["label"]) and w["power_ok"]]
    b = st.mean(controls)
    out.append({"what": "background b", "item": f"{len(controls)} controls", "measured":
                round(b, 6), "predicted": f"<= {w1d.BACKGROUND_STOP}",
                "held": b <= w1d.BACKGROUND_STOP})
    pred = _predictions()
    consistent = scored = 0
    for g, nodes, u, fps in points():
        mine = [w for w in windows if w["label"] == g and w["rate_fps"] == fps]
        good = [w for w in mine if w.get("usable")]
        lost = [_lost_per_sender(files, w["window"], list(nodes)) for w in mine]
        row: dict[str, Any] = {"what": "point", "item": f"{g} at {fps}/s (u = {u})"}
        p = pred[(g, fps)]
        fams = [family] if family else list(uh.FAMILIES)
        ends = list(CAPTURE) if len(nodes) == 3 else ["equal"]
        ns3 = {f: [float(p[f"ns3_{f}_{e}"]) for e in ends] for f in fams}
        if len(good) < MIN_USABLE:
            row |= {"measured": f"{len(good)}/{len(mine)} usable", "predicted": "",
                    "held": "not scored (fewer than 3 usable windows)"}
            out.append(row)
            continue
        loss = [1 - w["delivered_frac"] - b for w in good]
        m = st.mean(loss)
        h = T975[len(loss)] * st.stdev(loss) / math.sqrt(len(loss))
        row["measured"] = (f"{m:.5f} ({m - h:.5f}-{m + h:.5f}); fewest lost frames per sender "
                           f"per window {min(lost)}")
        row["predicted"] = "; ".join(
            f"{f}: {' to '.join(f'{v:.5f}' for v in ns3[f])} (hardware ÷ ns-3 "
            f"{' / '.join(f'{m / v:.2f}' for v in ns3[f])})" for f in fams)
        if family:
            lo, hi = min(ns3[family]), max(ns3[family])
            ok = lo <= m + h and hi >= m - h
            consistent += ok
            scored += 1
            row["held"] = ok
        else:
            row["held"] = "reported (W1p chose no single family)"
        out.append(row)
    out.append({"what": "points consistent", "item": family or "none", "measured":
                f"{consistent} of {scored}", "predicted": "", "held": "reported"})
    return out


def main() -> None:
    if "--score" in sys.argv:
        session = Path(sys.argv[sys.argv.index("--score") + 1])
        fam = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else None
        rows = score(session, None if fam in (None, "none") else fam)
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": f"w1r_{session.name}",
                     "family": fam or "none"}.items():
            buf.write(f"# {k}={v}\n")
        wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
        (REPO / "results" / "raw" / f"w1r_{session.name}.csv").write_text(buf.getvalue())
        print(buf.getvalue())
        return
    if "--predict" in sys.argv:
        rows = predict()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "w1r_predictions",
                     "ns3": "3.48 (authbc-links-audit)", "seeds": "1-30", "sim_s": SIM_S,
                     "frame_size": FRAME, "min_lost": MIN_LOST}.items():
            buf.write(f"# {k}={v}\n")
        wr = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                            lineterminator="\n", restval="")
        wr.writeheader()
        wr.writerows(rows)
        OUT.write_text(buf.getvalue())
        lines = plan(rows)
        PLAN.write_text("\n".join(lines) + "\n")
        print(buf.getvalue())
        print(f"plan: {len(lines) - 2} windows, {board_seconds(lines) / 60:.1f} min on the boards")


if __name__ == "__main__":
    main()
