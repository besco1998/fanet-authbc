"""Experiments built on the single frame definition (docs/04 §2 E6–E12; docs/02 T3', T6').

Added 2026-10 in answer to an external review of the paper. Each runner here either corrects a
result that rested on a composition error, or supplies evidence the review found missing:

    frame-components   E6   measured sizes of both frame formats            (audit F45, F48)
    e3-codec           E7   verifiability with the decoder in the loop      (F46)
    design-ladder      E8   every design rung: bytes, capacity, CPU, energy (review 2.3, 2.4, 4.1)
    exclusion-matrix   E9   which link carries which authenticated frame    (F47; review 2.2)
    freshness-budget   E10  fill + channel + verification against D_max     (review 4.9)
    lora-budget        E11  the LoRa batch at the record spacing it implies (F48)
    phy-sweep          E12  the capacity model at other PHY rates           (review 4.7)
    energy-table       E13  metered and modelled energy per record          (review 4.1)

All are deterministic functions of committed code, configs and frozen measured inputs, so all are
in the frozen-artifact gate. None reads or writes an artifact that existed before 2026-10.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import cache
from statistics import mean, median, stdev
from typing import Any

import numpy as np

from authbc.bench import framesizes, leanframes
from authbc.bench.experiments import CI_SEED, _read_raw, _Runner
from authbc.bench.stats import bootstrap_ci
from authbc.bench.telemgen import TelemetryRecord
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.encodings.delta_enc import DeltaEncoder
from authbc.models import bianchi, energy, lora, optimizer, phy
from authbc.models import frame as frame_model
from authbc.models.energy import EnergyConfig, Measured, Placement
from authbc.models.frame import FlatLayout
from authbc.placement import wire_v2
from authbc.placement.framer import frame_header_bytes_range, measure_frame_header_bytes
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt

_ED = Ed25519Scheme()
GENERATOR_STEP_S: float = 0.05     # the telemetry generator emits one record every 50 ms


# =========================================================================== E6 frame components
def _row(kind: str, fmt: str, item: str, stats: leanframes.SizeStats | float, **extra: Any
         ) -> dict[str, Any]:
    if isinstance(stats, leanframes.SizeStats):
        sizes = {"mean_bytes": round(stats.mean, 3), "min_bytes": stats.lo, "max_bytes": stats.hi,
                 "n": stats.n}
    else:
        sizes = {"mean_bytes": stats, "min_bytes": stats, "max_bytes": stats, "n": 1}
    return {"kind": kind, "format": fmt, "item": item, "stride": "", "spacing_s": "", "batch": "",
            "ref_interval": "", **sizes, "bytes_per_rec": "", **extra}


def _header_field_rows(points: Sequence[Sequence[Any]]) -> list[dict]:
    """Each header field's bytes over the flight: smallest and largest of the header points."""
    rows: list[dict] = []
    per_point = {
        "first": [frame_model.first_header_fields(src=src, base_seq=seq, n=4)
                  for _, src, seq in points],
        "lean": [frame_model.lean_header_fields(src=src, base_seq=seq, n=4, stream_bytes=50)
                 for _, src, seq in points],
    }
    for fmt, fields in per_point.items():
        for name in fields[0]:
            sizes = [f[name] for f in fields]
            # `mean_bytes` is the documented flight point, which the config lists last
            rows.append(_row("header_field", fmt, name, sizes[-1]) | {
                "min_bytes": min(sizes), "max_bytes": max(sizes), "n": len(sizes)})
    return rows


def run_frame_components(cfg: dict) -> list[dict]:
    """Sizes of the pieces every frame-level result is built from, both formats.

    `first` is the format of `placement/wire.py` with the delta encoder of `encodings/` (a byte
    model: its delta frames were never emitted); `lean` is `placement/wire_v2.py`, and every lean
    row is the length of an emitted frame or record stream.
    """
    rows: list[dict] = []
    for label, src, base_seq in cfg["header_points"]:
        rows.append(_row("header", "first", label,
                         measure_frame_header_bytes(4, src=src, base_seq=base_seq)))
        rows.append(_row("header", "lean", label, frame_model.lean_header_bytes(
            src=src, base_seq=base_seq, n=4, stream_bytes=50)))
    rows.append(_row("link", "first", "per record (inside the record)", 32))
    rows.append(_row("link", "lean", "per frame (its own field)", frame_model.LINK_FIELD_BYTES))
    rows.extend(_header_field_rows(cfg["header_points"]))

    for stride, n in cfg["stride_records"].items():
        spacing = {"stride": stride, "spacing_s": round(stride * GENERATOR_STEP_S, 3)}
        for fmt, (key, delta) in (
                ("first", leanframes.v1_delta_record_sizes(n=n, stride=stride)),
                ("lean", leanframes.lean_record_sizes(n=n, stride=stride))):
            rows.append(_row("record", fmt, "keyframe", key, **spacing))
            rows.append(_row("record", fmt, "delta", delta, **spacing))
    key0, _ = leanframes.lean_record_sizes(ts0=0)
    rows.append(_row("record", "lean", "keyframe at time zero", key0, stride=1,
                     spacing_s=GENERATOR_STEP_S))

    # every batch with each frame decoding alone, then the reference interval at one batch
    grid = [(b, 1) for b in cfg["batches"]] \
        + [(cfg["ref_batch"], r) for r in cfg["ref_intervals"] if r != 1]
    for batch, ref in grid:
        s = leanframes.lean_frame_sizes(batch, ref)
        rows.append(_row("frame", "lean", "self-batch", s, batch=batch, ref_interval=ref,
                         bytes_per_rec=round(s.mean / batch, 3)))
    for batch in cfg["inline_batches"]:
        s = leanframes.lean_frame_sizes(batch, inline=True)
        rows.append(_row("frame", "lean", "inline", s, batch=batch, ref_interval=1,
                         bytes_per_rec=round(s.mean / batch, 3)))
    low = leanframes.lean_frame_sizes(1, src=0, base_seq=0, ts0=0)
    rows.append(_row("frame", "lean", "self-batch at sender 0 and time zero", low, batch=1,
                     ref_interval=1, bytes_per_rec=round(low.mean, 3)))

    # every single-bit flip of one signed frame of the reference batch; `n` is the count
    census = leanframes.bit_flip_census(cfg["ref_batch"])
    for outcome in ("flips", "undecodable", "bad_signature", "accepted_unchanged",
                    "accepted_altered"):
        rows.append(_row("tamper", "lean", outcome, census["frame_bytes"],
                         batch=cfg["ref_batch"], ref_interval=1) | {"n": census[outcome]})
    return rows


# =========================================================================== E7 loss, codec in loop
def _loss_mask(rng: np.random.Generator, n: int, p: float, model: str,
               mean_burst: float) -> np.ndarray:
    """True where a frame is lost. `gilbert` loses every frame sent in its bad state."""
    if model == "iid":
        return rng.random(n) < p
    if model != "gilbert":
        raise ValueError(f"unknown loss model {model!r}")
    to_good = 1.0 / mean_burst
    to_bad = p * to_good / (1.0 - p)
    lost = np.empty(n, dtype=bool)
    bad = bool(rng.random() < p)                 # start in the stationary distribution
    for i in range(n):
        lost[i] = bad
        bad = bool(rng.random() >= to_good) if bad else bool(rng.random() < to_bad)
    return lost


def _theory(model: str, p: float, ref: int, mean_burst: float) -> float:
    if model == "iid":
        return frame_model.verifiability(p, ref)
    return frame_model.verifiability_gilbert(p, mean_burst, ref)


def run_loss_codec(cfg: dict) -> list[dict]:
    """V measured by sending real lean frames through a lossy channel into a real receiver.

    E3 drew a Bernoulli variable per frame and compared it with its own expectation; no codec was
    involved, so it could not see that a delta-coded record needs every frame since the last
    self-contained one (audit F46). Here a frame counts only if the receiver decodes it, verifies
    its signature and stores its records.
    """
    batch, n_frames, seeds = cfg["batch"], cfg["frames_per_seed"], cfg["seeds"]
    sk, pk = _ED.keygen(seed=bytes(range(32)))
    target = 1.0 - cfg["epsilon"]
    rows: list[dict] = []
    for ref in cfg["ref_intervals"]:
        streams = []
        for seed in seeds:
            recs = leanframes.chained_records(seed, n_frames * batch)
            sender = LeanSender(sk, ref_interval=ref)
            streams.append([sender.frame(recs[i:i + batch])
                            for i in range(0, len(recs), batch)])
        frame_bytes = mean(len(f) for s in streams for f in s)
        for model in cfg["loss_models"]:
            for p in cfg["p_values"]:
                v_by_seed, desync, lost_n = [], 0, 0
                for seed, frames in zip(seeds, streams, strict=True):
                    rng = np.random.default_rng(
                        [cfg["base_seed"], cfg["loss_models"].index(model), ref,
                         int(round(p * 1e6)), seed])
                    lost = _loss_mask(rng, n_frames, p, model, cfg["mean_burst_frames"])
                    rx = LeanReceiver({leanframes.CONVENTION_SRC: pk})
                    for data, gone in zip(frames, lost, strict=True):
                        if not gone:
                            rx.receive(data)
                    unexpected = {k: v for k, v in rx.counters.items()
                                  if v and k not in (Receipt.ACCEPTED, Receipt.DESYNC)}
                    if unexpected:           # a loss-only channel can produce nothing else
                        raise RuntimeError(f"receiver reported {unexpected} on a loss-only link")
                    v_by_seed.append(rx.counters[Receipt.ACCEPTED] / n_frames)
                    desync += rx.counters[Receipt.DESYNC]
                    lost_n += int(lost.sum())
                # The CI is of the MEAN, the statistic reported beside it. `bootstrap_ci` defaults
                # to the median, which is right for timings and wrong here: on a skewed sample
                # the median's interval need not even contain the mean.
                lo, hi = bootstrap_ci(v_by_seed, seed=CI_SEED, statistic=np.mean)
                v_th = _theory(model, p, ref, cfg["mean_burst_frames"])
                sent = n_frames * len(seeds)
                rows.append({
                    "loss_model": model, "p": p, "batch": batch, "ref_interval": ref,
                    "frame_bytes": round(frame_bytes, 3),
                    "bytes_per_rec": round(frame_bytes / batch, 3),
                    "V_meas": round(mean(v_by_seed), 5), "V_ci_lo": round(lo, 5),
                    "V_ci_hi": round(hi, 5),
                    "V_se": round(stdev(v_by_seed) / len(v_by_seed) ** 0.5, 5),
                    "V_theory": round(v_th, 5),
                    "frames_sent": sent, "frames_lost": lost_n, "frames_desync": desync,
                    "meets_target": int(v_th >= target),
                })
    return rows


# =========================================================================== E8 design ladder
def _crypto(cfg: dict) -> dict[tuple[str, str], float]:
    return {(r["scheme"], r["op"]): float(r["median_ns"]) * 1e-9
            for r in _read_raw(cfg["crypto_csv"]) if not r["agg_b"]}


def n_max(lam: float, batch: int, frame_bytes: float, ceiling: float, n_limit: int) -> int:
    """Largest neighbourhood with utilisation ≤ `ceiling` (the search `run_capacity` uses)."""
    best = 0
    for n in range(2, n_limit + 1):
        if optimizer.channel_utilisation(n, lam, batch, frame_bytes) > ceiling:
            break
        best = n
    return best


def cpu_seconds_per_neighbour(lam: float, batch: int, sigs_per_frame: int, t_verify_s: float,
                              t_hash_s: float) -> float:
    """Receiver CPU time one neighbour demands per second: its signatures and its chain hashes."""
    return (lam / batch) * sigs_per_frame * t_verify_s + lam * t_hash_s


@cache
def _lean_measured(batch: int, inline: bool) -> float:
    return leanframes.lean_frame_sizes(batch, inline=inline).mean


def _rungs(batch: int) -> list[dict[str, Any]]:
    """The design ladder at a given batch: each rung changes one thing about the one before."""
    cbor = framesizes.measured_sizes()["cbor"]
    v1_cbor = FlatLayout("first/cbor", 44, 0, cbor, cbor)
    v1_delta = leanframes.v1_delta_layout()
    lean = leanframes.lean_layout()
    lean_keys = FlatLayout("lean/keys", lean.header_bytes, lean.link_bytes,
                           lean.key_record_bytes, lean.key_record_bytes)
    published_ref = max(1, 16 // batch)      # K = 16 records is one keyframe per 16/b frames
    return [
        dict(format="first", rung="inline-1", label="sign every record; one record per frame",
             placement="A", encoding="cbor", batch=1, ref=1, sigs=1, sized_from="byte model",
             frame=v1_cbor.frame_bytes(64, 1), rec=cbor, hdr=44.0),
        dict(format="first", rung="inline-b", label="sign every record; share the frame",
             placement="A", encoding="cbor", batch=batch, ref=1, sigs=batch,
             sized_from="byte model", frame=v1_cbor.frame_bytes(64, batch, inline=True), rec=cbor,
             hdr=44.0),
        dict(format="first", rung="batch-cbor", label="one signature per frame",
             placement="B", encoding="cbor", batch=batch, ref=1, sigs=1, sized_from="byte model",
             frame=v1_cbor.frame_bytes(64, batch), rec=cbor, hdr=44.0),
        dict(format="first", rung="batch-delta-published",
             label="delta records; keyframe every 16 records (as published)", placement="B",
             encoding="delta", batch=batch, ref=published_ref, sigs=1, sized_from="byte model",
             frame=v1_delta.mean_frame_bytes(64, batch, published_ref),
             rec=v1_delta.delta_record_bytes,
             hdr=44.0 + (v1_delta.key_record_bytes - v1_delta.delta_record_bytes) / published_ref),
        dict(format="first", rung="batch-delta", label="delta records; every frame decodes alone",
             placement="B", encoding="delta", batch=batch, ref=1, sigs=1, sized_from="byte model",
             frame=v1_delta.frame_bytes(64, batch), rec=v1_delta.delta_record_bytes,
             hdr=44.0 + v1_delta.key_record_bytes - v1_delta.delta_record_bytes),
        dict(format="lean", rung="inline-1", label="sign every record; one record per frame",
             placement="B", encoding="lean", batch=1, ref=1, sigs=1, sized_from="emitted frames",
             frame=_lean_measured(1, False), rec=None, hdr=None),
        dict(format="lean", rung="inline-b", label="sign every record; share the frame",
             placement="A", encoding="lean", batch=batch, ref=1, sigs=batch,
             sized_from="emitted frames", frame=_lean_measured(batch, True), rec=None, hdr=None),
        dict(format="lean", rung="batch-keys", label="one signature per frame; no delta coding",
             placement="B", encoding="lean", batch=batch, ref=1, sigs=1,
             sized_from="measured components", frame=lean_keys.frame_bytes(64, batch), rec=None,
             hdr=None),
        dict(format="lean", rung="batch-delta", label="delta records; every frame decodes alone",
             placement="B", encoding="lean", batch=batch, ref=1, sigs=1,
             sized_from="emitted frames", frame=_lean_measured(batch, False), rec=None, hdr=None),
    ]


def _latency_s(lam: float, batch: int, frame_bytes: float) -> float:
    """D(b) of a frame of `frame_bytes`, by the model every published result uses (docs/02 §7)."""
    whole = EnergyConfig(placement=Placement.B, batch=batch, record_bytes=frame_bytes / batch,
                         auth_bytes=0.0, frame_hdr_bytes=0.0)
    return energy.freshness_delay_s(whole, lam)


def _freshness_batch(lam: float, d_max_s: float, frame_of: Callable[[int], float]) -> int:
    """Largest batch whose D(b) fits the freshness bound."""
    b = max(1, int(lam * d_max_s))
    while b > 1 and _latency_s(lam, b, frame_of(b)) > d_max_s:
        b -= 1
    return b


def run_design_ladder(cfg: dict) -> list[dict]:
    """Every rung of the design, at every operating point: bytes, verifiability, delay, capacity
    at both thresholds, receiver CPU, and energy where its inputs were measured.

    Answers three review comments at once. The published baseline signs every record AND sends
    one record per frame, so it confounds two effects (2.3); capacity was never ablated, only bytes
    (2.4a); and a receiver that must verify a whole neighbourhood has a CPU limit the envelope did
    not show (2.4c).
    """
    crypto = _crypto(cfg)
    t_ver, t_sign = crypto[("ed25519", "verify")], crypto[("ed25519", "sign")]
    t_hash = cfg["t_hash_ns"] * 1e-9
    cert = (cfg["cert_bytes"] + (cfg["cert_period"] - 1) * cfg["cert_digest_bytes"]) \
        / cfg["cert_period"]
    lean = leanframes.lean_layout()
    rows: list[dict] = []
    for op, lam, d_max in cfg["operating_points"]:
        batch = _freshness_batch(lam, d_max, lambda b: lean.frame_bytes(64, b))
        for r in _rungs(batch):
            b, frame = r["batch"], r["frame"]
            v = frame_model.verifiability(cfg["p_loss"], r["ref"])
            latency = _latency_s(lam, b, frame)
            per_nbr = cpu_seconds_per_neighbour(lam, b, r["sigs"], t_ver, t_hash)
            nu = n_max(lam, b, frame, cfg["u_saturation"], cfg["n_ceiling"])
            nv = n_max(lam, b, frame, cfg["u_v95"], cfg["n_ceiling"])
            n_cpu = 1 + int(1.0 / per_nbr)       # largest N with (N−1)·per_nbr ≤ one core
            e_radio = cfg["p_radio_w"] * bianchi.t_broadcast(frame) / b
            e_total: float | str = ""
            if r["rec"] is not None:           # encode time was measured for this encoder only
                ecfg = EnergyConfig(placement=Placement(r["placement"]), batch=b,
                                    record_bytes=r["rec"],
                                    auth_bytes=64.0 * r["sigs"], frame_hdr_bytes=r["hdr"])
                meas = Measured(t_enc_s=cfg["t_enc_ns"][r["encoding"]] * 1e-9, t_sign_s=t_sign,
                                t_verify_s=t_ver, p_cpu_w=cfg["p_cpu_w"],
                                p_radio_w=cfg["p_radio_w"], t_hash_s=t_hash)
                e_total = round(energy.per_record(ecfg, meas) * 1e6, 3)
            rows.append({
                "op": op, "lambda_rec_per_s": lam, "d_max_ms": round(d_max * 1e3, 1),
                "format": r["format"], "rung": r["rung"], "label": r["label"],
                "placement": r["placement"], "batch": b, "ref_interval": r["ref"],
                "sized_from": r["sized_from"], "frame_bytes": round(frame, 3),
                "bytes_per_rec": round(frame / b, 3),
                "bytes_per_rec_with_cert": round((frame + cert) / b, 3),
                "V": round(v, 5), "meets_v": int(v >= 1.0 - cfg["epsilon"]),
                "latency_ms": round(latency * 1e3, 3), "meets_d_max": int(latency <= d_max),
                "n_max_u_lt_1": nu, "n_max_v95": nv,
                "cpu_pct_at_n_v95": round(100.0 * (nv - 1) * per_nbr, 2),
                "n_cpu_one_core": n_cpu,
                # The neighbourhood a receiver can actually serve is the smaller of what the
                # channel delivers and what one core can verify.
                "n_feasible_v95": min(nv, n_cpu),
                "binds_at_v95": "cpu" if n_cpu < nv else "channel",
                "energy_radio_uj": round(e_radio * 1e6, 3), "energy_uj": e_total,
            })
        rows.extend(_search_rows(cfg, op, lam, d_max))
    return rows


def _search_rows(cfg: dict, op: str, lam: float, d_max: float) -> list[dict]:
    """The byte-minimal admissible configuration of each format, found by exhaustive search.

    The search is the claim that the reported design is an optimum and not a selection: it ranges
    over placement, batch and reference interval, and admits a point only if its frame fits the
    MTU, its records can be decoded and verified with probability ≥ 1−ε at loss p, and its oldest
    record is delivered within D_max.
    """
    cbor = framesizes.measured_sizes()["cbor"]
    lean = leanframes.lean_layout()
    candidates = {
        "first": [("cbor", FlatLayout("first/cbor", 44, 0, cbor, cbor)),
                  ("delta", leanframes.v1_delta_layout())],
        "lean": [("delta", lean)],
    }
    out: list[dict] = []
    for fmt, layouts in candidates.items():
        best: tuple[float, dict] | None = None
        for enc, layout in layouts:
            refs = (1,) if layout.stateless else tuple(cfg["ref_candidates"])
            for inline in (False, True):
                for b in range(1, cfg["search_max_batch"] + 1):
                    for ref in ((1,) if inline else refs):
                        frame = layout.mean_frame_bytes(64, b, ref, inline=inline)
                        biggest = layout.frame_bytes(64, b, inline=inline)
                        v = frame_model.verifiability(cfg["p_loss"], ref)
                        latency = _latency_s(lam, b, biggest)
                        if (biggest > cfg["mtu"] or v < 1.0 - cfg["epsilon"]
                                or latency > d_max):
                            continue
                        point = {"placement": "A" if inline else "B", "encoding": enc,
                                 "batch": b, "ref_interval": ref,
                                 "frame_bytes": round(frame, 3),
                                 "bytes_per_rec": round(frame / b, 3), "V": round(v, 5),
                                 "latency_ms": round(latency * 1e3, 3)}
                        if best is None or frame / b < best[0]:
                            best = (frame / b, point)
        if best is None:
            raise ValueError(f"design-ladder: no admissible {fmt} configuration at {op}")
        out.append({"op": op, "lambda_rec_per_s": lam, "d_max_ms": round(d_max * 1e3, 1),
                    "format": fmt, "rung": "SEARCH_OPTIMUM",
                    "label": "byte-minimal admissible configuration (exhaustive search)",
                    "sized_from": "measured components", "meets_v": 1, "meets_d_max": 1,
                    **best[1]})
    return out


# =========================================================================== E9 exclusion matrix
def _lean_one_record_range(sig_bytes: int) -> tuple[int, int]:
    """(smallest, largest) one-record lean frame over the flight envelope, for a `sig_bytes` tag."""
    lo = leanframes.lean_frame_sizes(1, src=0, base_seq=0, ts0=0, sig_bytes=sig_bytes).lo
    hi = leanframes.lean_frame_sizes(1, sig_bytes=sig_bytes).hi
    return lo, hi


def _floor_frames(sig_bytes: int) -> dict[str, int]:
    """The smallest frame each design can emit AT ALL: one record, every field zero, node 0.

    Every integer then takes its minimum width, so no telemetry and no moment of a flight can
    produce a smaller frame. Exclusion claimed against this floor does not depend on the generator.
    """
    zero = TelemetryRecord(src=0, seq=0, ts=0, prev_hash=bytes(32), lat=0, lon=0, alt=0,
                           vel_x=0, vel_y=0, vel_z=0, battery=0, mode=0)
    first = (frame_header_bytes_range(1)[0] + _auth_prefix_shift(sig_bytes) + sig_bytes
             + len(DeltaEncoder(keyframe_interval=1).encode(zero)))
    lean = frame_model.lean_frame_bytes(src=0, base_seq=0, n=1,
                                        stream_bytes=len(wire_v2.STREAM_FIELDS),
                                        sig_bytes=sig_bytes)
    return {"first": first, "lean": lean,
            "lean without on-air chain link": lean - frame_model.LINK_FIELD_BYTES}


def _auth_prefix_shift(sig_bytes: int) -> int:
    """H_f was measured around a 64 B signature; a shorter tag can have a shorter CBOR prefix."""
    return frame_model.cbor_prefix_bytes(sig_bytes) - frame_model.cbor_prefix_bytes(64)


def _verdict(floor: float, lo: float, hi: float, limit: int) -> str:
    """Whether one self-contained frame fits a payload limit, in four grades.

    * ``excluded`` — even the format's floor overflows: nothing it can emit fits.
    * ``excluded for this telemetry`` — a frame of zeros would fit; no measured frame does.
    * ``marginal`` — some measured frames fit and some do not.
    * ``feasible`` — every measured frame fits.
    """
    if floor > limit:
        return "excluded"
    if lo > limit:
        return "excluded for this telemetry"
    return "feasible" if hi <= limit else "marginal"


def run_exclusion_matrix(cfg: dict) -> list[dict]:
    """Which EU863-870 data rate can carry ONE self-contained authenticated frame (T6').

    The frame is header + chain link + authentication object + one record that decodes alone.
    Three designs are sized: the first format, the lean format, and the lean format with its
    on-air chain link removed — the last is arithmetic, not an implemented format, and is here to
    show what that relaxation would buy. Each is given a floor and a measured range, because the
    two answer different questions: the floor is what the format can do, the range is what this
    telemetry does over a flight (header and keyframe sizes grow with node id, sequence number
    and time).
    """
    h_lo, h_hi = frame_header_bytes_range(1)
    k1, _ = leanframes.v1_delta_record_sizes()
    rows: list[dict] = []
    for name, sig in cfg["auth_objects"]:
        lean_lo, lean_hi = _lean_one_record_range(sig)
        shift = _auth_prefix_shift(sig)
        designs = {
            "first": (h_lo + shift + sig + k1.lo, h_hi + shift + sig + k1.hi),
            "lean": (lean_lo, lean_hi),
            "lean without on-air chain link": (lean_lo - frame_model.LINK_FIELD_BYTES,
                                           lean_hi - frame_model.LINK_FIELD_BYTES),
        }
        floors = _floor_frames(sig)
        for dr, lim in lora.EU868_PAYLOAD_LIMITS.items():
            for design, (lo, hi) in designs.items():
                floor = floors[design]
                rows.append({
                    "dr": dr, "modulation": lim.modulation,
                    "payload_not_repeater": lim.n_not_repeater, "payload_repeater": lim.n_repeater,
                    "auth_object": name, "auth_bytes": sig, "design": design,
                    "frame_floor_bytes": floor,
                    "frame_min_bytes": lo, "frame_max_bytes": hi,
                    "signature_alone_overflows": int(sig > lim.n_not_repeater),
                    "verdict": _verdict(floor, lo, hi, lim.n_not_repeater),
                    "verdict_repeater": _verdict(floor, lo, hi, lim.n_repeater),
                })
    return rows


# =========================================================================== E10 freshness budget
def run_freshness_budget(cfg: dict) -> list[dict]:
    """End-to-end delay of the oldest record against D_max, with every term that was left out.

    The freshness model was fill time plus airtime. The review asked for verification time (4.9);
    channel-access delay had been measured (`ns3_delay_ci.csv`) and never added either. The
    channel term here is the simulator's whole non-fill delay — queueing, access, airtime — at the
    most loaded measured point that still meets V ≥ 0.95, so it is an upper bound for any lighter
    load. It was measured with 288 B frames at N = 50.
    """
    crypto = _crypto(cfg)
    delay = [r for r in _read_raw(cfg["delay_csv"])
             if float(r["channel_util"]) <= cfg["u_v95"]]
    worst = max(delay, key=lambda r: float(r["channel_util"]))
    rows: list[dict] = []
    for op, lam, d_max in cfg["operating_points"]:
        for scheme in cfg["schemes"]:
            fill = cfg["batch"] / lam
            verify = crypto[(scheme, "verify")]
            for stat in ("delay_mean_ms", "delay_p99_ms", "delay_max_ms"):
                channel = float(worst[stat]) * 1e-3
                total = fill + channel + verify
                rows.append({
                    "op": op, "lambda_rec_per_s": lam, "d_max_ms": round(d_max * 1e3, 1),
                    "batch": cfg["batch"], "scheme": scheme, "channel_stat": stat,
                    "channel_util_measured_at": float(worst["channel_util"]),
                    "fill_ms": round(fill * 1e3, 3), "channel_ms": round(channel * 1e3, 4),
                    "verify_ms": round(verify * 1e3, 4), "total_ms": round(total * 1e3, 3),
                    "margin_ms": round((d_max - total) * 1e3, 3),
                    "meets_d_max": int(total <= d_max),
                })
    return rows


# =========================================================================== E11 LoRa budget
@cache
def _delta_body_at(fmt: str, stride: int) -> float:
    """Mean delta-record body when transmitted records are `stride` generator steps apart.

    The first format's delta record carries its own 32 B chain link; under per-frame chaining
    (docs/02 §9b) that link moves to the frame, so it is subtracted here.
    """
    if fmt == "lean":
        return leanframes.lean_record_sizes(n=64, stride=stride)[1].mean
    return leanframes.v1_delta_record_sizes(n=64, stride=stride)[1].mean - 32.0


def _lora_point(batch: int, frame: float, delta: float, stride: int, dr: int,
                duty: float) -> dict[str, Any]:
    toa = lora.frame_time_on_air_s(int(-(-frame // 1)), dr)
    interval = lora.duty_cycle_interval_s(toa, duty)
    return {"batch": batch, "frame_bytes": round(frame, 2), "delta_bytes": round(delta, 2),
            "record_spacing_s": round(interval / batch, 2),
            "delta_measured_at_s": round(stride * GENERATOR_STEP_S, 2),
            "toa_ms": round(toa * 1e3, 2), "lambda_rec_per_s": round(batch / interval, 4),
            "bytes_per_rec": round(frame / batch, 2)}


def _lora_fit(fixed: float, key: float, fmt: str, limit: int, dr: int, duty: float,
              strides: Sequence[int]) -> dict[str, Any]:
    """Largest batch that fits `limit` when delta records are sized at the spacing it implies.

    A larger batch is a longer frame, hence a longer duty-cycle wait, hence records further apart
    and larger deltas — so the batch and the record size have to be solved together. The spacing
    is snapped to the nearest measured stride. Returns ``{"batch": 0}`` if not even one record fits.
    """
    for b in range(40, 0, -1):
        stride = strides[0]
        delta = _delta_body_at(fmt, stride)
        frame = fixed + key + (b - 1) * delta
        for _ in range(8):                       # converges in two or three passes
            if frame > limit:
                break
            spacing = lora.duty_cycle_interval_s(
                lora.frame_time_on_air_s(int(-(-frame // 1)), dr), duty) / b
            nearest = min(strides, key=lambda st: abs(st * GENERATOR_STEP_S - spacing))
            if nearest == stride:
                break
            stride, delta = nearest, _delta_body_at(fmt, nearest)
            frame = fixed + key + (b - 1) * delta
        if frame <= limit:
            return _lora_point(b, frame, delta, stride, dr, duty)
    return {"batch": 0}


def run_lora_budget(cfg: dict) -> list[dict]:
    """The LoRa batch and record rate, with frames that decode alone and deltas sized honestly.

    The published LoRa figures (b = 7, 0.182 rec/s at DR5) took a 13 B record body measured on
    records 50 ms apart and used it on a link that sends a record every several seconds, and they
    counted no keyframe (audit F48). This recomputes them; the published row is kept beside the
    corrected ones.
    """
    k1, _ = leanframes.v1_delta_record_sizes()
    kl, _ = leanframes.lean_record_sizes()
    h_lean = leanframes.lean_layout().header_bytes
    strides, duty = tuple(cfg["strides"]), cfg["duty_cycle"]
    rows: list[dict] = []
    for dr in cfg["data_rates"]:
        lim = lora.EU868_PAYLOAD_LIMITS[dr]
        for table, limit in (("not repeater compatible", lim.n_not_repeater),
                             ("repeater compatible", lim.n_repeater)):
            b_pub = int((limit - 44 - 64 - 32) // 13)
            published = _lora_point(b_pub, 44 + 64 + 32 + 13.0 * b_pub, 13.0, 1, dr, duty)
            fits = {
                "first; link per frame; AS PUBLISHED (13 B bodies and no keyframe)": published,
                "first; link per frame; frames decode alone":
                    _lora_fit(44 + 64 + 32, k1.mean - 32, "first", limit, dr, duty, strides),
                "lean; frames decode alone":
                    _lora_fit(h_lean + frame_model.LINK_FIELD_BYTES + 64, kl.mean, "lean", limit,
                              dr, duty, strides),
            }
            for design, fit in fits.items():
                rows.append({"dr": dr, "modulation": lim.modulation, "payload_table": table,
                             "payload_limit": limit, "design": design, **fit})
    return rows


# =========================================================================== E12 PHY sweep
def run_phy_sweep(cfg: dict) -> list[dict]:
    """Saturation capacity of the baseline and the design at other OFDM rates (MODEL ONLY).

    ⚠️ The broadcast model is validated against NS-3 at 6 Mb/s on a 20 MHz channel and nowhere
    else. Every other row is the same closed form with different timing constants. Only the
    saturation threshold is reported, because the measured V ≥ 0.95 ceiling is a 6 Mb/s number.
    """
    lam, batch = cfg["lambda_rec_per_s"], cfg["batch"]
    cbor = framesizes.measured_sizes()["cbor"]
    frames = {
        "first": (cbor + 64 + 44, leanframes.v1_delta_layout().frame_bytes(64, batch)),
        "lean": (_lean_measured(1, False), _lean_measured(batch, False)),
    }
    rows: list[dict] = []
    for width, rates in cfg["phys"].items():
        make = phy.ofdm_20mhz if width == "20MHz" else phy.ofdm_10mhz
        for rate in rates:
            p = make(rate)
            for fmt, (base, design) in frames.items():
                nb = phy.n_max(p, lam, 1, base, 1.0)
                nd = phy.n_max(p, lam, batch, design, 1.0)
                rows.append({
                    "channel": width, "rate_mbps": rate, "format": fmt,
                    "validated": int(width == "20MHz" and rate == 6),
                    "fixed_cost_us": round(p.fixed_cost_s() * 1e6, 2),
                    "baseline_frame_us": round(p.t_broadcast(base) * 1e6, 1),
                    "fixed_share_of_baseline_pct": round(
                        100.0 * p.fixed_cost_s()
                        / (p.t_broadcast(base) + (bianchi.W - 1) / 2 * p.slot_s), 1),
                    "n_max_baseline": nb, "n_max_design": nd,
                    "ratio": round(nd / nb, 3) if nb else "",
                })
    return rows



# =========================================================================== E13 energy table
def run_energy_table(cfg: dict) -> list[dict]:
    """Energy per record, per configuration: what was metered, and what the model adds to it.

    The paper said energy was measured and showed no energy result (review 4.1). The measurement
    exists: an INA219 on the Raspberry Pi 4 metered the SENDER pipeline — encode, chain hash, sign,
    assemble — for four configurations (`results/hw/energy/e2e/`, item D1). This reduces those
    files to one row each and sets the model beside them.

    ⚠️ A repetition is an incremental power: a loaded window minus an idle window. Three of the
    five A+JSON repetitions have an idle window 0.4–0.5 W above every other idle window of the
    campaign, which makes their difference meaningless in either direction (one reads 0.38 W, one
    0.82 W). Those repetitions are flagged by a rule stated here — idle power more than
    `idle_tolerance` from the campaign median — and the row reports both the count kept and the
    count metered. Nothing is dropped silently, and a row left with fewer than
    `min_clean_reps` repetitions says so in `reportable`.
    """
    reps = {name: _read_raw(f"energy/e2e/energy_{stem}.csv")
            for name, (stem, *_rest) in cfg["configurations"].items()}
    idle_median = median(float(r["p_idle_w"]) for rows in reps.values() for r in rows)
    crypto = _crypto(cfg)
    t_sign, t_hash = crypto[("ed25519", "sign")], cfg["t_hash_ns"] * 1e-9
    e2e = {r["role"]: r for r in _read_raw("e5_codesign.csv")}
    rows: list[dict] = []
    for name, (_stem, enc, batch, e5_role) in cfg["configurations"].items():
        clean = [r for r in reps[name]
                 if abs(float(r["p_idle_w"]) - idle_median) <= cfg["idle_tolerance"] * idle_median]
        per_rec = sorted(float(r["energy_per_op_uj"]) / batch for r in clean)
        sender_s = cfg["t_enc_ns"][enc] * 1e-9 + t_hash + t_sign / batch
        model = cfg["p_cpu_w"] * sender_s * 1e6
        metered = median(per_rec) if per_rec else float("nan")
        ok = len(clean) >= cfg["min_clean_reps"]
        rows.append({
            "configuration": name, "encoding": enc, "batch": batch,
            "reps_metered": len(reps[name]), "reps_clean": len(clean),
            "reportable": int(ok),
            "sender_uj_per_rec_median": round(metered, 3) if per_rec else "",
            "sender_uj_per_rec_min": round(per_rec[0], 3) if per_rec else "",
            "sender_uj_per_rec_max": round(per_rec[-1], 3) if per_rec else "",
            "sender_model_uj_per_rec": round(model, 3),
            "sender_residual_pct": round(100.0 * (metered - model) / model, 2) if per_rec else "",
            "end_to_end_model_uj_per_rec": float(e2e[e5_role]["energy_uj"]),
            "idle_power_median_w": round(idle_median, 4),
        })
    return rows


RUNNERS: dict[str, _Runner] = {
    "frame-components": _Runner(run_frame_components, "frame_components"),
    "e3-codec": _Runner(run_loss_codec, "e3_codec_loss"),
    "design-ladder": _Runner(run_design_ladder, "design_ladder"),
    "exclusion-matrix": _Runner(run_exclusion_matrix, "exclusion_matrix"),
    "freshness-budget": _Runner(run_freshness_budget, "freshness_budget"),
    "lora-budget": _Runner(run_lora_budget, "lora_budget"),
    "phy-sweep": _Runner(run_phy_sweep, "phy_sweep"),
    "energy-table": _Runner(run_energy_table, "energy_table"),
}
