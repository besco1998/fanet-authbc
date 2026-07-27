#!/usr/bin/env python3
"""x86 <-> RPi4 comparison for the P7b micro results (docs/04 §1, audit finding F6).

Reads the frozen x86 baseline (results/raw/p1_{crypto,sizes}.csv) and an ARM run harvested by
hw/run_micro.sh (results/hw/p1_{crypto,sizes}.<host>.csv) and reports, with pre-stated expectations
(Law 6):

  * per-op ARM/x86 ratio, against the documented 5-15x band;
  * verify >= sign within each scheme, and BLS-verify >> Ed25519-verify still holding on ARM;
  * F6 WATCH: does ECDSA still beat Ed25519 on ARM? On x86 it does (OpenSSL P-256 assembly). If ARM
    flips the order, E5's byte-tied scheme pick flips ECDSA -> Ed25519. Both are 64 B, so the 96.4 %
    auth-byte headline is unchanged either way -- but it is a FINDING that must be recorded;
  * ENCODED SIZES MUST BE IDENTICAL across platforms. The encoders are deterministic and
    integer-only, so any byte difference is a portability bug, not a platform effect (Law 7).

    ./hw/compare_platforms.py                                  # auto-discovers the ARM files
    ./hw/compare_platforms.py --arm results/hw/p1_crypto.authbc-pi4a.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw"

RATIO_LO, RATIO_HI = 5.0, 15.0     # docs/04 §1 anchor: RPi4 is ~5-15x slower than x86

# Clock speeds for CYCLE normalisation. A wall-clock ratio conflates two effects: the clock
# frequency difference and the per-cycle instruction efficiency; only the latter says anything
# about the code. The clock ratio is a hard FLOOR: nothing can be slower by less, so the 5-15x
# anchor is unreachable for any primitive equally optimised on both platforms (measured: Ed25519
# needs ~1.05-1.16x the cycles on ARM, so its wall ratio is ~the clock ratio and lands below 5x).
# f_x86 is the i5-14400F max turbo; the true sustained frequency during the x86 run is unknown under
# WSL2, so cycle counts are APPROXIMATE and only their ordering/magnitude should be relied on.
F_X86_HZ = 4.7e9
F_ARM_HZ = 1.8e9


def read_csv(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    meta: dict[str, str] = {}
    body: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
        else:
            body.append(line)
    return meta, list(csv.DictReader(io.StringIO("\n".join(body))))


def key(row: dict[str, str]) -> str:
    b = row.get("agg_b") or ""
    return f"{row['scheme']}:{row['op']}" + (f":{b}" if b else "")


def find_arm(kind: str, explicit: Path | None) -> Path:
    if explicit:
        return explicit
    hits = sorted(HW.glob(f"p1_{kind}.*.csv"))
    clean = [p for p in hits if ".THROTTLED" not in p.name]
    if not hits:
        sys.exit(f"no ARM {kind} file in {HW} — run hw/run_micro.sh on the Pi first")
    if not clean:
        sys.exit(f"only THROTTLED {kind} runs found ({[p.name for p in hits]}).\n"
                 "Fix cooling, REBOOT to clear the sticky bits, and re-run. Refusing to compare "
                 "throttled data (Law 3).")
    return clean[-1]


def compare_sizes(arm_path: Path) -> bool:
    _, x86 = read_csv(RAW / "p1_sizes.csv")
    _, arm = read_csv(arm_path)
    xm = {(r["encoding"], r["metric"]): r["value"] for r in x86}
    am = {(r["encoding"], r["metric"]): r["value"] for r in arm}
    diffs = [(k, xm[k], am[k]) for k in sorted(xm) if k in am and xm[k] != am[k]]
    print("\n== encoded sizes: must be IDENTICAL across platforms ==")
    if diffs:
        print("  !! PORTABILITY BUG — encoders are deterministic, sizes must not vary:")
        for (enc, metric), x, a in diffs:
            print(f"     {enc:9} {metric:14} x86={x:>10}  arm={a:>10}")
        return False
    print(f"  OK — all {len(xm)} size metrics byte-identical (deterministic encoders confirmed)")
    return True


def compare_crypto(arm_path: Path) -> None:
    xmeta, x86 = read_csv(RAW / "p1_crypto.csv")
    ameta, arm = read_csv(arm_path)
    xs = {key(r): float(r["median_ns"]) for r in x86}
    as_ = {key(r): float(r["median_ns"]) for r in arm}

    print(f"\n== timings: {ameta.get('device_model', 'ARM')} vs {xmeta.get('cpu', 'x86')} ==")
    print(f"   governor={ameta.get('device_governor')} "
          f"temp {ameta.get('device_temp_before')} -> {ameta.get('device_temp_after')}")
    clock_ratio = F_X86_HZ / F_ARM_HZ
    print(f"   clock floor = {clock_ratio:.2f}x  (x86 {F_X86_HZ / 1e9:.1f} GHz / ARM "
          f"{F_ARM_HZ / 1e9:.1f} GHz) — no wall ratio can fall below this")
    print(f"\n{'op':<24}{'x86 (us)':>11}{'ARM (us)':>11}{'wall':>8}{'cyc ARM/x86':>13}  band")
    out_of_band = []
    for k in sorted(as_.keys() & xs.keys()):
        ratio = as_[k] / xs[k]
        cyc = ratio / clock_ratio          # per-cycle efficiency: 1.0 = identical work per cycle
        mark = "ok" if RATIO_LO <= ratio <= RATIO_HI else "OUT"
        if mark == "OUT":
            out_of_band.append((k, ratio, cyc))
        print(f"{k:<24}{xs[k] / 1e3:>11.1f}{as_[k] / 1e3:>11.1f}"
              f"{ratio:>7.2f}x{cyc:>12.2f}x  {mark}")

    print("\n== ordering gates (must hold on both platforms) ==")
    for scheme in ("ed25519", "ecdsa_p256", "bls"):
        s, v = as_.get(f"{scheme}:sign"), as_.get(f"{scheme}:verify")
        if s and v:
            ok = "OK" if v >= s else "VIOLATED"
            print(f"  {scheme:<12} verify >= sign : {v / 1e3:8.1f} >= {s / 1e3:8.1f} us  {ok}")
    bls_v, ed_v = as_.get("bls:verify"), as_.get("ed25519:verify")
    if bls_v and ed_v:
        print(f"  BLS-verify >> Ed25519-verify : {bls_v / ed_v:.1f}x  "
              f"{'OK' if bls_v > 5 * ed_v else 'CHECK'}")

    # --- F6 watch -----------------------------------------------------------
    print("\n== F6 WATCH: ECDSA vs Ed25519 ordering ==")
    for label, d in (("x86", xs), ("ARM", as_)):
        e, d25 = d.get("ecdsa_p256:verify"), d.get("ed25519:verify")
        if e and d25:
            winner = "ECDSA" if e < d25 else "Ed25519"
            print(f"  {label}: ECDSA {e / 1e3:7.1f} us vs Ed25519 {d25 / 1e3:7.1f} us "
                  f"-> {winner} faster")
    xe, xd = xs.get("ecdsa_p256:verify"), xs.get("ed25519:verify")
    ae, ad = as_.get("ecdsa_p256:verify"), as_.get("ed25519:verify")
    if all((xe, xd, ae, ad)):
        flipped = (xe < xd) != (ae < ad)
        print("  => ORDER FLIPPED on ARM. Record as a finding: E5's byte-tied scheme pick becomes "
              "Ed25519 (D2's default).\n     Both are 64 B, so the 96.4% auth-byte headline is "
              "UNCHANGED." if flipped else
              "  => order preserved; E5's ECDSA pick still holds on ARM.")

    if out_of_band:
        print(f"\n== {len(out_of_band)} op(s) outside the {RATIO_LO}-{RATIO_HI}x band ==")
        for k, r, c in out_of_band:
            print(f"     {k:<24}wall {r:5.2f}x   cycles {c:5.2f}x")
        below = [x for x in out_of_band if x[1] < RATIO_LO]
        if below and all(c < 2.2 for _, _, c in below):
            print(f"   EXPLAINED, not a fault: these sit at ~{clock_ratio:.1f}x because ARM needs "
                  "only ~1-2x the CYCLES,\n   i.e. the primitive is about as well optimised on ARM "
                  "as on x86, so the wall ratio collapses\n   to the clock floor. The 5-15x anchor "
                  "is unreachable for such primitives and should be\n   restated per-cycle (raise "
                  "with Mohamed; do NOT silently widen the band).")
        else:
            print("   Investigate BEFORE recording (governor? throttling? thermal?).")
    else:
        print(f"\nAll ratios inside the {RATIO_LO}-{RATIO_HI}x band.")


def main() -> None:
    ap = argparse.ArgumentParser(description="compare frozen x86 vs ARM P1 micro results")
    ap.add_argument("--arm", type=Path, help="ARM p1_crypto CSV (default: newest non-THROTTLED)")
    ap.add_argument("--arm-sizes", type=Path, help="ARM p1_sizes CSV")
    args = ap.parse_args()
    crypto = find_arm("crypto", args.arm)
    sizes = find_arm("sizes", args.arm_sizes)
    print(f"x86 baseline : {RAW / 'p1_crypto.csv'}")
    print(f"ARM run      : {crypto}")
    compare_sizes(sizes)
    compare_crypto(crypto)
    print("\nNext: record this table in docs/audits/p7.md, then feed the measured timings + the "
          "INA219 powers into experiments/e5/config.yaml and re-freeze.")


if __name__ == "__main__":
    main()
