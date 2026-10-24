"""Three classical stream-signing schemes, implemented (revision A10; predictions/A10.md).

The paper placed these by their sizes alone (`models/stream_auth.py`, Table 5), so its figure for
TESLA and EMSS is an upper bound: a delivered frame is not a verified record. Here each is built —
sender and receiver, real keys, MACs, digests and Ed25519 signatures — so that a trace of which
frames a receiver got, and when, gives the time each record became VERIFIED. Sizes follow
`models/stream_auth.py`, so every frame is the size Table 5 simulated:

* **TESLA** (Perrig et al. 2000, §2): a 10 B MAC under the key of the packet's interval, the
  10 B key of interval i − d, a 4 B interval index. Keys form a one-way chain
  (K_i = H(K_{i+1})); a receiver holding K_0 authenticates a disclosed key by hashing it back,
  and accepts a packet only if it arrived before its interval's key could have been disclosed
  (the "safe packet" test, with the receiver's clock bound passed in).
* **EMSS** (Perrig et al. 2000, §3): every data packet carries the digests of the two packets
  before it; every k-th packet is followed by a signature packet that signs the digests of the
  last two data packets. A packet is authenticated once a chain of received packets links it to
  a verified signature packet.
* **Wong–Lam tree** (Wong & Lam 1999, §II-B): a block of four packets, a Merkle tree over their
  digests, the root signed; each packet carries the signature, its position and its two sibling
  digests, and verifies alone.

Truncations follow the sizes Table 5 used (80-bit TESLA MACs and keys, as in its authors'
prototype); they are no recommendation.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Any

from authbc.crypto.ed25519 import Ed25519Scheme

_ED = Ed25519Scheme()
TESLA_MAC = 10
TESLA_KEY = 10
TESLA_INDEX = 4
DIGEST = 32


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# ------------------------------------------------------------------------------------- TESLA
def tesla_chain(seed: bytes, length: int) -> list[bytes]:
    """K_0 … K_{length-1}: K_{n-1} from the seed, K_i = H(K_{i+1}) truncated; K_0 is public."""
    keys = [b""] * length
    keys[-1] = _h(seed)[:TESLA_KEY]
    for i in range(length - 2, -1, -1):
        keys[i] = _h(keys[i + 1])[:TESLA_KEY]
    return keys


def _mac_key(key: bytes) -> bytes:
    return _h(b"tesla-mac" + key)[:TESLA_KEY]


@dataclass
class TeslaSender:
    keys: list[bytes]
    interval_ms: float
    delay: int                     # d: the key of interval i is disclosed in interval i + d
    t0_ms: float = 0.0

    def interval(self, t_ms: float) -> int:
        return int((t_ms - self.t0_ms) // self.interval_ms) + 1      # interval 0 is K_0's

    def packet(self, payload: bytes, t_ms: float) -> bytes:
        i = self.interval(t_ms)
        mac = hmac.new(_mac_key(self.keys[i]), payload + i.to_bytes(TESLA_INDEX, "big"),
                       "sha256").digest()[:TESLA_MAC]
        disclosed = self.keys[i - self.delay] if i - self.delay >= 0 else bytes(TESLA_KEY)
        return payload + i.to_bytes(TESLA_INDEX, "big") + mac + disclosed


@dataclass
class TeslaReceiver:
    commitment: bytes              # K_0
    interval_ms: float
    delay: int
    payload_bytes: int
    t0_ms: float = 0.0
    max_sync_error_ms: float = 0.0
    _known: dict[int, bytes] = field(default_factory=dict)
    _held: list[tuple[int, bytes, bytes]] = field(default_factory=list)   # (interval, body, mac)
    unsafe: int = 0

    def __post_init__(self) -> None:
        self._known[0] = self.commitment

    def _authentic_key(self, j: int, key: bytes) -> bool:
        if j in self._known:
            return self._known[j] == key
        below = max(k for k in self._known if k < j)
        k = key
        for _ in range(j - below):
            k = _h(k)[:TESLA_KEY]
        if k != self._known[below]:
            return False
        self._known[j] = key
        return True

    def receive(self, data: bytes, t_ms: float) -> list[bytes]:
        """Payloads that became authenticated on this packet's arrival."""
        body = data[:self.payload_bytes]
        rest = data[self.payload_bytes:]
        i = int.from_bytes(rest[:TESLA_INDEX], "big")
        mac = rest[TESLA_INDEX:TESLA_INDEX + TESLA_MAC]
        disclosed = rest[TESLA_INDEX + TESLA_MAC:]
        # safe only if K_i cannot yet have been disclosed when the packet arrived
        disclosure_ms = self.t0_ms + (i + self.delay - 1) * self.interval_ms
        if t_ms + self.max_sync_error_ms < disclosure_ms:
            self._held.append((i, body, mac))
        else:
            self.unsafe += 1
        j = i - self.delay
        if j < 1 or not self._authentic_key(j, disclosed):
            return []
        out, keep = [], []
        for interval, held_body, held_mac in self._held:
            if interval <= j:
                key = self._derive(interval)
                good = hmac.new(_mac_key(key), held_body + interval.to_bytes(TESLA_INDEX, "big"),
                                "sha256").digest()[:TESLA_MAC]
                if hmac.compare_digest(good, held_mac):
                    out.append(held_body)
            else:
                keep.append((interval, held_body, held_mac))
        self._held = keep
        return out

    def _derive(self, interval: int) -> bytes:
        above = min(k for k in self._known if k >= interval)
        key = self._known[above]
        for _ in range(above - interval):
            key = _h(key)[:TESLA_KEY]
        return key


# -------------------------------------------------------------------------------------- EMSS
@dataclass
class EmssSender:
    sk: Any
    period: int                    # a signature packet after every `period` data packets
    _last: list[bytes] = field(default_factory=lambda: [bytes(DIGEST), bytes(DIGEST)])
    _count: int = 0

    def packets(self, payload: bytes) -> list[bytes]:
        """The data packet for `payload`, followed by a signature packet when one is due."""
        data = b"D" + payload + self._last[0] + self._last[1]
        self._last = [_h(data), self._last[0]]
        self._count += 1
        if self._count % self.period:
            return [data]
        digests = self._last[0] + self._last[1]
        return [data, b"S" + digests + _ED.sign(self.sk, digests)]


@dataclass
class EmssReceiver:
    pk: Any
    payload_bytes: int
    _by_digest: dict[bytes, bytes] = field(default_factory=dict)    # digest -> packet
    _trusted: set[bytes] = field(default_factory=set)

    def receive(self, data: bytes) -> list[bytes]:
        """Payloads that became authenticated on this packet's arrival."""
        if data[:1] == b"S":
            digests, sig = data[1:1 + 2 * DIGEST], data[1 + 2 * DIGEST:]
            if not _ED.verify(self.pk, digests, sig):
                return []
            new = [digests[:DIGEST], digests[DIGEST:]]
        else:
            d = _h(data)
            self._by_digest[d] = data
            if d not in self._trusted:
                return []
            new = [d]
        return self._spread(new)

    def _spread(self, digests: list[bytes]) -> list[bytes]:
        """Trust every digest reachable from the newly trusted ones through held packets."""
        out: list[bytes] = []
        stack = [d for d in digests if d not in self._trusted]
        while stack:
            d = stack.pop()
            if d in self._trusted:
                continue
            self._trusted.add(d)
            packet = self._by_digest.get(d)
            if packet is None:
                continue                      # trusted now; authenticated when it arrives
            out.append(packet[1:1 + self.payload_bytes])
            tail = packet[1 + self.payload_bytes:]
            stack += [tail[:DIGEST], tail[DIGEST:]]
        return out


# ---------------------------------------------------------------------------- Wong-Lam tree
def wong_lam_block(payloads: list[bytes], sk: Any) -> list[bytes]:
    """Four packets, each: payload ‖ position ‖ two sibling digests ‖ the root's signature."""
    if len(payloads) != 4:
        raise ValueError("this implementation signs blocks of four")
    leaves = [_h(p) for p in payloads]
    inner = [_h(leaves[0] + leaves[1]), _h(leaves[2] + leaves[3])]
    root = _h(inner[0] + inner[1])
    sig = _ED.sign(sk, root)
    return [p + bytes([k]) + leaves[k ^ 1] + inner[1 - k // 2] + sig
            for k, p in enumerate(payloads)]


def wong_lam_verify(packet: bytes, pk: Any, payload_bytes: int) -> bytes | None:
    """The payload if the packet verifies alone, else None."""
    p = packet[:payload_bytes]
    k = packet[payload_bytes]
    sib, uncle = (packet[payload_bytes + 1:payload_bytes + 1 + DIGEST],
                  packet[payload_bytes + 1 + DIGEST:payload_bytes + 1 + 2 * DIGEST])
    sig = packet[payload_bytes + 1 + 2 * DIGEST:]
    leaf = _h(p)
    pair = _h(leaf + sib) if k % 2 == 0 else _h(sib + leaf)
    root = _h(pair + uncle) if k < 2 else _h(uncle + pair)
    return p if _ED.verify(pk, root, sig) else None
