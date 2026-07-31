#!/usr/bin/env python3
"""Host-side Arduino capture + reduction for the P7b energy rig (Path A, hw/RIG.md).

Runs on the machine the Arduino is plugged into (this WSL2 box — see hw/RIG.md §9 for usbipd).
Two modes:

  capture   read the Arduino CSV stream and write a provenance-stamped samples file
            ./hw/ina219_capture.py --port /dev/ttyACM0 --out results/hw/energy/samples-<stamp>.csv

  reduce    merge that samples file with the Pi's manifest (hw/energy_loop.py) into energy/op
            ./hw/ina219_capture.py --reduce manifest-*.json samples-*.csv

Reduction pairs each (idle, load) window: energy/op = (P_loop - P_idle) * t_loop / n_ops, then
reports median + bootstrap CI over the repetitions (docs/04 §4). Windows the Pi flagged as
throttled are EXCLUDED and reported, never silently averaged in (Law 3/6).

No third-party dependency is required: pyserial is used when present, otherwise the port is
configured with `stty` and read as a plain file.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import statistics
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

BAUD = 115200
ENERGY_DIR = REPO / "results" / "hw" / "energy"
SAMPLE_COLS = ["ms", "window", "wtrans", "V1", "I1_mA", "P1_W", "V2", "I2_mA", "P2_W"]


# ----------------------------------------------------------------------------- capture
def _serial_lines(port: str) -> Iterator[str]:
    """Yield decoded lines from the Arduino: pyserial if installed, else stty + raw file read."""
    try:
        import serial  # type: ignore[import-not-found]

        with serial.Serial(port, BAUD, timeout=2) as ser:
            while True:
                raw = ser.readline()
                if raw:
                    yield raw.decode("ascii", "replace").strip()
    except ImportError:
        print(f"# pyserial not installed — falling back to stty+read on {port}")
        subprocess.run(["stty", "-F", port, str(BAUD), "raw", "-echo"], check=True)
        with open(port, "rb", buffering=0) as fh:
            buf = b""
            while True:
                chunk = fh.read(1)
                if not chunk:
                    continue
                if chunk == b"\n":
                    yield buf.decode("ascii", "replace").strip()
                    buf = b""
                else:
                    buf += chunk


def capture(port: str, out: Path, limit: float | None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    n = 0
    dropped = 0
    print(f"capturing {port} -> {out}   (Ctrl-C to stop)")
    with out.open("w", newline="") as fh:
        for key, val in (("schema", "authbc.energy.samples/1"), ("capture_host", platform.node()),
                         ("platform", platform.platform()), ("port", port), ("baud", BAUD),
                         ("capture_start_utc", stamp)):
            fh.write(f"# {key}={val}\n")
        # Write the canonical header OURSELVES. Attaching to an already-running sketch means the
        # first line is usually a fragment and the sketch's own header may never arrive, so the file
        # must be self-describing regardless of when capture started.
        # H1: the Arduino ms counter alone cannot be mapped to UTC — it restarts on reset
        # and a file may hold several sessions, so a single `capture_start_utc` header is an
        # ambiguous anchor. Stamping every sample with host UTC makes the timestamp-based
        # window recovery exact, which is what lets Pi-B (no sync wire) be reduced at all.
        fh.write(",".join([*SAMPLE_COLS, "host_utc"]) + "\n")
        fh.flush()
        try:
            for line in _serial_lines(port):
                if not line:
                    continue
                if line.startswith("#"):                      # sketch banner -> provenance
                    fh.write(f"{line}\n")
                    print(f"  {line}")
                    continue
                if line.startswith("ms,"):                    # sketch header: ours already written
                    continue
                parts = line.split(",")
                if len(parts) != len(SAMPLE_COLS):            # fragment or noise
                    dropped += 1
                    continue
                try:
                    [float(x) for x in parts]
                except ValueError:
                    dropped += 1
                    continue
                fh.write(f"{line},{datetime.now(UTC).isoformat()}\n")
                n += 1
                if n % 250 == 0:
                    fh.flush()
                    elapsed = (datetime.now(UTC) - started).total_seconds()
                    print(f"  {n} samples  ({elapsed:.0f}s)", end="\r", flush=True)
                if limit and (datetime.now(UTC) - started).total_seconds() >= limit:
                    break
        except KeyboardInterrupt:
            print("\n  stopped by user")
        finally:
            fh.flush()
    print(f"\nwrote {out}  ({n} samples, {dropped} malformed line(s) dropped)")
    if n == 0:
        print("!! no samples — check the port, the sketch, and (on WSL2) usbipd attach")
    if dropped > 5:
        print(f"!! {dropped} dropped lines is more than the 1-2 expected from a mid-stream attach "
              "— check the baud rate and cabling")


# ----------------------------------------------------------------------------- reduce
def _read_samples(path: Path) -> list[dict[str, str]]:
    """Parse the samples file, keeping only the FINAL monotonic run of `ms`.

    Opening the serial port toggles DTR and RESETS the Arduino, so a capture typically begins with a
    few stale samples buffered from before the reset, after which `ms` restarts at ~0. Any backward
    jump in `ms` therefore marks a stream restart; everything before the last one is stale and must
    be discarded or it would corrupt the window segmentation.
    """
    body = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    rows = list(csv.DictReader(io.StringIO("\n".join(body))))
    # A RESTART is a jump back to near zero (the Arduino's millis() begins again). Small backward
    # blips of a few tens of ms are out-of-order/duplicated serial lines, NOT restarts — treating
    # them as such once discarded an entire 150 s capture, so require the clock to land near zero.
    RESTART_MS = 5000
    start = 0
    for i in range(1, len(rows)):
        if int(rows[i]["ms"]) < int(rows[i - 1]["ms"]) and int(rows[i]["ms"]) < RESTART_MS:
            start = i                                   # stream restarted here
    if start:
        print(f"  (discarded {start} stale pre-reset sample(s) — Arduino resets on port open)")
    kept, last = [], -1
    for r in rows[start:]:                              # drop out-of-order serial stragglers
        v = int(r["ms"])
        if v >= last:
            kept.append(r)
            last = v
    if len(kept) != len(rows) - start:
        print(f"  (dropped {len(rows) - start - len(kept)} out-of-order sample(s))")
    return kept


# Samples dropped from the START of every window. The CPU takes a moment to reach steady state after
# the load starts (and to settle after it stops), so the leading samples straddle the transition and
# would bias both the idle and the load mean. 5 samples @50 Hz = 100 ms, <0.2 % of a 60 s window.
EDGE_TRIM = 5


def _segments(rows: list[dict[str, str]], channel: int) -> list[list[float]]:
    """Contiguous runs of window==1, each as that channel's power samples (leading edge trimmed)."""
    col = f"P{channel}_W"
    out: list[list[float]] = []
    cur: list[float] = []
    for r in rows:
        if r.get("window") == "1":
            cur.append(float(r[col]))
        elif cur:
            out.append(cur[EDGE_TRIM:] or cur)
            cur = []
    if cur:
        out.append(cur[EDGE_TRIM:] or cur)
    return out


def _segments_by_power_step(rows: list[dict[str, str]], channel: int,
                            windows: list[dict]) -> list[list[float]]:
    """Recover windows from the power signal itself — no clocks, no sync wire (hardware audit H1).

    Why not timestamps: the rig has one sync wire (Pi-A), so Pi-B can only be reduced from times.
    But the manifest's window bounds come from the *Pi's* clock while samples are stamped by the
    *capture host's* clock, and serial buffering adds lag on top. Measured, that offset biased
    energy low by **3-6 % on 60 s windows and 13-20 % on 5 s windows** — the tell is that the error
    scales inversely with window length, i.e. a fixed time shift, not a scale error. No amount of
    NTP fixes the serial lag, so absolute time is the wrong instrument.

    What is used instead: the load windows are plainly visible in the power trace as steps of
    several hundred mW. We threshold at the midpoint between the run's low and high power modes,
    take contiguous high runs as load and the low runs between them as idle, and match them to the
    manifest **by sequence**, which is the one thing both sides agree on exactly. The guard gap
    (1.0 s, ~50 samples) makes the runs unambiguous.
    """
    # Coarse crop by host clock, precise edges from the signal. Cross-host clock error is
    # sub-second (measured -0.11 s to -0.35 s) plus serial lag — fatal for a 5 s window boundary,
    # irrelevant for cropping a multi-minute campaign with 10 s of slack each side. This keeps
    # activity before and after the campaign (ssh, interpreter start-up) out of the step search.
    from datetime import datetime, timedelta
    if rows and rows[0].get("host_utc"):
        t_lo = datetime.fromisoformat(windows[0]["t_start_utc"]) - timedelta(seconds=10)
        t_hi = datetime.fromisoformat(windows[-1]["t_end_utc"]) + timedelta(seconds=10)
        cropped = [r for r in rows
                   if t_lo <= datetime.fromisoformat(r["host_utc"]) <= t_hi]
        if len(cropped) >= 10 * len(windows):
            rows = cropped

    col = f"P{channel}_W"
    p = [float(r[col]) for r in rows]
    lo, hi = min(p), max(p)
    if hi - lo < 0.10:
        raise SystemExit(
            f"!! channel {channel} power range is only {hi - lo:.3f} W — no load step is visible, "
            "so windows cannot be recovered from the signal. Is this the right channel, and was "
            "the DUT actually running the campaign?"
        )
    thr = (_mode_low(p) + _mode_high(p)) / 2.0

    runs: list[tuple[bool, list[float]]] = []
    cur: list[float] = [p[0]]
    state = p[0] >= thr
    for v in p[1:]:
        s = v >= thr
        if s == state:
            cur.append(v)
        else:
            runs.append((state, cur))
            cur, state = [v], s
    runs.append((state, cur))

    # Drop runs shorter than half the guard gap: those are edge ringing, not windows.
    min_len = 25
    runs = [(s, r) for s, r in runs if len(r) >= min_len]
    loads = [r for s, r in runs if s]
    idles = [r for s, r in runs if not s]
    n_load = sum(1 for w in windows if w["kind"] == "load")
    if len(loads) != n_load:
        raise SystemExit(
            f"!! found {len(loads)} load steps in the channel-{channel} power trace but the "
            f"manifest declares {n_load}. Refusing to guess an alignment (Law 3).\n"
            "\n"
            "   This is expected and is the documented limit of clock-free recovery (audit H1):\n"
            "   energy_loop.py runs >=1000 warm-up iterations before each measured window, and\n"
            "   warm-up draws power, so it appears as its own step. The signal cannot tell a\n"
            "   warm-up step from a measured one; only the GPIO line can.\n"
            "\n"
            "   Reducing a Pi WITHOUT a sync wire is therefore not supported. Fit the second\n"
            "   window wire (Pi-B BCM17 / pin 11 -> the Arduino's second window input) or move\n"
            "   the existing one to the Pi being measured. See hw/RIG.md."
        )

    out: list[list[float]] = []
    li = ii = 0
    for w in windows:
        if w["kind"] == "load":
            out.append(loads[li][EDGE_TRIM:] or loads[li])
            li += 1
        else:
            seg = idles[ii] if ii < len(idles) else idles[-1]
            out.append(seg[EDGE_TRIM:] or seg)
            ii += 1
    return out


def _mode_low(p: list[float]) -> float:
    s = sorted(p)
    return s[len(s) // 10]


def _mode_high(p: list[float]) -> float:
    s = sorted(p)
    return s[-len(s) // 10]


def reduce(manifest_path: Path, samples_path: Path, channel: int, out: Path | None,
           by_timestamp: bool = False) -> None:
    from authbc.bench.stats import bootstrap_ci

    man = json.loads(manifest_path.read_text())
    windows = man["windows"]
    rows = _read_samples(samples_path)
    if by_timestamp:
        segs = _segments_by_power_step(rows, channel, windows)
        print(f"manifest windows: {len(windows)}   power-step segments: {len(segs)}")
    else:
        segs = _segments(rows, channel)
        print(f"manifest windows: {len(windows)}   captured segments: {len(segs)}")
    if len(segs) != len(windows):
        sys.exit(
            f"!! window/segment mismatch ({len(windows)} vs {len(segs)}).\n"
            "   The capture must be running BEFORE energy_loop.py starts and until it finishes.\n"
            "   A floating sync pin also causes this — fit the 10k pulldown on D2 (hw/RIG.md).\n"
            "   Refusing to guess an alignment (Law 3: never bypass a failure)."
        )

    per_op: dict[str, list[float]] = {}
    rows: list[dict] = []
    skipped = 0
    for i in range(0, len(windows) - 1, 2):
        idle_w, load_w = windows[i], windows[i + 1]
        if idle_w["kind"] != "idle" or load_w["kind"] != "load":
            sys.exit(f"!! manifest not in idle/load pairs at index {i}")
        if not (idle_w["throttle_clean"] and load_w["throttle_clean"]):
            skipped += 1
            continue
        p_idle = statistics.mean(segs[i])
        p_loop = statistics.mean(segs[i + 1])
        n_ops = load_w["n_ops"]
        if n_ops <= 0:
            continue
        e_op = (p_loop - p_idle) * load_w["duration_s"] / n_ops
        per_op.setdefault(load_w["op"], []).append(e_op)
        rows.append({"op": load_w["op"], "rep": load_w["rep"],
                     "p_idle_w": round(p_idle, 5), "p_loop_w": round(p_loop, 5),
                     "delta_p_w": round(p_loop - p_idle, 5),
                     "t_loop_s": load_w["duration_s"], "n_ops": n_ops,
                     "energy_per_op_j": e_op, "energy_per_op_uj": round(e_op * 1e6, 6)})

    summary: list[dict] = []
    for op, vals in per_op.items():
        lo, hi = bootstrap_ci(vals, seed=12345) if len(vals) > 1 else (vals[0], vals[0])
        summary.append({"op": op, "reps": len(vals),
                        "energy_uj_median": round(statistics.median(vals) * 1e6, 6),
                        "energy_uj_ci_lo": round(lo * 1e6, 6),
                        "energy_uj_ci_hi": round(hi * 1e6, 6),
                        "delta_p_w_median": round(
                            statistics.median([r["delta_p_w"] for r in rows if r["op"] == op]), 5)})

    out = out or ENERGY_DIR / f"energy-{man['host']}-{man['run_utc']}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        for key in ("host", "run_utc", "platform", "python", "gpio_backend", "duration_s", "reps"):
            fh.write(f"# {key}={man.get(key)}\n")
        fh.write(f"# manifest={manifest_path.name}\n# samples={samples_path.name}\n")
        fh.write(f"# channel=P{channel}\n# reduced_utc={datetime.now(UTC).isoformat()}\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["op"])
        w.writeheader()
        w.writerows(rows)
    sfile = out.with_name(out.stem + "-summary.csv")
    with sfile.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]) if summary else ["op"])
        w.writeheader()
        w.writerows(summary)

    print(f"wrote {out}\nwrote {sfile}")
    if skipped:
        print(f"!! excluded {skipped} throttled rep(s) — improve cooling and re-run those ops")
    print("\nop                          energy/op        ΔP")
    for s in sorted(summary, key=lambda r: r["op"]):
        print(f"  {s['op']:<26} {s['energy_uj_median']:>10.3f} uJ  "
              f"{s['delta_p_w_median']:>6.3f} W")
    print("\nNext: put dP (p_cpu_w) + measured timings into experiments/e5/config.yaml, then "
          "`make exp-e4 exp-e5 figures` and re-freeze (verify-frozen will flag the drift).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Arduino INA219 capture / reduction (P7b Path A)")
    ap.add_argument("--port", default="/dev/ttyACM0", help="serial port (default /dev/ttyACM0)")
    ap.add_argument("--out", type=Path, help="output path")
    ap.add_argument("--seconds", type=float, help="stop capture after N seconds")
    ap.add_argument("--reduce", nargs=2, metavar=("MANIFEST", "SAMPLES"),
                    help="reduce a manifest + samples pair into energy/op")
    ap.add_argument("--by-timestamp", action="store_true",
                    help="recover windows from the power signal itself instead of the GPIO "
                         "`window` column (required for Pi-B: only Pi-A has a sync wire)")
    ap.add_argument("--channel", type=int, default=1, choices=(1, 2),
                    help="INA219 channel to reduce (1=Pi-A/DUT, 2=Pi-B)")
    args = ap.parse_args()

    if args.reduce:
        reduce(Path(args.reduce[0]), Path(args.reduce[1]), args.channel, args.out,
               args.by_timestamp)
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    capture(args.port, args.out or ENERGY_DIR / f"samples-{stamp}.csv", args.seconds)


if __name__ == "__main__":
    main()
