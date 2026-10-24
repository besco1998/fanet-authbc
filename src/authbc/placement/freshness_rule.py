"""A receiver rule that refuses delayed frames, at zero bytes (revision A5; predictions/A5.md).

`LeanReceiver` refuses a replay by sequence number only: a frame it has not seen is accepted
however old it is. An adversary that holds a sender's frames back — a relay that delays
everything it forwards — is therefore never detected (the paper's threat model lists this as
not protected). Every record already carries its sampling time `ts` in ms, signed with it, and
every UAV keeps GNSS time. The rule (`docs/AUTHBC Revision Plan.md`, A5):

    t_local − ts_newest ≤ Δ_acc = b/Λ + T_ch + t_v + 2σ_clk + g

where `ts_newest` is the newest record of the frame, σ_clk the clock error between sender and
receiver and g a guard. While a node has no GNSS fix its crystal drifts; `TimeWindow.widened`
adds the worst drift of both clocks, and beyond `max_window_ms` the receiver stops applying the
rule and marks what it accepts as TIME_UNVERIFIED, falling back to sequence numbers alone.

Why this is a layer and not an edit of `session_v2`: that file is timed on the board and held by
hash (`tests/test_bench_session_hw.py`). The rule reads the timestamp of a frame BEFORE its
signature is checked. That is sound: a frame whose timestamp was altered to look fresh then
fails its signature in `LeanReceiver`, and altering one to look stale only does what dropping
the frame would. It also means a stale frame costs the receiver a decode, not a verification.
The design sends a keyframe in every frame, so every frame's timestamps decode alone; a
dependent frame (one self-contained frame in r > 1) is passed on unchecked and counted.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from authbc.placement.session_v2 import LeanReceiver, Receipt, Received
from authbc.placement.wire import WireDecodeError
from authbc.placement.wire_v2 import DesyncError, decode_frame_v2


class TimeVerdict(StrEnum):
    FRESH = "fresh"                       # within the window; passed to the receiver
    STALE = "stale"                       # outside it; refused before verification
    TIME_UNVERIFIED = "time_unverified"   # the window has outgrown its limit: sequence only
    NOT_CHECKED = "not_checked"           # times unreadable alone (dependent or malformed)


@dataclass(frozen=True)
class TimeWindow:
    """Δ_acc and how it grows while GNSS time is lost."""

    batch: int
    lam: float               # records/s
    t_ch_ms: float           # worst channel delay
    t_v_ms: float            # one verification
    sigma_clk_ms: float      # clock error between the two nodes, one standard deviation
    guard_ms: float
    drift_ppm: float = 20.0  # crystal tolerance of each node

    @property
    def accept_ms(self) -> float:
        return (1000.0 * self.batch / self.lam + self.t_ch_ms + self.t_v_ms
                + 2.0 * self.sigma_clk_ms + self.guard_ms)

    def widened(self, outage_s: float) -> float:
        """The window after `outage_s` without GNSS: both clocks may have drifted, apart."""
        if outage_s < 0:
            raise ValueError("an outage cannot be negative")
        return self.accept_ms + 2.0 * self.drift_ppm * 1e-6 * outage_s * 1000.0

    def longest_outage_s(self, max_window_ms: float) -> float:
        """How long GNSS may be lost before the window passes `max_window_ms`."""
        if max_window_ms < self.accept_ms:
            raise ValueError("the limit is below the window itself")
        return (max_window_ms - self.accept_ms) / (2.0 * self.drift_ppm * 1e-6 * 1000.0)


@dataclass(frozen=True)
class TimedReceipt:
    verdict: TimeVerdict
    received: Received | None     # None when the frame was refused as stale


class TimedReceiver:
    """`LeanReceiver` behind the time window."""

    def __init__(self, inner: LeanReceiver, window: TimeWindow, max_window_ms: float) -> None:
        self.inner = inner
        self.window = window
        self.max_window_ms = max_window_ms
        self.counters: dict[str, int] = {v.value: 0 for v in TimeVerdict}

    def receive(self, data: bytes, t_local_ms: float, outage_s: float = 0.0) -> TimedReceipt:
        out = self._receive(data, t_local_ms, outage_s)
        self.counters[out.verdict.value] += 1
        return out

    def _receive(self, data: bytes, t_local_ms: float, outage_s: float) -> TimedReceipt:
        limit = self.window.widened(outage_s)
        if limit > self.max_window_ms:
            return TimedReceipt(TimeVerdict.TIME_UNVERIFIED, self.inner.receive(data))
        try:
            frame = decode_frame_v2(data)
        except (DesyncError, WireDecodeError):
            # its times cannot be read alone; the receiver reports what it is
            return TimedReceipt(TimeVerdict.NOT_CHECKED, self.inner.receive(data))
        newest = max(r.ts for r in frame.recs)
        if t_local_ms - newest > limit:
            return TimedReceipt(TimeVerdict.STALE, None)
        return TimedReceipt(TimeVerdict.FRESH, self.inner.receive(data))


def accepted(receipt: TimedReceipt) -> bool:
    """True iff the frame's records were stored."""
    return receipt.received is not None and receipt.received.receipt is Receipt.ACCEPTED
