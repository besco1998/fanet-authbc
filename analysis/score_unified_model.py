#!/usr/bin/env python3
"""Score the unified closed-form model against every ns-3 capacity crossing on file (task of
2026-11-17, work package A2; the model: docs/revision/2026-11-17_unified_model_spec.md).

One row per stored crossing, with the model's inputs (standard, rate, window, loss target, frame
bytes, frames per second, airtime) and both the two-constant law and the root of the loss
expression, each as an error against ns-3: 100·(model − ns-3)/ns-3. The traffic source of every
crossing is read from its own runs file, not assumed. Nothing is fitted; nothing is run.

    python analysis/score_unified_model.py      -> results/raw/unified_model_vs_ns3.csv
"""
from __future__ import annotations

import csv
import io
import sys
from collections.abc import Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "unified_model_vs_ns3.csv"
BAND_PCT = 5.0                      # the author's claimed band for the law and the root

# the two cells every 6 Mb/s file reuses (ns3/run_nmax_direct.py CELLS "C" and "D")
LEAN = {"C": (146, 50.0), "D": (173, 12.5)}


def _rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        yield from csv.DictReader(ln for ln in fh if not ln.startswith("#"))


# ns3/run_links.py passes --txJitterMs of one period on every run (line 94) and writes no jitter
# column: its runs used the designated source
ONE_PERIOD = "1 period (run_links.py)"


def _jitters(runs_file: str) -> dict[str, str]:
    """Each cell's traffic source in a runs file: its jitter value(s) in ms, as written."""
    out: dict[str, set[str]] = {}
    path = RAW / runs_file
    if path.exists():
        for r in _rows(path):
            out.setdefault(r["cell"], set()).add(r.get("jitter_ms", ONE_PERIOD))
    return {c: "/".join(sorted(v)) for c, v in out.items()}


def _phy(standard: str, rate_mbps: float) -> tuple[phy.OfdmPhy | phy.DsssPhy, uc.Access]:
    if standard == "80211a":
        return phy.ofdm_20mhz(rate_mbps), uc.A80211A
    if standard == "80211p":
        return phy.ofdm_10mhz(rate_mbps), uc.A80211P
    if standard == "80211b" and rate_mbps == 1:
        return phy.DSSS_1M, uc.A80211B
    raise ValueError(f"no PHY for {standard} at {rate_mbps} Mb/s")


def score_row(source: str, cell: str, ns3: float, frame_bytes: int, fps: float, *,
              standard: str = "80211a", rate_mbps: float = 6, w: int | None = None,
              eps: float = 0.05, jitter_ms: str = "", stored_frame_time_us: str = "",
              note: str = "") -> dict:
    """One crossing: the model's inputs, its two values, and both errors against ns-3."""
    p, acc = _phy(standard, rate_mbps)
    if w is not None and w != acc.w:
        acc = uc.Access(acc.slot_s, acc.difs_s, w, acc.delta_s)
    tf = uc.airtime_s(p, frame_bytes)
    rho, tau0 = uc.dcf_constants(eps, acc)
    law, root = uc.n_law(fps, tf, eps, acc), uc.n_root(fps, tf, eps, acc)
    stored_tf = (float(stored_frame_time_us) - acc.difs_s * 1e6) if stored_frame_time_us else ""
    return {"source_file": source, "cell": cell, "standard": standard, "rate_mbps": rate_mbps,
            "window": acc.w, "eps": eps, "frame_bytes": frame_bytes, "frames_per_s": fps,
            "jitter_ms": jitter_ms, "tf_us": round(tf * 1e6, 3),
            "tf_stored_us": round(stored_tf, 3) if stored_tf != "" else "",
            "tau0_us": round(tau0 * 1e6, 3), "rho_star": round(rho, 6),
            "law_valid": tf >= 2 * tau0, "ns3": ns3, "law": round(law, 3), "root": round(root, 3),
            "law_err_pct": round(100 * (law - ns3) / ns3, 2),
            "root_err_pct": round(100 * (root - ns3) / ns3, 2),
            "law_in_band": abs(law - ns3) <= BAND_PCT / 100 * ns3,
            "root_in_band": abs(root - ns3) <= BAND_PCT / 100 * ns3, "note": note}


def direct() -> list[dict]:
    """ns3_nmax_direct.csv: every bracketed CROSSING row, every traffic source."""
    out = []
    for r in _rows(RAW / "ns3_nmax_direct.csv"):
        if r["n_nodes"] != "CROSSING" or not r.get("n_cross_interp"):
            continue
        fps = float(r["lambda_rec_per_s"]) / int(r["batch"])
        one_period = abs(float(r["jitter_ms"]) - 1000 / fps) < 1e-6 * 1000 / fps
        note = "designated source" if one_period and r["skew_ppm"] in ("0", "0.0") else ""
        out.append(score_row("ns3_nmax_direct", r["cell"], float(r["n_cross_interp"]),
                             int(r["frame_bytes"]), fps,
                             jitter_ms=f"{r['jitter_ms']}/{r['skew_ppm']}ppm", note=note))
    return out


def simple(source: str, runs_file: str, crossing_col: str, *, phy_cols: bool = False,
           time_col: str = "", note_col: str = "") -> list[dict]:
    """A file whose rows each give frame_bytes, frames_per_s and one ns-3 crossing."""
    jit, out = _jitters(runs_file), []
    for r in _rows(RAW / f"{source}.csv"):
        cell = r.get("cell") or r.get("ns3_cell", "")
        kw = {"standard": r["standard"], "rate_mbps": float(r["rate_mbps"])} if phy_cols else {}
        out.append(score_row(source, cell, float(r[crossing_col]), int(r["frame_bytes"]),
                             float(r["frames_per_s"]), jitter_ms=jit.get(cell, ""),
                             stored_frame_time_us=r.get(time_col, "") if time_col else "",
                             note=r.get(note_col, "") if note_col else "", **kw))
    return out


def level97() -> list[dict]:
    jit = _jitters("ns3_level97_runs.csv")
    return [score_row("capacity_97", r["cell"], float(r["ns3_crossing"]), *LEAN[r["cell"]],
                      eps=round(1 - float(r["delivered_level"]), 6),
                      jitter_ms=jit.get(r["cell"], ""))
            for r in _rows(RAW / "capacity_97.csv")]


def windows() -> list[dict]:
    jit = {**{f"{c}@4": j for c, j in _jitters("ns3_w1a_cw3_runs.csv").items()},
           **{f"{c}@8": j for c, j in _jitters("ns3_w1a_cw7_runs.csv").items()}}
    return [score_row("w1a", r["cell"], float(r["ns3"]), *LEAN[r["cell"]], w=int(r["window"]),
                      jitter_ms=jit.get(f"{r['cell']}@{r['window']}", ""))
            for r in _rows(RAW / "w1a.csv") if r["cell"] in LEAN]       # the D/C rows are ratios


def dsss() -> list[dict]:
    jit, frames = _jitters("ns3_links_w1b_runs.csv"), {"Pb1B": (146, 50.0), "Pb1D": (173, 12.5)}
    return [score_row("w1b", r["cell"], float(r["ns3"]), *frames[r["cell"]], standard="80211b",
                      rate_mbps=1, jitter_ms=jit.get(r["cell"], ""))
            for r in _rows(RAW / "w1b.csv") if r["what"] == "crossing"]


def rules() -> list[dict]:
    """The six crossings of ns3_rule_{levels,cw31}_runs.csv, recomputed as dcf_model_check does."""
    import dcf_model_check as chk
    out = []
    for case in chk.CASES:
        measured, _ = chk.ns3_crossing(case)
        if measured is None:
            continue
        jit = _jitters(f"{case.stem}_runs.csv").get(case.cell, "")
        out.append(score_row(case.stem, case.cell, round(measured, 2), *LEAN[case.cell],
                             w=case.w0, eps=round(1 - case.level, 6), jitter_ms=jit,
                             note=case.name))
    return out


def all_rows() -> list[dict]:
    return (direct()
            + simple("batch_capacity", "ns3_batch_runs.csv", "ns3_crossing")
            + simple("design_map_validation", "ns3_design_map_runs.csv", "ns3_crossing",
                     note_col="role")
            + simple("phy_links", "ns3_links_phy_runs.csv", "ns3_crossing", phy_cols=True,
                     time_col="frame_time_us")
            + simple("pq_capacity", "ns3_pq_runs.csv", "ns3_crossing", time_col="frame_time_us")
            + level97() + windows() + dsss() + rules())


def write(rows: list[dict]) -> None:
    buf = io.StringIO()
    config = {"band_pct": BAND_PCT, "a": uc.A80211A, "p": uc.A80211P, "b": uc.A80211B}
    for k, v in {**provenance.env_block(), "run": "unified_model_vs_ns3",
                 "config_hash": provenance.config_hash({k: str(v) for k, v in config.items()}),
                 "model": "src/authbc/models/unified_capacity.py; error = 100(model-ns3)/ns3"
                 }.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())


def main() -> None:
    rows = all_rows()
    write(rows)
    print(f"wrote {OUT.relative_to(REPO)} ({len(rows)} crossings)")
    for r in rows:
        flag = "" if (r["law_in_band"] and r["root_in_band"]) else "  <-- outside ±5 %"
        print(f"  {r['source_file']:22s} {r['cell']:9s} {r['standard']} {r['rate_mbps']:>4} "
              f"W{r['window']:<2} eps {r['eps']:<5} ns3 {r['ns3']:8.2f} law {r['law']:8.2f} "
              f"({r['law_err_pct']:+6.2f}%) root {r['root']:8.2f} ({r['root_err_pct']:+6.2f}%) "
              f"{r['jitter_ms']:>14s} {r['note']}{flag}")


if __name__ == "__main__":
    main()
