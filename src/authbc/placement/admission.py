"""What a receiver checks before it spends a signature verification (revision A7;
predictions/A7.md).

Every frame that reaches `LeanReceiver` costs a decode, a rebuild of its records (one SHA-256
each) and an Ed25519 verification, whether or not it is genuine, so a flood of frames that name
a real sender, carry a newer sequence number and a wrong signature costs the receiver as much
as honest traffic. The plan compares four admission steps, applied here IN ORDER, each cheaper
than the next:

1. **Group MAC** (optional): an 8 B truncated HMAC-SHA256 under a key every swarm member
   holds, prepended to the frame (`GroupMac.wrap`). An outsider's frame is refused at the
   cost of one HMAC. Zero bytes of the frame format change: the tag is an envelope around it.
2. **Cheap checks**: the frame's length lies in the range a lean frame can have, its CBOR map
   parses with the eight keys, it names a known sender, and its sequence number is newer than
   the last accepted and no more than `window` ahead — all before any record is rebuilt.
3. **Per-sender rate cap**: a token bucket at the sender's own frame rate times (1 + slack);
   an impostor can then crowd out only the sender it names.
4. The receiver itself: decode, rebuild, verify, store.

`AdmissionReceiver` counts what each stage refused, so the harness can price each path.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import cbor2

from authbc.placement.session_v2 import LeanReceiver, Receipt, Received
from authbc.placement.wire_v2 import F_BASE_SEQ, F_N, F_SRC, MAX_RECORDS

TAG_BYTES = 8


class Refused(StrEnum):
    MAC = "mac"
    SHAPE = "shape"
    UNKNOWN = "unknown_sender"
    SEQ_WINDOW = "seq_window"
    RATE = "rate"


@dataclass(frozen=True)
class GroupMac:
    key: bytes
    tag_bytes: int = TAG_BYTES

    def tag(self, frame: bytes) -> bytes:
        return hmac.new(self.key, frame, hashlib.sha256).digest()[:self.tag_bytes]

    def wrap(self, frame: bytes) -> bytes:
        return self.tag(frame) + frame

    def unwrap(self, data: bytes) -> bytes | None:
        """The frame if its tag is right, else None (constant-time comparison)."""
        frame = data[self.tag_bytes:]
        return frame if hmac.compare_digest(data[:self.tag_bytes], self.tag(frame)) else None


@dataclass
class TokenBucket:
    rate: float                          # frames per second
    burst: float
    _tokens: float = 0.0
    _last: float | None = None

    def take(self, t_s: float) -> bool:
        if self._last is None:
            self._tokens = self.burst
        else:
            self._tokens = min(self.burst, self._tokens + (t_s - self._last) * self.rate)
        self._last = t_s
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


@dataclass(frozen=True)
class Policy:
    group_mac: GroupMac | None = None
    cheap_checks: bool = False
    window: int = 1024                   # how far ahead of the last accepted seq a frame may be
    min_bytes: int = 120                 # the lean frame's shortest (one record, small ints)
    max_bytes: int = 1500
    rate_cap: float | None = None        # frames/s per sender; None = no cap
    slack: float = 0.5
    burst: float = 4.0


@dataclass
class AdmissionReceiver:
    inner: LeanReceiver
    policy: Policy
    known: frozenset[int]                # senders whose keys the receiver holds
    refused: dict[str, int] = field(default_factory=lambda: {r.value: 0 for r in Refused})
    _buckets: dict[int, TokenBucket] = field(default_factory=dict)
    _last_seq: dict[int, int] = field(default_factory=dict)

    def receive(self, data: bytes, t_s: float = 0.0) -> Received | Refused:
        p = self.policy
        frame = data
        if p.group_mac is not None:
            unwrapped = p.group_mac.unwrap(data)
            if unwrapped is None:
                return self._refuse(Refused.MAC)
            frame = unwrapped
        if p.cheap_checks:
            reason = self._cheap(frame)
            if reason is not None:
                return self._refuse(reason)
        if p.rate_cap is not None:
            src = _peek_or_none(frame)
            if src is not None:
                bucket = self._buckets.setdefault(
                    src, TokenBucket(p.rate_cap * (1 + p.slack), p.burst))
                if not bucket.take(t_s):
                    return self._refuse(Refused.RATE)
        got = self.inner.receive(frame)
        if got.receipt is Receipt.ACCEPTED and got.records:
            self._last_seq[got.records[0].src] = got.records[-1].seq
        return got

    def _cheap(self, frame: bytes) -> Refused | None:
        if not self.policy.min_bytes <= len(frame) <= self.policy.max_bytes:
            return Refused.SHAPE
        header = _peek_or_none(frame, full=True)
        if header is None:
            return Refused.SHAPE
        src, base_seq, n = header
        if src not in self.known:
            return Refused.UNKNOWN
        last = self._last_seq.get(src)
        if last is not None and (base_seq <= last or base_seq > last + 1 + self.policy.window):
            return Refused.SEQ_WINDOW
        if not 1 <= n <= MAX_RECORDS:
            return Refused.SHAPE
        return None

    def _refuse(self, reason: Refused) -> Refused:
        self.refused[reason.value] += 1
        return reason


def _peek_or_none(frame: bytes, full: bool = False) -> Any:
    """(src, base_seq, n) from the CBOR map, without rebuilding a record; None if unparseable.
    `full` asks for the whole triple, else only the source."""
    try:
        obj = cbor2.loads(frame)
        if not isinstance(obj, dict) or set(obj) != set(range(8)):
            return None
        src, base_seq, n = obj[F_SRC], obj[F_BASE_SEQ], obj[F_N]
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (src, base_seq, n)):
            return None
        return (src, base_seq, n) if full else src
    except (cbor2.CBORDecodeError, TypeError, ValueError, KeyError):
        return None
