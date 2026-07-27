#!/usr/bin/env python3
"""Why does Ed25519 beat ECDSA-P256 on ARM but lose on x86? (investigates audit finding F6)

Three candidate explanations must be separated before F6 can be reported as a hardware/library
result rather than an artefact of our own wrapper:

  (a) HARDWARE      — microarchitecture: x86 has ADX/BMI2/MULX big-integer paths that OpenSSL's
                      nistp256 assembly exploits; aarch64 has no equivalent for P-256.
  (b) LIBRARY       — different `cryptography` / OpenSSL versions, or different EC method selected.
  (c) OUR CODE      — asymmetric wrapper cost. `Ed25519Scheme.sign/verify` are one bare C call each,
                      but `EcdsaP256Scheme` also runs ASN.1 DER encode/decode plus bigint<->bytes
                      conversion in PYTHON on every operation, because the project accounts ECDSA
                      signatures as fixed-width 64 B r||s rather than 70-72 B DER (docs/02 T1).
                      Python is far slower relative to C on ARM than on x86, so this overhead is
                      inflated on the Pi and could by itself flip the ordering.

This script measures the wrapper overhead SEPARATELY from the cryptographic core, so the comparison
can be redone on equal terms: raw C sign/verify with no conversion, versus the full wrapped call.

Run it on BOTH platforms and compare:  ./hw/why_ed25519_wins.py
"""

from __future__ import annotations

import gc
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

MSG = bytes(range(200)) * 1                      # 200 B, same as the P1 harness
REPS = 3000
WARMUP = 500


def bench(fn, reps: int = REPS) -> float:
    """Median-ish ns/op with GC off and a checksum to defeat dead-code elimination."""
    for _ in range(WARMUP):
        fn()
    best = None
    gc.disable()
    try:
        for _ in range(5):
            acc = 0
            t0 = time.perf_counter_ns()
            for _ in range(reps):
                r = fn()
                acc ^= (r if isinstance(r, int)
                        else len(r) if isinstance(r, bytes) else id(r))
            dt = (time.perf_counter_ns() - t0) / reps
            best = dt if best is None else min(best, dt)
            assert acc == acc
    finally:
        gc.enable()
    return float(best)


def main() -> None:
    import cryptography
    from cryptography.hazmat.backends.openssl.backend import backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature,
        encode_dss_signature,
    )

    from authbc.crypto.ecdsa_p256 import EcdsaP256Scheme, der_to_raw64, raw64_to_der
    from authbc.crypto.ed25519 import Ed25519Scheme

    print("=" * 78)
    print(f"PLATFORM  {platform.machine()}  {platform.platform()}")
    print(f"python    {sys.version.split()[0]}")
    print(f"cryptography {cryptography.__version__}   openssl {backend.openssl_version_text()}")
    try:
        flags = [ln for ln in Path("/proc/cpuinfo").read_text().splitlines()
                 if ln.lower().startswith(("flags", "features"))][:1]
        print(f"cpu features {flags[0].split(':', 1)[1].strip()[:180] if flags else 'n/a'}")
    except Exception:                                                    # noqa: BLE001
        pass
    print("=" * 78)

    ecdsa, ed = EcdsaP256Scheme(), Ed25519Scheme()
    sk_e, pk_e = ecdsa.keygen()
    sk_d, pk_d = ed.keygen(seed=bytes(32))
    halg = ec.ECDSA(hashes.SHA256())

    der_sig = sk_e.sign(MSG, halg)                 # native DER form
    raw_sig = der_to_raw64(der_sig)                # our 64 B wire form
    ed_sig = ed.sign(sk_d, MSG)

    r = {
        # --- cryptographic core only (no conversion) ---------------------------
        "ecdsa sign  (C only, DER out)": lambda: sk_e.sign(MSG, halg),
        "ecdsa verify(C only, DER in)": lambda: pk_e.verify(der_sig, MSG, halg),
        "ed25519 sign  (C only)": lambda: ed.sign(sk_d, MSG),
        "ed25519 verify(C only)": lambda: ed.verify(pk_d, MSG, ed_sig),
        # --- our wrapper's extra Python/ASN.1 work ------------------------------
        "  der_to_raw64  (sign path)": lambda: der_to_raw64(der_sig),
        "  raw64_to_der  (verify path)": lambda: raw64_to_der(raw_sig),
        "  decode_dss_signature": lambda: decode_dss_signature(der_sig),
        "  encode_dss_signature": lambda: encode_dss_signature(1 << 200, 1 << 200),
        # --- full wrapped calls (what P1/E5 actually measure) -------------------
        "ecdsa sign  (WRAPPED)": lambda: ecdsa.sign(sk_e, MSG),
        "ecdsa verify(WRAPPED)": lambda: ecdsa.verify(pk_e, MSG, raw_sig),
    }
    out = {k: bench(f) for k, f in r.items()}

    print(f"\n{'operation':<34}{'ns/op':>12}{'us/op':>10}")
    for k, v in out.items():
        print(f"{k:<34}{v:>12,.0f}{v / 1000:>10.2f}")

    cs, cv = out["ecdsa sign  (C only, DER out)"], out["ecdsa verify(C only, DER in)"]
    ws, wv = out["ecdsa sign  (WRAPPED)"], out["ecdsa verify(WRAPPED)"]
    ds, dv = out["ed25519 sign  (C only)"], out["ed25519 verify(C only)"]

    print("\n--- wrapper overhead attributable to OUR code (not the crypto) ---")
    print(f"  sign  : wrapped {ws / 1000:7.2f} us - core {cs / 1000:7.2f} us = "
          f"{(ws - cs) / 1000:6.2f} us  ({100 * (ws - cs) / ws:5.1f}% of the measured time)")
    print(f"  verify: wrapped {wv / 1000:7.2f} us - core {cv / 1000:7.2f} us = "
          f"{(wv - cv) / 1000:6.2f} us  ({100 * (wv - cv) / wv:5.1f}% of the measured time)")

    print("\n--- the F6 comparison, on EQUAL terms ---")
    for label, e_s, e_v in (("as measured (wrapped ECDSA)", ws, wv),
                            ("core-only  (no conversion) ", cs, cv)):
        win_s = "Ed25519" if ds < e_s else "ECDSA"
        win_v = "Ed25519" if dv < e_v else "ECDSA"
        print(f"  {label}: sign  ECDSA {e_s / 1000:7.2f} vs Ed25519 {ds / 1000:7.2f} us -> {win_s}")
        print(f"  {' ' * len(label)}  verify ECDSA {e_v / 1000:7.2f} vs Ed25519 {dv / 1000:7.2f} "
              f"us -> {win_v}")
    print("\nIf the winner is the same on both lines, F6 is a genuine hardware/library effect.")
    print("If it changes, our DER<->raw64 wrapper is (partly) responsible and must be reported.")


if __name__ == "__main__":
    main()
