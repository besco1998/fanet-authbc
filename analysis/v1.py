#!/usr/bin/env python3
"""V1a — the closed form as stated, tested on the hardware directly (predictions/V1a.md).

Decided by Mohamed on 2026-11-28 (docs/DECISIONS.md, "fixing the model report's three open
issues"). No hardware session so far has scored the closed form: W1e, W1j and W1k were predicted by
W1c's event simulation, and W1r only recorded the closed form's values. On three radios the part
of the closed form that applies is the finite-station form (N = 3 to 5, occupancy at most 0.5,
`authbc.models.finite_station`), at the standard's window W = 32 and rule set A. V1a scores it as
stated, with nothing taken from the radios but the airtime the model already uses.

* **The session:** the trio (pi-A, pi-B, the Pi 3), 802.11b at 1 Mb/s, the 145 B UDP frame (ns-3
  frameSize 173), each frame at an instant drawn anew in its period; occupancy 0.3, 0.4 and 0.5 at
  W1c's rates (`dsss_hardware.occupancy_rate`). Five rounds; each round holds one window at every
  occupancy, in rotated order, then a control window (one board alone at 50 frames/s). A rate check
  per board before and after.
* **Each window is sized** so that a point's five windows expect at least `MIN_LOST_POINT` lost
  receptions (three senders, two receivers each) under the lowest of the candidate predictions.
* **The loss, as W1d defined it** (`dsss_three.window_rows`): the trio's frames received by the
  other two boards, over frames sent times two, less the background from the control windows.
* **Scored:** the finite-station form within ±15 % of the measured loss at each point (U-FS's
  tolerance). **Reported:** (G5) and (G25) at W = 32, ns-3 with the standard rule (W = 32 for
  every board, equal power, 30 seeds × 100 s) and W1c's event simulation with the standard rule.

    python analysis/v1.py --predict
        -> results/raw/v1a_predictions.csv and experiments/channel24/plan_v1a.txt
    python analysis/v1.py --score results/hw/channel24/<session>   -> results/raw/v1a_<session>.csv
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

import dsss_hardware as w1c  # noqa: E402
import dsss_three as w1d  # noqa: E402
import w1r  # noqa: E402

from authbc.bench import provenance  # noqa: E402

NODES = (1, 2, 3)
GROUP = "ABC"
OCCUPANCY = (0.3, 0.4, 0.5)
POINTS: list[tuple[float, int]] = [(u, w1c.occupancy_rate(3, u, w1r.FRAME)) for u in OCCUPANCY]
ROUNDS = 5
MIN_LOST_POINT = 400
POWER_MBM = 1500
TOL = 0.15
SEEDS = range(1, 31)
OUT = REPO / "results" / "raw" / "v1a_predictions.csv"
PLAN = w1d.PLANS / "plan_v1a.txt"


def _ns3(job: tuple[int, int]) -> float:
    """One ns-3 run of the trio, the standard rule (W = 32 for every board), equal power."""
    fps, seed = job
    import run_unified as ru
    from ns3_paths import ns3_root

    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "r"
        args = [
            str(exe),
            f"--nNodes={len(NODES)}",
            f"--simTime={w1r.SIM_S}",
            f"--seed={seed}",
            f"--outPrefix={pre}",
            *ru.Cell(w1r.FRAME, float(fps), "80211b", "DsssRate1Mbps").args(),
        ]
        ru.run_checked(args, env)
        total = dict(csv.reader(pre.with_suffix(".csv").read_text().splitlines()[1:]))
    return 1 - float(total["delivered_frac"])


def _event(job: tuple[int, int]) -> float:
    """One run of W1c's event simulation (the standard rule at 802.11b), the trio at `fps`."""
    fps, seed = job
    return 1 - w1c._job((len(NODES), float(fps), w1r.FRAME, seed))[3]


def window_seconds(fps: int, p_min: float) -> int:
    """A window's length: the point's ROUNDS windows expect MIN_LOST_POINT lost receptions
    (three senders, two receivers) at p_min, over the sender's seconds − 3 of sending."""
    need = 3 + MIN_LOST_POINT / (ROUNDS * len(NODES) * (len(NODES) - 1) * fps * p_min)
    return max(25, 5 * math.ceil(need / 5))


def predict(workers: int = 10) -> list[dict[str, Any]]:
    jobs = [(fps, s) for _u, fps in POINTS for s in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        ns3 = dict(zip(jobs, ex.map(_ns3, jobs), strict=True))
        event = dict(zip(jobs, ex.map(_event, jobs), strict=True))
    rows = []
    for u, fps in POINTS:
        closed = w1r._closed(len(NODES), fps)
        row: dict[str, Any] = {
            "group": GROUP,
            "u": u,
            "fps_per_board": fps,
            "finite_w32": closed["finite_w32"],
            "g5_w32": closed["g5_w32"],
            "g25_w32": closed["g25_w32"],
        }
        v = [ns3[(fps, s)] for s in SEEDS]
        row |= {"ns3_standard": st.mean(v), "ns3_standard_se": st.stdev(v) / math.sqrt(len(v))}
        e = [event[(fps, s)] for s in SEEDS]
        row |= {"event_standard": st.mean(e), "event_standard_se": st.stdev(e) / math.sqrt(len(e))}
        p_min = min(float(str(row[k])) for k in ("finite_w32", "ns3_standard", "event_standard"))
        row |= {"p_min": p_min, "seconds": window_seconds(fps, p_min)}
        row["expected_lost_point"] = (
            ROUNDS * len(NODES) * (len(NODES) - 1) * fps * (row["seconds"] - 3) * p_min
        )
        rows.append(row)
    return rows


def plan(rows: list[dict[str, Any]]) -> list[str]:
    """Rate checks, five rounds of one window per occupancy (rotated) and a control, rate checks."""
    sec = {int(r["fps_per_board"]): int(r["seconds"]) for r in rows}
    checks = [f"R{n} {w1d.RATE_CHECK_FPS} {w1d.PAYLOAD_UDP} {n} 25" for n in NODES]
    # every board at 15 dBm from the first window on, as C1 (the kit's sixth field: node:mBm)
    first = [checks[0] + " " + ",".join(f"{n}:{POWER_MBM}" for n in NODES), *checks[1:]]
    body = []
    for k in range(ROUNDS):
        order = POINTS[k % len(POINTS) :] + POINTS[: k % len(POINTS)]
        for _u, fps in order:
            body.append(f"{GROUP} {fps} {w1d.PAYLOAD_UDP} {','.join(map(str, NODES))} {sec[fps]}")
        node = NODES[k % len(NODES)]
        body.append(f"B{node} {w1d.CONTROL_FPS} {w1d.PAYLOAD_UDP} {node} 25")
    return (
        [
            "# nodes: 1,2,3",
            "# V1a: the trio at occupancy 0.3, 0.4 and 0.5, five rounds,"
            " a control after each (analysis/v1.py)",
        ]
        + first
        + body
        + checks
    )


def _predictions() -> dict[int, dict[str, str]]:
    with OUT.open() as fh:
        return {
            int(r["fps_per_board"]): r
            for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
        }


def score(session: Path) -> list[dict[str, Any]]:
    """V1a as registered: validity, then the finite-station form against each point's loss."""
    import hw_session as hs

    windows = w1d.window_rows(session)
    out: list[dict[str, Any]] = [
        {
            "what": "frame burst off on every board",
            "item": "",
            "measured": "",
            "predicted": "0 before and after",
            "held": hs.frameburst_off(session),
        }
    ]
    for w in windows:
        if w["label"] in ("R1", "R2", "R3"):
            c = w["cycle_us"] * 1e-6
            out.append(
                {
                    "what": "rate check",
                    "item": w["window"],
                    "measured": w["cycle_us"],
                    "predicted": "1900-2600 us",
                    "held": w1d.RATE_BAND_S[0] <= c <= w1d.RATE_BAND_S[1],
                }
            )
    controls = [w for w in windows if w1d.CONTROL.fullmatch(w["label"]) and w["power_ok"]]
    b = st.mean(w["loss"] for w in controls)
    out.append(
        {
            "what": "background b",
            "item": f"{len(controls)} controls",
            "measured": round(b, 6),
            "predicted": f"<= {w1d.BACKGROUND_STOP}",
            "held": b <= w1d.BACKGROUND_STOP,
        }
    )
    for n in NODES:
        mine = [w["loss"] for w in controls if w["label"] == f"B{n}"]
        out.append(
            {
                "what": "link loss alone",
                "item": w1d.BOARDS[n],
                "measured": round(max(mine), 6) if mine else "",
                "predicted": "<= 0.01",
                "held": bool(mine) and max(mine) <= 0.01,
            }
        )
    pred = _predictions()
    for u, fps in POINTS:
        mine = [w for w in windows if w["label"] == GROUP and w["rate_fps"] == fps]
        good = [w for w in mine if w.get("usable")]
        p = pred[fps]
        row: dict[str, Any] = {"what": "point", "item": f"{GROUP} at {fps}/s (u = {u})"}
        if len(good) < w1r.MIN_USABLE:
            out.append(
                row
                | {
                    "measured": f"{len(good)}/{len(mine)} usable",
                    "predicted": "",
                    "held": "not scored (fewer than 3 usable windows)",
                }
            )
            continue
        loss = [1 - w["delivered_frac"] - b for w in good]
        m = st.mean(loss)
        h = w1r.T975[len(loss)] * st.stdev(loss) / math.sqrt(len(loss))
        fin = float(p["finite_w32"])
        row["measured"] = f"{m:.5f} ({m - h:.5f}-{m + h:.5f}); {len(good)} windows"
        row["predicted"] = (
            f"finite {fin:.5f} ({100 * (fin / m - 1):+.1f} %); "
            f"G5 {float(p['g5_w32']):.5f}; G25 {float(p['g25_w32']):.5f}; "
            f"ns-3 {float(p['ns3_standard']):.5f}; "
            f"event {float(p['event_standard']):.5f}"
        )
        row["held"] = abs(fin - m) <= TOL * m
        out.append(row)
    return out


def _write(rows: list[dict[str, Any]], path: Path, run: str) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run}.items():
        buf.write(f"# {k}={v}\n")
    wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    path.write_text(buf.getvalue())


def markdown() -> str:
    """The registration's prediction table, from the predictions file (never typed)."""
    lines = [
        "| u | frames/s per board | **finite-station, W = 32** | (G5) | (G25) | ns-3, standard "
        "(± s.e.) | event simulation, standard (± s.e.) | window (s) | expected lost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for fps, r in sorted(_predictions().items()):
        lines.append(
            f"| {float(r['u']):g} | {fps} | **{100 * float(r['finite_w32']):.3f} %** | "
            f"{100 * float(r['g5_w32']):.3f} % | {100 * float(r['g25_w32']):.3f} % | "
            f"{100 * float(r['ns3_standard']):.3f} ± {100 * float(r['ns3_standard_se']):.3f} % | "
            f"{100 * float(r['event_standard']):.3f} ± {100 * float(r['event_standard_se']):.3f} % "
            f"| {r['seconds']} | {float(r['expected_lost_point']):.0f} |"
        )
    return "\n".join(lines)


def main() -> None:
    if "--markdown" in sys.argv:
        print(markdown())
        return
    if "--plan" in sys.argv:  # the plan again from the stored predictions, without new runs
        lines = plan(list(_predictions().values()))
        PLAN.write_text("\n".join(lines) + "\n")
        print(f"plan: {PLAN.relative_to(REPO)}, {w1r.board_seconds(lines) / 60:.1f} min")
        return
    if "--score" in sys.argv:
        session = Path(sys.argv[sys.argv.index("--score") + 1])
        rows = score(session)
        _write(rows, REPO / "results" / "raw" / f"v1a_{session.name}.csv", f"v1a_{session.name}")
        for r in rows:
            print(r)
        return
    if "--predict" in sys.argv:
        rows = predict()
        _write(rows, OUT, "v1a_predictions")
        lines = plan(rows)
        PLAN.write_text("\n".join(lines) + "\n")
        for r in rows:
            print(r)
        print(f"plan: {PLAN.relative_to(REPO)}, {w1r.board_seconds(lines) / 60:.1f} min")
        return
    for u, fps in POINTS:
        print(u, fps, w1r._closed(len(NODES), fps))


if __name__ == "__main__":
    main()
