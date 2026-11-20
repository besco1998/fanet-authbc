#!/usr/bin/env python3
"""U-CAP: ns-3's receiver rule for two overlapping frames, predicted from its source, then
measured (`ns3/authbc-capture.cc`).

Work package D of `docs/prompts/NEXT_PHASE_PROMPT.md`; the registration is `predictions/UCAP.md`.

**The setting.** Frame Y is received at P_Y = −60 dBm and sent first. Frame X is received at
P_Y + SIR and starts Δ after it. Noise is F·k·290·B = −93.966 dBm (20 MHz), and both frames carry
a 173 B payload (a 209 B MPDU).

**The rule, as read in ns-3.48** (file:line in the registration):
1. **Δ < 4 µs: both preambles are in one detection window.** At its end, the strongest preamble
   is kept (`phy-entity.cc:1048–1076`), and it is detected only if its SINR is at least 4 dB. The
   SINR counts every interferer that arrived before that instant (`interference-helper.cc:
   433–463`; `threshold-preamble-detection-model.cc:31–40`). The other frame is lost. This holds
   with or without a frame-capture model, which is never consulted here.
2. **Δ ≥ 4 µs: Y was detected alone.**
   * With `SimpleFrameCaptureModel` (margin 5 dB, window 16 µs from Y's detection at 4 µs), X
     takes over if P_X > P_Y + 5 dB and X arrives by 20 µs (`phy-entity.cc:439–486`;
     `simple-frame-capture-model.cc:68–73`). Then Y is aborted and X goes through detection,
     with Y as interference.
   * Otherwise X is dropped, and Y is decoded with X as interference from Δ on.
3. **Decoding:**
   * DSSS 1 Mb/s: `DsssErrorRateModel`, success (1 − ½·e^(−22·SINR))^bits
     (`dsss-error-rate-model.cc:43–49`). The PLCP header runs 144–192 µs and the payload
     192–1864 µs, 1 bit per µs;
   * OFDM 6 Mb/s: `TableBasedErrorRateModel`. The payload success comes from
     `ns3/authbc-per.cc` at that SINR; for part of a payload it is raised to the share of its bits
     (the 32 B table scales as (1 − per)^(size/32)). A partially interfered 4 µs SIG chunk is
     neglected, so these values carry a stated 0.05 allowance.

    python analysis/ucap.py --predict      -> results/raw/ucap_predictions.csv
    python analysis/ucap.py --score DIR    -> results/raw/ucap_scored.csv
"""
from __future__ import annotations

import csv
import io
import math
import os
import subprocess
import sys
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

PY_DBM = -60.0
NOISE_DBM = -93.966
DETECT_DB = 4.0
MARGIN_DB = 5.0
DETECT_US = 4.0
WINDOW_END_US = DETECT_US + 16.0
SIRS = tuple(range(-2, 21))
OFFSETS = (0.0, 2.0, 19.0, 20.0, 21.0, 200.0)
SCORED_OFFSETS = (0.0, 2.0, 19.0, 21.0, 200.0)     # 20 µs is the window's edge: reported only
ALLOWANCE = 0.05
OUT_PRED = REPO / "results" / "raw" / "ucap_predictions.csv"
OUT_SCORE = REPO / "results" / "raw" / "ucap_scored.csv"


def _w(dbm: float) -> float:
    return 10 ** (dbm / 10)


def sinr_db(signal_dbm: float, interferer_dbm: float | None) -> float:
    interference = _w(NOISE_DBM) + (_w(interferer_dbm) if interferer_dbm is not None else 0.0)
    return 10 * math.log10(_w(signal_dbm) / interference)


def dsss_success(sinr: float, bits: int) -> float:
    return (1 - 0.5 * math.exp(-22.0 * 10 ** (sinr / 10))) ** bits


@cache
def ofdm_payload_success(sinr: float) -> float:
    """csr_payload of the whole 209 B MPDU at 6 Mb/s, from ns-3's own table (authbc-per)."""
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-per-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    out = subprocess.run([str(exe), "--mode=OfdmRate6Mbps", f"--rxPowerDbm={NOISE_DBM + sinr!r}",
                          "--sizes=173"], env=env, capture_output=True, text=True, check=True)
    row = next(csv.DictReader(io.StringIO(out.stdout)))
    return float(row["csr_payload"])


OFDM_PAYLOAD_US = (20.0, 304.0)
OFDM_PAYLOAD_BITS = 1704
DSSS_BITS_US = (144.0, 1864.0)


def decode(standard: str, sinr: float, from_us: float) -> float:
    """Success of a frame whose decoded fields are interfered at `sinr` from `from_us` on."""
    if standard == "80211b":
        start, end = DSSS_BITS_US
        return dsss_success(sinr, round(end - max(from_us, start)))
    start, end = OFDM_PAYLOAD_US
    share = (end - max(from_us, start)) / (end - start)
    return ofdm_payload_success(round(sinr, 6)) ** share


def predict(standard: str, capture: bool, offset_us: float, sir_db: float) -> tuple[float, float]:
    """(P[X received], P[Y received]) by the rule as read in ns-3.48's source."""
    px_dbm = PY_DBM + sir_db
    if offset_us < DETECT_US:                              # one detection window
        if px_dbm > PY_DBM:
            x_ok = sinr_db(px_dbm, PY_DBM) >= DETECT_DB
            return (decode(standard, sinr_db(px_dbm, PY_DBM), 0.0) if x_ok else 0.0), 0.0
        y_ok = sinr_db(PY_DBM, px_dbm) >= DETECT_DB      # ties go to Y, the first (lower UID)
        return 0.0, (decode(standard, sinr_db(PY_DBM, px_dbm), 0.0) if y_ok else 0.0)
    if capture and offset_us <= WINDOW_END_US and px_dbm > PY_DBM + MARGIN_DB:
        x_sinr = sinr_db(px_dbm, PY_DBM)
        return (decode(standard, x_sinr, 0.0) if x_sinr >= DETECT_DB else 0.0), 0.0
    return 0.0, decode(standard, sinr_db(PY_DBM, px_dbm), offset_us)


def predictions() -> list[dict[str, object]]:
    rows = []
    for standard in ("80211a", "80211b"):
        for capture in (False, True):
            for off in OFFSETS:
                for sir in SIRS:
                    px, py = predict(standard, capture, off, float(sir))
                    rows.append({"standard": standard, "capture": int(capture),
                                 "offset_us": off, "sir_db": sir, "p_x": px, "p_y": py,
                                 "scored": int(off in SCORED_OFFSETS)})
    return rows


def _held(pred: float, got: int, trials: int) -> bool:
    if pred <= 1e-9:
        return got == 0
    if pred >= 1 - 1e-9:
        return got == trials
    return abs(got / trials - pred) <= ALLOWANCE


def score(run_dir: Path) -> list[dict[str, object]]:
    pred = {(r["standard"], r["capture"], r["offset_us"], r["sir_db"]): r for r in predictions()}
    rows = []
    for f in sorted(run_dir.glob("*.csv")):
        if f.name.endswith("_drops.csv"):
            continue
        for r in csv.DictReader(f.open()):
            key = (r["standard"], int(r["capture"]), float(r["offset_us"]),
                   int(float(r["sir_db"])))
            p, n = pred[key], int(r["trials"])
            xo, yo = int(r["x_ok"]), int(r["y_ok"])
            rows.append({**{k: p[k] for k in ("standard", "capture", "offset_us", "sir_db")},
                         "trials": n, "x_measured": xo / n, "x_predicted": p["p_x"],
                         "y_measured": yo / n, "y_predicted": p["p_y"], "scored": p["scored"],
                         "held": int(_held(p["p_x"], xo, n) and _held(p["p_y"], yo, n))})
    return rows


def _write(path: Path, rows: list[dict[str, object]], run: str) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash({"py_dbm": PY_DBM, "sirs": SIRS,
                                                        "offsets": OFFSETS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def main() -> None:
    if "--predict" in sys.argv:
        _write(OUT_PRED, predictions(), "ucap_predictions")
        print(f"wrote {OUT_PRED.relative_to(REPO)}")
    elif "--score" in sys.argv:
        rows = score(Path(sys.argv[sys.argv.index("--score") + 1]))
        _write(OUT_SCORE, rows, "ucap_scored")
        scored = [r for r in rows if r["scored"]]
        print(f"{sum(r['held'] for r in scored)} of {len(scored)} scored points held")


if __name__ == "__main__":
    main()
