#!/usr/bin/env python3
"""The preflight before W1p, W1q and W1r, on the three Pis alone: three rate checks, GO or not.

hw/channel/README.md §"Preflight before every long run", rules 1 and 5, without the TP-Link of
`hw_preflight.py`; plan `experiments/channel24/plan_w1pqr_preflight.txt`, run by
`hw/channel/run_window_plan2.sh`. Frame burst is checked as those sessions' validity requires
(`predictions/W1p.md`, "Validity").

* **GO:** every board's files are there; every rate check (R1, R2, R3) is inside W1d's band,
  1.9–2.6 ms per frame; no board reports a throttle bit; frame burst read 0 before and after.
* **RETRY:** the only fault is a cycle below the band. That is F129's first ad-hoc session after a
  boot, limited by its own offered rate (1 666 µs at 600 frames/s on 2026-11-22): the boards, now
  warm, are run once more.
* **NO-GO** otherwise.

The preflight is never scored; it decides only whether a long run starts.

    python analysis/pis_preflight.py DIR   -> exit 0 GO, 4 RETRY, 3 NO-GO
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dsss_three as w1d  # noqa: E402
import hw_session as hs  # noqa: E402

NODES = (1, 2, 3)                     # pi-A, pi-B, the Pi 3
EXIT = {"GO": 0, "NO-GO": 3, "RETRY": 4}


@dataclass
class Result:
    """The verdict with its reasons: `too_fast` alone gives RETRY, anything in `failing` NO-GO."""
    cycles: dict[str, float | None] = field(default_factory=dict)
    too_fast: list[str] = field(default_factory=list)
    failing: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "NO-GO" if self.failing else ("RETRY" if self.too_fast else "GO")


def _throttle_values(node_dir: Path) -> set[str]:
    values: set[str] = set()
    for path in node_dir.glob("ctr_node*_*.json"):
        ctr = json.loads(path.read_text())
        values |= {ctr.get("throttled_before", "missing"), ctr.get("throttled_after", "missing")}
    return values


def check(session: Path) -> Result:
    missing = [n for n in NODES if not (session / f"node{n}" / "session.log").is_file()]
    if missing:
        return Result(failing=[f"node {n}: no session.log" for n in missing])
    r = Result()
    cycles, fast, failing = r.cycles, r.too_fast, r.failing
    for w in w1d.window_rows(session):
        if not w1d.RATE_CHECK.fullmatch(w["label"]):
            continue
        c = w.get("cycle_us")
        cycles[w["window"]] = c
        if c is None:
            failing.append(f"{w['window']}: no cycle")
        elif c < 1e6 * w1d.RATE_BAND_S[0]:
            fast.append(f"{w['window']}: {c} us")
        elif c > 1e6 * w1d.RATE_BAND_S[1]:
            failing.append(f"{w['window']}: slow, {c} us")
    if len(cycles) != len(NODES):
        failing.append(f"{len(cycles)} rate checks, not {len(NODES)}")
    for n in NODES:
        fb = hs.frameburst(session, n)
        if fb != ("0", "0"):
            failing.append(f"node {n}: frame burst {fb}")
        throttled = _throttle_values(session / f"node{n}") - {"0x0"}
        if throttled:
            failing.append(f"node {n}: throttled {sorted(throttled)}")
    return r


def main() -> None:
    r = check(Path(sys.argv[1]))
    for window, c in r.cycles.items():
        print(f"{window}: cycle {c} us")
    print(f"verdict: {r.verdict} | too fast: {r.too_fast} | failing: {r.failing}")
    sys.exit(EXIT[r.verdict])


if __name__ == "__main__":
    main()
