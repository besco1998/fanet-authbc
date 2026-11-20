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

    python analysis/g1_capture.py   -> results/raw/g1_capture.csv
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


def session(name: str) -> list[dict[str, object]]:
    run_dir, wfile = SESSIONS[name]
    run = HW / run_dir
    nodes = sorted(int(p.name[4:]) for p in run.glob("node*") if p.name[4:].isdigit())
    wins = [r for r in csv.DictReader(ln for ln in (HW / wfile).open() if not ln.startswith("#"))]
    usable = [w for w in wins if w.get("usable", "") != "False"]
    link: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for w in usable:
        s = [int(x) for x in w["senders"].split(",")]
        if len(s) == 1 and float(w["rate_fps"]) <= 60:
            for k, v in window_counts(run, w["window"], s, nodes).items():
                link.setdefault(k, []).append(v)
    ell = {k: 1 - sum(r for _s, r in v) / sum(s for s, _r in v) for k, v in link.items()}
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


def main() -> None:
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
