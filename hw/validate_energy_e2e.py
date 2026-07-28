#!/usr/bin/env python3
"""D1 — end-to-end validation of the composed energy model (docs/OPEN_ITEMS.md §D).

**The gap this closes.** P7b measured the model's *inputs* — `p_cpu_w`, `p_radio_w` and every
per-operation timing — but nothing ever measured the model's *output*. E5's 112.08 µJ/record is
`t_enc + t_sign/b + …` multiplied by measured powers and summed: composed from measured parts, never
compared against a meter. A model can be built from correct pieces and still be wrong, because
composition is where the assumptions live (per-record attribution, the airtime term, what counts as
"incremental" power).

**What this does.** Runs the *actual* optimized configuration end to end — stateful delta encode →
SHA-256 chain link → Ed25519 sign once per b=4 records → frame assembly — at a fixed record rate
inside a GPIO-marked window, exactly like `energy_loop.py`'s per-op windows. The INA219 rig then
reduces the window to an incremental power, and this script converts that to µJ/record and compares
it against `models.energy.per_record` under the *same* configuration.

**Why the CPU term only.** The rig meters the board, so it sees compute, not the transmit path. The
model's radio term is charged against `p_radio_w`, which was measured separately on the 2-node link
(`results/hw/energy/p_radio_w.md`). This validation therefore targets the **CPU component** and says
so; the radio component's own measurement stands on its own and is not re-derived here.

Usage on the Pi (see hw/energy_protocol.md §7):

    python3 hw/validate_energy_e2e.py --seconds 60 --reps 5 --out results/hw/energy/e2e/
    # then, on the capture host:
    python3 hw/ina219_capture.py --reduce <manifest.json> <samples.csv> --channel 1

Law 6 applies: the EXPECTED value is printed before the measurement is read, and the comparison is
reported whatever it says. A gap >10 % is a finding to investigate in writing, not to average away.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import telemgen  # noqa: E402
from authbc.crypto.registry import get_scheme  # noqa: E402
from authbc.encodings.registry import new_encoder  # noqa: E402
from authbc.models.energy import (  # noqa: E402
    EnergyConfig,
    Measured,
    Placement,
    per_record,
)

sys.path.insert(0, str(REPO / "hw"))
from energy_loop import GAP_S, WARMUP, SyncLine, device_state, window_is_clean  # noqa: E402

# The E5 optimized configuration (docs/02 §7a, experiments/e5/config.yaml).
ENCODING = "delta"
SCHEME = "ed25519"
BATCH = 4
H_F = 44          # MEASURED from the wire format (B1, docs/01 §2a)
G_A = 64
RECORD_BYTES = 45.0


def build_pipeline():
    """One zero-arg callable that produces ONE authenticated frame of `BATCH` records.

    Deliberately the whole pipeline, not a single primitive: encode (stateful, so delta behaves as
    it does in the stream), chain, sign once per frame, assemble. That composition is what the model
    claims to predict.
    """
    scheme = get_scheme(SCHEME)
    sk, _pk = scheme.keygen(seed=hashlib.sha256(b"d1:e2e").digest())
    enc = new_encoder(ENCODING)
    recs = telemgen.samples(seed=1, n=10_000)
    state = {"i": 0, "prev": bytes(32)}

    def one_frame() -> object:
        payloads = []
        for _ in range(BATCH):
            rec = recs[state["i"] % len(recs)]
            state["i"] += 1
            body = enc.encode(rec)
            payloads.append(state["prev"] + body)
            state["prev"] = hashlib.sha256(state["prev"] + body).digest()
        covered = b"".join(payloads)
        sig = scheme.sign(sk, covered)
        return len(covered) + len(sig) + H_F

    return one_frame


def predicted_cpu_uj_per_record(p_cpu_w: float, t_enc_s: float, t_sign_s: float,
                                t_verify_s: float) -> float:
    """What the model says the CPU costs per record, in µJ, for this configuration."""
    cfg = EnergyConfig(placement=Placement.B, batch=BATCH, record_bytes=RECORD_BYTES,
                       auth_bytes=G_A, frame_hdr_bytes=H_F, n_frames=1)
    # radio power set to ~0 so `per_record` returns the CPU term alone — this rig meters
    # the board, not the transmit path (see the module docstring).
    meas = Measured(t_enc_s=t_enc_s, t_sign_s=t_sign_s, t_verify_s=t_verify_s,
                    p_cpu_w=p_cpu_w, p_radio_w=1e-12)
    return per_record(cfg, meas) * 1e6


def run_window(fn, seconds: float) -> tuple[int, int]:
    checksum, n = 0, 0
    gc.disable()
    try:
        end = time.perf_counter_ns() + int(seconds * 1e9)
        while time.perf_counter_ns() < end:
            out = fn()
            checksum ^= out if isinstance(out, int) else hash(out)
            n += 1
    finally:
        gc.enable()
    return n, checksum & 0xFFFFFFFFFFFFFFFF


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=60.0, help="measured window length")
    ap.add_argument("--reps", type=int, default=5, help="active/idle window pairs")
    ap.add_argument("--out", type=Path, default=REPO / "results/hw/energy/e2e",
                    help="directory for the manifest")
    ap.add_argument("--p-cpu-w", type=float, default=0.634,
                    help="measured incremental CPU power (P7b default)")
    ap.add_argument("--t-enc-ns", type=float, default=47759.0, help="measured delta encode (ARM)")
    ap.add_argument("--t-sign-ns", type=float, default=88120.2, help="measured Ed25519 sign (ARM)")
    ap.add_argument("--t-verify-ns", type=float, default=259498.7,
                    help="measured Ed25519 verify (ARM)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    predicted = predicted_cpu_uj_per_record(args.p_cpu_w, args.t_enc_ns * 1e-9,
                                            args.t_sign_ns * 1e-9, args.t_verify_ns * 1e-9)
    # Law 6: state the expectation BEFORE reading the meter.
    print("=" * 72)
    print("D1 end-to-end energy validation — EXPECTED VALUE, stated before measurement")
    print("=" * 72)
    print(f"  configuration     : {ENCODING} + {SCHEME} + placement B, b={BATCH}, H_f={H_F} B")
    print(f"  model inputs      : p_cpu={args.p_cpu_w} W, t_enc={args.t_enc_ns/1e3:.2f} µs, "
          f"t_sign={args.t_sign_ns/1e3:.2f} µs, t_verify={args.t_verify_ns/1e3:.2f} µs")
    print(f"  PREDICTED CPU     : {predicted:.3f} µJ/record")
    print("  acceptance        : |measured - predicted| / predicted <= 10 %")
    print("                      a larger gap is a FINDING to explain in writing (Law 7),")
    print("                      never a tolerance to widen (Law 3).\n")

    pipeline = build_pipeline()
    for _ in range(WARMUP):                       # outside every window, per energy_loop.warmup
        pipeline()

    sync = SyncLine()
    if not sync.available:
        print("WARNING: GPIO sync line unavailable — windows will not be machine-alignable.",
              file=sys.stderr)

    windows = []
    for rep in range(1, args.reps + 1):
        for label, fn in (("idle", None), ("e2e_frame_pipeline", pipeline)):
            time.sleep(GAP_S)
            before = device_state()
            t0 = time.perf_counter()
            with sync.window():
                if fn is None:
                    time.sleep(args.seconds)
                    n_ops, checksum = 0, 0
                else:
                    n_ops, checksum = run_window(fn, args.seconds)
            duration = time.perf_counter() - t0
            after = device_state()
            clean = window_is_clean(before["throttled"], after["throttled"])
            windows.append({
                "rep": rep, "label": label, "n_ops": n_ops, "checksum": checksum,
                "duration_s": duration, "records": n_ops * BATCH,
                "throttle_clean": clean, "before": before, "after": after,
            })
            status = "" if clean else "  ** THROTTLED — discard **"
            rate = (n_ops * BATCH / duration) if duration else 0.0
            print(f"  rep{rep} {label:20s} frames={n_ops:<8} records/s={rate:>9.1f}{status}")

    manifest = {
        "experiment": "d1_energy_e2e",
        "configuration": {"encoding": ENCODING, "scheme": SCHEME, "placement": "B",
                          "batch": BATCH, "h_f": H_F, "g_a": G_A},
        "model_inputs": {"p_cpu_w": args.p_cpu_w, "t_enc_ns": args.t_enc_ns,
                         "t_sign_ns": args.t_sign_ns, "t_verify_ns": args.t_verify_ns},
        "predicted_cpu_uj_per_record": predicted,
        "windows": windows,
        "note": ("Reduce with hw/ina219_capture.py --reduce <this> <samples.csv> --channel 1. "
                 "Measured µJ/record = (P_active - P_idle) * duration_s / records."),
    }
    path = args.out / f"manifest_{int(time.time())}.json"
    path.write_text(json.dumps(manifest, indent=2))
    sync.close()
    print(f"\n  manifest -> {path}")
    print("  NEXT: reduce the INA219 samples against this manifest, then record measured vs")
    print(f"        predicted ({predicted:.3f} µJ/record) in docs/audits/ and close D1.")


if __name__ == "__main__":
    main()
