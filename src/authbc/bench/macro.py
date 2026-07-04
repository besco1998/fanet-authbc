"""End-to-end macrobench pipeline (docs/03 §3 bench/macro).

generator → framer → broadcast channel (loss + airtime) → unpack/verify → per-receiver ledger.
Each UAV signs and packs its own records (placement A or B); every other node overhears each
frame with probability (1−p), verifies it, and ingests the verified records into ITS OWN store.

Metrics: V = verified record-instances / broadcast record-instances (T3's verifiability),
per-receiver store counters, and total sender airtime. Deterministic given the seed.
"""

from __future__ import annotations

from dataclasses import dataclass

from authbc.bench import telemgen
from authbc.channel.emulator import BroadcastChannel
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.store import Store
from authbc.placement.inline import InlineFramer
from authbc.placement.self_batch import SelfBatchFramer
from authbc.placement.wire import decode_frame, encode_frame

_ED = Ed25519Scheme()
_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_FRAMERS = {"A": InlineFramer, "B": SelfBatchFramer}


@dataclass(frozen=True)
class MacroConfig:
    placement: str  # "A" or "B"
    n_uav: int
    records_per_uav: int
    b: int
    p: float
    seed: int


def _payloads(seed: int, n: int) -> list[dict[str, int]]:
    """All n telemetry payloads for a src in one pass (O(n), not O(n²))."""
    return [{k: getattr(r, k) for k in _TELEMETRY} for r in telemgen.samples(seed=seed, n=n)]


def run_macro(cfg: MacroConfig) -> dict:
    srcs = list(range(1, cfg.n_uav + 1))
    keys = {s: _ED.keygen(seed=bytes([s]) * 32) for s in srcs}
    channel = BroadcastChannel(srcs, p=cfg.p, seed=cfg.seed)
    stores = {s: Store() for s in srcs}

    broadcast_instances = verified_instances = 0
    for s in srcs:  # each UAV is a sender
        sk, pk = keys[s]
        chain = Chain(src=s)
        recs = [chain.append(pl, ts=100 + i)
                for i, pl in enumerate(_payloads(s, cfg.records_per_uav))]
        framer = _FRAMERS[cfg.placement](sk)
        for frame in framer.pack(recs, b=cfg.b):
            fbytes = encode_frame(frame)
            broadcast_instances += frame.n * (cfg.n_uav - 1)  # one copy per other node
            for rx in channel.broadcast(s, fbytes):
                out, mask = framer.unpack(decode_frame(fbytes), pk=pk)
                for rec, ok in zip(out, mask, strict=True):
                    if ok:
                        stores[rx].ingest(rec)  # chain-level dedup/replay/equivocation
                        verified_instances += 1

    total_stored = sum(st.counters["stored"] for st in stores.values())
    v = verified_instances / broadcast_instances if broadcast_instances else 0.0
    return {
        "placement": cfg.placement, "n_uav": cfg.n_uav, "records_per_uav": cfg.records_per_uav,
        "b": cfg.b, "p": cfg.p, "seed": cfg.seed,
        "broadcast_instances": broadcast_instances, "verified_instances": verified_instances,
        "V": v, "total_stored": total_stored,
        "total_airtime_us": channel.total_airtime_us(),
    }
