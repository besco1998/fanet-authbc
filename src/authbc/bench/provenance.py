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


def as_written(value: float) -> float:
    """A number as a result file holds it: six significant figures (the `:g` the drivers write).

    A reader that compares a stored value with the exact one it was computed from misses every
    value six figures cannot hold. That stayed invisible while every sending period was 20, 50,
    80 or 200 ms, and dropped a whole cell the first time one was 1000/50.5 ms: stored 19.802,
    looked up as 19.801980198… (finding F56). Compare `float(stored) == as_written(exact)`.
    """
    return float(f"{value:g}")


def cpu_model() -> str:
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def env_block() -> dict[str, str]:
    """Environment provenance (docs/06 §1: record cpu + note the uncontrolled WSL governor)."""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu": cpu_model(),
        "governor": "WSL, governor uncontrolled",
        "cryptography": version("cryptography"),
        "blspy": version("blspy"),
        "cbor2": version("cbor2"),
        "msgpack": version("msgpack"),
    }


def config_hash(config: dict) -> str:
    """Stable 16-hex-char hash of a config dict (order-independent)."""
    blob = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
