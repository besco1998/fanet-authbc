#!/usr/bin/env python3
"""What post-quantum signatures would cost AUTHBC (Tier-2 item 6). Projection, not a contribution.

⚠️ **This claims nothing novel.** Practical PQ authentication for vehicular broadcast is already
solved at NDSS level (Twardokus et al. 2024) and for 5G broadcast (arXiv 2510.23457); the earlier
novelty survey killed a PQC direction for exactly that reason. What is reported here is the
*mechanical consequence* of substituting published PQ signature sizes into **our own** byte model,
so that a foreseeable reviewer question has a quantified answer instead of a shrug.

**Every size is quoted from a source held in `docs/literature/`, never from memory:**

* ML-DSA / Dilithium2 — **2420 B signature**, 1312 B public key
  (arXiv 2510.23457: *"Dilithium2 … produces a 2420-byte signature and a 1312-byte"* public key).
* SPHINCS+ — **7856 B signature** (same source: *"with a 7856-byte signature, nearly 3× that of
  ML-DSA"*).
* Certificate sizes and the fragment counts a real deployment needs, from NDSS 2024 Table III
  (*"RESULTING SIZES OF FRAMES … |CS| IS THE SIZE OF THE ENTIRE CERTIFICATE"*): ECDSA 162 B / β=1,
  Falcon 858 B / β=2, Dilithium 2588 B / β=4, SPHINCS+ 8024 B / β=8, XMSS 2860 B / β=3.

**The two things our model says, which the sources do not:**

1. `b ≤ ⌊Λ·D_max⌋` (T2a) caps the batch at **5** at the adopted operating point, so a PQ signature
   has almost nothing to amortize over — the batch needed to reach Ed25519's overhead is orders of
   magnitude beyond what the freshness deadline permits.
2. A 2420 B signature plus the 44 B header **already exceeds the 1500 B MTU on its own**, so
   placement B stops fitting in one frame at *any* batch size. That is not a tuning problem; it is
   why NDSS 2024 needs a fragmentation design at all.

Writes results/raw/pqc_projection.csv.
"""
from __future__ import annotations

import csv
import io
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import framesizes, provenance  # noqa: E402
from authbc.models.energy import Placement  # noqa: E402
from authbc.models.optimizer import bytes_per_record  # noqa: E402

H_F, MTU = 44.0, 1500.0
LAM, D_MAX_S = 50.0, 0.100          # the adopted 3GPP-compliant operating point
B_ADOPTED = 4

# name -> (signature bytes, source)
SCHEMES = {
    "Ed25519 (current)": (64.0, "docs/06 §4 - raw r||s, measured"),
    "Falcon-512": (666.0, "NDSS 2024 Tab. III gives cert 858 B / beta=2; sig size NOT quoted "
                          "there -- see note"),
    "ML-DSA / Dilithium2": (2420.0, "arXiv 2510.23457, quoted"),
    "SPHINCS+-128s": (7856.0, "arXiv 2510.23457, quoted"),
}
# ⚠️ Falcon's *signature* size is not stated in either held source (NDSS Table III reports the
# certificate). It is carried here only to bracket the range and is flagged in the CSV so it is
# never quoted as sourced. Everything the paper claims uses ML-DSA and SPHINCS+, which are quoted.


def main() -> None:
    s = framesizes.measured_sizes()["delta"]
    b_cap = int(LAM * D_MAX_S)
    rows = []
    print(f"payload s = {s:.3f} B, H_f = {H_F:.0f} B, MTU = {MTU:.0f} B")
    print(f"freshness cap on the batch (T2a): b <= floor(Lambda*D_max) = {b_cap}\n")
    print(f"{'scheme':<22}{'g_a':>8}{'B/rec b=4':>12}{'vs Ed25519':>12}"
          f"{'frame B':>10}{'frames':>8}{'b for parity':>14}{'fill s':>9}")

    ed_ref = bytes_per_record(Placement.B, B_ADOPTED, s, SCHEMES["Ed25519 (current)"][0], H_F, 1)
    for name, (g_a, src) in SCHEMES.items():
        per_rec = bytes_per_record(Placement.B, B_ADOPTED, s, g_a, H_F, 1)
        frame = B_ADOPTED * s + g_a + H_F
        frames = math.ceil(frame / MTU)
        # batch that would bring PQ auth overhead down to Ed25519's 27 B/record
        ed_overhead = (SCHEMES["Ed25519 (current)"][0] + H_F) / B_ADOPTED
        b_parity = (g_a + H_F) / ed_overhead
        fill_s = b_parity / LAM
        rows.append({
            "scheme": name, "sig_bytes": g_a, "source": src,
            "bytes_per_rec_b4": round(per_rec, 3),
            "ratio_vs_ed25519": round(per_rec / ed_ref, 3),
            "frame_bytes_b4": round(frame, 1),
            "frames_needed": frames,
            "fits_one_mtu_at_any_b": int(g_a + H_F <= MTU),
            "batch_for_ed25519_parity": round(b_parity, 1),
            "fill_time_s_at_parity": round(fill_s, 3),
            "fill_vs_d_max": round(fill_s / D_MAX_S, 1),
        })
        print(f"{name:<22}{g_a:>8.0f}{per_rec:>12.1f}{per_rec / ed_ref:>11.2f}x"
              f"{frame:>10.0f}{frames:>8}{b_parity:>14.0f}{fill_s:>9.2f}")

    print("\nsignature+header alone vs MTU:")
    for name, (g_a, _) in SCHEMES.items():
        ok = "fits" if g_a + H_F <= MTU else "EXCEEDS -- placement B cannot fit one frame at ANY b"
        print(f"  {name:<22}{g_a + H_F:>8.0f} B   {ok}")

    out = REPO / "results" / "raw" / "pqc_projection.csv"
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "pqc_projection",
            "config_hash": provenance.config_hash(
                {"schemes": {k: v[0] for k, v in SCHEMES.items()}, "h_f": H_F, "mtu": MTU,
                 "lam": LAM, "d_max": D_MAX_S, "b": B_ADOPTED})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    buf.write("# Tier-2 item 6: PQ signature sizes substituted into OUR byte model. Projection\n")
    buf.write("# only -- no novelty claimed; the prior art is NDSS 2024 and arXiv 2510.23457.\n")
    buf.write("# ⚠️ Falcon's SIGNATURE size is not quoted in either held source (they give the\n")
    buf.write("#    certificate); it brackets the range and must not be cited as sourced.\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
