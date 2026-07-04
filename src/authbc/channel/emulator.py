"""In-process 802.11 broadcast emulator + airtime ledger (docs/01 §1, docs/03 §3 channel/).

One sender broadcasts a frame; every OTHER node receives it independently with probability
(1−p) — per-receiver i.i.d. Bernoulli(p) drop from a single seeded RNG (deterministic given the
seed). Airtime is charged to the **sender only, once per frame** (broadcast has one transmission,
no ACKs) — receivers add none, which is the anti-double-counting invariant. MTU is enforced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np

from authbc.channel.airtime import airtime_broadcast
from authbc.placement.framer import M_MTU


@dataclass
class NodeMetrics:
    frames_tx: int = 0
    frames_rx: int = 0
    bytes_tx: int = 0
    bytes_rx: int = 0
    airtime_us: float = 0.0


class BroadcastChannel:
    def __init__(self, node_ids: Sequence[int], p: float, seed: int, *, mtu: int = M_MTU) -> None:
        if not (0.0 <= p <= 1.0):
            raise ValueError("p must be in [0,1]")
        self.p = p
        self.mtu = mtu
        self.node_ids = list(node_ids)
        self._rng = np.random.default_rng(seed)
        self.metrics: dict[int, NodeMetrics] = {n: NodeMetrics() for n in self.node_ids}

    def broadcast(self, sender: int, frame_bytes: bytes) -> list[int]:
        """Broadcast one frame; return the list of node_ids that received it (kept w.p. 1−p)."""
        length = len(frame_bytes)
        if length > self.mtu:
            raise ValueError(f"frame {length} B exceeds MTU {self.mtu} B")
        s = self.metrics[sender]
        s.frames_tx += 1
        s.bytes_tx += length
        s.airtime_us += airtime_broadcast(length)  # sender-only, once per frame

        received: list[int] = []
        for nid in self.node_ids:  # fixed order ⇒ reproducible draws
            if nid == sender:
                continue
            if self._rng.random() >= self.p:  # kept with probability (1−p)
                r = self.metrics[nid]
                r.frames_rx += 1
                r.bytes_rx += length
                received.append(nid)
        return received

    def total_airtime_us(self) -> float:
        return sum(m.airtime_us for m in self.metrics.values())

    def metrics_rows(self) -> list[dict]:
        """Tidy rows (sorted by node) — same seed ⇒ byte-identical output (determinism gate)."""
        return [{"node": n, **asdict(self.metrics[n])} for n in sorted(self.metrics)]
