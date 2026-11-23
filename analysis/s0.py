#!/usr/bin/env python3
"""S0 — the frame-level campaign's gate (predictions/S0.md; docs/DECISIONS.md, 2026-11-23): does
the TP-Link sniffer on Blue 2 (rtl8188eus af3bf004 plus the approved TSF line, monitor mode,
channel 11) record what the campaign needs? No scored result of the campaign exists before it
passes.

The session: the three Pis run `experiments/channel24/plan_s0.txt` (`run_window_plan2.sh`); the
sniffer records from 60 s before the plan to 60 s after it (`run_sniffer2.sh`), and Blue 1 runs the
one WL18xx retest in the last window. Every criterion is read from the raw files only:

* **capture completeness:** each Pi alone at 50 frames/s, 145 B, 1 000 frames; the sniffer's
  share of the sender's sequence numbers 0 … sent − 1 (pi-A scored, ≥ 99 %; the others reported);
* **timestamps:** the share of our frames with TSFT; with it, the saturated single-sender
  windows' start-to-start intervals must be at least the frame's airtime (1 864 µs) for ≥ 99 % of
  consecutive pairs, and their median must agree with the receivers' cycle within 2 %;
* **signal:** pi-A's mean per-frame dBm at 12, 9 and 6 dBm, less its mean at 15 dBm, against
  −3, −6, −9 dB, each within ±1.5 dB;
* **rate and preamble:** every frame of ours decoded at 1 Mb/s; the preamble is not readable
  (the driver never sets the short-preamble flag) and is reported as such;
* **bad frames:** any frame flagged with a bad checksum in the saturated pair window, yes or no.

Each window's frames are taken from the sniffer by the sender's address and the host-time span
in which the receivers logged that window's frames (± 0.5 s; NTP on both sides).

    python analysis/s0.py --plan              -> experiments/channel24/plan_s0.txt
    python analysis/s0.py --score SESSION     -> results/raw/s0_<session>.csv
"""
from __future__ import annotations

import csv
import io
import statistics as st
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_three as w1d  # noqa: E402
import hw_session as hs  # noqa: E402
import pcap_frames as pf  # noqa: E402

PLAN = w1d.PLANS / "plan_s0.txt"
PAYLOAD = w1d.PAYLOAD_UDP            # 145 B
T_F_US = 1864.0                      # 145 B at 1 Mb/s, long preamble (uh.W1F_FRAME)
P0_MBM = 1500
POWER_STEPS_DB = (0, 3, 6, 9)        # pi-A at 15, 12, 9, 6 dBm
COMPLETENESS_MIN = 0.99
TSFT_SHARE_MIN = 0.99
START_TO_START_SHARE = 0.99
CYCLE_AGREE = 0.02
SIGNAL_TOL_DB = 1.5
SPAN_MARGIN_NS = 500_000_000
TSF_WRAP = 1 << 32


def plan() -> list[str]:
    checks = [f"R{n} 600 {PAYLOAD} {n} 25" for n in (1, 2, 3)]
    lines = ["# nodes: 1,2,3", "# S0: the sniffer gate (analysis/s0.py)"] + checks
    lines += [f"G{n} 50 {PAYLOAD} {n} 23 {n}:{P0_MBM}" for n in (1, 2, 3)]   # 20 s: 1 000 frames
    lines += [f"P{15 - d} 50 {PAYLOAD} 1 25 1:{P0_MBM - 100 * d}" for d in POWER_STEPS_DB]
    lines += [f"X 600 {PAYLOAD} 1,2 25 1:{P0_MBM}"]
    lines += [f"W 50 {PAYLOAD} 1 60"]                    # the WL18xx retest, Blue 1
    return lines + checks


# ---- reading the session ----------------------------------------------------------------------
def window_spans(session: Path) -> dict[str, tuple[int, int, list[int]]]:
    """{tag: (first ns, last ns, senders)} from the receivers' timestamp files."""
    out: dict[str, tuple[int, int, list[int]]] = {}
    for tag, parts in w1d._files(session).items():
        senders = [int(s) for s in next(iter(parts["ctr"].values()))["senders"].split(",")]
        times = []
        for n, d in hs.node_dirs(session).items():
            p = d / f"rxts_node{n}_{tag}.csv"
            if p.is_file():
                with p.open() as fh:
                    times += [int(r["t_ns"]) for r in csv.DictReader(fh) if int(r["t_ns"]) > 0]
        if times:
            out[tag] = (min(times), max(times), senders)
    return out


def sniffer_frames(session: Path) -> list[pf.Frame]:
    caps = sorted((session / "sniffer").glob("sniff_*.pcap"))
    if len(caps) != 1:
        raise FileNotFoundError(f"{session}/sniffer: {len(caps)} captures, not 1")
    return list(pf.parse(caps[0]))


def in_window(frames: list[pf.Frame], span: tuple[int, int, list[int]], sender: int
              ) -> list[pf.Frame]:
    lo, hi = span[0] - SPAN_MARGIN_NS, span[1] + SPAN_MARGIN_NS
    ip = f"10.0.0.{sender}"
    return [f for f in frames if f.src_ip == ip and f.seq is not None and lo <= f.host_ns <= hi]


def unwrap_tsft(values: list[int]) -> list[int]:
    """The driver's TSFT is the descriptor's 32-bit TSF word: add 2³² at each wrap."""
    out, base, prev = [], 0, None
    for v in values:
        if prev is not None and v < prev - TSF_WRAP // 2:
            base += TSF_WRAP
        out.append(v + base)
        prev = v
    return out


# ---- the criteria -----------------------------------------------------------------------------
def completeness(frames: list[pf.Frame], sent: int) -> float:
    got = {f.seq for f in frames if f.seq is not None and 0 <= f.seq < sent}
    return len(got) / sent


def start_to_start_us(frames: list[pf.Frame]) -> list[float]:
    """TSFT differences between consecutive sequence numbers of one sender. TSFT is unwrapped in
    capture order, the order the sniffer received the frames in."""
    timed = [f for f in frames if f.tsft_us is not None and f.seq is not None]
    by_seq: dict[int, int] = {}
    for f, t in zip(timed, unwrap_tsft([f.tsft_us for f in timed if f.tsft_us is not None]),
                    strict=True):
        by_seq.setdefault(f.seq if f.seq is not None else -1, t)
    seqs = sorted(by_seq)
    return [float(by_seq[b] - by_seq[a]) for a, b in zip(seqs, seqs[1:], strict=False)
            if b == a + 1]


def signal_steps(levels: dict[int, float]) -> dict[int, float]:
    """{step dB: measured fall} from {set dBm: mean signal}, against 15 dBm."""
    top = levels[15]
    return {15 - p: top - v for p, v in levels.items() if p != 15}


def score(session: Path) -> list[dict[str, Any]]:
    frames = sniffer_frames(session)
    spans = window_spans(session)
    files = w1d._files(session)
    tags: dict[str, list[str]] = {}
    for tag in sorted(spans, key=lambda x: int(x.split("_")[0])):
        tags.setdefault(tag.split("_")[1], []).append(tag)
    out: list[dict[str, Any]] = [{"what": "frame burst off on every board", "item": "",
                                  "measured": "", "predicted": "0 before and after",
                                  "held": hs.frameburst_off(session)}]
    ours = [f for f in frames if f.src_ip and f.src_ip.startswith("10.0.0.") and f.seq is not None]
    # completeness
    for n in (1, 2, 3):
        tag = tags[f"G{n}"][0]
        sent = files[tag]["tx"][n]["sent"]
        share = completeness(in_window(frames, spans[tag], n), sent)
        out.append({"what": "capture completeness", "item": f"node {n}, {sent} sent",
                    "measured": round(share, 5), "predicted": f">= {COMPLETENESS_MIN}",
                    "held": share >= COMPLETENESS_MIN if n == 1 else "reported"})
    # timestamps
    tsft_share = sum(f.tsft_us is not None for f in ours) / len(ours)
    out.append({"what": "TSFT present", "item": f"{len(ours)} frames of ours",
                "measured": round(tsft_share, 5), "predicted": f">= {TSFT_SHARE_MIN}",
                "held": tsft_share >= TSFT_SHARE_MIN})
    if tsft_share < TSFT_SHARE_MIN:
        # host time only: its jitter against pi-B's kernel times of pi-A's G1 frames (W1p's form)
        import w1p
        tag = tags["G1"][0]
        sniff = {f.seq: f.host_ns for f in in_window(frames, spans[tag], 1) if f.seq is not None}
        got = w1p.pair_variance_ns2(sniff, hs.timestamps(session, 2, tag)[1])
        out.append({"what": "host-time jitter, sniffer against pi-B (us)", "item": tag,
                    "measured": round(got["robust_var_ns2"] ** 0.5 / 1e3, 2),
                    "predicted": "reported: the campaign's timing needs TSFT",
                    "held": "reported"})
    else:
        rows = w1d.window_rows(session)
        for w in rows:
            if not w1d.RATE_CHECK.fullmatch(w["label"]):
                continue
            n = int(w["label"][1])
            s2s = start_to_start_us(in_window(frames, spans[w["window"]], n))
            short = sum(x < T_F_US for x in s2s) / len(s2s)
            med = st.median(s2s)
            agree = abs(med - w["cycle_us"]) / w["cycle_us"]
            out.append({"what": "TSFT start-to-start", "item": w["window"],
                        "measured": f"{len(s2s)} pairs; below {T_F_US:g} us {100 * short:.2f} %; "
                                    f"median {med:.1f} us against the receivers' cycle "
                                    f"{w['cycle_us']} us ({100 * agree:.2f} %)",
                        "predicted": f"below airtime < {100 * (1 - START_TO_START_SHARE):g} %; "
                                     f"median within {100 * CYCLE_AGREE:g} %",
                        "held": short <= 1 - START_TO_START_SHARE and agree <= CYCLE_AGREE})
    # signal
    levels = {}
    for d in POWER_STEPS_DB:
        tag = tags[f"P{15 - d}"][0]
        sig = [f.signal_dbm for f in in_window(frames, spans[tag], 1) if f.signal_dbm is not None]
        levels[15 - d] = st.mean(sig)
    for step, fall in sorted(signal_steps(levels).items()):
        out.append({"what": "signal follows set power", "item": f"{step} dB down",
                    "measured": round(fall, 2), "predicted": f"{step} ± {SIGNAL_TOL_DB}",
                    "held": abs(fall - step) <= SIGNAL_TOL_DB})
    out.append({"what": "mean signal per set power (dBm)", "item": "pi-A",
                "measured": {p: round(v, 2) for p, v in sorted(levels.items())},
                "predicted": "", "held": "reported"})
    # rate and preamble
    at_1m = sum(f.rate_mbps == 1.0 for f in ours) / len(ours)
    out.append({"what": "every frame at 1 Mb/s", "item": f"{len(ours)} frames",
                "measured": round(at_1m, 6), "predicted": "1.0", "held": at_1m == 1.0})
    out.append({"what": "preamble", "item": "", "measured": "not readable: the driver never sets "
                "the short-preamble flag", "predicted": "", "held": "reported"})
    # bad frames
    lo, hi, _ = spans[tags["X"][0]]
    bad = sum(f.bad_fcs for f in frames if lo - SPAN_MARGIN_NS <= f.host_ns <= hi + SPAN_MARGIN_NS)
    out.append({"what": "bad-checksum frames passed", "item": "the saturated pair",
                "measured": "yes" if bad else "no", "predicted": "no (the driver drops them)",
                "held": "reported"})
    # the WL18xx retest (Blue 1, the last window): frames of pi-A it recorded
    blue1 = sorted((session / "blue1").glob("*.pcap"))
    if blue1:
        lo, hi, _ = spans[tags["W"][0]]
        heard = [f for f in pf.parse(blue1[0]) if f.src_ip == "10.0.0.1" and f.seq is not None
                 and lo - SPAN_MARGIN_NS <= f.host_ns <= hi + SPAN_MARGIN_NS]
        out.append({"what": "WL18xx retest: pi-A's frames recorded", "item": "Blue 1, AP role + "
                    "monitor", "measured": len(heard), "predicted": "0 (wlcore: no filter API)",
                    "held": "reported"})
    return out


def _write(rows: list[dict[str, Any]], path: Path, run: str) -> str:
    from authbc.bench import provenance
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run}.items():
        buf.write(f"# {k}={v}\n")
    wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    path.write_text(buf.getvalue())
    return buf.getvalue()


def main() -> None:
    if "--score" in sys.argv:
        session = Path(sys.argv[sys.argv.index("--score") + 1])
        print(_write(score(session), REPO / "results" / "raw" / f"s0_{session.name}.csv",
                     f"s0_{session.name}"))
    elif "--plan" in sys.argv:
        PLAN.write_text("\n".join(plan()) + "\n")
        print("\n".join(plan()))


if __name__ == "__main__":
    main()
