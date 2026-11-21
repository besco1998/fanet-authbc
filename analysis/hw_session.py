#!/usr/bin/env python3
"""Readers for the files `hw/channel/run_window_plan2.sh` adds to a session (W1p, W1q, W1r of
2026-11-21), beside W1d's tx/rx/ctr JSONs, which `dsss_three.window_rows` reduces unchanged.

A session is `<session>/node<N>/` per board, as the launchers collect it. Per node:
* `rxts_node<N>_<tag>.csv`: src, seq, t_ns, every frame's kernel receive time (`bcast_rx.py
  --timestamps`);
* `rssi_node<N>.jsonl`: one line per reading, halfway through and after each window, with the
  zero-address reading and each peer's by address (`rssi.sh`); a failed read is kept as its
  error text, never as a number;
* `session.log`: the frame-burst read-backs before the first window and after the last.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

FB_BEFORE = re.compile(r"frameburst before the windows: (\S+)")
FB_AFTER = re.compile(r"frameburst after the windows: (\S+)")


def node_dirs(session: Path) -> dict[int, Path]:
    return {int(p.name[4:]): p for p in sorted(session.glob("node*")) if p.name[4:].isdigit()}


def node_of(address: str) -> int:
    """10.0.0.<N> → N."""
    return int(address.rsplit(".", 1)[1])


def timestamps(session: Path, node: int, tag: str) -> dict[int, dict[int, int]]:
    """{sender node: {seq: t_ns}} as received at `node` in window `tag` (first copy kept)."""
    path = node_dirs(session)[node] / f"rxts_node{node}_{tag}.csv"
    out: dict[int, dict[int, int]] = {}
    with path.open() as fh:
        for r in csv.DictReader(fh):
            t = int(r["t_ns"])
            if t > 0:
                out.setdefault(node_of(r["src"]), {}).setdefault(int(r["seq"]), t)
    return out


def _dbm(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def rssi(session: Path, node: int) -> list[dict[str, Any]]:
    """Every reading at `node`: tag, when, "any" and "peers" ({node: dBm}); None if it failed."""
    path = node_dirs(session)[node] / f"rssi_node{node}.jsonl"
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out.append({"tag": r["tag"], "when": r["when"], "any": _dbm(r["any"]),
                    "peers": {node_of(ip): _dbm(p["rssi"]) for ip, p in r["peers"].items()}})
    return out


def frameburst(session: Path, node: int) -> tuple[str, str]:
    """The firmware's frame-burst read-backs, before the first window and after the last."""
    log = (node_dirs(session)[node] / "session.log").read_text()
    b, a = FB_BEFORE.search(log), FB_AFTER.search(log)
    return (b.group(1) if b else "missing", a.group(1) if a else "missing")


def frameburst_off(session: Path) -> bool:
    """Every board read 0 before and after, or the session is void (W1p, W1q, W1r)."""
    return all(frameburst(session, n) == ("0", "0") for n in node_dirs(session))
