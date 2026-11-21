"""Synthetic sessions in the layout `hw/channel/run_window_plan2.sh` writes, for testing the W1p,
W1q and W1r scorers against a known truth. Not a model of the radios: each window's on-air frames,
receptions, receive times and RSSI readings are given by the test."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Window:
    label: str
    rate: float
    senders: tuple[int, ...]
    seconds: int = 25
    # per sender: the receive time in ns of each frame it put on air (seq = index), before jitter
    times: dict[int, list[float]] = field(default_factory=dict)
    # (sender, receiver) -> the set of seqs received
    got: dict[tuple[int, int], set[int]] = field(default_factory=dict)
    sent: dict[int, int] = field(default_factory=dict)   # sendto's count (default: frames on air)
    throttled: str = "0x0"


def write_session(root: Path, nodes: tuple[int, ...], windows: list[Window],
                  stamp: Callable[[int, float], int],
                  rssi: Callable[[int, Window], dict[str, object]],
                  frameburst: tuple[str, str] = ("0", "0")) -> Path:
    """`stamp(receiver, t_ns)` gives a receiver's timestamp of a frame received at true time t;
    `rssi(receiver, window)` gives {"any": text, "peers": {node: text}} for that window."""
    for n in nodes:
        d = root / f"node{n}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "session.log").write_text(
            f"[t] frameburst before the windows: {frameburst[0]} (asked: 0)\n"
            f"[t] frameburst after the windows: {frameburst[1]}\n")
        (d / f"rssi_node{n}.jsonl").write_text("")
    for k, w in enumerate(windows):
        tag = f"{k:02d}_{w.label}_{w.rate:g}fps"
        for r in nodes:
            d = root / f"node{r}"
            by_source, rows = {}, []
            for s in w.senders:
                if s == r:
                    continue
                seqs = sorted(w.got.get((s, r), set()))
                ts = w.times[s]
                if seqs:
                    by_source[f"10.0.0.{s}"] = {
                        "received_unique": len(seqs), "duplicates": 0, "min_seq": seqs[0],
                        "max_seq": seqs[-1], "span_s": (ts[seqs[-1]] - ts[seqs[0]]) / 1e9,
                        "seqs": seqs}
                rows += [(f"10.0.0.{s}", q, stamp(r, ts[q])) for q in seqs]
            rows.sort(key=lambda x: x[2])
            (d / f"rx_node{r}_{tag}.json").write_text(json.dumps(
                {"received_unique": sum(v["received_unique"] for v in by_source.values()),
                 "duplicates": 0, "by_source": by_source}))
            (d / f"rxts_node{r}_{tag}.csv").write_text(
                "src,seq,t_ns\n" + "".join(f"{a},{b},{c}\n" for a, b, c in rows))
            (d / f"ctr_node{r}_{tag}.json").write_text(json.dumps(
                {"tag": tag, "node": r, "senders": ",".join(map(str, w.senders)),
                 "seconds": w.seconds, "tx_packets": 0, "tx_dropped": 0, "rx_packets": 0,
                 "throttled_before": "0x0", "throttled_after": w.throttled}))
            if r in w.senders:
                n_air = len(w.times[r])
                sent = w.sent.get(r, n_air)
                (d / f"tx_node{r}_{tag}.json").write_text(json.dumps(
                    {"sent": sent, "rate": w.rate, "achieved_fps": w.rate, "late": 0}))
            reading = rssi(r, w)
            with (d / f"rssi_node{r}.jsonl").open("a") as fh:
                for when in ("mid", "after"):
                    fh.write(json.dumps({
                        "tag": tag, "when": when, "t": "0", "node": r, "any": reading["any"],
                        "peers": {f"10.0.0.{p}": {"mac": f"02:00:00:00:00:0{p}", "rssi": v}
                                  for p, v in reading["peers"].items()}}) + "\n")
    return root
