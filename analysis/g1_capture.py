#!/usr/bin/env python3
"""G1 (work package G of `docs/prompts/NEXT_PHASE_PROMPT.md`): capture on the hardware, estimated
from existing logs only. A lower bound needing no model.

**What the logs hold:** per window, each sender's frames sent and each receiver's frames received
by source. There are no per-frame sequence lists, timestamps or RSSI
(`hw/channel/bcast_rx.py` kept only counts), so single capture events cannot be seen.

**The estimator,** fixed before it was computed:
* **link loss** ℓ_ij of sender j at receiver i: from the session's single-sender windows at 60
  frames/s or less (the backgrounds), pooled;
* in each usable window with two or more senders, sender j's loss at receiver i is
  L_ij = 1 − received_ij/sent_j, and its collision-attributable part is c_ij = L_ij − ℓ_ij;
* **without capture,** a collision destroys j's frame at every receiver alike, so c_ij is the
  same at every receiver. **D_j = max_i c_ij − min_i c_ij** is then a lower bound on the share of
  j's frames lost at some receiver and received at another;
* **the confound:** a receiver that drops frames itself (F123's reading of the low-load excess)
  also raises D. It drops every sender's frames, so the double difference
  DD = (c_ij − c_kj) − (c_im − c_km), over two senders j, m and two receivers i, k, cancels it.
  The largest |DD| per window is reported beside D;
* the bands are kept apart: these are the 2.4 GHz sessions. At 5 GHz the only sessions are two
  boards, each the other's only receiver, so no frame can be received at one receiver and lost
  at another.

    python analysis/g1_capture.py          -> results/raw/g1_capture.csv
    python analysis/g1_capture.py --null   -> results/raw/g1_capture_null.csv
"""
from __future__ import annotations

import csv
import io
import json
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402

HW = REPO / "results" / "hw" / "channel24"
OUT = REPO / "results" / "raw" / "g1_capture.csv"
SESSIONS = {"W1e": ("w1e_2026-11-05", "w1e_2026-11-05_windows.csv"),
            "W1f": ("w1f_2026-11-05", "w1f_2026-11-05_windows.csv"),
            "W1j": ("w1j_2026-11-06/w1j_2026-11-06_run", "w1j_2026-11-06_run_windows.csv"),
            "W1k": ("w1k_2026-11-06/w1k_2026-11-06_run", "w1k_2026-11-06_run_windows.csv"),
            "W1n s2": ("w1n_2026-11-08_s2/w1n_2026-11-08_s2_run",
                       "w1n_2026-11-08_s2_run_windows.csv")}


def _json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def window_counts(run: Path, tag: str, senders: list[int],
                  nodes: list[int]) -> dict[tuple[int, int], tuple[int, int]]:
    """{(sender j, receiver i): (sent_j, received_ij)} for one window."""
    out = {}
    for j in senders:
        sent = _json(run / f"node{j}" / f"tx_node{j}_{tag}.json").get("sent")
        if not sent:
            continue
        for i in nodes:
            if i == j:
                continue
            rx = _json(run / f"node{i}" / f"rx_node{i}_{tag}.json").get("by_source", {})
            got = rx.get(f"10.0.0.{j}", {}).get("received_unique")
            if got is not None:
                out[(j, i)] = (sent, got)
    return out


def _link(run: Path, usable: list[dict[str, str]],
          nodes: list[int]) -> dict[tuple[int, int], tuple[int, int]]:
    """{(j, i): (sent, received)} pooled over the single-sender windows at 60 frames/s or less."""
    link: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for w in usable:
        s = [int(x) for x in w["senders"].split(",")]
        if len(s) == 1 and float(w["rate_fps"]) <= 60:
            for k, v in window_counts(run, w["window"], s, nodes).items():
                link.setdefault(k, []).append(v)
    return {k: (sum(s for s, _r in v), sum(r for _s, r in v)) for k, v in link.items()}


def _session_inputs(name: str) -> tuple[Path, list[int], list[dict[str, str]]]:
    run_dir, wfile = SESSIONS[name]
    run = HW / run_dir
    nodes = sorted(int(p.name[4:]) for p in run.glob("node*") if p.name[4:].isdigit())
    wins = [r for r in csv.DictReader(ln for ln in (HW / wfile).open() if not ln.startswith("#"))]
    return run, nodes, [w for w in wins if w.get("usable", "") != "False"]


def session(name: str) -> list[dict[str, object]]:
    run, nodes, usable = _session_inputs(name)
    ell = {k: 1 - got / sent for k, (sent, got) in _link(run, usable, nodes).items()}
    rows = []
    for w in usable:
        s = [int(x) for x in w["senders"].split(",")]
        if len(s) < 2:
            continue
        counts = window_counts(run, w["window"], s, nodes)
        c = {k: (1 - got / sent) - ell.get(k, 0.0) for k, (sent, got) in counts.items()}
        for j in s:
            recv = [i for i in nodes if (j, i) in c]
            if len(recv) < 2:
                continue
            cj = [c[(j, i)] for i in recv]
            rows.append({"session": name, "window": w["window"], "label": w["label"],
                         "rate_fps": float(w["rate_fps"]), "senders": w["senders"], "sender": j,
                         "receivers": len(recv), "collision_loss_mean": sum(cj) / len(cj),
                         "d_lower_bound": max(cj) - min(cj)})
        dd: float | str = ""        # needs two senders and two other receivers: 4 boards
        for j, m in combinations(s, 2):
            for i, k in combinations(nodes, 2):
                keys = [(j, i), (j, k), (m, i), (m, k)]
                if all(x in c for x in keys):
                    v = abs((c[(j, i)] - c[(j, k)]) - (c[(m, i)] - c[(m, k)]))
                    dd = v if dd == "" else max(float(dd), v)
        for r in rows:
            if r["window"] == w["window"] and r["session"] == name:
                r["dd_max_window"] = dd
    return rows


NULL_DRAWS = 1000
NULL_OUT = REPO / "results" / "raw" / "g1_capture_null.csv"


def _dd_max(c: dict[tuple[int, int], float], s: list[int], nodes: list[int]) -> float | None:
    best = None
    for j, m in combinations(s, 2):
        for i, k in combinations(nodes, 2):
            keys = [(j, i), (j, k), (m, i), (m, k)]
            if all(x in c for x in keys):
                v = abs((c[(j, i)] - c[(j, k)]) - (c[(m, i)] - c[(m, k)]))
                best = v if best is None else max(best, v)
    return best


def null(name: str) -> dict[str, object]:
    """D and |DD| when nothing differs between receivers but count noise (added 2026-11-21).

    D is the range of per-receiver estimates, each with its own count noise, and |DD| the largest
    of several such differences: both are sample extremes, positive even with no capture (F139's
    pattern). The null keeps each window as measured and removes every receiver effect:
    * sender j's collided frames, K = round(sent_j × its mean c_ij), are lost at every receiver;
    * its other frames are lost at receiver i with probability ℓ_ij, independently;
    * ℓ_ij is re-estimated from a binomial draw at its own background count.
    Written before it was computed: side by side (W1e, W1f), the null median of D is of the same
    order as the measured 0.28 %; in the 1 m square the measured 1.4–2.0 % lies well above its null.
    """
    import zlib

    import numpy as np
    rng = np.random.default_rng(zlib.crc32(f"g1_null:{name}".encode()))
    run, nodes, usable = _session_inputs(name)
    bg = _link(run, usable, nodes)
    ell = {k: 1 - got / sent for k, (sent, got) in bg.items()}
    d_obs: list[float] = []
    dd_obs: list[float] = []
    d_null: list[np.ndarray] = []
    dd_null: list[np.ndarray] = []
    for w in usable:
        s = [int(x) for x in w["senders"].split(",")]
        if len(s) < 2:
            continue
        counts = window_counts(run, w["window"], s, nodes)
        c = {k: (1 - got / sent) - ell.get(k, 0.0) for k, (sent, got) in counts.items()}
        sim = {}
        for (j, i), (sent, _got) in counts.items():
            cj = [c[(j, r)] for r in nodes if (j, r) in c]
            k_col = max(0, round(sent * sum(cj) / len(cj)))
            li = ell.get((j, i), 0.0)
            got = rng.binomial(sent - k_col, 1 - li, NULL_DRAWS)
            n_bg = bg.get((j, i), (0, 0))[0]
            li_hat = (1 - rng.binomial(n_bg, 1 - li, NULL_DRAWS) / n_bg) if n_bg else 0.0
            sim[(j, i)] = (1 - got / sent) - li_hat
        for j in s:
            recv = [i for i in nodes if (j, i) in c]
            if len(recv) < 2:
                continue
            d_obs.append(max(c[(j, i)] for i in recv) - min(c[(j, i)] for i in recv))
            stack = np.array([sim[(j, i)] for i in recv])
            d_null.append(stack.max(axis=0) - stack.min(axis=0))
        dd = _dd_max(c, s, nodes)
        if dd is not None:
            dd_obs.append(dd)
            per = [abs((sim[(j, i)] - sim[(j, k)]) - (sim[(m, i)] - sim[(m, k)]))
                   for j, m in combinations(s, 2) for i, k in combinations(nodes, 2)
                   if all(x in sim for x in ((j, i), (j, k), (m, i), (m, k)))]
            dd_null.append(np.max(np.array(per), axis=0))
    dn = np.median(np.array(d_null), axis=0)
    row: dict[str, object] = {
        "session": name, "sender_windows": len(d_obs), "draws": NULL_DRAWS,
        "d_median_measured": float(np.median(d_obs)),
        "d_median_null_mean": float(dn.mean()), "d_median_null_p95": float(np.quantile(dn, 0.95)),
        "d_share_above_own_null_p95": float(np.mean(
            [o > np.quantile(x, 0.95) for o, x in zip(d_obs, d_null, strict=True)]))}
    if dd_obs:
        ddn = np.median(np.array(dd_null), axis=0)
        row.update({"dd_median_measured": float(np.median(dd_obs)),
                    "dd_median_null_mean": float(ddn.mean()),
                    "dd_median_null_p95": float(np.quantile(ddn, 0.95)),
                    "dd_share_above_own_null_p95": float(np.mean(
                        [o > np.quantile(x, 0.95) for o, x in zip(dd_obs, dd_null, strict=True)]))})
    return row


def main() -> None:
    if "--null" in sys.argv:
        out = [null(name) for name in SESSIONS]
        keys = list(dict.fromkeys(k for r in out for k in r))
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "g1_capture_null"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=keys, lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(out)
        NULL_OUT.write_text(buf.getvalue())
        for r in out:
            print({k: round(v, 5) if isinstance(v, float) else v for k, v in r.items()})
        return
    rows = [r for name in SESSIONS for r in session(name)]
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "g1_capture"}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for name in SESSIONS:
        rs = [r for r in rows if r["session"] == name]
        if not rs:
            print(f"{name}: no multi-sender window with two receivers")
            continue
        d = sorted(float(r["d_lower_bound"]) for r in rs)
        dd = sorted(float(r["dd_max_window"]) for r in rs if r["dd_max_window"] != "")
        dd_text = (f"|DD| median {dd[len(dd) // 2]:.4f}, max {dd[-1]:.4f}" if dd
                   else "|DD| not computable (fewer than four boards)")
        print(f"{name}: {len(rs)} sender-windows; D median {d[len(d) // 2]:.4f}, "
              f"90th {d[int(0.9 * (len(d) - 1))]:.4f}, max {d[-1]:.4f}; {dd_text}")


if __name__ == "__main__":
    main()
