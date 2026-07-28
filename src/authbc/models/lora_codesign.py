"""LoRa co-design optimizer — the LoRa arm as a joint optimization (docs/02 §9, T5).

Same method as the 802.11 arm (`models.optimizer`): enumerate the discrete design space
exhaustively, filter on hard constraints, return the **full Pareto set** over competing objectives.
No configuration is hand-picked; the frontier is the result.

**The design space has a fifth knob here.** On 802.11 it is (encoding × scheme × placement ×
batch). On LoRa the **data rate** is a design variable too — spreading factor trades airtime
against link budget, and airtime is rationed by regulation, so DR is the single most consequential
choice available. It cannot be fixed in advance without begging the question.

Objectives (all simultaneous, none weighted):

    minimize on-air bytes per record       (T1/T2)
    maximize sustainable record rate Λ     (duty-cycle limited — the scarce quantity here)
    minimize freshness D of a batch        (docs/02 §7)
    maximize verifiability V               (T3)
    maximize relative range                (what a higher spreading factor actually buys)

**Range is an objective, not decoration.** Without it the optimizer trivially selects the fastest
data rate every time — DR6 has the shortest airtime, so it dominates on both Λ and D, and the whole
DR axis collapses. Range is derived from the SX1276 receiver-sensitivity table (Rev.7, RFS_L125_HF
/ RFS_L250_HF, Band 1) as a *ratio* between data rates: TX power, antennas and fading are identical
across DRs and cancel, so no link budget is needed and nothing is assumed.

Hard constraints:

    * regional payload limit: frame ≤ N(DR)       (RP002-1.0.3 Table 13)
    * verifiability:          V ≥ 1−ε             (T3)
    * verify throughput:      t_verify(b)·Λ ≤ 1   (T4/T5)

**Why Λ and D are both objectives and neither is a constraint.** On 802.11, Λ is an application
input and freshness a bound to respect. On LoRa the duty cycle *derives* both: a frame of airtime T
may repeat only every T/duty, so Λ = b·duty/T and D = T/duty. Larger batches raise Λ (the per-frame
preamble and signature amortise) but lengthen T and therefore worsen D. That tension is the LoRa
co-design problem, and it has no 802.11 counterpart.

**Energy is deliberately absent.** The measured `p_radio_w = 0.218 W` is a Wi-Fi figure from the
RPi4 rig; reusing it for a LoRa transceiver would be fabrication. Airtime per record is reported
instead — it is what the regulator actually rations, and it is measured, not assumed. A LoRa energy
column needs a LoRa radio measurement (⚠️ open).
"""

from __future__ import annotations

from dataclasses import dataclass

from authbc.models import lora
from authbc.models.energy import EnergyConfig, Measured, Placement, verify_time_per_record_s
from authbc.models.optimizer import (
    EncodingSpec,
    SchemeSpec,
    bytes_per_record,
    frame_auth_bytes,
    n_frames,
    verifiability,
)

MAX_GRID_POINTS: int = 200_000


@dataclass(frozen=True)
class LoRaCandidate:
    """One fully-evaluated LoRa design point."""

    encoding: str
    scheme: str
    placement: Placement
    batch: int
    dr: int
    chain_mode: str            # "per_record" (D6-frozen wire) or "per_frame" (audit F5)
    frame_bytes: float
    bytes_per_record: float
    toa_s: float
    duty_interval_s: float
    lambda_max: float          # sustainable records/s under the duty-cycle quota
    freshness_s: float
    verifiability: float
    verify_time_s: float
    airtime_per_record_s: float
    sensitivity_dbm: float
    relative_range: float      # vs DR6, from the sensitivity delta (free-space exponent)


@dataclass(frozen=True)
class LoRaConstraints:
    """Hard constraints for the LoRa arm. Λ and D are derived, so neither appears here."""

    epsilon: float = 0.05
    p_loss: float = 0.05
    duty_cycle: float = lora.DUTY_CYCLE
    chain_hash_bytes: int = 32
    frame_hdr_bytes: int = 44        # MEASURED (B1, docs/01 §2a)


@dataclass(frozen=True)
class LoRaResult:
    pareto: list[LoRaCandidate]
    feasible: list[LoRaCandidate]
    evaluated: int
    infeasible: int
    skipped: int


def _dominates(a: LoRaCandidate, b: LoRaCandidate) -> bool:
    """a Pareto-dominates b: no worse on all five objectives, strictly better on ≥1."""
    no_worse = (
        a.bytes_per_record <= b.bytes_per_record
        and a.lambda_max >= b.lambda_max
        and a.freshness_s <= b.freshness_s
        and a.verifiability >= b.verifiability
        and a.relative_range >= b.relative_range
    )
    strictly_better = (
        a.bytes_per_record < b.bytes_per_record
        or a.lambda_max > b.lambda_max
        or a.freshness_s < b.freshness_s
        or a.verifiability > b.verifiability
        or a.relative_range > b.relative_range
    )
    return no_worse and strictly_better


def pareto_front(cands: list[LoRaCandidate]) -> list[LoRaCandidate]:
    return [c for c in cands if not any(_dominates(o, c) for o in cands if o is not c)]


def _evaluate(enc: EncodingSpec, sch: SchemeSpec, plc: Placement, batch: int, dr: int,
              chain_mode: str, con: LoRaConstraints) -> tuple[LoRaCandidate | None, bool]:
    if plc is Placement.C and not sch.supports_aggregate:
        return None, False
    rate = lora.EU868_DATA_RATES[dr]

    # `per_frame` lifts the 32 B chain hash out of every record and charges it once per frame
    # (audit F5); the receiver derives the rest. `per_record` is the D6-frozen wire format.
    per_rec = enc.record_bytes if chain_mode == "per_record" \
        else enc.record_bytes - con.chain_hash_bytes
    frame_extra = 0 if chain_mode == "per_record" else con.chain_hash_bytes
    if per_rec <= 0:
        return None, False

    n = n_frames(batch, per_rec, sch.auth_bytes, con.frame_hdr_bytes,
                 rate.max_app_payload) if plc is Placement.D else 1
    auth = frame_auth_bytes(plc, batch, sch.auth_bytes)
    frame = con.frame_hdr_bytes + auth + frame_extra + batch * per_rec
    if frame > rate.max_app_payload:
        return None, False                      # will not fit the regional limit — not a candidate

    toa = lora.frame_time_on_air_s(int(-(-frame // 1)), dr)
    interval = lora.duty_cycle_interval_s(toa, con.duty_cycle)
    lam = batch / interval

    cfg = EnergyConfig(placement=plc, batch=batch, record_bytes=per_rec,
                       auth_bytes=auth, frame_hdr_bytes=con.frame_hdr_bytes, n_frames=n)
    # `verify_time_per_record_s` reads only the TIMING fields (verified: _verify_cpu_per_record
    # touches t_verify_s / t_agg_verify_s and nothing else). Measured still validates powers > 0,
    # so both are set to 1 W as inert sentinels — no energy is computed here, deliberately, since
    # the only measured p_radio_w in this project is a Wi-Fi figure (see the module docstring).
    meas = Measured(t_enc_s=enc.t_enc_s, t_sign_s=sch.t_sign_s, t_verify_s=sch.t_verify_s,
                    p_cpu_w=1.0, p_radio_w=1.0,
                    t_agg_build_s=sch.t_agg_build_s, t_agg_verify_s=sch.t_agg_verify_s)
    verify_t = verify_time_per_record_s(cfg, meas)
    v = verifiability(plc, n, con.p_loss)

    cand = LoRaCandidate(
        encoding=enc.name, scheme=sch.name, placement=plc, batch=batch, dr=dr,
        chain_mode=chain_mode, frame_bytes=frame,
        bytes_per_record=bytes_per_record(plc, batch, per_rec, sch.auth_bytes,
                                          con.frame_hdr_bytes, n) + frame_extra / batch,
        toa_s=toa, duty_interval_s=interval, lambda_max=lam, freshness_s=interval,
        verifiability=v, verify_time_s=verify_t, airtime_per_record_s=toa / batch,
        sensitivity_dbm=rate.sensitivity_dbm, relative_range=lora.relative_range(dr),
    )
    feasible = v >= 1.0 - con.epsilon and verify_t * lam <= 1.0
    return cand, feasible


def solve(encodings: list[EncodingSpec], schemes: list[SchemeSpec],
          placements: list[Placement], batches: list[int], data_rates: list[int],
          constraints: LoRaConstraints,
          chain_modes: tuple[str, ...] = ("per_record",)) -> LoRaResult:
    """Exhaustively enumerate the LoRa design space and return the Pareto set.

    The space is (encoding × scheme × placement × batch × **data rate** × chain mode). Points that
    cannot fit the regional payload limit are *skipped* rather than counted infeasible: they are
    not designs that fail a constraint, they are designs that do not exist.
    """
    grid = (len(encodings) * len(schemes) * len(placements) * len(batches)
            * len(data_rates) * len(chain_modes))
    if grid == 0:
        raise ValueError("empty design space")
    if grid > MAX_GRID_POINTS:
        raise ValueError(f"grid has {grid} points > MAX_GRID_POINTS={MAX_GRID_POINTS}")

    feasible: list[LoRaCandidate] = []
    evaluated = infeasible = skipped = 0
    for enc in encodings:
        for sch in schemes:
            for plc in placements:
                for dr in data_rates:
                    for mode in chain_modes:
                        for b in batches:
                            cand, ok = _evaluate(enc, sch, plc, b, dr, mode, constraints)
                            if cand is None:
                                skipped += 1
                                continue
                            evaluated += 1
                            if ok:
                                feasible.append(cand)
                            else:
                                infeasible += 1
    return LoRaResult(pareto=pareto_front(feasible), feasible=feasible,
                      evaluated=evaluated, infeasible=infeasible, skipped=skipped)
