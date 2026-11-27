#!/usr/bin/env python3
"""S0b — the AR9271 sniffer's gate, beside the TP-Link (predictions/S0b.md; docs/DECISIONS.md,
2026-11-23 "After the gate S0 failed" and 2026-11-27 "S0b's signal criterion").

Two sniffers record the same session: the AR9271 (mainline `ath9k_htc`, the capture under test,
`SESSION/sniffer_ar/`) and the TP-Link (the TSF build, `SESSION/sniffer/`). Scored on the AR9271:

* **completeness:** every Pi's 1 000 frames at 50 frames/s, ≥ 0.99 each (S0 found the misses
  depend on the sender, so all three are scored);
* **TSFT** on ≥ 0.99 of our frames; in each saturated rate check, < 1 % of consecutive intervals
  below the airtime, and **the mean** interval within 1 % of the receivers' cycle (S0's median
  against a mean was a registration error);
* **signal:** pi-A at 15, 12, 9, 6 dBm; on the frames both sniffers recorded, the AR9271's fall
  from 15 dBm equals the TP-Link's within ±1.0 dB at each step (Mohamed, 2026-11-27);
* **rate:** every frame of ours at 1 Mb/s.

Reported: the preamble (ath9k reports it), bad-checksum frames in the saturated pair (expected:
some), the TP-Link's completeness, both sniffers' falls against the set power, and the diagnostic:
pi-B's and the Pi 3's own steps at the AR9271 (Mohamed's rule, `linearity_verdict`).

    python analysis/s0b.py --score SESSION     -> results/raw/s0b_<session>.csv
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
import hw_mac_timing as mt  # noqa: E402
import hw_session as hs  # noqa: E402
import pcap_frames as pf  # noqa: E402
import s0  # noqa: E402

COMPLETENESS_MIN = 0.99
TSFT_SHARE_MIN = 0.99
BELOW_AIRTIME_MAX = 0.01
MEAN_AGREE = 0.01
AGREE_DB = 1.0               # the AR9271's step against the TP-Link's, same frames
LINEAR_DB = 1.5              # the diagnostic: pi-B's and the Pi 3's steps against the set power
STEPS_DBM = (15, 12, 9, 6)
LABEL = {1: "PA", 2: "PB", 3: "PC"}


def capture(session: Path, folder: str) -> list[pf.Frame]:
    caps = sorted((session / folder).glob("*.pcap"))
    if len(caps) != 1:
        raise FileNotFoundError(f"{session}/{folder}: {len(caps)} captures, not 1")
    return list(pf.parse(caps[0]))


def by_seq(frames: list[pf.Frame]) -> dict[int, pf.Frame]:
    out: dict[int, pf.Frame] = {}
    for f in frames:
        if f.seq is not None:
            out.setdefault(f.seq, f)
    return out


def falls(levels: dict[int, float]) -> dict[int, float]:
    """{step dB: fall from 15 dBm} from {set dBm: mean signal}."""
    return {15 - p: levels[15] - v for p, v in levels.items() if p != 15}


def linearity_verdict(steps: dict[int, dict[int, float]]) -> str:
    """Mohamed's rule (2026-11-27), on pi-B's and the Pi 3's falls at the AR9271,
    {node: {step: fall}}."""
    if all(abs(f - s) <= LINEAR_DB for d in steps.values() for s, f in d.items()):
        return "the AR9271 is linear; the compression is pi-A's transmitter"
    return ("sender and receiver compression cannot be separated without an external reference; "
            "the HackRF measurement is proposed")


def score(session: Path) -> list[dict[str, Any]]:
    ar, tp = capture(session, "sniffer_ar"), capture(session, "sniffer")
    spans = s0.window_spans(session)
    files = w1d._files(session)
    tags: dict[str, list[str]] = {}
    for tag in sorted(spans, key=lambda x: int(x.split("_")[0])):
        tags.setdefault(tag.split("_")[1], []).append(tag)
    log = (session / "sniffer_ar" / "sniffer.log").read_text() if (
        session / "sniffer_ar" / "sniffer.log").is_file() else ""
    out: list[dict[str, Any]] = [
        {"what": "frame burst off on every board", "item": "", "measured": "",
         "predicted": "0 before and after", "held": hs.frameburst_off(session)},
        {"what": "the sniffer under test is ath9k_htc", "item": "", "measured":
         "yes" if "module ath9k_htc" in log else "no", "predicted": "yes",
         "held": "module ath9k_htc" in log}]
    for n in (1, 2, 3):
        tag = tags[f"G{n}"][0]
        sent = files[tag]["tx"][n]["sent"]
        share = s0.completeness(s0.in_window(ar, spans[tag], n), sent)
        tp_share = s0.completeness(s0.in_window(tp, spans[tag], n), sent)
        out.append({"what": "capture completeness (AR9271)", "item": f"node {n}, {sent} sent",
                    "measured": round(share, 5), "predicted": f">= {COMPLETENESS_MIN}",
                    "held": share >= COMPLETENESS_MIN})
        out.append({"what": "capture completeness (TP-Link)", "item": f"node {n}",
                    "measured": round(tp_share, 5), "predicted": "", "held": "reported"})
    ours = [f for f in ar if f.src_ip and f.src_ip.startswith("10.0.0.") and f.seq is not None]
    tsft = sum(f.tsft_us is not None for f in ours) / len(ours)
    out.append({"what": "TSFT present (AR9271)", "item": f"{len(ours)} frames",
                "measured": round(tsft, 5), "predicted": f">= {TSFT_SHARE_MIN}",
                "held": tsft >= TSFT_SHARE_MIN})
    for w in w1d.window_rows(session):
        if not w1d.RATE_CHECK.fullmatch(w["label"]) or tsft < TSFT_SHARE_MIN:
            continue
        n = int(w["label"][1])
        d = mt.intervals(s0.in_window(ar, spans[w["window"]], n))
        below = sum(x < s0.T_F_US for x in d) / len(d)
        agree = abs(st.mean(d) - w["cycle_us"]) / w["cycle_us"]
        out.append({"what": "TSFT start-to-start (AR9271)", "item": w["window"],
                    "measured": f"{len(d)} pairs; below airtime {100 * below:.2f} %; mean "
                                f"{st.mean(d):.1f} us against {w['cycle_us']} us "
                                f"({100 * agree:.2f} %)",
                    "predicted": "below < 1 %; mean within 1 %",
                    "held": below < BELOW_AIRTIME_MAX and agree <= MEAN_AGREE})
    # signal: pi-A's steps on the frames both sniffers recorded
    lv_ar: dict[int, float] = {}
    lv_tp: dict[int, float] = {}
    for p in STEPS_DBM:
        tag = tags[f"PA{p}"][0]
        a, t = by_seq(s0.in_window(ar, spans[tag], 1)), by_seq(s0.in_window(tp, spans[tag], 1))
        both = [q for q in a if q in t and a[q].signal_dbm is not None
                and t[q].signal_dbm is not None]
        lv_ar[p] = st.mean(float(a[q].signal_dbm or 0) for q in both)
        lv_tp[p] = st.mean(float(t[q].signal_dbm or 0) for q in both)
    f_ar, f_tp = falls(lv_ar), falls(lv_tp)
    for step in sorted(f_ar):
        out.append({"what": "signal step: AR9271 against TP-Link, same frames",
                    "item": f"pi-A {step} dB down", "measured":
                    f"AR9271 {f_ar[step]:.2f}, TP-Link {f_tp[step]:.2f} dB",
                    "predicted": f"equal within ±{AGREE_DB}",
                    "held": abs(f_ar[step] - f_tp[step]) <= AGREE_DB})
    rate = sum(f.rate_mbps == 1.0 for f in ours) / len(ours)
    out.append({"what": "every frame at 1 Mb/s (AR9271)", "item": f"{len(ours)} frames",
                "measured": round(rate, 6), "predicted": "1.0", "held": rate == 1.0})
    # reported
    short = sum(bool(f.short_preamble) for f in ours) / len(ours)
    out.append({"what": "short-preamble share (AR9271)", "item": "", "measured": round(short, 4),
                "predicted": "", "held": "reported"})
    lo, hi, _ = spans[tags["X"][0]]
    bad = sum(f.bad_fcs for f in ar if lo - s0.SPAN_MARGIN_NS <= f.host_ns
              <= hi + s0.SPAN_MARGIN_NS)
    out.append({"what": "bad-checksum frames passed (AR9271)", "item": "the saturated pair",
                "measured": bad, "predicted": "some (fcsfail)", "held": "reported"})
    out.append({"what": "pi-A's falls against the set power", "item": "AR9271 | TP-Link",
                "measured": f"{ {s: round(v, 2) for s, v in sorted(f_ar.items())} } | "
                            f"{ {s: round(v, 2) for s, v in sorted(f_tp.items())} }",
                "predicted": "3, 6, 9", "held": "reported"})
    diag: dict[int, dict[int, float]] = {}
    for n in (2, 3):
        lv = {}
        for p in STEPS_DBM:
            fr = s0.in_window(ar, spans[tags[f"{LABEL[n]}{p}"][0]], n)
            lv[p] = st.mean(float(f.signal_dbm) for f in fr if f.signal_dbm is not None)
        diag[n] = falls(lv)
        out.append({"what": "diagnostic: steps at the AR9271", "item": f"node {n}",
                    "measured": {s: round(v, 2) for s, v in sorted(diag[n].items())},
                    "predicted": f"3, 6, 9 ± {LINEAR_DB}", "held": "reported"})
    out.append({"what": "diagnostic: who compresses", "item": "", "measured":
                linearity_verdict(diag), "predicted": "", "held": "reported"})
    return out


def main() -> None:
    from authbc.bench import provenance
    session = Path(sys.argv[sys.argv.index("--score") + 1])
    rows = score(session)
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": f"s0b_{session.name}"}.items():
        buf.write(f"# {k}={v}\n")
    wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    (REPO / "results" / "raw" / f"s0b_{session.name}.csv").write_text(buf.getvalue())
    print(buf.getvalue())


if __name__ == "__main__":
    main()
