"""Parse NS-3 authbc-sat outputs → results/raw CSV (docs/06 §2: never hand-copy numbers).

Reads each run's `<prefix>.stats` (app-level goodput) and, when present, its `<prefix>.flowmon`
(FlowMonitor XML, unicast) for a per-flow throughput cross-check. Writes one tidy row per run.
"""

from __future__ import annotations

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authbc.bench import provenance  # noqa: E402

FIELDS = ["mode", "nNodes", "frameSize", "simTime", "seed", "rx_bytes", "goodput_mbps",
          "flowmon_throughput_mbps"]


def parse_stats(path: Path) -> dict:
    d: dict[str, str] = {}
    for line in path.read_text().splitlines()[1:]:  # skip "key,value" header
        k, _, v = line.partition(",")
        d[k.strip()] = v.strip()
    return d


def parse_flowmon(path: Path) -> float:
    """Aggregate rxBytes / active duration across flows → throughput (Mbit/s)."""
    root = ET.parse(path).getroot()
    rx_bytes = 0
    first, last = None, None
    for flow in root.iter("Flow"):
        rx_bytes += int(flow.get("rxBytes", 0))
        t0 = _to_ns(flow.get("timeFirstTxPacket"))
        t1 = _to_ns(flow.get("timeLastRxPacket"))
        if t0 is not None:
            first = t0 if first is None else min(first, t0)
        if t1 is not None:
            last = t1 if last is None else max(last, t1)
    if not rx_bytes or first is None or last is None or last <= first:
        return 0.0
    return rx_bytes * 8.0 / ((last - first) / 1e9) / 1e6


def _to_ns(val: str | None) -> float | None:
    if not val:
        return None
    return float(val.rstrip("nsN")) if val[-1].isalpha() else float(val)


def main() -> None:
    ap = argparse.ArgumentParser(description="parse NS-3 authbc-sat outputs")
    ap.add_argument("--stats", nargs="+", required=True, help="one or more <prefix>.stats files")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows: list[dict] = []
    for stats_path in args.stats:
        sp = Path(stats_path)
        d = parse_stats(sp)
        fm = sp.with_suffix(".flowmon")
        d["flowmon_throughput_mbps"] = round(parse_flowmon(fm), 4) if fm.exists() else ""
        rows.append({k: d.get(k, "") for k in FIELDS})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        # Law 7 / audit S6: raw CSVs carry env + config provenance. This writer emitted none, so
        # ns3_smoke.csv was the one NS-3 artifact whose producing environment was unrecorded.
        meta = {**provenance.env_block(), "run": "ns3_smoke",
                "config_hash": provenance.config_hash({"stats": sorted(args.stats)})}
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"parsed {len(rows)} runs -> {out}")


if __name__ == "__main__":
    main()
