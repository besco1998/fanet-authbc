#!/usr/bin/env python3
"""P7b energy op-driver — runs on the DUT Pi, drives the sync line IN-PROCESS (Path A, hw/RIG.md).

For each measured operation this alternates a 60 s IDLE window and a 60 s LOAD window, raising a
GPIO sync line for exactly the duration of each window so the Arduino meter-host tags every sample.
No separate `gpioset` call and no wall-clock alignment: the line is opened, driven and released by
this process, and every window is also stamped with UTC + monotonic times so the host can
cross-check (or recover the windows entirely) if the GPIO path is unavailable.

Timing follows the P1 rules (docs/06 §3): gc disabled inside the loop, >=1000 warmup iterations, an
accumulated checksum to defeat dead-code elimination, and time.perf_counter_ns throughout. Unlike P1
each op runs for a wall-clock WINDOW (so it aligns with the meter) and reports n_ops.

Outputs a manifest JSON (default results/hw/energy/manifest-<host>-<UTC>.json) that
`hw/ina219_capture.py --reduce` merges with the Arduino sample stream to produce energy/op.

    ./hw/energy_loop.py --quick                 # 5 s windows x2 reps: rig validation
    ./hw/energy_loop.py                         # full campaign: 60 s windows x5 reps
    ./hw/energy_loop.py --ops ed25519:sign,delta:encode

RELIABILITY: the sync line is released by a finally-block, an atexit hook AND SIGINT/SIGTERM
handlers, so an aborted run cannot leave it stuck high (which would silently mark every later
sample as in-window). libgpiod v2, v1 and sysfs are tried in that order; if all fail the run still
proceeds and records gpio_available=false so the host falls back to the timestamps.
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import gc
import json
import platform
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

DEFAULT_CHIP = "gpiochip0"   # RPi4 (BCM2711) main bank
DEFAULT_LINE = 17            # BCM GPIO17 = header pin 11
WARMUP = 1000
MSG_BYTES = 200              # same fixed message as P1 (docs/04 §1)
AGG_BATCHES = (2, 4, 8, 16, 32)


# ----------------------------------------------------------------------------- sync line
class SyncLine:
    """Drives the Pi->Arduino window line, with guaranteed release.

    Tries libgpiod v2, then v1, then sysfs. `available` is False if none worked — the caller keeps
    running and the host falls back to timestamps rather than aborting a long campaign.
    """

    def __init__(self, chip: str = DEFAULT_CHIP, line: int = DEFAULT_LINE) -> None:
        self.chip_name, self.line_num, self.backend = chip, line, "none"
        self._req = self._line = self._sysfs = None
        self._high = False
        self._open()
        atexit.register(self.close)
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(ValueError):       # not in main thread -> skip
                signal.signal(sig, self._on_signal)

    # -- backends ---------------------------------------------------------------
    def _open(self) -> None:
        for backend in (self._open_v2, self._open_v1, self._open_sysfs):
            try:
                backend()
                return
            except Exception as exc:                     # noqa: BLE001 - try the next backend
                print(f"  sync: {backend.__name__} unavailable ({type(exc).__name__}: {exc})")
        print("  sync: NO GPIO BACKEND — continuing with timestamp-only windows")

    def _open_v2(self) -> None:
        import gpiod  # libgpiod >= 2.x
        from gpiod.line import Direction, Value

        self._req = gpiod.request_lines(
            f"/dev/{self.chip_name}", consumer="authbc-energy",
            config={self.line_num: gpiod.LineSettings(direction=Direction.OUTPUT,
                                                      output_value=Value.INACTIVE)})
        self.backend = "libgpiod2"

    def _open_v1(self) -> None:
        import gpiod  # libgpiod 1.x

        chip = gpiod.Chip(self.chip_name)
        self._line = chip.get_line(self.line_num)
        self._line.request(consumer="authbc-energy", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
        self.backend = "libgpiod1"

    def _open_sysfs(self) -> None:
        base = Path("/sys/class/gpio")
        # Recent RPi kernels offset the sysfs numbering by the chip base (often 512).
        for offset in (0, 512):
            num = self.line_num + offset
            d = base / f"gpio{num}"
            if not d.exists():
                with contextlib.suppress(OSError):
                    (base / "export").write_text(str(num))
            if d.exists():
                (d / "direction").write_text("out")
                (d / "value").write_text("0")
                self._sysfs = d
                self.backend = f"sysfs(+{offset})"
                return
        raise RuntimeError("sysfs gpio export failed")

    @property
    def available(self) -> bool:
        return self.backend != "none"

    # -- drive ------------------------------------------------------------------
    def set(self, high: bool) -> None:
        try:
            if self.backend == "libgpiod2":
                from gpiod.line import Value
                self._req.set_value(self.line_num, Value.ACTIVE if high else Value.INACTIVE)
            elif self.backend == "libgpiod1":
                self._line.set_value(1 if high else 0)
            elif self._sysfs is not None:
                (self._sysfs / "value").write_text("1" if high else "0")
            self._high = high
        except Exception as exc:                          # noqa: BLE001 - never abort a campaign
            print(f"  sync: set({high}) failed: {exc}")

    @contextlib.contextmanager
    def window(self) -> Iterator[None]:
        """Hold the line high for the body; ALWAYS lower it, even on exception."""
        self.set(True)
        try:
            yield
        finally:
            self.set(False)

    def _on_signal(self, signum, _frame) -> None:
        self.close()
        sys.exit(128 + signum)

    def close(self) -> None:
        if self._high:
            self.set(False)
        with contextlib.suppress(Exception):
            if self._req is not None:
                self._req.release()
            elif self._line is not None:
                self._line.release()
        self._req = self._line = None


# ----------------------------------------------------------------------------- device state
def _sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:                                     # noqa: BLE001 - metadata is best-effort
        return "NA"


def device_state() -> dict[str, str]:
    gov = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    return {
        "temp": _sh(["vcgencmd", "measure_temp"]) or "NA",
        "throttled": _sh(["vcgencmd", "get_throttled"]) or "NA",
        "governor": gov.read_text().strip() if gov.exists() else "NA",
    }


# ----------------------------------------------------------------------------- op set
def build_ops(selected: str | None) -> dict[str, Callable[[], object]]:
    """name -> zero-arg callable returning a value that feeds the anti-DCE checksum."""
    import hashlib
    import random

    from authbc.bench import telemgen
    from authbc.crypto.registry import all_schemes, get_scheme
    from authbc.encodings.registry import new_encoder

    rng = random.Random(1)
    msg = bytes(rng.randrange(256) for _ in range(MSG_BYTES))
    ops: dict[str, Callable[[], object]] = {}

    for scheme in all_schemes():
        sk, pk = scheme.keygen(seed=hashlib.sha256(f"1:{scheme.name}".encode()).digest())
        sig = scheme.sign(sk, msg)
        ops[f"{scheme.name}:sign"] = lambda sc=scheme, k=sk: sc.sign(k, msg)
        ops[f"{scheme.name}:verify"] = lambda sc=scheme, p=pk, g=sig: sc.verify(p, msg, g)

    bls = get_scheme("bls")
    for b in AGG_BATCHES:
        keys = [bls.keygen(seed=hashlib.sha256(f"1:bls{b}_{i}".encode()).digest())
                for i in range(b)]
        msgs = [bytes(rng.randrange(256) for _ in range(MSG_BYTES)) for _ in range(b)]
        sigs = [bls.sign(sk, m) for (sk, _), m in zip(keys, msgs, strict=True)]
        pks = [pk for _, pk in keys]
        agg = bls.aggregate(sigs)
        ops[f"bls:aggregate:{b}"] = lambda s=sigs: bls.aggregate(s)
        ops[f"bls:agg_verify:{b}"] = lambda p=pks, m=msgs, a=agg: bls.aggregate_verify(p, m, a)

    # Encoders: ONE stateful instance reused across the stream (a fresh encoder per record would
    # make delta emit all keyframes — the P1b pitfall).
    recs = telemgen.samples(seed=1, n=10_000)
    for name in ("json", "cbor", "msgpack", "delta"):
        enc = new_encoder(name)
        counter = {"i": 0}

        def _encode(e=enc, c=counter, r=recs):
            rec = r[c["i"] % len(r)]
            c["i"] += 1
            return e.encode(rec)

        ops[f"{name}:encode"] = _encode

    if selected:
        want = {s.strip() for s in selected.split(",") if s.strip()}
        missing = want - ops.keys()
        if missing:
            sys.exit(f"unknown ops: {sorted(missing)}\navailable: {sorted(ops)}")
        ops = {k: v for k, v in ops.items() if k in want}
    return ops


# ----------------------------------------------------------------------------- windows
def run_window(fn: Callable[[], object] | None, seconds: float) -> tuple[int, int]:
    """Run `fn` in a tight loop for `seconds` (or idle if None). Returns (n_ops, checksum)."""
    if fn is None:
        time.sleep(seconds)
        return 0, 0
    for _ in range(WARMUP):
        fn()
    checksum = 0
    n = 0
    gc.disable()
    try:
        end = time.perf_counter_ns() + int(seconds * 1e9)
        while time.perf_counter_ns() < end:
            out = fn()
            checksum ^= hash(out) if not isinstance(out, int) else out
            n += 1
    finally:
        gc.enable()
    return n, checksum & 0xFFFFFFFFFFFFFFFF


def timed_window(sync: SyncLine, label: str, fn, seconds: float, rep: int) -> dict:
    before = device_state()
    t0_utc, t0 = datetime.now(UTC).isoformat(), time.perf_counter()
    with sync.window():
        n_ops, checksum = run_window(fn, seconds)
    t1, t1_utc = time.perf_counter(), datetime.now(UTC).isoformat()
    after = device_state()
    thr_ok = before["throttled"].endswith("0x0") and after["throttled"].endswith("0x0")
    row = {"op": label, "rep": rep, "kind": "idle" if fn is None else "load",
           "t_start_utc": t0_utc, "t_end_utc": t1_utc, "duration_s": round(t1 - t0, 6),
           "n_ops": n_ops, "checksum": checksum,
           "temp_before": before["temp"], "temp_after": after["temp"],
           "throttled_before": before["throttled"], "throttled_after": after["throttled"],
           "throttle_clean": thr_ok}
    flag = "" if thr_ok else "   !! THROTTLED — run invalid"
    rate = f"{n_ops / (t1 - t0):,.0f}/s" if n_ops else "idle"
    print(f"  [{label} rep{rep} {row['kind']:4}] {t1 - t0:5.1f}s  {rate:>12}{flag}")
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description="P7b energy op-driver with in-process GPIO sync")
    ap.add_argument("--duration", type=float, default=60.0, help="window seconds (default 60)")
    ap.add_argument("--reps", type=int, default=5, help="repetitions per op (default 5)")
    ap.add_argument("--ops", help="comma-separated subset, e.g. ed25519:sign,delta:encode")
    ap.add_argument("--chip", default=DEFAULT_CHIP)
    ap.add_argument("--line", type=int, default=DEFAULT_LINE)
    ap.add_argument("--quick", action="store_true", help="5 s windows x2 reps (rig validation)")
    ap.add_argument("--out", type=Path, help="manifest path (default results/hw/energy/…)")
    args = ap.parse_args()
    if args.quick:
        args.duration, args.reps = 5.0, 2

    ops = build_ops(args.ops)
    sync = SyncLine(args.chip, args.line)
    print(f"sync backend: {sync.backend} (chip={args.chip} line={args.line})")
    print(f"{len(ops)} ops x {args.reps} reps x 2 windows x {args.duration:.0f}s "
          f"≈ {len(ops) * args.reps * 2 * args.duration / 60:.0f} min\n")

    windows: list[dict] = []
    try:
        for name, fn in ops.items():
            for rep in range(1, args.reps + 1):
                windows.append(timed_window(sync, name, None, args.duration, rep))   # idle
                windows.append(timed_window(sync, name, fn, args.duration, rep))     # load
    finally:
        sync.close()

    host, stamp = socket.gethostname().split(".")[0], datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or REPO / "results" / "hw" / "energy" / f"manifest-{host}-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": "authbc.energy.manifest/1",
        "host": host, "run_utc": stamp, "platform": platform.platform(),
        "python": sys.version.split()[0],
        "gpio_available": sync.available, "gpio_backend": sync.backend,
        "gpio_chip": args.chip, "gpio_line": args.line,
        "duration_s": args.duration, "reps": args.reps, "warmup": WARMUP,
        "msg_bytes": MSG_BYTES, "windows": windows,
    }, indent=2))
    bad = [w for w in windows if not w["throttle_clean"]]
    print(f"\nwrote {out}  ({len(windows)} windows)")
    if bad:
        print(f"!! {len(bad)} window(s) THROTTLED — exclude them; improve cooling and re-run")
    print("next: hw/ina219_capture.py --reduce <this manifest> <samples.csv>")


if __name__ == "__main__":
    main()
