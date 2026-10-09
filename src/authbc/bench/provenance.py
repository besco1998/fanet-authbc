"""Run provenance — env block + config hash stamped on every CSV (docs/06 §1,§3; docs/07 §7).

Every result row carries the config hash; every CSV carries the env block so a number can be
traced to the machine, library versions, and config that produced it (Law 7).
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path


def as_written(value: float) -> float:
    """A number as a result file holds it: six significant figures (the `:g` the drivers write).

    A reader that compares a stored value with the exact one it was computed from misses every
    value six figures cannot hold. That stayed invisible while every sending period was 20, 50,
    80 or 200 ms, and dropped a whole cell the first time one was 1000/50.5 ms: stored 19.802,
    looked up as 19.801980198… (finding F56). Compare `float(stored) == as_written(exact)`.
    """
    return float(f"{value:g}")


GOVERNOR_FILE = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
NO_GOVERNOR = "WSL, governor uncontrolled"


def model_in_cpuinfo(text: str) -> str | None:
    """The processor named in /proc/cpuinfo: `model name` on x86, the board's `Model` on ARM."""
    for key in ("model name", "Model"):
        for line in text.splitlines():
            if line.startswith(key) and ":" in line:
                return line.split(":", 1)[1].strip()
    return None


def cpu_model() -> str:
    try:
        named = model_in_cpuinfo(Path("/proc/cpuinfo").read_text())
    except OSError:
        named = None
    return named or platform.processor() or "unknown"


def governor() -> str:
    """This machine's frequency governor, or the note that it exposes none.

    The development machine (WSL2) exposes none and its frequency is the host's business; a
    board exposes one. Until 2026-10-09 this was a constant, so a file made on a Raspberry Pi
    said `governor=WSL, governor uncontrolled` beside the true value that `hw/run_micro.sh`
    prepends as `device_governor`, and `cpu=unknown` beside `device_model`. Where nothing is
    exposed the old note is returned unchanged, so every header written here stays as it was.
    """
    try:
        return GOVERNOR_FILE.read_text().strip() or NO_GOVERNOR
    except OSError:
        return NO_GOVERNOR


def env_block() -> dict[str, str]:
    """Environment provenance (docs/06 §1: the processor, and its governor where one is exposed)."""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu": cpu_model(),
        "governor": governor(),
        "cryptography": version("cryptography"),
        "blspy": version("blspy"),
        "cbor2": version("cbor2"),
        "msgpack": version("msgpack"),
    }


def config_hash(config: dict) -> str:
    """Stable 16-hex-char hash of a config dict (order-independent)."""
    blob = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
