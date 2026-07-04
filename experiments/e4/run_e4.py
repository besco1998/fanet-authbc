"""E4 runner — Ed25519↔BLS energy crossover from MEASURED P1 timings (docs/04 §2, docs/02 T4).

Reads `results/raw/p1_crypto.csv` (sign/verify/BLS-aggregate medians + bootstrap CIs) and
`p1_sizes.csv` (encoded record sizes) and writes two provenance-stamped, immutable CSVs:

  * results/raw/e4_crossover.csv — the power-independent crossover: for the scheme pair
    Ed25519↔BLS over ρ (relay fraction) × b (batch) × Λ (record rate): the byte saving Δ(b), the
    radio time saved ΔRADIO, the extra CPU ΔCPU (median + CI propagated from P1), the break-even
    power ratio κ*=P_r/P_c, the verify-throughput feasibility of each scheme, and the winner for
    physically plausible powers (P_r/P_c ≲ 0.5).
  * results/raw/e4_bytes.csv — on-air bytes/record per encoding × scheme × placement × b.

Absolute joules are DEFERRED to P7 (powers P_c/P_r need the ⚠️ D5 meter); the tested
`models.energy.per_record` produces them once measured powers exist. Everything here is measured
timing or byte-accounting — no fabricated numbers, no assumed watts (CLAUDE.md Law 2/7).
"""

from __future__ import annotations

import csv
from pathlib import Path

from authbc.bench import provenance
from authbc.models import crossover as x

# Repo layout (cwd-independent): this file is <repo>/experiments/e4/run_e4.py.
REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "results" / "raw"

# Sweep (docs/04 §2 E4 row). b∈ measured BLS aggregate batch sizes (p1_crypto.csv).
RHOS = (0.0, 0.25, 0.5, 1.0)
LAMBDAS = (50, 200, 800, 2000)
BATCHES = (2, 4, 8, 16, 32)
H_F = 40.0   # frame header bytes (docs/02 T2)
H_A = 0.0    # BLS aggregate header (parameter; 0 = BLS-best case, docs/audits/p5)
SCHEME_G = {"ed25519": 64.0, "ecdsa_p256": 64.0, "bls": x.G_AGG_BYTES}


# --- CSV I/O ------------------------------------------------------------------------------
def _read_csv(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Read one of our CSVs: `# key=value` header block + a DictReader body."""
    meta: dict[str, str] = {}
    lines = path.read_text().splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
        else:
            body_start = i
            break
    reader = csv.DictReader(lines[body_start:])
    return meta, list(reader)


def _write_csv(path: Path, meta: dict, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}={v}\n")
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# --- parse the measured P1 inputs ---------------------------------------------------------
def load_crypto(path: Path) -> dict:
    """Extract the timings E4 needs (seconds): Ed25519/BLS verify, BLS agg_verify(b)."""
    _, rows = _read_csv(path)
    ns = 1e-9

    def triple(scheme: str, op: str, agg_b: str = "") -> tuple[float, float, float]:
        for r in rows:
            if r["scheme"] == scheme and r["op"] == op and r["agg_b"] == agg_b:
                return (float(r["median_ns"]) * ns, float(r["ci_lo_ns"]) * ns,
                        float(r["ci_hi_ns"]) * ns)
        raise KeyError(f"missing {scheme}/{op}/agg_b={agg_b!r} in {path.name}")

    return {
        "t_vf_ed": triple("ed25519", "verify"),
        "t_vf_bls": triple("bls", "verify"),
        "t_av": {b: triple("bls", "agg_verify", str(b)) for b in BATCHES},
    }


def load_sizes(path: Path) -> dict[str, float]:
    """encoding → mean encoded bytes s (p1_sizes.csv)."""
    _, rows = _read_csv(path)
    return {r["encoding"]: float(r["value"]) for r in rows if r["metric"] == "mean_bytes"}


# --- crossover grid -----------------------------------------------------------------------
def crossover_rows(cy: dict) -> list[dict]:
    ed_med, ed_lo, ed_hi = cy["t_vf_ed"]
    rows: list[dict] = []
    for b in BATCHES:
        av_med, av_lo, av_hi = cy["t_av"][b]
        bls_med, bls_lo, bls_hi = cy["t_vf_bls"]
        d_relay = x.delta_relay_bytes(b, h_a=H_A)
        d_own = x.delta_own_bytes(b)
        dr_relay = x.radio_saving_s(d_relay)
        dr_own = x.radio_saving_s(d_own)

        # ΔCPU is increasing in BLS time, decreasing in Ed time ⇒ monotone CI propagation.
        cpu_relay = {
            "med": x.extra_cpu_relay_s(av_med, b, ed_med),
            "lo": x.extra_cpu_relay_s(av_lo, b, ed_hi),
            "hi": x.extra_cpu_relay_s(av_hi, b, ed_lo),
        }
        cpu_own = {
            "med": x.extra_cpu_own_s(bls_med, ed_med, b),
            "lo": x.extra_cpu_own_s(bls_lo, ed_hi, b),
            "hi": x.extra_cpu_own_s(bls_hi, ed_lo, b),
        }
        for rho in RHOS:
            d_bytes = x.mix(rho, d_own, d_relay)
            dradio = x.mix(rho, dr_own, dr_relay)                # bytes are exact ⇒ no CI
            dcpu = {k: x.mix(rho, cpu_own[k], cpu_relay[k]) for k in ("med", "lo", "hi")}
            kstar = {k: x.kappa_star(dcpu[k], dradio) for k in ("med", "lo", "hi")}
            # per-record verify time each scheme must sustain at rate Λ
            bls_vf_rec = x.mix(rho, bls_med / b, av_med / b)
            ed_vf_rec = x.mix(rho, ed_med / b, ed_med)           # own amortized; relay per-record
            for lam in LAMBDAS:
                rows.append({
                    "scheme_pair": "ed25519_vs_bls",
                    "rho": rho, "b": b, "lambda": lam,
                    "delta_bytes": round(d_bytes, 4),
                    "radio_saving_us": round(dradio * 1e6, 4),
                    "extra_cpu_us_med": round(dcpu["med"] * 1e6, 4),
                    "extra_cpu_us_lo": round(dcpu["lo"] * 1e6, 4),
                    "extra_cpu_us_hi": round(dcpu["hi"] * 1e6, 4),
                    "kappa_star_med": round(kstar["med"], 4),
                    "kappa_star_lo": round(kstar["lo"], 4),
                    "kappa_star_hi": round(kstar["hi"], 4),
                    "ed_verify_ok": x.verify_throughput_ok(ed_vf_rec, lam),
                    "bls_verify_ok": x.verify_throughput_ok(bls_vf_rec, lam),
                    "winner_plausible": x.winner_for_plausible_powers(kstar["med"]),
                })
    return rows


def bytes_rows(sizes: dict[str, float]) -> list[dict]:
    rows: list[dict] = []
    for enc, s in sizes.items():
        for scheme, g in SCHEME_G.items():
            for b in BATCHES:
                own = s + (g + H_F) / b                      # self-batch: one sig / frame
                if scheme == "bls":
                    relay = s + (g + H_A + H_F) / b          # aggregate: one agg / frame
                else:
                    relay = s + g + H_F / b                  # per-record sig
                rows.append({
                    "encoding": enc, "scheme": scheme, "b": b,
                    "own_selfbatch_bytes": round(own, 4),
                    "relay_bytes": round(relay, 4),
                })
    return rows


def main() -> None:
    cy = load_crypto(RAW / "p1_crypto.csv")
    sizes = load_sizes(RAW / "p1_sizes.csv")

    ed_med = cy["t_vf_ed"][0]
    bls_med = cy["t_vf_bls"][0]
    speedup = bls_med / ed_med  # the "20–60×" doc anticipation vs measured (Law 6 honesty)

    env = provenance.env_block()
    cfg = {"rhos": RHOS, "lambdas": LAMBDAS, "batches": BATCHES, "h_f": H_F, "h_a": H_A}
    meta = {**env, "run": "e4_crossover", "config_hash": provenance.config_hash(cfg),
            "ed25519_verify_speedup_vs_bls": round(speedup, 3),
            "plausible_kappa_max": x.PLAUSIBLE_KAPPA_MAX, "R_bps": int(x.R_BPS)}

    cross = crossover_rows(cy)
    _write_csv(RAW / "e4_crossover.csv", meta,
               ["scheme_pair", "rho", "b", "lambda", "delta_bytes", "radio_saving_us",
                "extra_cpu_us_med", "extra_cpu_us_lo", "extra_cpu_us_hi",
                "kappa_star_med", "kappa_star_lo", "kappa_star_hi",
                "ed_verify_ok", "bls_verify_ok", "winner_plausible"], cross)
    _write_csv(RAW / "e4_bytes.csv", {**env, "run": "e4_bytes",
               "config_hash": provenance.config_hash({"h_f": H_F, "h_a": H_A})},
               ["encoding", "scheme", "b", "own_selfbatch_bytes", "relay_bytes"], bytes_rows(sizes))

    winners = {r["winner_plausible"] for r in cross}
    kmin = min(r["kappa_star_med"] for r in cross)
    print(f"wrote {RAW/'e4_crossover.csv'} ({len(cross)} rows) and {RAW/'e4_bytes.csv'}")
    print(f"Ed25519 verify is {speedup:.1f}x cheaper than BLS single-verify "
          "(doc anticipated 20-60x)")
    print(f"winners across grid: {winners}; min kappa*={kmin} "
          f"(plausible band <= {x.PLAUSIBLE_KAPPA_MAX})")


if __name__ == "__main__":
    main()
