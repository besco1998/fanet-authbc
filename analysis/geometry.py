#!/usr/bin/env python3
"""The geometry record of a frame-level campaign session (docs/DECISIONS.md, 2026-11-23): the
distances, heights and antenna directions of every board and of the sniffer, the room and nearby
metal, and the photographs, filled in at the boards from
`experiments/channel24/geometry_template.json`. W1s showed that the same tape distances need not
give the same radio geometry (its Δ at equal power was −5 dB against W1q's +7), so no session of
the campaign is scored without this record complete.

    python analysis/geometry.py SESSION/geometry.json   -> the missing fields, exit 1 if any
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def missing(record: dict[str, Any], prefix: str = "") -> list[str]:
    """Every field left empty (None or "") in the record, as dotted paths."""
    out: list[str] = []
    for k, v in record.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            out += missing(v, path + ".")
        elif v is None or v == "" or (isinstance(v, str) and "|" in v):
            out.append(path)
    return out


def main() -> None:
    gaps = missing(json.loads(Path(sys.argv[1]).read_text()))
    print("\n".join(gaps) if gaps else "complete")
    sys.exit(1 if gaps else 0)


if __name__ == "__main__":
    main()
