#!/usr/bin/env python3
"""U-C3 (a key record once in r frames) and U-C4 (a signed unit over n frames), scored as
predictions/UC3.md and UC4.md fix them (the rules: docs/revision/2026-11-17_unified_model_spec.md
§4, `authbc.models.unified_capacity`).

Reads the driver's summaries `results/raw/unified_c3_r{2,4}.csv` and `unified_c4_n{2,3}.csv`
(their CROSSING@0.95 rows, on the verified share) and the runs behind them. Writes
`results/raw/unified_c34_scored.csv`:
* **C3:** the law (G9) and the root of (G5) at ε_r with the mean airtime, each held within ±5 %;
* **C4:** the root at ε_n held within ±5 %; the law, outside its range (T_f < 2τ0), held only if
  it lies above ns-3's crossing, as its author states;
* **reported, not scored:** the ratio to r = 1 (cell D, stored ns-3 124.55) and, at every node
  count, the verified share against the rule applied to the measured per-frame delivered fraction.

    python analysis/unified_c34.py
"""
from __future__ import annotations

import csv
import io
import statistics as st
import sys
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "unified_c34_scored.csv"
EPS, TOL, F_UNIT = 0.05, 0.05, 12.5
N1_NS3 = 124.55                      # cell D, designated source (ns3_nmax_direct)
C3 = {2: "unified_c3_r2", 4: "unified_c3_r4"}
C4 = {2: ("unified_c4_n2", 98), 3: ("unified_c4_n3", 73)}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def c3_model(r: int) -> tuple[float, float, float, float]:
    """(ε_r, mean T_f, law, root) for a 173 B key frame and r − 1 frames of 158 B."""
    p = phy.OFDM_20MHZ_6M
    e = uc.eps_keyrecord(r, EPS)
    tf = (uc.airtime_s(p, 173) + (r - 1) * uc.airtime_s(p, 158)) / r
    return e, tf, uc.n_law(F_UNIT, tf, e), uc.n_root(F_UNIT, tf, e)


def c4_model(n: int, size: int) -> tuple[float, float, float, float]:
    """(ε_n, T_f, law, root) for n frames per unit at n·f frames/s."""
    e = uc.eps_fragment(n, EPS)
    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, size)
    return e, tf, uc.n_law(n * F_UNIT, tf, e), uc.n_root(n * F_UNIT, tf, e)


def err_pct(model: float, ns3: float) -> float:
    return 100.0 * (model - ns3) / ns3


def within(model: float, ns3: float) -> bool:
    return abs(model - ns3) <= TOL * ns3


def crossing(stem: str) -> tuple[float, float, float]:
    rows = [r for r in _rows(RAW / f"{stem}.csv") if r["n_nodes"] == "CROSSING@0.95"]
    if (len(rows) != 1 or rows[0]["delivered_stdev"] != "bracketed 1.000"
            or rows[0]["seeds"] != "30"):
        raise ValueError(f"{stem}: expected one 30-seed CROSSING@0.95 row, bracketed throughout")
    r = rows[0]
    return float(r["delivered_mean"]), float(r["delivered_min"]), float(r["delivered_max"])


def rule_check(stem: str, rule: Callable[[float], float]) -> list[dict[str, object]]:
    """Per node count: the mean verified share, and the rule on the mean per-frame delivery."""
    by: dict[int, list[tuple[float, float]]] = {}
    for r in _rows(RAW / f"{stem}_runs.csv"):
        by.setdefault(int(r["n_nodes"]), []).append((float(r["verified_frac"]),
                                                     float(r["delivered_frac"])))
    out = []
    for n, v in sorted(by.items()):
        ver, p = st.mean(a for a, _ in v), 1 - st.mean(b for _, b in v)
        out.append({"n_nodes": n, "verified": round(ver, 6),
                    "rule_on_measured_p": round(rule(p), 6), "diff": round(ver - rule(p), 6)})
    return out


def main() -> None:
    rows: list[dict[str, object]] = []
    checks: list[dict[str, object]] = []
    for r, stem in C3.items():
        e, tf, law, root = c3_model(r)
        x, lo, hi = crossing(stem)
        rows.append({"item": "C3", "cell": f"K{r}", "k": r, "eps_frame": round(e, 6),
                     "tf_us": round(tf * 1e6, 3), "ns3": x, "ci_lo": lo, "ci_hi": hi,
                     "law": round(law, 3), "law_err_pct": round(err_pct(law, x), 2),
                     "law_verdict": "held" if within(law, x) else "failed",
                     "root": round(root, 3), "root_err_pct": round(err_pct(root, x), 2),
                     "root_verdict": "held" if within(root, x) else "failed",
                     "ns3_ratio_to_r1": round(x / N1_NS3, 4),
                     "law_ratio_to_r1": round(law / uc.n_law(F_UNIT, c3_model(1)[1], EPS), 4),
                     "root_ratio_to_r1": round(root / uc.n_root(F_UNIT, c3_model(1)[1], EPS), 4)})
        checks += [{"item": "C3", "cell": f"K{r}", **c} for c in rule_check(
            stem, lambda p, r=r: sum((1 - p) ** j for j in range(1, r + 1)) / r)]
    for n, (stem, size) in C4.items():
        e, tf, law, root = c4_model(n, size)
        x, lo, hi = crossing(stem)
        rows.append({"item": "C4", "cell": f"F{n}", "k": n, "eps_frame": round(e, 6),
                     "tf_us": round(tf * 1e6, 3), "ns3": x, "ci_lo": lo, "ci_hi": hi,
                     "law": round(law, 3), "law_err_pct": round(err_pct(law, x), 2),
                     "law_verdict": "held (above ns-3)" if law > x else "failed (not above)",
                     "root": round(root, 3), "root_err_pct": round(err_pct(root, x), 2),
                     "root_verdict": "held" if within(root, x) else "failed",
                     "ns3_ratio_to_r1": round(x / N1_NS3, 4), "law_ratio_to_r1": "",
                     "root_ratio_to_r1": ""})
        checks += [{"item": "C4", "cell": f"F{n}", **c}
                   for c in rule_check(stem, lambda p, n=n: (1 - p) ** n)]
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "unified_c34",
                 "config_hash": provenance.config_hash({"eps": EPS, "tol": TOL, "c3": C3,
                                                        "c4": C4, "n1": N1_NS3})}.items():
        buf.write(f"# {k}={v}\n")
    for table in (rows, checks):
        w = csv.DictWriter(buf, fieldnames=list(table[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(table)
        buf.write("\n")
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
