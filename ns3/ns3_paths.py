"""Single source of truth for which NS-3 tree the drivers use (decision D4).

Until 2026-07-29 the path was hardcoded in five separate files, which made it impossible to run the
same scenario against two NS-3 versions — exactly what a version migration has to do in order to
show that results did not move. It is now one constant with an environment override:

    AUTHBC_NS3=ns3/ns-allinone-3.41/ns-3.41 python ns3/run_matrix.py    # the old tree
    python ns3/run_matrix.py                                            # the pinned tree

`NS3_VERSION` is recorded in every artifact's provenance header, so a frozen CSV always says which
simulator produced it.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The pinned tree (D4). Change here, not in the drivers.
DEFAULT_NS3 = REPO / "ns3" / "ns-3.48"

# NS-3 trees this repo knows about, newest first — used only for diagnostics.
KNOWN_TREES = (
    REPO / "ns3" / "ns-3.48",
    REPO / "ns3" / "ns-allinone-3.41" / "ns-3.41",
)


def ns3_root() -> Path:
    """The NS-3 tree to run, honouring AUTHBC_NS3 (absolute, or relative to the repo)."""
    override = os.environ.get("AUTHBC_NS3")
    if override:
        p = Path(override)
        root = p if p.is_absolute() else REPO / p
    else:
        root = DEFAULT_NS3
    if not (root / "ns3").is_file():
        present = [str(t.relative_to(REPO)) for t in KNOWN_TREES if (t / "ns3").is_file()]
        raise FileNotFoundError(
            f"no NS-3 at {root} (looked for {root / 'ns3'}).\n"
            f"  trees present here: {present or 'none'}\n"
            f"  build one per ns3/README.md, or set AUTHBC_NS3.")
    return root


def ns3_version(root: Path | None = None) -> str:
    """The tree's version string, for artifact provenance (e.g. '3.48')."""
    root = root or ns3_root()
    vf = root / "VERSION"
    if vf.is_file():
        return vf.read_text().strip()
    return root.name.replace("ns-", "")
