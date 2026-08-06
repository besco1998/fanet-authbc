#!/usr/bin/env python3
"""Do the four axes actually COUPLE? A factorial ablation (Tier-2 item 4).

**The gap this closes.** The paper's central claim is a *co-design*: that encoding, authentication
placement, signature scheme and batching must be optimised **together**. The evidence offered so far
is a **decomposition** — 79.2 % of the byte saving attributed to placement×batching, 20.8 % to
encoding. A decomposition and an ablation are not the same thing:

* a **decomposition** splits a total among axes and is possible even when the axes are perfectly
  independent;
* an **ablation** asks what happens when you remove one axis, and only its *interaction* terms show
  that the axes need each other.

⚠️ If the axes turn out to be separable, "co-design" is overclaimed and the honest framing is
"four independent optimisations applied together". This script is written to be able to return that
answer.

**Design.** Full 2^k factorial on `bytes_per_record`, each axis at its baseline level (the naive
A+JSON configuration) and its co-design level. Main effects and every interaction are computed by
the standard Yates contrast, so an interaction of zero means the axes are additive.

**The scheme axis is handled separately and deliberately.** At the operating point the co-design and
the baseline pick the *same* scheme (Ed25519, 64 B) and ECDSA-P256 is also 64 B, so that axis is
byte-degenerate by construction — including it as a 0/0 contrast would manufacture a null. Its real
cost is reported instead by pricing the one scheme that differs, BLS at 96 B.

Writes results/raw/factorial_ablation.csv.
"""
from __future__ import annotations

import csv
import io
import itertools
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import framesizes, provenance  # noqa: E402
from authbc.models.energy import Placement  # noqa: E402
from authbc.models.optimizer import bytes_per_record  # noqa: E402

H_F, G_A_ED, G_A_BLS = 44.0, 64.0, 96.0
B_BASE, B_OPT = 1, 4

# axis -> (baseline level, co-design level)
AXES = {
    "encoding": ("json", "delta"),
    "placement": ("A", "B"),
    "batching": (B_BASE, B_OPT),
}


def _bytes(encoding: str, placement: str, batch: int, g_a: float = G_A_ED) -> float:
    s = framesizes.measured_sizes()[encoding]
    plc = Placement.A if placement == "A" else Placement.B
    return bytes_per_record(plc, batch, s, g_a, H_F, 1)


def main() -> None:
    names = list(AXES)
    # level index 0 = baseline, 1 = co-design; enumerate the full 2^k design
    corners = list(itertools.product((0, 1), repeat=len(names)))
    value = {}
    rows = []
    for corner in corners:
        levels = {n: AXES[n][i] for n, i in zip(names, corner, strict=True)}
        v = _bytes(levels["encoding"], levels["placement"], levels["batching"])
        value[corner] = v
        rows.append({
            "encoding": levels["encoding"], "placement": levels["placement"],
            "batch": levels["batching"],
            "axes_at_codesign": sum(corner),
            "bytes_per_rec": round(v, 4),
        })

    base, full = value[(0,) * len(names)], value[(1,) * len(names)]
    print(f"baseline (A+JSON, b=1) = {base:.3f} B/rec")
    print(f"co-design (B+delta, b=4) = {full:.3f} B/rec   total saving "
          f"{base - full:.3f} B ({100 * (base - full) / base:.2f} %)\n")

    # Yates contrasts: effect of a subset S = 2^-(k-1) * sum over corners of
    # (product of +-1 for axes in S) * value. Interactions are the subsets with |S| > 1.
    print(f"{'term':<34}{'effect (B/rec)':>16}   interpretation")
    effects = {}
    k = len(names)
    for r in range(1, k + 1):
        for subset in itertools.combinations(range(k), r):
            total = 0.0
            for corner in corners:
                sign = 1.0
                for ax in subset:
                    sign *= 1.0 if corner[ax] == 1 else -1.0
                total += sign * value[corner]
            eff = total / (2 ** (k - 1))
            label = " x ".join(names[i] for i in subset)
            effects[label] = eff
            kind = "MAIN" if r == 1 else ("2-way" if r == 2 else "3-way")
            print(f"{label:<34}{eff:>16.4f}   {kind}")

    inter = {k_: v for k_, v in effects.items() if " x " in k_}
    largest = max(inter.items(), key=lambda kv: abs(kv[1]))
    main_only = {k_: v for k_, v in effects.items() if " x " not in k_}
    print(f"\nlargest interaction: {largest[0]} = {largest[1]:+.4f} B/rec")
    print(f"largest main effect: "
          f"{max(main_only.items(), key=lambda kv: abs(kv[1]))[0]} = "
          f"{max(abs(v) for v in main_only.values()):.4f} B/rec")

    # The specific structural claim worth checking: placement is inert without batching.
    a_b1, b_b1 = _bytes("delta", "A", 1), _bytes("delta", "B", 1)
    a_b4, b_b4 = _bytes("delta", "A", B_OPT), _bytes("delta", "B", B_OPT)
    print(f"\nplacement A->B at b=1: {a_b1:.3f} -> {b_b1:.3f}  (saves {a_b1 - b_b1:.3f} B)")
    print(f"placement A->B at b={B_OPT}: {a_b4:.3f} -> {b_b4:.3f}  (saves {a_b4 - b_b4:.3f} B)")

    # Scheme axis, priced separately (see the module docstring for why it is not in the factorial).
    ed, bls = _bytes("delta", "B", B_OPT, G_A_ED), _bytes("delta", "B", B_OPT, G_A_BLS)
    print(f"\nscheme at the optimum: Ed25519 {ed:.3f} vs BLS {bls:.3f} B/rec "
          f"(+{bls - ed:.3f}); ECDSA-P256 is also 64 B, so the axis is byte-degenerate "
          f"between the two the optimizer considers")

    for label, eff in effects.items():
        rows.append({"encoding": "", "placement": "", "batch": "", "axes_at_codesign": "",
                     "bytes_per_rec": "", "term": label, "effect_bytes": round(eff, 4)})

    out = REPO / "results" / "raw" / "factorial_ablation.csv"
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "factorial_ablation",
            "config_hash": provenance.config_hash(
                {"axes": {k_: list(map(str, v)) for k_, v in AXES.items()},
                 "h_f": H_F, "g_a": G_A_ED})}
    for k_, v in meta.items():
        buf.write(f"# {k_}={v}\n")
    buf.write("# Tier-2 item 4: is the co-design claim an ABLATION result, or only a\n")
    buf.write("# decomposition? Rows with `term` are Yates contrasts; interactions\n")
    buf.write("# are the terms containing ' x '.\n")
    w = csv.DictWriter(buf, fieldnames=["encoding", "placement", "batch", "axes_at_codesign",
                                        "bytes_per_rec", "term", "effect_bytes"], restval="")
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
