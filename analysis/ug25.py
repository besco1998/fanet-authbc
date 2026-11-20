#!/usr/bin/env python3
"""U-G25: (G25), the periodic-source loss expression, against ns-3 on new cells.

Work package B of `docs/prompts/NEXT_PHASE_PROMPT.md`; the registration is `predictions/UG25.md`.

**The cells.** Two PHYs, two frame sizes × two frame rates each:
* 802.11b at 1 Mb/s, long preamble;
* 802.11a at 6 Mb/s.

None was simulated before: `--scan` checks every stored CSV.

**The predictions.** For each cell and target ε ∈ {0.05, 0.02}:
* the (G25) root, scored at ±5 %;
* the Poisson root of (G5), reported only;
* the pilot grid's centre.

**The co-waiting count.** The mean number of other stations holding a frame when a busy period
that a frame arrived into ends (U-C1's definition, `analysis/unified_c1.py`), measured against
R·K and K at four loads per cell.

    python analysis/ug25.py              -> the predictions, printed (what the registration holds)
    python analysis/ug25.py --scan       -> every stored CSV row at a cell's (bytes, frames/s)
    python analysis/ug25.py --markdown   -> the registration's table
    python analysis/ug25.py --score STEM -> results/raw/ug25_scored.csv
"""
from __future__ import annotations

import csv
import io
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

EPS = (0.05, 0.02)
TOL = 0.05
OUT = REPO / "results" / "raw" / "ug25_scored.csv"


@dataclass(frozen=True)
class G25Cell:
    standard: str
    frame_bytes: int
    fps: float

    @property
    def access(self) -> uc.Access:
        return uc.A80211B if self.standard == "80211b" else uc.A80211A

    @property
    def tf_s(self) -> float:
        ph = phy.DSSS_1M if self.standard == "80211b" else phy.OFDM_20MHZ_6M
        return uc.airtime_s(ph, self.frame_bytes)


CELLS: dict[str, G25Cell] = {
    "GB120F15": G25Cell("80211b", 120, 15.0),
    "GB120F20": G25Cell("80211b", 120, 20.0),
    "GB240F15": G25Cell("80211b", 240, 15.0),
    "GB240F20": G25Cell("80211b", 240, 20.0),
    "GA640F20": G25Cell("80211a", 640, 20.0),
    "GA640F30": G25Cell("80211a", 640, 30.0),
    "GA900F20": G25Cell("80211a", 900, 20.0),
    "GA900F30": G25Cell("80211a", 900, 30.0),
}


def predictions() -> list[dict[str, object]]:
    """Per cell and target: the (G25) root, the Poisson root, and R at the (G25) root."""
    rows = []
    for name, c in CELLS.items():
        for eps in EPS:
            g25 = pc.n_root_periodic(c.fps, c.tf_s, eps, c.access)
            poisson = uc.n_root(c.fps, c.tf_s, eps, c.access)
            rows.append({"cell": name, "standard": c.standard, "frame_bytes": c.frame_bytes,
                         "fps": c.fps, "tf_us": round(c.tf_s * 1e6, 3), "eps": eps,
                         "g25_root": g25, "poisson_root": poisson,
                         "g25_over_poisson_pct": 100 * (g25 / poisson - 1)})
    return rows


def predicted_k(c: G25Cell, n: int, p: float) -> tuple[float, float]:
    """K of (G4) and R·K of (G25) at N stations, with p the measured loss inside a."""
    acc, nu = c.access, (n - 1) * c.fps
    a = nu * (c.tf_s - acc.delta_s) * (1 - p / 2)
    gam, eta = nu * acc.difs_s, nu * acc.slot_s * (acc.w - 1) / 2
    k = a * (1 + gam + 2 * eta) / (1 - gam - a)
    return k, pc.r_bb(n - 1, a + gam) * k


_BYTES = ("frame_bytes", "frameSize", "frame_size", "payload_bytes", "bytes", "payload")
_FPS = ("fps", "frames_per_s", "framesPerSec", "frame_rate", "frames_per_sec")


def scan_prior(root: Path = REPO / "results") -> list[tuple[str, str, int, float]]:
    """Every stored CSV row whose (bytes, frames/s) equals a cell's, whatever its PHY."""
    wanted = {(c.frame_bytes, c.fps): name for name, c in CELLS.items()}
    hits = []
    for path in sorted(root.rglob("*.csv")):
        text = "".join(ln for ln in path.read_text(errors="replace").splitlines(keepends=True)
                       if not ln.startswith("#"))
        reader = csv.DictReader(io.StringIO(text))
        cols = reader.fieldnames or []
        bcol = next((c for c in _BYTES if c in cols), None)
        fcol = next((c for c in _FPS if c in cols), None)
        if not (bcol and fcol):
            continue
        for row in reader:
            try:
                key = (int(float(row[bcol])), float(row[fcol]))
            except (TypeError, ValueError):
                continue
            if key in wanted:
                hits.append((wanted[key], str(path.relative_to(REPO)), *key))
    return hits


def markdown() -> str:
    """The registration's prediction table, generated (never typed)."""
    lines = ["| cell | PHY | frame | frames/s | T_f (µs) | ε | **(G25) root** | Poisson root | "
             "(G25) over Poisson |", "|---|---|---|---|---|---|---|---|---|"]
    for r in predictions():
        lines.append(f"| {r['cell']} | {r['standard']} | {r['frame_bytes']} B | {r['fps']:g} | "
                     f"{r['tf_us']:g} | {r['eps']:g} | **{r['g25_root']:.2f}** | "
                     f"{r['poisson_root']:.2f} | {r['g25_over_poisson_pct']:+.2f} % |")
    return "\n".join(lines)


def main() -> None:
    if "--markdown" in sys.argv:
        print(markdown())
        return
    if "--scan" in sys.argv:
        hits = scan_prior()
        print(f"{len(hits)} stored rows at a cell's (bytes, frames/s)")
        for h in hits:
            print("  ", h)
        return
    for r in predictions():
        print(f"{r['cell']:9s} {r['standard']} {r['frame_bytes']:4d} B {r['fps']:5.1f}/s "
              f"T_f {r['tf_us']:8.3f} us  eps {r['eps']:.2f}  G25 {r['g25_root']:7.3f}  "
              f"Poisson {r['poisson_root']:7.3f}  ({r['g25_over_poisson_pct']:+.2f} %)")


if __name__ == "__main__":
    main()
