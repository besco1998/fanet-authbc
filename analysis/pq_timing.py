#!/usr/bin/env python3
"""Falcon-512 and ML-DSA-44 sign and verify times from liboqs 0.16.0 `speed_sig` (revision A15;
predictions/A15.md, its timing part).

`speed_sig -d 10 <alg>`, three repetitions per algorithm, on a quiet host and on pi-B (logs from
`~/.cache/authbc-logs/a15_host_speed.sh` and the board's run script). Each repetition reports a
mean time per operation over ~10 s; the row gives the median of the three and their range.
What a frame costs follows at the design's rates: a sender signs 12.5 frames/s, a receiver of
124 neighbours verifies 1 550 frames/s.

    python analysis/pq_timing.py LOG [LOG ...]     # results/hw/pq_speed_sig.<host>.csv each
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SIGN_RATE, VERIFY_RATE = 12.5, 124 * 12.5
OPS = ("keypair", "sign", "verify")


def parse(text: str) -> dict[tuple[str, str], list[float]]:
    """(algorithm, operation) -> the mean µs of each repetition."""
    out: dict[tuple[str, str], list[float]] = defaultdict(list)
    alg = None
    for line in text.splitlines():
        if m := re.match(r"## rep \d+ (\S+)", line):
            alg = m.group(1)
            continue
        if line.startswith("Ended at"):      # a repetition ends; the --info run after the last
            alg = None                       # one is not a repetition of anything
            continue
        cols = [c.strip() for c in line.split("|")]
        if alg and len(cols) >= 4 and cols[0] in OPS:
            out[(alg, cols[0])].append(float(cols[3]))     # time (us): mean
    return out


def rows_of(parsed: dict[tuple[str, str], list[float]]) -> list[dict]:
    rows = []
    for (alg, op), means in sorted(parsed.items()):
        med = st.median(means)
        rate = {"sign": SIGN_RATE, "verify": VERIFY_RATE}.get(op)
        rows.append({"alg": alg, "op": op, "reps": len(means), "median_us": round(med, 2),
                     "lo_us": round(min(means), 2), "hi_us": round(max(means), 2),
                     "core_share_at_design_rate": round(med * rate / 1e6, 5) if rate else ""})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", type=Path)
    for log in ap.parse_args().logs:
        text = log.read_text()
        head = re.search(r"^# host (\S+) .*$", text, re.M)
        host = head.group(1) if head else log.stem.split(".")[-1]
        rows = rows_of(parse(text))
        buf = io.StringIO()
        for line in text.splitlines():
            if line.startswith("# ") or line.startswith("--- board"):
                buf.write(f"# {line.lstrip('#- ').strip()}\n")
        buf.write(f"# source={log.name}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        out = REPO / "results" / "hw" / f"pq_speed_sig.{host}.csv"
        out.write_text(buf.getvalue())
        print(out)
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
