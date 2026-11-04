#!/usr/bin/env python3
"""W1c: the predictions for the 2.4 GHz hardware campaign, registered before any board session.

predictions/W1c.md. Five boards (two Pi 4, a Pi 3 Model B, two BeagleBone Blue) in one ad-hoc cell
at 2.4 GHz, broadcasting at 802.11b's 1 Mb/s. The model is the one W1b tested against ns-3 at that
PHY (`dsss_campaign.RULE`, F119): it predicted ns-3's crossings within 1 %, and five stations stand
for many up to the crossing. Every grid point here stays below overload, where W1b showed that a
queue's discard policy, not the access rule, decides delivery.

    python analysis/dsss_hardware.py   -> results/raw/w1c_predictions.csv
"""
from __future__ import annotations

import csv
import io
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_campaign as w1b  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models.phy import DSSS_1M  # noqa: E402
from authbc.sim import dcf_own_queue as oq  # noqa: E402

OUT = REPO / "results" / "raw" / "w1c_predictions.csv"
SEEDS = 30
UDP_IP_BYTES = 28                   # the boards send UDP; ns-3's frames are MAC payload
DESIGNS = {"AUTHBC": (173, 12.5), "per-record": (146, 50.0)}   # MAC payload, frames/s per node
BOARDS = 5
OCCUPANCY = (0.50, 0.70, 0.85)
NODES = (2, 3, 4, 5)
NEQ_GRID = {"AUTHBC": (22, 26, 30, 34), "per-record": (6, 7, 8, 9, 10)}
RATE_CHECK_OFFERED = 600            # frames/s offered to one board alone: beyond saturation
OTHER_RATES_BPS = (2e6, 5.5e6, 11e6)   # what the rate check must tell 1 Mb/s apart from


def udp_payload(mac_payload: int) -> int:
    return mac_payload - UDP_IP_BYTES


def cycle_s(rate_bps: float, mac_payload: int) -> float:
    """One saturated sender's mean frame-to-frame time under the standard rule at a DSSS rate."""
    ppdu = DSSS_1M.plcp_s + 8.0 * (mac_payload + 36) / rate_bps
    return ppdu + DSSS_1M.difs_s + (DSSS_1M.w0 - 1) / 2 * DSSS_1M.slot_s


def occupancy_rate(n: int, u: float, mac_payload: int) -> int:
    """Frames/s per board that fill `u` of the medium among `n` boards (F70's definition)."""
    return round(u / (n * DSSS_1M.t_broadcast(mac_payload)))


def board_rate(design: str, neq: int) -> float:
    """A12's mapping inverted: five boards at this rate stand for `neq` nodes at the design's."""
    return (neq - 1) * DESIGNS[design][1] / (BOARDS - 1)


def offered_load(design: str, neq: int) -> float:
    mac, _f = DESIGNS[design]
    return BOARDS * board_rate(design, neq) * DSSS_1M.t_broadcast(mac)


def _job(job: tuple[int, float, int, int]) -> tuple[int, float, int, float]:
    n, fps, mac, seed = job
    r = oq.run(n, fps, w1b.airtime_s(mac), rule=w1b.RULE, seed=seed, difs_s=DSSS_1M.difs_s)
    return n, fps, mac, r.delivered_frac


def predict(workers: int) -> list[dict]:
    rows: list[dict] = []
    for name, rate in (("1 Mb/s", 1e6), *((f"{r / 1e6:g} Mb/s", r) for r in OTHER_RATES_BPS)):
        rows.append({"what": "rate check", "design": "AUTHBC frame", "n": 1, "u": "", "n_eq": "",
                     "fps_per_board": RATE_CHECK_OFFERED,
                     "udp_payload": udp_payload(173), "offered_load": "",
                     "model_delivered": "", "model_loss": "",
                     "note": f"{name}: cycle {1e6 * cycle_s(rate, 173):.0f} us"})
    jobs = []
    contention = [(n, u, occupancy_rate(n, u, 173)) for n in NODES for u in OCCUPANCY]
    jobs += [(n, float(f), 173, s) for n, _u, f in contention for s in range(1, SEEDS + 1)]
    equiv = [(d, neq, board_rate(d, neq)) for d in DESIGNS for neq in NEQ_GRID[d]]
    jobs += [(BOARDS, f, DESIGNS[d][0], s) for d, _neq, f in equiv for s in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_job, jobs, chunksize=10)
    by: dict[tuple[int, float, int], list[float]] = {}
    for n, f, mac, d in got:
        by.setdefault((n, f, mac), []).append(d)
    for n, u, f in contention:
        d = st.mean(by[(n, float(f), 173)])
        rows.append({"what": "contention", "design": "AUTHBC frame", "n": n, "u": u, "n_eq": "",
                     "fps_per_board": f, "udp_payload": udp_payload(173),
                     "offered_load": round(n * f * DSSS_1M.t_broadcast(173), 4),
                     "model_delivered": round(d, 5), "model_loss": round(1 - d, 5),
                     "note": "band 0.6-1.4x loss" if n == 2 else "band 0.3-1.4x loss"})
    curves: dict[str, dict[int, float]] = {}
    for d, neq, f in equiv:
        v = st.mean(by[(BOARDS, f, DESIGNS[d][0])])
        curves.setdefault(d, {})[neq] = v
        rows.append({"what": "capacity-equivalent", "design": d, "n": BOARDS, "u": "",
                     "n_eq": neq, "fps_per_board": round(f, 3),
                     "udp_payload": udp_payload(DESIGNS[d][0]),
                     "offered_load": round(offered_load(d, neq), 4),
                     "model_delivered": round(v, 5), "model_loss": round(1 - v, 5), "note": ""})
    x = {d: interpolated_crossing(c, w1b.V_TARGET) for d, c in curves.items()}
    if any(v is None for v in x.values()):
        raise SystemExit("a capacity-equivalent grid does not bracket its crossing")
    for d, v in x.items():
        rows.append({"what": "crossing", "design": d, "n": BOARDS, "u": "", "n_eq": round(v, 2),
                     "fps_per_board": "", "udp_payload": "", "offered_load": "",
                     "model_delivered": "", "model_loss": "",
                     "note": f"band {0.9 * v:.2f}-{1.1 * v:.2f}"})
    ratio = x["AUTHBC"] / x["per-record"]
    rows.append({"what": "ratio", "design": "AUTHBC/per-record", "n": BOARDS, "u": "",
                 "n_eq": round(ratio, 3), "fps_per_board": "", "udp_payload": "",
                 "offered_load": "", "model_delivered": "", "model_loss": "",
                 "note": f"band {0.9 * ratio:.3f}-{1.1 * ratio:.3f}"})
    return rows


def _write(rows: list[dict]) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "designs": DESIGNS, "occupancy": OCCUPANCY, "nodes": NODES,
              "neq_grid": NEQ_GRID, "boards": BOARDS, "phy": DSSS_1M.name,
              "rate_check_offered": RATE_CHECK_OFFERED}
    for k, v in {**provenance.env_block(), "run": "w1c_predictions",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    rows = predict(workers)
    _write(rows)
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
