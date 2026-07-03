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
