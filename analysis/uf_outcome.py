#!/usr/bin/env python3
"""U-F's outcome tables, generated from the scored and diagnostic files, never typed by hand.

Reads `results/raw/uf_scored.csv` (`python analysis/uf.py --score`, the registered scoring) and
`results/raw/uf_diagnose_*.csv` (`python analysis/uf_diagnose.py`, unscored), and scores the
outlier through `uf.score_outlier`, as registered. Prints the markdown appended to
`predictions/UF.md` below its outcome line.

    python analysis/uf_outcome.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import uf  # noqa: E402

RAW = REPO / "results" / "raw"


def _read(name: str) -> list[dict[str, str]]:
    with (RAW / name).open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def _f(x: str, nd: int = 2) -> str:
    return f"{float(x):.{nd}f}" if x not in ("", "nan") else "—"


def _pct(x: str) -> str:
    return f"{float(x):+.2f} %" if x not in ("", "nan") else "—"


def _side(err: float) -> str:
    return "optimistic" if err > 0 else "conservative"


def scored_table() -> str:
    ci = {r["config"]: r for r in _read("uf_diagnose_ci.csv")}
    lines = ["| config | ns-3 average crossing (95 % CI) | (G23), (G25) | error | | "
             "Poisson error | no-capture error | ns-3 every-sender crossing (95 % CI) | "
             "(G24), (G25) | error | |",
             "|" + "---|" * 11]
    for r in _read("uf_scored.csv"):
        c = ci[r["config"]]
        held23 = "held" if r["g23_held"] == "1" else f"**failed**, {_side(float(r['g23_err_pct']))}"
        if r["ns3_every_sender_crossing"] == "":
            avg, worst, _s = uf._per_n(r["config"])
            n0 = min(worst)
            bound = 100 * (float(r["g24_g25"]) - n0) / n0
            w_cell = f"below the grid: {worst[n0]:.4f} at N = {n0}"
            e24, held24 = f"> {bound:+.2f} %", "**failed**, optimistic"
        else:
            w_cell = (f"{_f(r['ns3_every_sender_crossing'])} ({_f(c['every_sender_lo'])}–"
                      f"{_f(c['every_sender_hi'])})")
            e24 = _pct(r["g24_err_pct"])
            held24 = ("held" if r["g24_held"] == "1"
                      else f"**failed**, {_side(float(r['g24_err_pct']))}")
        lines.append(
            f"| {r['config']} | {_f(r['ns3_average_crossing'])} ({_f(c['average_lo'])}–"
            f"{_f(c['average_hi'])}) | {_f(r['g23_g25'])} | {_pct(r['g23_err_pct'])} | {held23} | "
            f"{_pct(r['g23_poisson_err_pct'])} | {_pct(r['no_capture_err_pct'])} | {w_cell} | "
            f"{_f(r['g24_g25'])} | {e24} | {held24} |")
    return "\n".join(lines)


def outlier_line() -> str:
    o = uf.score_outlier()
    return (f"| FOUT, N = {o['n']}, {o['seeds']} seeds | node 0's loss: measured "
            f"{o['node0_loss_measured']:.4f}, predicted {o['node0_loss_predicted']:.4f} | "
            f"{o['err_pct']:+.2f} % | {'held' if o['held'] else '**failed**'} (±20 %) | "
            f"the others' mean loss {o['others_mean_loss']:.4f} |")


def q_table() -> str:
    scored = {r["config"]: r for r in _read("uf_scored.csv")}
    qs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in _read("uf_diagnose_q.csv"):
        qs[r["config"]].append(r)
    ev: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in _read("uf_diagnose_events.csv"):
        e, p = ev[r["config"]], float(r["pairs"])
        e["pairs"] += p
        e["meas"] += p * float(r["q_measured"])
        e["n"] = float(r["n"])
    lines = ["| config | closed form, registered q̄ | × (N − 2)/(N − 1) at ns-3's crossing | "
             "ns-3, no-capture ratio q̂ at the nearest N | ns-3, on the collision events |",
             "|---|---|---|---|---|"]
    for c in uf.CONFIGS:
        a = scored[c.name]["ns3_average_crossing"]
        n = float(a) if a else float(uf.n_ref_for(c))
        rows = qs.get(c.name, [])
        near = min(rows, key=lambda r: abs(int(r["n"]) - n)) if rows else None
        qbar = uf.registered()[c.name]["q_bar"]
        ratio = (f"{float(near['q_hat']):.3f} ± {float(near['q_hat_se']):.3f} (N = {near['n']}"
                 f"{', approximate' if near['approximate'] == '1' else ''})" if near else "—")
        got = ev.get(c.name)
        evs = f"{got['meas'] / got['pairs']:.4f} (N = {got['n']:.0f})" if got else "—"
        lines.append(f"| {c.name} | {qbar:.4f} | {qbar * (n - 2) / (n - 1):.4f} | {ratio} | "
                     f"{evs} |")
    return "\n".join(lines)


def corrected_table() -> str:
    lines = ["| config | (G23) registered → with the factor | error registered → with it | "
             "(G24) registered → with it | error with it |", "|---|---|---|---|---|"]
    for r in _read("uf_diagnose_corrected.csv"):
        lines.append(f"| {r['config']} | {_f(r['g23_registered'])} → {_f(r['g23_corrected'])} | "
                     f"{_pct(r['g23_registered_err_pct'])} → {_pct(r['g23_corrected_err_pct'])} | "
                     f"{_f(r['g24_registered'])} → {_f(r['g24_corrected'])} | "
                     f"{_pct(r['g24_corrected_err_pct'])} |")
    return "\n".join(lines)


def worst_table() -> str:
    lines = ["| config | N | sd across senders: measured | geometry alone | binomial noise | "
             "geometry + noise | worst sender: measured | geometry alone (what ε_w models) | "
             "geometry + noise |", "|" + "---|" * 9]
    for r in _read("uf_diagnose_worst.csv"):
        lines.append(f"| {r['config']} | {r['n']} | {_f(r['sd_measured'], 4)} | "
                     f"{_f(r['sd_geometry'], 4)} | {_f(r['sd_binomial'], 4)} | "
                     f"{_f(r['sd_geometry_plus_noise'], 4)} | "
                     f"**{_f(r['worst_measured'], 4)}** | {_f(r['worst_geometry'], 4)} | "
                     f"**{_f(r['worst_geometry_plus_noise'], 4)}** |")
    return "\n".join(lines)


def pairs_table() -> str:
    """The registered per-pair report. The ceiling is the correlation a perfect model would reach
    under the count noise alone: sd(predicted) / sd(predicted + noise)."""
    lines = ["| config | N | pairs | mean loss: measured | (G22), p_c from (G25) | "
             "sd across pairs: measured | predicted + count noise | correlation | ceiling |",
             "|" + "---|" * 9]
    for r in _read("uf_diagnose_pairs.csv"):
        ceiling = float(r["sd_predicted"]) / float(r["sd_predicted_plus_noise"])
        lines.append(f"| {r['config']} | {r['n']} | {r['pairs']} | {_f(r['mean_measured'], 4)} | "
                     f"{_f(r['mean_predicted'], 4)} | {_f(r['sd_measured'], 4)} | "
                     f"{_f(r['sd_predicted_plus_noise'], 4)} | {_f(r['correlation'], 3)} | "
                     f"{ceiling:.3f} |")
    return "\n".join(lines)


def split_table() -> str:
    lines = ["| config | total (G23) error | loss-curve term (linear; quadratic) | q term | "
             "closure |",
             "|---|---|---|---|---|"]
    for r in _read("uf_diagnose_split.csv"):
        lines.append(f"| {r['config']} | {_pct(r['total_err_pct'])} | "
                     f"{_pct(r['loss_curve_term_pct'])}; "
                     f"{_pct(r['loss_curve_term_pct_quadratic'])} | {_pct(r['q_term_pct'])} | "
                     f"{_pct(r['closure_pct'])} |")
    return "\n".join(lines)


def counts() -> dict[str, Any]:
    s = _read("uf_scored.csv")
    return {"g23_held": sum(r["g23_held"] == "1" for r in s),
            "g24_held": sum(r["g24_held"] == "1" for r in s), "of": len(s)}


def main() -> None:
    print(counts())
    for title, fn in (("scored", scored_table), ("outlier", outlier_line), ("q", q_table),
                      ("split", split_table), ("corrected", corrected_table),
                      ("worst", worst_table), ("pairs", pairs_table)):
        print(f"\n<!-- {title} -->")
        print(fn())


if __name__ == "__main__":
    main()
