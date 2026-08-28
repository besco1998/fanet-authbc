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

# The telemetry substrate is 802.11 BROADCAST, which never ACKs (audit F2), so a frame's
# channel-busy time is its PPDU plus DIFS — `bianchi.t_broadcast`. There is deliberately no
# "T_fx" constant here any more: since decision D9 airtime is computed from the exact OFDM symbol
# count, which is a STEP function of the frame size, so no fixed part plus linear term exists.


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
    # SHA-256 of one chain link (item D7). Defaults to 0.0 so existing callers keep working, but
    # leaving it 0 silently reproduces the F14 omission — set it from a MEASURED per-platform
    # figure (results/hw/p1_crypto.*.csv, scheme=sha256 op=chain_link).
    t_hash_s: float = 0.0
    t_agg_build_s: float | None = None    # build one aggregate signature (relay, per frame)
    t_agg_verify_s: float | None = None   # aggregate-verify one frame (receiver, per frame)

    def __post_init__(self) -> None:
        for name in ("t_enc_s", "t_sign_s", "t_verify_s", "t_hash_s"):
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
        # Audit E18: `placement.wire.Placement` shares its member names with this enum, so an
        # `is Placement.A` test silently evaluates False if the wrong one is passed, and the energy
        # figure comes out wrong with no error. Catch it where the object is built.
        if not isinstance(self.placement, Placement):
            raise TypeError(
                f"placement must be authbc.models.energy.Placement, got "
                f"{type(self.placement).__module__}.{type(self.placement).__name__} — "
                f"the modelling and wire Placement enums are not interchangeable"
            )
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
    """Total channel-busy airtime of the batch [s] (docs/02 §6/§7): n broadcast frames.

    The batch occupies n frames carrying b·s + g_a + n·H_f payload bytes in total; the model has
    no per-frame split, so the payload is charged evenly across the n frames and each frame's
    airtime is computed EXACTLY (`bianchi.t_broadcast` = OFDM PPDU + DIFS). For n_frames=1 this is
    the single-frame §7 form. For block-level D it charges one PPDU + one DIFS + one header per
    frame the block occupies, so D's per-frame overhead is not silently undercounted.

    Broadcast, never unicast (audit F2): no SIFS, no ACK. Airtime is quantised to whole 4 µs OFDM
    symbols (decision D9), so it is NOT linear in the payload.
    """
    n = cfg.n_frames
    data_bytes = cfg.batch * cfg.record_bytes + cfg.auth_bytes + n * cfg.frame_hdr_bytes
    return n * bianchi.t_broadcast(data_bytes / n)


def queueing_delay_s(cfg: EnergyConfig, lam: float) -> float:
    """M/M/1 mean waiting time in the frame queue [s] (docs/02 §7).

    The station emits one frame per *b* records, so frames arrive at λ_f = Λ/b and are served in
    `radio_airtime_s` each; the offered load is ρ = Λ·T_air(b)/b, exactly as docs/02 §7 states.
    Mean waiting time of an M/M/1 queue is W_q = ρ·T_air / (1−ρ).

    Saturating the frame queue (ρ ≥ 1) means the station cannot clear its own telemetry, so the
    configuration is unusable rather than merely slow; we return infinity so any latency bound
    rejects it instead of reporting a large-but-finite delay.

    ⚠️ **M/M/1 is a conservative stand-in, not the true queue.** Arrivals here are periodic and
    service is a fixed airtime for a fixed frame size, i.e. D/D/1, whose waiting time is exactly
    **zero** for ρ < 1. M/M/1 therefore over-states W_q — the safe direction for a latency bound.
    It is numerically irrelevant either way: ρ ≈ 2·10⁻⁴ at the adopted point, giving W_q well
    under a microsecond against a 100 ms budget.

    ⚠️ docs/02 §7 claimed this term was "not implemented ... omitted rather than approximated,
    which makes D(b) a lower bound". That was true when written and false since; the term is
    implemented here and called by `freshness_delay_s`. Corrected in the docs 2026-08-28.
    """
    if lam <= 0:
        raise ValueError(f"lam must be > 0 records/s, got {lam}")
    t_air = radio_airtime_s(cfg)
    rho = lam * t_air / cfg.batch
    if rho >= 1.0:
        return float("inf")
    return rho * t_air / (1.0 - rho)


def batch_window_s(cfg: EnergyConfig, lam: float) -> float:
    """Duration of the batch window: from the window opening to the b-th record arriving [s].

    b inter-arrival gaps, hence ``b/Λ``. Confirmed by discrete-event simulation under both
    deterministic and Poisson arrivals (``tests/test_freshness_convention.py``); for Poisson the
    window is Erlang(b, Λ), whose mean is exactly b/Λ.
    """
    return cfg.batch / lam


def oldest_record_age_s(cfg: EnergyConfig, lam: float) -> float:
    """Age of the OLDEST record in the batch when the frame is transmitted [s].

    The oldest record is the FIRST to arrive, so it waits out the remaining ``b−1`` gaps:
    ``(b−1)/Λ``, not ``b/Λ``. Erlang(b−1, Λ) under Poisson arrivals, mean (b−1)/Λ. Both forms
    are confirmed by simulation to 0.2 % at 200k frames.
    """
    return (cfg.batch - 1) / lam


def freshness_delay_s(cfg: EnergyConfig, lam: float) -> float:
    """D(b) — WORST-CASE end-to-end latency of the oldest record in a batch [s] (docs/02 §7).

    ``D(b) = b/Λ + T_air + W_q``.

    ⚠️ **Which quantity b/Λ is, stated because the two differ by a full sampling interval.**
    ``b/Λ`` is the *batch-window duration* (`batch_window_s`); the *oldest record's age* at
    transmission is ``(b−1)/Λ`` (`oldest_record_age_s`). Both are verified by simulation. The
    constraint this feeds is 3GPP TS 22.125 R-5.2.2-011, an end-to-end **message** latency bound,
    which wants the record age — so on its face ``b/Λ`` charges one gap too many.

    It is nonetheless retained as the **worst case**, and it is exactly that: a record timestamped
    at its sample instant may describe vehicle state up to ``1/Λ`` older, and

        (b−1)/Λ  +  1/Λ  =  b/Λ

    so ``b/Λ`` bounds end-to-end latency including sampling quantisation. **This is a deliberate
    conservative choice, not an oversight** — but it was undocumented until the 2026-08-28 math
    audit, and it is worth ~3 percentage points of headline: at Λ=50/D=100 ms the tight reading
    admits b=5 (66.6 B/record, −61.78 %) where the worst case admits b=4 (72.0 B, −58.68 %).

    ⚠️ It also drives the "knife-edge" passage in docs/02 §7a, whose 100.37 ms is a worst-case
    figure; the oldest record there is aged 50.37 ms. See `tests/test_freshness_convention.py`.
    """
    return batch_window_s(cfg, lam) + radio_airtime_s(cfg) + queueing_delay_s(cfg, lam)


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

    **The chain-hash term (D7, added 2026-07-29).** Every record is hashed once by the sender to
    form the next `prev_hash` and once by the receiver to verify the link, so the system pays
    **2·t_hash per record**. This term was missing entirely and is half of the ~32 % energy gap
    measured in F14; the other half is that a single `p_cpu_w` understates a composed pipeline.
    It does NOT amortize over b — the chain is per-record by construction.

    ⚠️ **Validated end-to-end against INA219 (audit F14/D1, 2026-07-29).** The composition was
    first measured ~32 % low. Two causes were found and both are now fixed:
    (i) **D7** — no chain-hash term. Every record is SHA-256'd to form `prev_hash`; that is now
    charged as 2·t_hash (sender extends the chain, receiver verifies), measured 2745.5 ns on ARM.
    (ii) **D6** — `p_cpu_w` was the median over eight *isolated primitives* (0.634 W). Metered on
    four *composed* pipelines it is **0.749 W (+18.2 %)**, and those four agree to 3.8 %, so a
    single constant remains right — the methodology was wrong, not the assumption.

    **Residual after both fixes: +7.5 % to +14.3 %** across the four E5 configurations, and it has
    one identified cause — frame assembly (list building, concatenation) between crypto calls. That
    is deliberately NOT charged: it is CPython overhead of a prototype, and charging it would make
    this model describe our Python code rather than the design. **Read every energy figure as a
    lower bound of roughly 10-14 % on that account.**

    Byte results are power-free and unaffected by any of this.
    """
    b = cfg.batch
    # 2x: the sender hashes each record to extend the chain, the receiver re-hashes to verify it.
    chain_hash_s = 2.0 * m.t_hash_s                                                         # [s]
    cpu_time_s = (m.t_enc_s + chain_hash_s
                  + _sign_cpu_per_record(cfg, m) + _verify_cpu_per_record(cfg, m))          # [s]
    e_cpu = m.p_cpu_w * cpu_time_s                                                          # [J]
    e_radio = m.p_radio_w * radio_airtime_s(cfg) / b                                        # [J]
    return e_cpu + e_radio
