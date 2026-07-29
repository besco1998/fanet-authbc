#!/usr/bin/env python3
"""Make the signetlabdei/lorawan module compile under our optimized NS-3 profile (D2).

**The problem.** 57 of the module's sources use `NS_LOG_*` macros and *none* of them include
`ns3/log.h`; they rely on it arriving transitively. Our build profile is
`--build-profile=optimized`, which sets `NS3_ASSERT=OFF` and `NS3_LOG=OFF`, and under that
configuration the transitive chain no longer reaches `log.h`. Result:

    error: expected constructor, destructor, or type conversion before '(' token
    error: 'NS_LOG_FUNCTION' was not declared in this scope

**Why patch rather than change the profile.** The frozen 802.11 results were produced with the
optimized profile on ns-3.41. Rebuilding the comparison on a different profile would confound a
version migration with a build-profile change, and the whole point of Phase 3 is to isolate the
version. Including what you use is also simply correct C++, so this is a fix, not a workaround.

**Idempotent.** Running it twice is a no-op. The NS-3 tree is git-ignored, so this script — not the
patched tree — is the reproducible artifact. Re-run it after any `git pull` inside the module.
"""

from __future__ import annotations

import sys
from pathlib import Path

INCLUDE = '#include "ns3/log.h"'


def patch_file(path: Path) -> bool:
    text = path.read_text()
    if "NS_LOG" not in text or INCLUDE in text:
        return False
    lines = text.splitlines(keepends=True)
    # Insert after the LAST include of the leading include block, so the module's own paired
    # header still comes first (ns-3 style) and include order stays stable.
    last = None
    for i, ln in enumerate(lines):
        if ln.startswith("#include"):
            last = i
        elif last is not None and ln.strip() and not ln.startswith("#include"):
            break
    if last is None:
        return False
    lines.insert(last + 1, INCLUDE + "\n")
    path.write_text("".join(lines))
    return True


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent / "ns-3.48" / "contrib" / "lorawan")
    if not root.is_dir():
        sys.exit(f"lorawan module not found at {root}")
    patched = [p for p in sorted(root.rglob("*"))
               if p.suffix in {".cc", ".h"} and patch_file(p)]
    print(f"patched {len(patched)} file(s) under {root}")
    for p in patched[:5]:
        print(f"  {p.relative_to(root)}")
    if len(patched) > 5:
        print(f"  ... and {len(patched) - 5} more")


if __name__ == "__main__":
    main()
