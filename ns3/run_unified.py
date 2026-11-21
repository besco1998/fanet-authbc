#!/usr/bin/env python3
"""Runs for the unified-model validation (task of 2026-11-17, work packages C and D): every new
ns-3 run of the task goes through the audit twin `authbc-links-audit.cc`, which is
`authbc-links.cc` at its defaults (gate: `ns3/verify_audit_twin.py`). Registrations come first
(`predictions/U*.md`, tag `prereg-U*`); this driver only runs what they name.

    python ns3/run_unified.py --cells UB16 --pilot              # 5 seeds, coarse grid
    python ns3/run_unified.py --cells UB16 --n 350 355 ... --seeds 30   # the measurement
    python ns3/run_unified.py --cells C --n 14 --seeds 10 --trace DIR    # keep the traces

Raw runs go to results/raw/<stem>_runs.csv (one row per cell, N and seed, appended, resumable);
the summary to results/raw/<stem>.csv: per node count the mean, spread and seeds (for a C3/C4
cell, of the verified fraction — the columns keep their delivered_* names), then one
CROSSING row per cell — the straight-line crossing of the mean delivered fraction and its
bootstrap interval over seeds, as the frozen campaign computes them (`authbc.bench.stats`).
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import statistics as st
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing, interpolated_crossing_ci  # noqa: E402
from authbc.sim.verified import (  # noqa: E402
    read_allrx,
    unit_completion_ns,
    units_sent,
    untimed,
    verified_key_chain,
    verified_units,
)

RAW = REPO / "results" / "raw"
SIM_TIME = 20.0
BOOTSTRAP_SEED = 0


@dataclass(frozen=True)
class Cell:
    frame_bytes: int
    fps: float
    standard: str = "80211a"
    mode: str = "OfdmRate6Mbps"
    extra: tuple[str, ...] = ()           # further audit-twin options
    verify: str = ""                      # "key:r" or "unit:n": score verified records (C3, C4)
    sim_s: float = SIM_TIME               # simulated seconds (U-FS: 100 s, for losses of 0.2–1 %)

    def args(self) -> list[str]:
        a = [f"--frameSize={self.frame_bytes}", f"--framesPerSec={self.fps!r}",
             f"--txJitterMs={one_period_ms(self.fps)!r}", *self.extra]
        if (self.standard, self.mode) != ("80211a", "OfdmRate6Mbps"):
            a += [f"--standard={self.standard}", f"--dataMode={self.mode}"]
        return a


def one_period_ms(fps: float) -> float:
    """One sending period in ms that the scenario's guard accepts (as `run_nmax_direct`)."""
    period = 1000.0 / fps
    while period * 1e-3 > 1.0 / fps:
        period = math.nextafter(period, 0.0)
    return period


# lean format: 137 B fixed + 9 B per record, 50 records/s, 802.11a 6 Mb/s (U-C1, U-C2)
CELLS: dict[str, Cell] = {
    "C": Cell(146, 50.0),
    "D": Cell(173, 12.5),
    "UB16": Cell(137 + 9 * 16, 50.0 / 16),
    "UB32": Cell(137 + 9 * 32, 50.0 / 32),
    "UB64": Cell(137 + 9 * 64, 50.0 / 64),
}
# U-D (predictions/UD.md): standard 802.11b, 1 Mb/s, long preamble. D1 and D3: the base and
# design frames at W = 32 (the standard's) and, by --cwMin = W − 1, at W = 16 and 8.
_B = {"standard": "80211b", "mode": "DsssRate1Mbps"}
for _name, (_bytes, _fps) in {"Pb1B": (146, 50.0), "Pb1D": (173, 12.5)}.items():
    CELLS[_name] = Cell(_bytes, _fps, **_B)
    for _w in (16, 8):
        CELLS[f"{_name}W{_w}"] = Cell(_bytes, _fps, extra=(f"--cwMin={_w - 1}",), **_B)
# D2: the batch sweep at 10 records/s, ℓ(b) = 137 + 9b, f = 10/b
for _b in (1, 2, 4, 8, 16, 32):
    CELLS[f"DB{_b}"] = Cell(137 + 9 * _b, 10.0 / _b, **_B)
# C3: cell D with a key record once in r frames — a 173 B key frame, then r − 1 frames of 158 B,
# all with b = 4 records; a frame verifies only with every earlier frame of its group.
CELLS["K2"] = Cell(173, 12.5, extra=("--sizePattern=173,158",), verify="key:2")
CELLS["K4"] = Cell(173, 12.5, extra=("--sizePattern=173,158,158,158",), verify="key:4")
# C4: cell D's 173 B signed unit as n frames handed to the MAC together, each with its own 23 B
# header (98 B, 73 B); frames_per_s is the unit rate, the frame rate is n times it.
CELLS["F2"] = Cell(98, 12.5, extra=("--burst=2",), verify="unit:2")
CELLS["F3"] = Cell(73, 12.5, extra=("--burst=3",), verify="unit:3")
# C5, setting D1 (predictions/UC5D1.md): 802.11a at 48 Mb/s, every link received at −77.17 dBm
# (FixedRssLossModel), the lean format at 200 records/s.
for _b in (1, 2, 4, 8, 16, 32):
    CELLS[f"W48B{_b}"] = Cell(137 + 9 * _b, 200.0 / _b, "80211a", "OfdmRate48Mbps",
                              extra=("--rxPowerDbm=-77.17",))
# U-C4S (predictions/UC4S.md): U-C4's units with each frame on its own jittered slot ("spread"),
# per-source send counts (--perNode) so that only whole units count.
CELLS["F2P"] = Cell(98, 25.0, extra=("--perNode=1",), verify="unit:2")
CELLS["F3P"] = Cell(73, 37.5, extra=("--perNode=1",), verify="unit:3")
# U-C4B (predictions/UC4B.md): the burst correction's new cells, units sent as a burst.
CELLS["BB2"] = Cell(98, 12.5, "80211b", "DsssRate1Mbps", extra=("--burst=2",), verify="unit:2")
CELLS["BB3"] = Cell(73, 12.5, "80211b", "DsssRate1Mbps", extra=("--burst=3",), verify="unit:3")
CELLS["AB120"] = Cell(72, 12.5, extra=("--burst=2", "--sizePattern=72,71"), verify="unit:2")
# Diagnostics for U-C4's failure, not registered: the same frames at the same frame rate, but
# each sent on its own jittered slot instead of in a burst. Only the per-frame loss is compared.
CELLS["F2S"] = Cell(98, 25.0)
CELLS["F3S"] = Cell(73, 37.5)
# Tooling checks, not registered: cell D with r = 1 and n = 1 must give the delivered fraction.
CELLS["DK1"] = Cell(173, 12.5, verify="key:1")
CELLS["DU1"] = Cell(173, 12.5, verify="unit:1")
# U-G25 (predictions/UG25.md, work package B of docs/prompts/NEXT_PHASE_PROMPT.md): (G25) on new
# cells, the same as analysis/ug25.py's (tests/test_ug25.py holds them equal).
for _bytes, _fps in ((120, 15.0), (120, 20.0), (240, 15.0), (240, 20.0)):
    CELLS[f"GB{_bytes}F{_fps:g}"] = Cell(_bytes, _fps, **_B)
for _bytes, _fps in ((640, 20.0), (640, 30.0), (900, 20.0), (900, 30.0)):
    CELLS[f"GA{_bytes}F{_fps:g}"] = Cell(_bytes, _fps)
# U-FS (predictions/UFS.md): the finite-station form at N = 3–5, u ≤ 0.5, 100 s runs; the cells
# are analysis/ufs.py's, imported so that the two cannot drift apart.
sys.path.insert(0, str(REPO / "analysis"))
from ufs import CELLS as _FS_CELLS  # noqa: E402

for _c in _FS_CELLS:
    CELLS[_c.name] = Cell(_c.frame_bytes, _c.fps, _c.standard,
                          "DsssRate1Mbps" if _c.standard == "80211b" else "OfdmRate6Mbps",
                          sim_s=100.0)
# U-F (predictions/UF.md): capture and geometry; the configurations are analysis/uf.py's.
# Per-source and per-pair files are kept only when the driver is given --trace DIR.
from uf import CONFIGS as _F_CONFIGS  # noqa: E402
from uf import OUTLIER as _F_OUTLIER  # noqa: E402
from uf import OUTLIER_M as _F_OUTLIER_M  # noqa: E402
from uf import TX_DBM as _F_TX_DBM  # noqa: E402


def _f_cell(c, extra: tuple[str, ...] = ()) -> Cell:
    return Cell(c.frame_bytes, c.fps, c.standard,
                "DsssRate1Mbps" if c.standard == "80211b" else "OfdmRate6Mbps",
                extra=(f"--radiusM={c.radius_m!r}", f"--pathLossExp={c.alpha}",
                       f"--txPowerDbm={_F_TX_DBM!r}", "--perNode=1", "--perPair=1",
                       *(("--nakagamiM=1",) if c.fading else ()), *extra))


for _c in _F_CONFIGS:
    CELLS[_c.name] = _f_cell(_c)
CELLS["FOUT"] = _f_cell(_F_OUTLIER, (f"--outlierM={_F_OUTLIER_M!r}",))

# U-H (predictions/UH.md), group (a): the 5 GHz burst-off anchor, N = 2, the 1 464 B MPDU
# (frameSize 1 428), W = 10 and 16; and the saturated pair at 400 frames/s offered.
for _w in (10, 16):
    for _f in (124.0, 174.0, 211.0, 400.0):
        CELLS[f"HA{_f:g}W{_w}"] = Cell(1428, _f, extra=(f"--cwMin={_w - 1}",), sim_s=100.0)
# U-H group (b): W1f's four boards at 65 frames/s, 802.11b 1 Mb/s, ns-3 frameSize 173; each
# board's window from its one-sender cycle under two slot/DIFS families (analysis/uh.py), as
# CWmin = W − 1 per node; two capture ends: equal power (E), and equal mean power with Rayleigh
# per frame and ns-3's frame-capture model at its 5 dB margin (C), the assumed channel.
from uh import FAMILIES as _H_FAMILIES  # noqa: E402
from uh import W1F_FRAME as _H_FRAME  # noqa: E402
from uh import W1F_RATE as _H_RATE  # noqa: E402
from uh import board_windows as _h_windows  # noqa: E402

for _fam, (_slot, _difs) in _H_FAMILIES.items():
    _cw = ",".join(str(w - 1) for w in _h_windows(_fam))
    _slot_opt = () if _slot == 20e-6 else (f"--slotUs={round(_slot * 1e6)}",)
    for _end, _cap in (("E", ()), ("C", ("--nakagamiM=1", "--captureMarginDb=5"))):
        CELLS[f"HB{_fam}{_end}"] = Cell(_H_FRAME, _H_RATE, "80211b", "DsssRate1Mbps",
                                        extra=(f"--cwMinList={_cw}", *_slot_opt, *_cap),
                                        sim_s=100.0)

# Diagnostic, not registered (2026-11-20): ns-3 at the event comparison's own cells
# (analysis/finite_station_check.py), N = 2 and 3, to see which event simulation ns-3 follows at
# small N after U-FS's expectation missed. 10 seeds of 100 s each, as the comparison ran.
for _std, _size, _ph in (("80211b", 145, "DsssRate1Mbps"), ("80211a", 1400, "OfdmRate6Mbps")):
    from authbc.models import phy as _phy
    from authbc.models import unified_capacity as _uc
    _tf = _uc.airtime_s(_phy.DSSS_1M if _std == "80211b" else _phy.OFDM_20MHZ_6M, _size)
    for _n in (2, 3):
        for _u in (0.3, 0.5, 0.7, 0.85):
            CELLS[f"DG{_std[-1].upper()}{_size}N{_n}U{round(_u * 100)}"] = Cell(
                _size, _u / (_n * _tf), _std, _ph, sim_s=100.0)


def run_checked(args: list[str], env: dict[str, str]) -> None:
    """Run one ns-3 process; on failure say how, with its stderr. On 2026-11-18 a launch exited
    127 (the loader) once and could not be explained afterwards: the stderr was not kept."""
    proc = subprocess.run(args, env=env, capture_output=True)
    if proc.returncode != 0:
        tail = proc.stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(f"exit {proc.returncode}: {' '.join(args[:3])} …\nstderr: {tail}")


def run_one(cell: str, n: int, seed: int, trace_dir: Path | None,
            trace_opts: tuple[str, ...]) -> dict[str, str]:
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        out = trace_dir if trace_dir is not None else Path(td)
        prefix = out / f"{cell}_n{n}_s{seed}"
        args = [str(exe), f"--nNodes={n}", f"--simTime={CELLS[cell].sim_s}", f"--seed={seed}",
                f"--outPrefix={prefix}", *CELLS[cell].args()]
        if trace_dir is not None:
            args += list(trace_opts)
        if CELLS[cell].verify:
            args.append("--traceAllRx=1")
        run_checked(args, env)
        kv = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
        extra = verified(cell, n, int(kv["tx_frames"]), Path(f"{prefix}_allrx.csv"))
    c = CELLS[cell]
    return {**extra, "cell": cell, "frame_bytes": str(c.frame_bytes), "frames_per_s": repr(c.fps),
            "standard": c.standard, "mode": c.mode, "extra": " ".join(c.extra),
            "n_nodes": str(n), "seed": str(seed), "sim_time_s": repr(CELLS[cell].sim_s),
            "tx_frames": kv["tx_frames"], "rx_frames": kv["rx_frames"],
            "delivered_frac": kv["delivered_frac"], "delay_mean_ms": kv["delay_mean_ms"],
            "delay_p99_ms": kv["delay_p99_ms"]}


FIELDS = ["cell", "frame_bytes", "frames_per_s", "standard", "mode", "extra", "n_nodes", "seed",
          "sim_time_s", "tx_frames", "rx_frames", "delivered_frac", "delay_mean_ms",
          "delay_p99_ms"]
VERIFIED_FIELDS = [*FIELDS, "verified", "verified_of", "verified_frac", "unit_wait_mean_ms",
                   "unit_wait_p99_ms"]


def verified(cell: str, n: int, tx_frames: int, allrx: Path) -> dict[str, str]:
    """For a C3/C4 cell: the (receiver, frame or unit) pairs that verify, out of all sent, from
    the run's full reception trace (`authbc.sim.verified`). The trace is a temporary file, unless
    --trace keeps it."""
    rule = CELLS[cell].verify
    if not rule:
        return {}
    kind, ks = rule.split(":")
    k = int(ks)
    timed = read_allrx(str(allrx))
    got = untimed(timed)
    wait = {"unit_wait_mean_ms": "", "unit_wait_p99_ms": ""}
    if kind == "key":
        ok, of = verified_key_chain(got, k), tx_frames * (n - 1)
    elif kind == "unit":
        nodes = allrx.with_name(allrx.name.replace("_allrx.csv", "_nodes.csv"))
        if nodes.exists():          # frames sent one by one (--perNode): whole units per source
            sent = per_source_sent(nodes)
            ok, of = verified_units(got, k, sent), units_sent(sent, k) * (n - 1)
        else:                       # a burst: every unit is sent whole
            if tx_frames % k:
                raise ValueError(f"{cell}: {tx_frames} frames sent is not whole units of {k}")
            ok, of = verified_units(got, k), tx_frames // k * (n - 1)
        waits = sorted(unit_completion_ns(timed, k))
        if waits:
            p99 = waits[min(len(waits) - 1, int(0.99 * len(waits)))]
            wait = {"unit_wait_mean_ms": f"{st.mean(waits) / 1e6:.6f}",
                    "unit_wait_p99_ms": f"{p99 / 1e6:.6f}"}
    else:
        raise ValueError(f"{cell}: unknown verification rule {rule!r}")
    return {"verified": str(ok), "verified_of": str(of), "verified_frac": f"{ok / of:.6f}",
            **wait}


def per_source_sent(nodes: Path) -> dict[int, int]:
    """Frames each source sent, from the twin's `<out>_nodes.csv` (--perNode)."""
    with nodes.open(encoding="utf-8") as fh:
        return {int(r["node"]): int(r["tx_frames"]) for r in csv.DictReader(fh)}


def read_runs(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def _header(run: str, config: dict) -> str:
    return "".join(f"# {k}={v}\n" for k, v in {**provenance.env_block(), "run": run,
                                                 "ns3": "3.48 (authbc-links-audit)",
                                                 "config_hash": provenance.config_hash(config)
                                                 }.items())


def append_runs(path: Path, rows: list[dict[str, str]], stem: str) -> None:
    new = not path.exists()
    fields = VERIFIED_FIELDS if "verified_frac" in rows[0] else FIELDS
    if not new:                         # never append rows of another shape to a file
        with path.open(encoding="utf-8") as fh:
            header = next(ln for ln in fh if not ln.startswith("#")).rstrip("\n").split(",")
        if header != fields:
            raise SystemExit(f"{path.name}: its columns are not this run's; use another --stem")
    with path.open("a", encoding="utf-8", newline="") as fh:
        if new:
            fh.write(_header(f"{stem}_runs", {"cells": {k: str(v) for k, v in CELLS.items()},
                                              "sim_time": SIM_TIME}))
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def summarise(runs: list[dict[str, str]], seeds: int, levels: tuple[float, ...]) -> list[dict]:
    """Per (cell, N) dispersion over exactly `seeds` runs, then a CROSSING row per level."""
    by: dict[str, dict[int, list[float]]] = {}
    for r in runs:                      # C3/C4 cells cross on verified records, the rest on frames
        metric = "verified_frac" if r.get("verified_frac") else "delivered_frac"
        by.setdefault(r["cell"], {}).setdefault(int(r["n_nodes"]), []).append(float(r[metric]))
    out: list[dict] = []
    for cell, per_n in sorted(by.items()):
        full = {n: v for n, v in sorted(per_n.items()) if len(v) == seeds}
        for n, v in full.items():
            out.append({"cell": cell, "n_nodes": n, "seeds": len(v),
                        "delivered_mean": round(st.mean(v), 6),
                        "delivered_min": round(min(v), 6), "delivered_max": round(max(v), 6),
                        "delivered_stdev": round(st.stdev(v), 6) if len(v) > 1 else ""})
        means = {n: st.mean(v) for n, v in full.items()}
        for level in levels:
            x = interpolated_crossing(means, level)
            ci = interpolated_crossing_ci(full, threshold=level, seed=BOOTSTRAP_SEED)
            out.append({"cell": cell, "n_nodes": f"CROSSING@{level:g}", "seeds": seeds,
                        "delivered_mean": round(x, 3) if x is not None else "",
                        "delivered_min": round(ci[0], 3) if ci else "",
                        "delivered_max": round(ci[1], 3) if ci else "",
                        "delivered_stdev": f"bracketed {ci[2]:.3f}" if ci else ""})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cells", nargs="+", required=True, choices=list(CELLS))
    ap.add_argument("--n", type=int, nargs="+", help="node counts (default: the pilot grid)")
    ap.add_argument("--pilot", action="store_true", help="5 seeds on a coarse grid")
    ap.add_argument("--center", type=float, help="pilot grid centre (the registered root)")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--first-seed", type=int, default=1)
    ap.add_argument("--stem", required=True, help="results/raw/<stem>_runs.csv and <stem>.csv")
    ap.add_argument("--levels", type=float, nargs="+", default=[0.95])
    ap.add_argument("--trace", type=Path, help="keep traces in this directory")
    ap.add_argument("--trace-opts", nargs="*", default=["--traceMac=1"])
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    if args.pilot:
        if args.center is None or len(args.cells) != 1:
            raise SystemExit("--pilot needs one cell and --center")
        step = max(1, round(args.center * 0.05))
        args.n = [max(2, round(args.center) + k * step) for k in range(-3, 4)]
        args.seeds = 5
    if not args.n:
        raise SystemExit("give --n, or --pilot with --center")
    path = RAW / f"{args.stem}_runs.csv"
    done = {(r["cell"], int(r["n_nodes"]), int(r["seed"])) for r in read_runs(path)}
    todo = [(c, n, s) for c in args.cells for n in args.n
            for s in range(args.first_seed, args.first_seed + args.seeds) if (c, n, s) not in done]
    if args.trace:
        args.trace.mkdir(parents=True, exist_ok=True)
    print(f"{len(done)} runs on file, {len(todo)} to do, {args.workers} at a time", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, c, n, s, args.trace, tuple(args.trace_opts))
                   for c, n, s in todo]
        for k, f in enumerate(as_completed(futures), 1):
            append_runs(path, [f.result()], args.stem)
            if k % 10 == 0 or k == len(futures):
                print(f"  {k}/{len(futures)} done", flush=True)
    runs = read_runs(path)
    summary = summarise(runs, args.seeds, tuple(args.levels))
    buf = io.StringIO(_header(args.stem, {"seeds": args.seeds, "levels": args.levels}))
    w = csv.DictWriter(buf, fieldnames=list(summary[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(summary)
    (RAW / f"{args.stem}.csv").write_text(buf.getvalue())
    for r in summary:
        if str(r["n_nodes"]).startswith("CROSSING"):
            print(r)


if __name__ == "__main__":
    main()
