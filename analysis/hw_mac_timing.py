#!/usr/bin/env python3
"""C1 — each sender alone, its MAC timing from the sniffer's TSFT (the frame-level campaign;
predictions/C1.md; docs/DECISIONS.md, 2026-11-23). Calibration: every number is reported, none is
scored, and none is used to score anything it was measured from.

From a sender's frames in one window, in the order the sniffer received them:

* **start-to-start intervals** between consecutive sequence numbers, both captured: a pair that
  straddles a frame the sniffer missed is excluded by its sequence numbers (Mohamed, 2026-11-23);
* **the gap** after a frame, its interval less the frame's airtime at 1 Mb/s with the long preamble
  (192 µs + 8 µs per byte of the MPDU: the UDP payload plus 64 B of UDP, IP, LLC/SNAP, MAC header
  and FCS);
* **the lattice:** the spacing σ of the gap histogram (1 µs bins), the lag of its autocorrelation's
  smallest lag within 80 % of the highest peak between 5 and 40 µs (a harmonic can peak as high);
* **the floor:** the gap's 1st percentile, and the share of gaps within σ/2 of it, the share sent
  with no backoff (W1s's observation: 37–46 % for the Pi 4s, from the receivers);
* **the backoff index** k = round((gap − floor)/σ): W − 1 where its histogram (k ≥ 1) falls below
  half its plateau and stays there (`w_minus_1`), the share at k = 0, and the share beyond 128
  slots (the tail no uniform backoff explains);
* **airtime across sizes:** the 1st percentile of the interval against the MPDU length, by least
  squares: the slope against 8 µs/B (1 Mb/s), the intercept against preamble + DIFS (242 µs for
  the long preamble and the standard's 50 µs, 220 µs with 28 µs, 146 µs with the short preamble);
* **the sensitivity to missed frames:** the same statistics on the pairs whose neighbours on both
  sides were also captured, and the receivers' kernel-timestamp mean cycle beside the sniffer's.

    python analysis/hw_mac_timing.py SESSION   -> results/raw/c1_<session>.csv
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
import pcap_frames as pf  # noqa: E402
import s0  # noqa: E402

PREAMBLE_LONG_US = 192.0
US_PER_BYTE = 8.0                    # 1 Mb/s
MPDU_OVERHEAD = 64                   # UDP 8 + IP 20 + LLC/SNAP 8 + MAC header 24 + FCS 4
LAG_MIN_US, LAG_MAX_US = 5, 40
HARMONIC_SHARE = 0.8
FLOOR_Q = 0.01
K_SCAN = 128


def airtime_us(payload: int) -> float:
    return PREAMBLE_LONG_US + US_PER_BYTE * (payload + MPDU_OVERHEAD)


def intervals(frames: list[pf.Frame], strict: bool = False) -> list[float]:
    """Consecutive sequence numbers' TSFT differences. strict: the pair's neighbours on both sides
    (a − 1 and b + 1) were captured too, so no missed frame is next to it."""
    timed = [f for f in frames if f.tsft_us is not None and f.seq is not None]
    t = s0.unwrap_tsft([f.tsft_us for f in timed if f.tsft_us is not None])
    by_seq: dict[int, int] = {}
    for f, u in zip(timed, t, strict=True):
        if f.seq is not None:
            by_seq.setdefault(f.seq, u)
    out = []
    for a in sorted(by_seq):
        b = a + 1
        if b not in by_seq:
            continue
        if strict and (a - 1 not in by_seq or b + 1 not in by_seq):
            continue
        out.append(float(by_seq[b] - by_seq[a]))
    return out


def quantile(v: list[float], q: float) -> float:
    s = sorted(v)
    return s[min(len(s) - 1, max(0, round(q * (len(s) - 1))))]


def lattice_us(gaps: list[float]) -> int | None:
    """The lag (µs) of the gap histogram's highest autocorrelation peak in 5–40 µs, or None."""
    lo = int(min(gaps))
    hist: dict[int, int] = {}
    for g in gaps:
        hist[int(g) - lo] = hist.get(int(g) - lo, 0) + 1
    n = max(hist) + 1
    h = [hist.get(i, 0) for i in range(n)]
    mean = sum(h) / n
    d = [x - mean for x in h]
    c = {lag: sum(d[i] * d[i + lag] for i in range(n - lag))
         for lag in range(LAG_MIN_US, LAG_MAX_US + 1)}
    top = max(c.values())
    if top <= 0:
        return None
    # the smallest lag near the highest peak: a harmonic (2σ, 3σ) can peak as high as σ itself
    return min(lag for lag, v in c.items() if v >= HARMONIC_SHARE * top)


def w_minus_1(k: list[int]) -> int | None:
    """Where the backoff index's histogram (k ≥ 1) falls below half its plateau (the median count
    over k = 1 … 8) and stays below for three indices: W − 1 if the backoff is uniform on
    0 … W − 1. The k = 0 cell is left out: it also holds the frames sent with no backoff."""
    counts = [sum(1 for x in k if x == i) for i in range(K_SCAN + 1)]
    plateau = st.median(counts[1:9])
    if plateau <= 0:
        return None
    for i in range(1, K_SCAN - 2):
        if all(counts[j] < 0.5 * plateau for j in (i, i + 1, i + 2)):
            return i - 1
    return None


def gap_stats(gaps: list[float]) -> dict[str, Any]:
    floor = quantile(gaps, FLOOR_Q)
    sigma = lattice_us(gaps)
    out: dict[str, Any] = {"pairs": len(gaps), "gap_mean_us": round(st.mean(gaps), 1),
                           "gap_median_us": round(st.median(gaps), 1),
                           "gap_floor_us": round(floor, 1), "lattice_us": sigma}
    if sigma:
        k = [round((g - floor) / sigma) for g in gaps]
        out |= {"share_no_backoff": round(sum(1 for g in gaps if abs(g - floor) <= sigma / 2)
                                          / len(gaps), 4),
                "w_minus_1": w_minus_1(k),
                "share_k0": round(sum(1 for x in k if x == 0) / len(k), 4),
                "share_beyond_scan": round(sum(1 for x in k if x > K_SCAN) / len(k), 4)}
    return out


def airtime_fit(points: list[tuple[int, float]]) -> dict[str, float]:
    """Least squares of the interval's 1st percentile against the MPDU length: slope, intercept."""
    x = [float(p + MPDU_OVERHEAD) for p, _ in points]
    y = [v for _, v in points]
    mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / sxx
    return {"slope_us_per_byte": round(slope, 3), "intercept_us": round(my - slope * mx, 1)}


def score(session: Path) -> list[dict[str, Any]]:
    frames = s0.sniffer_frames(session)
    spans = s0.window_spans(session)
    files = w1d._files(session)
    cycles = {w["window"]: w.get("cycle_us") for w in w1d.window_rows(session)}
    out: list[dict[str, Any]] = []
    floors: dict[int, list[tuple[int, float]]] = {}
    for tag in sorted(spans, key=lambda x: int(x.split("_")[0])):
        _lo, _hi, senders = spans[tag]
        if len(senders) != 1:
            continue
        n = senders[0]
        tx = files[tag]["tx"][n]
        got = s0.in_window(frames, spans[tag], n)
        d = intervals(got)
        if len(d) < 50:
            continue
        payload = int(tx["bytes"])
        rate = float(tag.rsplit("_", 1)[1].removesuffix("fps"))
        row: dict[str, Any] = {"window": tag, "sender": n, "payload": payload, "offered": rate,
                               "sent": tx["sent"],
                               "completeness": round(s0.completeness(got, tx["sent"]), 4),
                               "interval_mean_us": round(st.mean(d), 1),
                               "interval_p01_us": round(quantile(d, FLOOR_Q), 1),
                               "receivers_cycle_us": cycles.get(tag)}
        gaps = [x - airtime_us(payload) for x in d]
        row |= gap_stats(gaps)
        strict = [x - airtime_us(payload) for x in intervals(got, strict=True)]
        if len(strict) >= 50:
            s = gap_stats(strict)
            row |= {"strict_pairs": s["pairs"], "strict_gap_mean_us": s["gap_mean_us"],
                    "strict_share_no_backoff": s.get("share_no_backoff")}
        out.append(row)
        if rate >= 600:
            floors.setdefault(n, []).append((payload, row["interval_p01_us"]))
    for n, pts in sorted(floors.items()):
        if len({p for p, _ in pts}) >= 2:
            out.append({"window": "airtime fit", "sender": n, "payload": "all sizes",
                        **airtime_fit(sorted(pts))})
    return out


def main() -> None:
    from authbc.bench import provenance
    session = Path(sys.argv[1])
    rows = score(session)
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": f"c1_{session.name}"}.items():
        buf.write(f"# {k}={v}\n")
    wr = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                        lineterminator="\n", restval="")
    wr.writeheader()
    wr.writerows(rows)
    (REPO / "results" / "raw" / f"c1_{session.name}.csv").write_text(buf.getvalue())
    print(buf.getvalue())


if __name__ == "__main__":
    main()
