#!/usr/bin/env python3
"""W3a: frame loss measured on air at 802.11b 1 Mb/s, traced frame by frame, replayed through the
real decoder. Plans, statistics, score.

predictions/W3a.md. The paper's loss processes are generated or simulated, and "no loss was
measured on air". pi-A sends alone, from another room, at a power set in software; pi-B, the Pi 3
and the TP-Link each record every sequence number they receive (`hw/channel/bcast_rx.py`, `seqs`).
Three sizes, interleaved in time:
* S, the one-record frame of the frame-linked format (147 B on the IP layer);
* A, AUTHBC's four-record frame (173 B, as in W1);
* L, 1000 B of payload, a lever on length dependence.
Each received list becomes a lost-frame mask of the length pi-A sent.

    python analysis/w3a_loss.py --plan [--tuning]  -> experiments/channel24/plan_w3a[_tuning].txt
    python analysis/w3a_loss.py --tune DIR         -> the loss each receiver saw, per size
    python analysis/w3a_loss.py --score DIR:MBM [DIR:MBM ...] --name NAME
        -> results/raw/w3a_NAME.csv
    python analysis/w3a_loss.py --cycles DIR:MBM [DIR:MBM ...] --name NAME
        -> results/raw/w3a_NAME_cycles.csv, the frames sent and lost in every window (reporting,
           added after the outcome; the score is unchanged)

Reused: `verifiability_margin.burst_stats` and `.v_of_masks` (A3's trace replay through
`LeanReceiver`), `frame_model.verifiability`, `.verifiability_gilbert`, `.length_scaled_loss`, W1d's
rate-check band and `hw_preflight.power_check_at`.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
from collections.abc import Sequence
from functools import cache
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_three as w1d  # noqa: E402
import hw_preflight as pf  # noqa: E402
import verifiability_margin as vm  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.models import frame as frame_model  # noqa: E402
from authbc.placement.session_v2 import LeanSender  # noqa: E402

PLAN = w1d.PLANS / "plan_w3a.txt"
PLAN_TUNING = w1d.PLANS / "plan_w3a_tuning.txt"
IP_UDP = 28
SIZES = {"S": 119, "A": 145, "L": 1000}               # UDP payload, B
FRAME_BYTES = {k: v + IP_UDP for k, v in SIZES.items()}  # on the IP layer, as the paper's frames
RATE = 50                                             # frames/s, 22 s a window
SENDER, RECEIVERS = 1, (2, 3, 4)
BATCH = 4                                             # AUTHBC's four-record frame
P_MIN = 0.01                                          # the claims read traces losing >= 1 %
TARGET_V = 0.95


def plan(tuning: bool = False) -> list[str]:
    """R1, then S A L (four times; once for a tuning run), then R1 again. pi-A sends alone."""
    r1 = f"R1 {w1d.RATE_CHECK_FPS} {w1d.PAYLOAD_UDP} {SENDER}"
    body = [f"{k} {RATE} {SIZES[k]} {SENDER}" for k in "SAL"] * (1 if tuning else 4)
    head = ["# nodes: 1,2,3",
            "# W3a: pi-A alone, from another room; S, A and L interleaved; rate checks around."]
    return head + [r1] + body + ([] if tuning else [r1])


def lost_mask(seqs: Sequence[int], sent: int) -> np.ndarray:
    """True where frame i of the `sent` was not received."""
    got = np.asarray(seqs, dtype=int)
    if got.size and (got.min() < 0 or got.max() >= sent):
        raise ValueError(f"a received number outside 0..{sent - 1}")
    lost = np.ones(sent, dtype=bool)
    lost[got] = False
    return lost


def loss_stats(masks: Sequence[np.ndarray]) -> dict[str, float]:
    lost, bursts = vm.burst_stats(list(masks))
    n = sum(len(m) for m in masks)
    p = lost / n
    return {"frames": n, "lost": lost, "p_hat": p,
            "mean_burst": lost / bursts if bursts else float("nan"), "iid_burst": 1 / (1 - p)}


def model_length_ratio(p_s: float, label: str) -> float:
    """The paper's bit-error model: loss of `label`'s frame over the one-record frame's."""
    return frame_model.length_scaled_loss(
        p_s, FRAME_BYTES[label], ref_frame_bytes=FRAME_BYTES["S"],
        overhead_bytes=bianchi.MAC_OVH_BYTES) / p_s


@cache
def _stream(ref: int, n_frames: int) -> tuple[tuple[bytes, ...], object]:
    sk, pk = Ed25519Scheme().keygen(seed=bytes(range(32)))
    recs = leanframes.chained_records(1, n_frames * BATCH)
    sender = LeanSender(sk, ref_interval=ref)
    return tuple(sender.frame(recs[i:i + BATCH]) for i in range(0, len(recs), BATCH)), pk


def v_through_decoder(masks: Sequence[np.ndarray], ref: int) -> list[float]:
    """V of each mask: AUTHBC's four-record frames, one key record per `ref`, the real receiver."""
    frames, pk = _stream(ref, max(len(m) for m in masks))
    return vm.v_of_masks(list(frames), pk, list(masks))


# ---------------------------------------------------------------------------------- sessions
def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _windows(session: Path) -> list[str]:
    return sorted(p.name[len("tx_node1_"):-len(".json")]
                  for p in (session / "node1").glob("tx_node1_*.json"))


def traces(session: Path) -> tuple[dict[tuple[str, int], list[np.ndarray]], list[str]]:
    """{(size label, receiver): masks, one per window}, and the windows with a file missing."""
    out: dict[tuple[str, int], list[np.ndarray]] = {}
    missing = []
    for tag in _windows(session):
        label = tag.split("_")[1]
        if label not in SIZES:
            continue
        sent = _load(session / "node1" / f"tx_node1_{tag}.json")["sent"]
        for r in RECEIVERS:
            path = session / f"node{r}" / f"rx_node{r}_{tag}.json"
            src = _load(path)["by_source"].get(f"10.0.0.{SENDER}") if path.exists() else None
            if src is None or "seqs" not in src:
                missing.append(f"{tag} node{r}")
                continue
            out.setdefault((label, r), []).append(lost_mask(src["seqs"], sent))
    return out, missing


def _rate_checks(session: Path) -> list[dict]:
    lo, hi = w1d.RATE_BAND_S
    rows = []
    for tag in (t for t in _windows(session) if t.split("_")[1] == "R1"):
        cycles = []
        for r in RECEIVERS:
            path = session / f"node{r}" / f"rx_node{r}_{tag}.json"
            g = _load(path)["by_source"].get(f"10.0.0.{SENDER}") if path.exists() else None
            if g and g["max_seq"] > g["min_seq"]:
                cycles.append(g["span_s"] / (g["max_seq"] - g["min_seq"]))
        c = st.mean(cycles) if cycles else float("nan")
        rows.append({"what": "rate check", "group": tag, "measured": round(1e6 * c, 1),
                     "held": bool(cycles) and lo <= c <= hi})
    return rows


def _group_rows(mbm: int, session: Path) -> tuple[list[dict], list[str], list[dict]]:
    by, missing = traces(session)
    rows = []
    for (label, r), masks in sorted(by.items()):
        s = loss_stats(masks)
        row = {"what": "trace", "mbm": mbm, "size": label, "receiver": r,
               "windows": len(masks), "frames": s["frames"], "lost": s["lost"],
               "p_hat": round(s["p_hat"], 5), "mean_burst": round(s["mean_burst"], 3),
               "iid_burst": round(s["iid_burst"], 3)}
        if label == "A":
            v1 = st.mean(v_through_decoder(masks, ref=1))
            v4 = st.mean(v_through_decoder(masks, ref=4))
            row |= {"V_r1": round(v1, 6), "V_r4": round(v4, 6),
                    "V_r4_iid": round(frame_model.verifiability(s["p_hat"], 4), 6),
                    "V_r4_gilbert": round(frame_model.verifiability_gilbert(
                        s["p_hat"], s["mean_burst"], 4), 6) if s["lost"] else "",
                    "_v1_exact": all(abs(v - (1 - m.mean())) <= 1e-12 for v, m in
                                     zip(v_through_decoder(masks, ref=1), masks, strict=True))}
        rows.append(row)
    return rows, missing, _rate_checks(session)


def score(session: Path, mbm: int) -> list[dict]:
    return score_all([(session, mbm)])


def score_all(sessions: Sequence[tuple[Path, int]]) -> list[dict]:
    """Validity per session, a row per trace group, then W3a-1..3 over every valid session."""
    head, groups = [], []
    for session, mbm in sessions:
        g, missing, rates = _group_rows(mbm, session)
        log = (session / "node1" / "txpower.log")
        power = pf.power_check_at(log.read_text() if log.exists() else "", mbm)
        valid = (len(rates) == 2 and all(r["held"] for r in rates) and power and not missing)
        head += [{"what": "session", "group": session.name, "mbm": mbm, "held": valid,
                  "measured": f"rate checks {[r['measured'] for r in rates]}; power read back "
                              f"{power}; missing {len(missing)}"}]
        if valid:
            groups += g
    a_rows = [g for g in groups if g["size"] == "A"]
    claim1 = [g for g in a_rows if g["p_hat"] >= P_MIN]

    def same_link(g: dict, size: str) -> dict:
        return next(h for h in groups if h["mbm"] == g["mbm"] and h["receiver"] == g["receiver"]
                    and h["size"] == size)

    s_and_l = [(g, same_link(g, "L")) for g in groups if g["size"] == "S" and g["p_hat"] >= P_MIN]
    lost_s = sum(s["lost"] for s, _ in s_and_l)
    lost_l = sum(ll["lost"] for _, ll in s_and_l)
    p_s = lost_s / sum(s["frames"] for s, _ in s_and_l) if s_and_l else float("nan")
    p_l = lost_l / sum(ll["frames"] for _, ll in s_and_l) if s_and_l else float("nan")
    measured_ratio = p_l / p_s if s_and_l and p_s else float("nan")
    model_ratio = model_length_ratio(p_s, "L") if s_and_l and p_s else float("nan")
    # stronger than the model only if shown: the 95 % interval of the ratio of two proportions
    # (on the log scale) lies wholly above the model's ratio; equal ratios are not a failure
    n_s, n_l = (sum(s["frames"] for s, _ in s_and_l), sum(ll["frames"] for _, ll in s_and_l))
    se = (np.sqrt(1 / lost_l - 1 / n_l + 1 / lost_s - 1 / n_s)
          if s_and_l and lost_s and lost_l else float("nan"))
    ratio_lo = measured_ratio * float(np.exp(-1.96 * se))
    # W3a-1 fails only if shown: pooled over the traces, V(r=4) below its independent value by more
    # than the 95 % one-sided sampling margin. A frame's fate is shared by the groups of r = 4 it
    # starts, so the binomial variance is inflated by r (the design effect).
    n1 = sum(g["frames"] for g in claim1)
    got = sum(g["V_r4"] * g["frames"] for g in claim1)
    want = sum(g["V_r4_iid"] * g["frames"] for g in claim1)
    margin = 1.645 * float(np.sqrt(sum(4 * g["frames"] * g["V_r4_iid"] * (1 - g["V_r4_iid"])
                                       for g in claim1)))
    claims = [
        {"what": "W3a-1", "group": "real loss hurts dependent frames no more than independent loss",
         "measured": f"V(r=4) {got / n1:.5f} against {want / n1:.5f} independent, margin "
                     f"{margin / n1:.5f} ({len(claim1)} traces; "
                     f"{sum(g['V_r4'] >= g['V_r4_iid'] for g in claim1)} at or above)"
         if claim1 else "no trace at p >= 1 %",
         "held": bool(claim1) and got >= want - margin},
        {"what": "W3a-2", "group": "AUTHBC as built loses only its own frames: V(r=1) = 1 - p",
         "measured": f"{sum(g['_v1_exact'] for g in a_rows)}/{len(a_rows)} traces exact",
         "held": bool(a_rows) and all(g["_v1_exact"] for g in a_rows)},
        {"what": "W3a-3", "group": "length dependence no stronger than the bit-error model",
         "measured": f"p(L)/p(S) {measured_ratio:.3f} (95 % lower bound {ratio_lo:.3f}) "
                     f"against {model_ratio:.3f} at p(S) {p_s:.4f} ({len(s_and_l)} links)",
         "held": bool(s_and_l) and ratio_lo <= model_ratio},
    ]
    a_s = [(g, same_link(g, "S")) for g in a_rows]
    nan = float("nan")
    pa = sum(g["lost"] for g, _ in a_s) / sum(g["frames"] for g, _ in a_s) if a_s else nan
    ps_a = sum(s["lost"] for _, s in a_s) / sum(s["frames"] for _, s in a_s) if a_s else nan
    near = min(a_rows, key=lambda g: abs(g["p_hat"] - 0.05)) if a_rows else None
    reported = [
        {"what": "reported: AUTHBC's length penalty", "group": "p(A)/p(S), all links",
         "measured": f"{pa / ps_a:.3f} against the model's {model_length_ratio(ps_a, 'A'):.3f}"
         if a_s and ps_a else "", "held": ""},
        {"what": "reported: the link nearest 5 %", "group": f"{near['mbm']} mBm, node"
         f"{near['receiver']}" if near else "",
         "measured": f"p {near['p_hat']:.4f}, V(r=1) {near['V_r1']:.4f}, meets 0.95: "
                     f"{near['V_r1'] >= TARGET_V}" if near else "", "held": ""},
    ]
    clean = [{k: v for k, v in g.items() if not k.startswith("_")} for g in groups]
    return head + clean + claims + reported


def tune(session: Path) -> list[str]:
    by, missing = traces(session)
    out = []
    for (label, r), m in sorted(by.items()):
        s = loss_stats(m)
        out.append(f"{label} node{r}: loss {100 * s['p_hat']:.2f} % ({s['lost']}/{s['frames']}), "
                   f"mean burst {s['mean_burst']:.2f} (independent {s['iid_burst']:.2f})")
    return out + [f"missing: {missing}"] if missing else out


# --------------------------------------------- reporting, added 2026-11-07 after the outcome
# Not part of the score: `score_all` and the scored CSV are as registered. These give the window
# counts the paper and thesis quote, and the interval the outcome reported.
def cycles(session: Path, mbm: int) -> list[dict]:
    """One row per window: its size, receiver, place among that size's windows, frames sent and
    lost. The k-th S, A and L windows of a session are one cycle, a minute apart at most."""
    by, _missing = traces(session)
    return [{"mbm": mbm, "receiver": r, "size": label, "cycle": k, "sent": len(m),
             "lost": int(m.sum())}
            for (label, r), masks in sorted(by.items()) for k, m in enumerate(masks)]


def length_penalty_bootstrap(rows: Sequence[dict], seed: int = 20261107,
                             n: int = 5000) -> tuple[float, float, float]:
    """p(A)/p(S) pooled, and its 95 % percentile interval, resampling paired S/A cycles.

    A cycle's two windows share the channel's state, and the loss swings between windows, so
    the cycle is the unit; resampling single frames would treat them as independent and give an
    interval far too narrow (W3a outcome). Units in session order (power falling), receiver,
    cycle, as the outcome's computation of 2026-11-07 drew them."""
    cell = {(int(r["mbm"]), int(r["receiver"]), int(r["cycle"]), r["size"]):
            (int(r["lost"]), int(r["sent"])) for r in rows}
    keys = sorted({k[:3] for k in cell if k[3] == "S"}, key=lambda k: (-k[0], k[1], k[2]))
    units = [cell[k + ("S",)] + cell[k + ("A",)] for k in keys]

    def ratio(us: Sequence[tuple[int, ...]]) -> float:
        lost_s, sent_s, lost_a, sent_a = (sum(col) for col in zip(*us, strict=True))
        return (lost_a / sent_a) / (lost_s / sent_s)

    rng = random.Random(seed)
    boot = sorted(ratio([rng.choice(units) for _ in units]) for _ in range(n))
    return ratio(units), boot[int(0.025 * n)], boot[int(0.975 * n) - 1]


def _write(path: Path, rows: list[dict]) -> None:
    import csv
    import io
    buf = io.StringIO()
    config = {"sizes": SIZES, "rate": RATE, "batch": BATCH, "p_min": P_MIN,
              "rate_band_s": w1d.RATE_BAND_S}
    for k, v in {**provenance.env_block(), "run": "w3a",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    fields = list(dict.fromkeys(k for r in rows for k in r))
    w = csv.DictWriter(buf, fieldnames=fields, restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--plan", action="store_true")
    what.add_argument("--tune", type=Path, metavar="DIR")
    what.add_argument("--score", nargs="+", metavar="DIR:MBM")
    what.add_argument("--cycles", nargs="+", metavar="DIR:MBM")
    ap.add_argument("--tuning", action="store_true")
    ap.add_argument("--name", default="session")
    args = ap.parse_args()
    if args.plan:
        out = PLAN_TUNING if args.tuning else PLAN
        out.write_text("\n".join(plan(args.tuning)) + "\n")
        print(out.read_text())
    elif args.tune:
        print("\n".join(tune(args.tune)))
    elif args.cycles:
        pairs = [(Path(s.rsplit(":", 1)[0]), int(s.rsplit(":", 1)[1])) for s in args.cycles]
        rows = [row for session, mbm in pairs for row in cycles(session, mbm)]
        _write(w1d.RAW / f"w3a_{args.name}_cycles.csv", rows)
        pooled, lo, hi = length_penalty_bootstrap(rows)
        print(f"{len(rows)} windows; p(A)/p(S) {pooled:.3f}, 95 % {lo:.3f}-{hi:.3f}")
    else:
        pairs = [(Path(s.rsplit(":", 1)[0]), int(s.rsplit(":", 1)[1])) for s in args.score]
        rows = score_all(pairs)
        _write(w1d.RAW / f"w3a_{args.name}.csv", rows)
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
