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
    banner: list[str] = []
    print(f"capturing {port} -> {out}   (Ctrl-C to stop)")
    with out.open("w", newline="") as fh:
        for key, val in (("schema", "authbc.energy.samples/1"), ("capture_host", platform.node()),
                         ("platform", platform.platform()), ("port", port), ("baud", BAUD),
                         ("capture_start_utc", stamp)):
            fh.write(f"# {key}={val}\n")
        fh.flush()
        try:
            for line in _serial_lines(port):
                if not line:
                    continue
                if line.startswith("#"):                      # sketch banner -> provenance
                    banner.append(line)
                    fh.write(f"{line}\n")
                    print(f"  {line}")
                    continue
                if line.startswith("ms,"):                    # sketch header row
                    fh.write(f"{line}\n")
                    continue
                fh.write(f"{line}\n")
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
    print(f"\nwrote {out}  ({n} samples)")
    if n == 0:
        print("!! no samples — check the port, the sketch, and (on WSL2) usbipd attach")


# ----------------------------------------------------------------------------- reduce
def _read_samples(path: Path) -> list[dict[str, str]]:
    body = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def _segments(rows: list[dict[str, str]], channel: int) -> list[list[float]]:
    """Contiguous runs of window==1, each as the list of that channel's power samples."""
    col = f"P{channel}_W"
    out: list[list[float]] = []
    cur: list[float] = []
    for r in rows:
        if r.get("window") == "1":
            cur.append(float(r[col]))
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def reduce(manifest_path: Path, samples_path: Path, channel: int, out: Path | None) -> None:
    from authbc.bench.stats import bootstrap_ci

    man = json.loads(manifest_path.read_text())
    windows = man["windows"]
    segs = _segments(_read_samples(samples_path), channel)
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
    ap.add_argument("--channel", type=int, default=1, choices=(1, 2),
                    help="INA219 channel to reduce (1=Pi-A/DUT, 2=Pi-B)")
    args = ap.parse_args()

    if args.reduce:
        reduce(Path(args.reduce[0]), Path(args.reduce[1]), args.channel, args.out)
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    capture(args.port, args.out or ENERGY_DIR / f"samples-{stamp}.csv", args.seconds)


if __name__ == "__main__":
    main()
