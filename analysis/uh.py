#!/usr/bin/env python3
"""U-H: the hardware-matched configurations (work package H, Mohamed's D4 decisions of 2026-11-19).

**(a) The 5 GHz anchor:** the two-Pi-4 sessions of 2026-10-09 with frame burst logged off.
* N = 2, 802.11a 6 Mb/s, the 1 400 B UDP frame: a 1 464 B MPDU, 1 976 µs on air; ns-3's
  frameSize is 1 428.
* 124, 174 and 211 frames/s per board, sent with the per-period redrawn source, as in ns-3.
* Two window candidates, the standard slot (9 µs) and DIFS (34 µs) in both:
  * **W = 10**, from the burst-off one-sender cycle of 2 050 µs: mean backoff 40 µs = 9(W − 1)/2;
  * **W = 16**, the standard's. It also fits the saturated pair's 12.4 % through 2/(W + 1) =
    11.8 %, model-dependent. That pair session (S1) is not one H reproduces, so Mohamed's rule
    allows it.
* N = 2 is each board the other's only receiver, so capture cannot occur, and the capture end
  equals the no-capture end by construction.

**(b) 2.4 GHz:** the sessions ran with frame burst at the driver default (on). A session is
reproduced only where no station could hold two frames.
* **The rule,** from offered rate and frame airtime: the chance that a board's next frame arrives
  within the shortest service time S = T_f + DIFS + 1.5σ (the fastest board alone, W = 4) is
  S²f²/2 for the redrawn source. Under 1 %, the window is reproduced; otherwise it is flagged.
* **Only W1f's four-board windows at 65 frames/s pass** (0.80 %). The rest lie at 1.4–9.3 %.
* **W1f at 65 frames/s:** N = 4 (pi-A, pi-B, the Pi 3, the TP-Link), the 145 B UDP frame
  (1 864 µs, ns-3 frameSize 173), u = 0.485.
* **Per-board windows** from W1f's measured one-sender cycles (1 941.4, 1 945.3, 2 413.4 and
  1 962.6 µs), under two slot/DIFS families:
  * σ 20 / DIFS 50: W = 4, 4, 51, 6;
  * σ 9 / DIFS 28: W = 12, 13, 117, 17.
* **Two capture ends:** equal power (no capture); and the assumed channel of Mohamed's decision
  (equal mean power, Nakagami m = 1 per frame, ns-3's frame-capture model on).

**The closed forms** (reported beside ns-3, none scored): (G5) Poisson, (G25), and the
finite-station form where accepted (N = 3–5, u ≤ 0.5, so at W1f only).

    python analysis/uh.py           -> the registration's tables
    python analysis/uh.py --flags   -> results/raw/uh_flags.csv: the rule on every window
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.models import finite_station as fs  # noqa: E402
from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

ANCHOR_FRAME = 1428
ANCHOR_RATES = (124.0, 174.0, 211.0)
ANCHOR_W = (10, 16)
ANCHOR_HW_LOSS = {124.0: 0.00321, 174.0: 0.00516, 211.0: 0.00837}   # contention_2nodes_fb_off.csv
W1F_RATE = 65.0
W1F_FRAME = 173
W1F_CYCLES_US = (1941.35, 1945.25, 2413.35, 1962.6)   # W1f's rate checks, per board, averaged
FAMILIES = {"s20d50": (20e-6, 50e-6), "s9d28": (9e-6, 28e-6)}


def board_windows(family: str) -> list[int]:
    """W per board from its one-sender cycle: cycle = T_f + DIFS + σ(W − 1)/2."""
    slot, difs = FAMILIES[family]
    tf = uc.airtime_s(phy.DSSS_1M, W1F_FRAME)
    return [round(1 + 2 * (c * 1e-6 - tf - difs) / slot) for c in W1F_CYCLES_US]


def anchor_table() -> str:
    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, ANCHOR_FRAME)
    lines = ["| frames/s | hardware loss (burst off) | W | (G5) | (G25), outside its range | "
             "finite-station, not accepted at N = 2 |", "|---|---|---|---|---|---|"]
    for f in ANCHOR_RATES:
        for w in ANCHOR_W:
            acc = uc.Access(9e-6, 34e-6, w)
            lines.append(f"| {f:g} | {ANCHOR_HW_LOSS[f]:.5f} | {w} | {uc.loss(f, tf, acc):.5f} | "
                         f"{pc.loss_periodic(2, f, tf, acc):.5f} | {fs.loss(2, f, tf, acc):.5f} |")
    return "\n".join(lines)


def w1f_table() -> str:
    tf = uc.airtime_s(phy.DSSS_1M, W1F_FRAME)
    acc = uc.A80211B
    return ("| W1f, 4 boards at 65 frames/s (u = "
            f"{4 * W1F_RATE * tf:.3f}) | (G5) {uc.loss(3 * W1F_RATE, tf, acc):.5f} | (G25) "
            f"{pc.loss_periodic(4, W1F_RATE, tf, acc):.5f} | finite-station "
            f"{fs.loss(4, W1F_RATE, tf, acc):.5f} | the standard's W = 32 in all three |")


QUEUE_SLOT, QUEUE_DIFS, QUEUE_BACKOFF_SLOTS = 20e-6, 50e-6, 1.5   # the fastest board alone, W = 4
QUEUE_FLAG = 0.01
UDP_IP_BYTES = 28


def flags() -> list[dict[str, Any]]:
    """The frame-burst rule on every multi-sender window of the registered sessions, from the
    logs: each window's UDP payload from a sender's transmit record, its frames/s from the plan.

    S = T_f + DIFS + 1.5σ; P(next frame within S) = S²f²/2 for the redrawn source; flagged at 1 %.
    The rule and its threshold were fixed in `predictions/UH.md` before this code was written; the
    registration's 0.80 % and 1.4–9.3 % came from the same rule computed by hand.
    """
    import csv
    import json
    sys.path.insert(0, str(REPO / "analysis"))
    import g1_capture as g1
    out = []
    for name, (run_dir, wfile) in g1.SESSIONS.items():
        run = g1.HW / run_dir
        wins = [r for r in csv.DictReader(ln for ln in (g1.HW / wfile).open()
                                          if not ln.startswith("#"))]
        for w in wins:
            senders = [int(x) for x in w["senders"].split(",")]
            if len(senders) < 2 or w.get("usable", "") == "False":
                continue
            tx = run / f"node{senders[0]}" / f"tx_node{senders[0]}_{w['window']}.json"
            udp = json.loads(tx.read_text())["bytes"]
            f = float(w["rate_fps"])
            tf = uc.airtime_s(phy.DSSS_1M, udp + UDP_IP_BYTES)
            s = tf + QUEUE_DIFS + QUEUE_BACKOFF_SLOTS * QUEUE_SLOT
            p = (s * f) ** 2 / 2
            out.append({"session": name, "window": w["window"], "label": w["label"],
                        "n": len(senders), "fps": f, "udp_bytes": udp, "tf_us": tf * 1e6,
                        "p_two_queued": p, "reproduced": int(p < QUEUE_FLAG)})
    return out


def flags_table(rows: list[dict[str, Any]]) -> str:
    """One line per (session, N, frames/s, payload), from the per-window rows."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((r["session"], r["n"], r["fps"], r["udp_bytes"]), []).append(r)
    lines = ["| session | N | frames/s per board | UDP payload | windows | S²f²/2 | |",
             "|---|---|---|---|---|---|---|"]
    for (s, n, f, b), v in groups.items():
        p = float(v[0]["p_two_queued"])
        lines.append(f"| {s} | {n} | {f:g} | {b} B | {len(v)} | {100 * p:.2f} % | "
                     f"{'**reproduced**' if p < QUEUE_FLAG else 'flagged'} |")
    return "\n".join(lines)


def anchor_rule_a(seeds: int = 30) -> list[dict[str, float]]:
    """Rule A's simulation (F137: it tracks ns-3 at small N) at the anchor's rates, N = 2.

    Not the saturated pair: rule A's loop does not tie frames to stations, so a station holding
    two frames cannot be represented there.
    """
    import random
    import statistics as st
    sys.path.insert(0, str(REPO / "analysis"))
    import finite_station_check as fsc

    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, ANCHOR_FRAME)
    out = []
    for w in ANCHOR_W:
        acc = uc.Access(9e-6, 34e-6, w)
        for f in ANCHOR_RATES:
            ps = []
            for seed in range(1, seeds + 1):
                rng = random.Random(1000 * seed + 2)
                ps.append(fsc.rule_a(fsc.arrivals(2, f, "jitter", rng), tf, acc, rng))
            out.append({"w": w, "fps": f, "rule_a_loss": st.mean(ps),
                        "rule_a_se": st.stdev(ps) / seeds ** 0.5})
    return out


def main() -> None:
    if "--flags" in sys.argv:
        import csv
        import io

        from authbc.bench import provenance
        rows = flags()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "uh_flags"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        (REPO / "results" / "raw" / "uh_flags.csv").write_text(buf.getvalue())
        print(flags_table(rows))
        return
    if "--rule-a" in sys.argv:
        import csv
        import io

        from authbc.bench import provenance
        rows = anchor_rule_a()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "uh_anchor_rule_a"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        (REPO / "results" / "raw" / "uh_anchor_rule_a.csv").write_text(buf.getvalue())
        for r in rows:
            print(r)
        return
    print(anchor_table())
    print()
    print(w1f_table())
    print({f: board_windows(f) for f in FAMILIES})


if __name__ == "__main__":
    main()
