"""Per-record energy model for authenticated, batched telemetry (implements docs/02 §7).

Canonical formula (docs/02 §7), self-batch (placement B) form:

    E = P_c·(t_enc + t_sg/b + t_ver_amort(b)) + P_r·T_air(frame)/b

    * P_c  — CPU power while encoding/signing/verifying          [W]
    * P_r  — radio (receive) power while a frame is on air        [W]
    * t_enc — encode one record                                  [s]
    * t_sg  — produce the frame/block signature; ONE covers b own records ⇒ /b   [s]
    * t_ver_amort(b) — receiver verify amortized per record; the receiver verifies
      once per frame in B ⇒ t_vf/b                               [s]
    * T_air(frame) — channel-busy airtime of the frame (docs/02 §6), amortized /b [s]

    ⇒ E has units [W·s] = [J] per record.

Placements differ ONLY in how the sign / verify CPU terms amortize (docs/01 §4, docs/02 §7):

    A (inline per-record):   sign = t_sg,          verify = t_vf          (b = 1, no amortize)
    B (self-batch frame):    sign = t_sg/b,        verify = t_vf/b        (the canonical form)
    C (relay cross-signer):  sign = t_sg + t_ag/b, verify = t_av/b        (originators each sign;
        the relay builds ONE aggregate per frame (t_ag), receiver aggregate-verifies once (t_av))
    D (block over n frames): sign = t_sg/b,        verify = t_vf/b        (one sig over the block)

Aggregate timings (t_ag, t_av) are REQUIRED for C and must be supplied as measured values —
we never fabricate them (CLAUDE.md Law 2/7). The radio term is receiver-side only, exactly as
docs/02 §7 states; transmit energy is out of this formula's scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from authbc.models import bianchi

# Fixed (payload-independent) channel-busy time of ONE BROADCAST frame (audit finding F2).
# bianchi.T_FX is the UNICAST value: it includes SIFS + ACK because a unicast exchange is
# DATA->SIFS->ACK. The telemetry substrate is 802.11 BROADCAST, which never ACKs, so the correct
# fixed part is T_phy + 8*MAC_OVH/R + DIFS + delta. Using the unicast figure over-counted the
# receiver radio term by ~22 us per frame. Matches channel/airtime.T_FX_BROADCAST_US.
T_FX_BROADCAST: float = (bianchi.T_PHY + 8.0 * bianchi.MAC_OVH_BYTES / bianchi.R_BPS
                         + bianchi.DIFS + bianchi.DELTA)


class Placement(StrEnum):
    """Authentication placement (docs/01 §4): A inline, B self-batch, C relay, D block."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(frozen=True)
class Measured:
    """Measured per-op timings and platform powers fed into the energy model.

    All times in seconds, powers in watts. `t_agg_build_s` / `t_agg_verify_s` are only needed
    for placement C (cross-signer aggregation); leave them None otherwise.
    """

    t_enc_s: float          # encode one record
    t_sign_s: float         # produce one ordinary signature
    t_verify_s: float       # verify one ordinary signature
    p_cpu_w: float          # CPU power
    p_radio_w: float        # radio receive power
    t_agg_build_s: float | None = None    # build one aggregate signature (relay, per frame)
    t_agg_verify_s: float | None = None   # aggregate-verify one frame (receiver, per frame)

    def __post_init__(self) -> None:
        for name in ("t_enc_s", "t_sign_s", "t_verify_s"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be ≥ 0, got {getattr(self, name)}")
        if self.p_cpu_w <= 0 or self.p_radio_w <= 0:
            raise ValueError("powers must be > 0")


@dataclass(frozen=True)
class EnergyConfig:
    """The frame geometry / placement a per-record energy figure is computed for."""

    placement: Placement
    batch: int              # b records per frame (per block for D); ≥ 1
    record_bytes: float     # s — encoded record size
    auth_bytes: float       # g_a — auth object carried per frame/block
    frame_hdr_bytes: float  # H_f — frame header
    n_frames: int = 1       # frames the batch spans: 1 for A/B/C; n(b) ≥ 1 for block-level D

    def __post_init__(self) -> None:
        if self.batch < 1:
            raise ValueError(f"batch b must be ≥ 1, got {self.batch}")
        if self.n_frames < 1:
            raise ValueError(f"n_frames must be ≥ 1, got {self.n_frames}")
        for name in ("record_bytes", "auth_bytes", "frame_hdr_bytes"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be ≥ 0")


def frame_bytes(cfg: EnergyConfig) -> float:
    """On-air size of ONE frame carrying b records + auth object + header (docs/02 §7).

    Single-frame notion (A/B/C). For block-level D the batch spans cfg.n_frames frames — use
    `radio_airtime_s` for the true multi-frame on-air time.
    """
    return cfg.batch * cfg.record_bytes + cfg.auth_bytes + cfg.frame_hdr_bytes


def radio_airtime_s(cfg: EnergyConfig) -> float:
    """Total channel-busy airtime of the batch [s] (docs/02 §6): n frames, each T_fx + its data.

    = n·T_fx + 8·(b·s + g_a + n·H_f)/R. For n_frames=1 this reduces EXACTLY to
    T_air(b·s+g_a+H_f) — the single-frame §7 form; for D it counts one T_fx + one header per
    frame the block occupies, so D's per-frame overhead is not silently undercounted.

    Uses T_FX_BROADCAST (≈100 µs), NOT bianchi.T_FX (≈122 µs, unicast incl. SIFS+ACK) — audit
    finding F2, RESOLVED in the P7 re-run.
    """
    n = cfg.n_frames
    data_bytes = cfg.batch * cfg.record_bytes + cfg.auth_bytes + n * cfg.frame_hdr_bytes
    return n * T_FX_BROADCAST + 8.0 * data_bytes / bianchi.R_BPS


def _sign_cpu_per_record(cfg: EnergyConfig, m: Measured) -> float:
    """Signing CPU time attributable to one record [s], per placement (docs/02 §7)."""
    b = cfg.batch
    if cfg.placement is Placement.A:
        return m.t_sign_s                       # one signature per record
    if cfg.placement in (Placement.B, Placement.D):
        return m.t_sign_s / b                    # one signature amortized over b own records
    # C: each record is signed by its originator (t_sg) + relay builds one aggregate per frame.
    if m.t_agg_build_s is None:
        raise ValueError("placement C requires Measured.t_agg_build_s")
    return m.t_sign_s + m.t_agg_build_s / b


def _verify_cpu_per_record(cfg: EnergyConfig, m: Measured) -> float:
    """Verify CPU time attributable to one record [s], per placement (docs/02 §7)."""
    b = cfg.batch
    if cfg.placement is Placement.A:
        return m.t_verify_s                      # verify each record individually
    if cfg.placement in (Placement.B, Placement.D):
        return m.t_verify_s / b                   # one frame/block verify amortized over b
    # C: aggregate-verify once per frame, amortized over b.
    if m.t_agg_verify_s is None:
        raise ValueError("placement C requires Measured.t_agg_verify_s")
    return m.t_agg_verify_s / b


def verify_time_per_record_s(cfg: EnergyConfig, m: Measured) -> float:
    """Amortized receiver verify time per record [s] (docs/02 §7).

    Exposed so the optimizer's verify-throughput constraint t_verify(b)·Λ ≤ 1 (docs/02 T4/T5)
    uses the SAME verify model as the energy figure — one source of truth.
    """
    return _verify_cpu_per_record(cfg, m)


def per_record(cfg: EnergyConfig, m: Measured) -> float:
    """Energy per record [J] = P_c·(t_enc + t_sg' + t_vf') + P_r·T_air(frame)/b (docs/02 §7).

    t_sg' and t_vf' are the placement-amortized sign/verify times. Deterministic and pure.
    """
    b = cfg.batch
    cpu_time_s = m.t_enc_s + _sign_cpu_per_record(cfg, m) + _verify_cpu_per_record(cfg, m)  # [s]
    e_cpu = m.p_cpu_w * cpu_time_s                                                          # [J]
    e_radio = m.p_radio_w * radio_airtime_s(cfg) / b                                        # [J]
    return e_cpu + e_radio
