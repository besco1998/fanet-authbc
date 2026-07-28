"""Co-design optimizer: exhaustive Pareto search over (encoding, scheme, placement, batch).

Implements docs/03 §3 (models/ optimizer) and the co-design theorem docs/02 T5. The discrete
design space is tiny (a few encodings × schemes × placements × batch sizes ≤ ~2000 points), so
we enumerate it exhaustively — no solver, no heuristics — and return the FULL Pareto set over
three objectives, not a single argmin:

    minimize on-air bytes/record   (T1/T2)
    minimize energy/record         (docs/02 §7 via models.energy)
    maximize verifiability V       (T3)
    minimize freshness delay D(b)  (docs/02 §7)

Hard constraints filter a candidate out entirely:
  * MTU:            single-frame placements (A/B/C) must fit b·s+g_a+H_f ≤ M.
  * verifiability:  V ≥ 1−ε  (T3; via n(b) for block-level D).
  * verify-throughput: t_verify(b)·Λ ≤ 1  (T4/T5 — receiver must keep up at record rate Λ).
  * freshness:      D(b) ≤ D_max  (docs/02 §7 — "enforce ... in the optimizer").

**Freshness was previously computed and discarded** (audit F10). It was read as "soft = annotated,
not filtered", and then not annotated either — so the byte-optimal batch violated the 250 ms bound
by 6.2× with nothing in any artifact to show it. Batching buys bytes with staleness, so a co-design
optimizer that cannot see freshness is not optimizing the actual problem. It is now BOTH a hard
constraint (a config that misses the freshness requirement is inadmissible, exactly like one that
misses V) and a fourth Pareto objective (so the bytes↔freshness trade-off is visible inside the
feasible region).

Closed form worth noting: fill time dominates D(b), so the freshness-feasible batch is
**b ≲ Λ·D_max** — at Λ=20 records/s and D_max=250 ms that is b ≤ 5, independent of encoding.

Byte / frame-span model (docs/02 §6, T2, T3):
  * A/B/C span one frame: bytes/rec = s + (g_a+H_f)/b.
  * D spans n(b)=⌈(b·s+g_a+H_f)/M⌉ frames with ONE block signature: bytes/rec =
    s + (g_a + n·H_f)/b, and the energy radio term bills one T_fx + one header per frame
    (models.energy.radio_airtime_s). n(b) uses the doc-T3 formula (one nominal H_f in the
    numerator); the per-frame header accounting in the energy term is noted in docs/audits/p5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from authbc.models import energy
from authbc.models.energy import EnergyConfig, Measured, Placement

# Enumeration guard: the space is meant to be small (docs/03 §3 "≤ ~2k points"). A larger grid
# is almost certainly a mis-specified sweep — fail loudly rather than churn.
MAX_GRID_POINTS: int = 5000

_SINGLE_FRAME = (Placement.A, Placement.B, Placement.C)


# --- input specs --------------------------------------------------------------------------
@dataclass(frozen=True)
class EncodingSpec:
    """An encoding choice e: record size s and its per-record encode time."""

    name: str
    record_bytes: float   # s
    t_enc_s: float


@dataclass(frozen=True)
class SchemeSpec:
    """A signature scheme σ: auth-object size g_a and its per-op timings.

    `t_agg_build_s` / `t_agg_verify_s` are required only for cross-signer placement C.
    """

    name: str
    auth_bytes: float     # g_a
    t_sign_s: float
    t_verify_s: float
    t_agg_build_s: float | None = None
    t_agg_verify_s: float | None = None

    @property
    def supports_aggregate(self) -> bool:
        return self.t_agg_build_s is not None and self.t_agg_verify_s is not None


@dataclass(frozen=True)
class Platform:
    """Platform/link constants shared by every candidate."""

    p_cpu_w: float
    p_radio_w: float
    frame_hdr_bytes: float   # H_f
    mtu_bytes: float         # M


@dataclass(frozen=True)
class Constraints:
    """Optimization constraints (docs/02 T3/T5, §7)."""

    epsilon: float           # verifiability target: require V ≥ 1−ε
    p_loss: float            # per-frame loss probability p
    lam: float               # record arrival rate Λ [records/s]
    d_max_s: float = 0.250   # freshness bound D_max, seconds (docs/02 §7 — enforced)


@dataclass(frozen=True)
class Candidate:
    """One evaluated design point and its three objectives + diagnostics."""

    encoding: str
    scheme: str
    placement: Placement
    batch: int
    n_frames: int
    bytes_per_record: float
    energy_j: float
    verifiability: float
    verify_time_s: float     # amortized verify per record (throughput constraint)
    latency_s: float         # freshness of the oldest record in the batch
    meets_latency: bool      # soft: latency_s ≤ D_max


@dataclass(frozen=True)
class OptimizeResult:
    """Full result: the Pareto set plus the feasible pool and bookkeeping for auditability."""

    pareto: list[Candidate]
    feasible: list[Candidate]
    evaluated: int           # grid points enumerated
    skipped: int             # (scheme, placement) combos not applicable (e.g. C w/o aggregate)
    infeasible: int          # evaluated but violated a hard constraint


# --- model helpers ------------------------------------------------------------------------
def n_frames(batch: int, s: float, g_a: float, h_f: float, mtu: float) -> int:
    """n(b) = ⌈(b·s + g_a + H_f)/M⌉ frames a batch spans (docs/02 T3). Always ≥ 1."""
    return max(1, math.ceil((batch * s + g_a + h_f) / mtu))


def verifiability(placement: Placement, n: int, p_loss: float) -> float:
    """V (T3): frame-level self-verifiable ⇒ 1−p; block-level D ⇒ (1−p)^n."""
    if placement is Placement.D:
        return (1.0 - p_loss) ** n
    return 1.0 - p_loss


def frame_auth_bytes(placement: Placement, batch: int, g_a: float) -> float:
    """Auth bytes carried in a frame: A carries b per-record sigs (b·g_a); B/C/D carry one g_a.

    A is inline per-record authentication (docs/01 §4, T1) — batching does NOT amortize its
    signature, which is exactly why A is the naive baseline. B/C fold b records under one auth
    object; D uses one block signature.
    """
    return batch * g_a if placement is Placement.A else g_a


def bytes_per_record(placement: Placement, batch: int, s: float, g_a: float, h_f: float,
                     n: int) -> float:
    """On-air bytes/record: A → s+g_a+H_f/b (no auth amortization); B/C → s+(g_a+H_f)/b (T2);
    D → s+(g_a+n·H_f)/b (T3)."""
    headers = n * h_f if placement is Placement.D else h_f
    return s + (frame_auth_bytes(placement, batch, g_a) + headers) / batch


def _dominates(a: Candidate, b: Candidate) -> bool:
    """a Pareto-dominates b: no worse on all 4 objectives, strictly better on ≥ 1.

    Objectives: min bytes, min energy, max verifiability, min freshness delay (audit F10).
    """
    no_worse = (
        a.bytes_per_record <= b.bytes_per_record
        and a.energy_j <= b.energy_j
        and a.verifiability >= b.verifiability
        and a.latency_s <= b.latency_s
    )
    strictly_better = (
        a.bytes_per_record < b.bytes_per_record
        or a.energy_j < b.energy_j
        or a.verifiability > b.verifiability
        or a.latency_s < b.latency_s
    )
    return no_worse and strictly_better


def pareto_front(candidates: list[Candidate]) -> list[Candidate]:
    """Return the non-dominated subset (order preserved). O(n²) — the space is tiny.

    No float tolerance is applied to domination: near-ties are kept as distinct trade-offs
    rather than silently merged (that would hide a real difference — Law 7).
    """
    return [c for c in candidates if not any(_dominates(o, c) for o in candidates if o is not c)]


# --- which constraint binds, and what compression is therefore worth (docs/02 T2a) ----------
def freshness_batch_bound(lam: float, d_max_s: float) -> int:
    """Largest batch whose fill time alone fits the freshness budget: ⌊Λ·D_max⌋.

    Fill time b/Λ dominates D(b) at telemetry rates (airtime and queueing are microseconds against
    a 250 ms budget), so this is the freshness ceiling on b — and it depends on NEITHER the
    encoding nor the scheme.
    """
    if lam <= 0 or d_max_s <= 0:
        raise ValueError(f"lam and d_max_s must be > 0, got {lam}, {d_max_s}")
    return int(lam * d_max_s)


def mtu_batch_bound(record_bytes: float, auth_bytes: int, frame_hdr_bytes: int,
                    mtu_bytes: int) -> int:
    """Largest single-frame batch: b_max = ⌊(M − H_f − g_a)/s⌋ (docs/02 T2)."""
    usable = mtu_bytes - frame_hdr_bytes - auth_bytes
    return int(usable // record_bytes) if record_bytes > 0 else 0


def binding_constraint(record_bytes: float, auth_bytes: int, frame_hdr_bytes: int,
                       mtu_bytes: int, lam: float, d_max_s: float) -> str:
    """Which ceiling binds the batch: ``"freshness"`` or ``"mtu"`` (docs/02 T2a).

    Freshness binds ⇔ ⌊Λ·D_max⌋ < ⌊(M − H_f − g_a)/s⌋. Both ceilings are integers, so the exact
    boundary is s < (M − H_f − g_a)/(⌊Λ·D_max⌋+1) — the continuous form s < (M−H_f−g_a)/(Λ·D_max)
    is an approximation that is off by one batch step (232.7 B vs 279.2 B on 802.11 at Λ=20).
    """
    b_fresh = freshness_batch_bound(lam, d_max_s)
    b_mtu = mtu_batch_bound(record_bytes, auth_bytes, frame_hdr_bytes, mtu_bytes)
    return "freshness" if b_fresh < b_mtu else "mtu"


def effective_amplification(record_bytes: float, auth_bytes: int, frame_hdr_bytes: int,
                            mtu_bytes: int, lam: float, d_max_s: float) -> float:
    """What one saved payload byte is actually worth on air, dC/ds (docs/02 T2a).

    T2's amplification law A = M/(M−H_f−g_a) is derived AT the MTU limit, where b_max = usable/s
    makes the overhead term proportional to s. It therefore holds only in the MTU-limited regime.

    When **freshness** binds, b ≈ Λ·D_max is independent of s, so
    C(s) = s + (g_a+H_f)/(Λ·D_max)  ⇒  **dC/ds = 1 exactly**: compression pays 1×, not A×, and the
    residual authentication cost is a floor (g_a+H_f)/(Λ·D_max) that compression cannot touch.

    Measured consequence: on 802.11 (M=1500, Λ=20, D_max=250 ms) freshness binds for every s below
    232.7 B — i.e. for every encoding in this study (45–191 B) — so A is never operative here. On
    a low-rate link (LoRa, M=222) the MTU binds and A≈1.88 IS operative, which is where the
    "compression pays A-times" leverage actually lives.
    """
    if binding_constraint(record_bytes, auth_bytes, frame_hdr_bytes, mtu_bytes,
                          lam, d_max_s) == "freshness":
        return 1.0
    usable = mtu_bytes - frame_hdr_bytes - auth_bytes
    return mtu_bytes / usable


# --- the search ---------------------------------------------------------------------------
def _evaluate(enc: EncodingSpec, sch: SchemeSpec, plc: Placement, batch: int,
              plat: Platform, con: Constraints) -> tuple[Candidate | None, bool]:
    """Evaluate one grid point. Returns (candidate, feasible); candidate is None if the combo
    is not applicable (e.g. placement C with a non-aggregate scheme)."""
    if plc is Placement.C and not sch.supports_aggregate:
        return None, False  # not applicable — skip, not "infeasible"

    n = n_frames(batch, enc.record_bytes, sch.auth_bytes, plat.frame_hdr_bytes, plat.mtu_bytes) \
        if plc is Placement.D else 1

    cfg = EnergyConfig(
        placement=plc,
        batch=batch,
        record_bytes=enc.record_bytes,
        auth_bytes=frame_auth_bytes(plc, batch, sch.auth_bytes),  # A: b·g_a ; B/C/D: g_a
        frame_hdr_bytes=plat.frame_hdr_bytes,
        n_frames=n,
    )
    meas = Measured(
        t_enc_s=enc.t_enc_s,
        t_sign_s=sch.t_sign_s,
        t_verify_s=sch.t_verify_s,
        p_cpu_w=plat.p_cpu_w,
        p_radio_w=plat.p_radio_w,
        t_agg_build_s=sch.t_agg_build_s,
        t_agg_verify_s=sch.t_agg_verify_s,
    )

    v = verifiability(plc, n, con.p_loss)
    verify_t = energy.verify_time_per_record_s(cfg, meas)
    # Freshness of the OLDEST record in the batch: fill + flight + M/M/1 queueing, the full
    # docs/02 §7 model (the queueing term was specified but unimplemented until audit P3).
    latency = energy.freshness_delay_s(cfg, con.lam)
    cand = Candidate(
        encoding=enc.name,
        scheme=sch.name,
        placement=plc,
        batch=batch,
        n_frames=n,
        bytes_per_record=bytes_per_record(plc, batch, enc.record_bytes, sch.auth_bytes,
                                          plat.frame_hdr_bytes, n),
        energy_j=energy.per_record(cfg, meas),
        verifiability=v,
        verify_time_s=verify_t,
        latency_s=latency,
        meets_latency=latency <= con.d_max_s,
    )

    # hard constraints
    frame_data = (
        batch * enc.record_bytes
        + frame_auth_bytes(plc, batch, sch.auth_bytes)
        + plat.frame_hdr_bytes
    )
    single_frame_fits = plc not in _SINGLE_FRAME or frame_data <= plat.mtu_bytes
    feasible = (
        single_frame_fits
        and v >= 1.0 - con.epsilon              # verifiability (T3)
        and verify_t * con.lam <= 1.0           # verify-throughput (T4/T5)
        and latency <= con.d_max_s              # freshness (docs/02 §7, audit F10)
    )
    return cand, feasible


def solve(encodings: list[EncodingSpec], schemes: list[SchemeSpec],
          placements: list[Placement], batches: list[int],
          platform: Platform, constraints: Constraints) -> OptimizeResult:
    """Exhaustively evaluate the (e, σ, placement, b) grid; return the full Pareto set.

    Raises ValueError if the grid exceeds MAX_GRID_POINTS (a mis-specified sweep, docs/03 §3).
    """
    grid = len(encodings) * len(schemes) * len(placements) * len(batches)
    if grid > MAX_GRID_POINTS:
        raise ValueError(f"grid has {grid} points > MAX_GRID_POINTS={MAX_GRID_POINTS}")
    if grid == 0:
        raise ValueError("empty design space")

    feasible: list[Candidate] = []
    evaluated = skipped = infeasible = 0
    for enc in encodings:
        for sch in schemes:
            for plc in placements:
                for b in batches:
                    cand, ok = _evaluate(enc, sch, plc, b, platform, constraints)
                    if cand is None:
                        skipped += 1
                        continue
                    evaluated += 1
                    if ok:
                        feasible.append(cand)
                    else:
                        infeasible += 1

    return OptimizeResult(
        pareto=pareto_front(feasible),
        feasible=feasible,
        evaluated=evaluated,
        skipped=skipped,
        infeasible=infeasible,
    )
