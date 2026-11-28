#!/usr/bin/env python3
"""U-J: the safe-side claim of the root of (G5) against ns-3, by traffic source (predictions/UJ.md).

Decided by Mohamed on 2026-11-28 (docs/DECISIONS.md). In the stored scorecard every positive error
of the root of (G5), and the one optimistic miss of the law (G9), is a run whose senders are
strictly periodic with frozen phases (audit A1): a pair that collides once collides every period.
With jittered or drifting timers the root lay below ns-3 in all 68 stored cases. U-J tests that
scope on new cells, so that it rests on fresh evidence and not on dropping the stored miss.

**The sources** (the audit twin's `JitteredPeriodicSource`, `ns3/authbc-links-audit.cc`):
* `FZ` frozen: the default OnOff source, one random start phase per station for the whole run;
* `DR` drift: each station's period stretched by U(−20, +20) ppm (a crystal's tolerance), with a
  1 µs jitter, the scenario's minimum for a skew (below the 4 µs detection window);
* `J01`, `J1`: each frame moved by U(0, 0.1 ms) or U(0, 1 ms) from its place on the grid;
* `DS` the designated source: each frame at an instant drawn anew in its period.

**The model values** do not depend on the source: the root of (G5) and the law (G9) at ε = 0.05,
802.11a 6 Mb/s, W = 16 (`authbc.models.unified_capacity`).

    python analysis/uj.py              -> the predictions, printed
    python analysis/uj.py --scan       -> every stored CSV row at a cell's (bytes, frames/s)
    python analysis/uj.py --markdown   -> the registration's table
    python analysis/uj.py --score      -> results/raw/uj_scored.csv
"""

from __future__ import annotations

import csv
import io
import statistics as st
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

EPS = 0.05
TOL = 0.05
RAW = REPO / "results" / "raw"
OUT = RAW / "uj_scored.csv"


@dataclass(frozen=True)
class Source:
    """A traffic source: per-frame jitter in ms (None: one period; 0: the frozen OnOff source)
    and the per-station rate offset bound in ppm."""

    jitter_ms: float | None
    skew_ppm: float = 0.0

    @property
    def frozen(self) -> bool:
        return self.jitter_ms == 0.0


SOURCES: dict[str, Source] = {
    "FZ": Source(0.0),
    "DR": Source(0.001, 20.0),
    "J01": Source(0.1),
    "J1": Source(1.0),
    "DS": Source(None),
}


@dataclass(frozen=True)
class JCell:
    name: str
    frame_bytes: int
    fps: float
    source: str

    @property
    def tf_s(self) -> float:
        return uc.airtime_s(phy.OFDM_20MHZ_6M, self.frame_bytes)


# Cell 1 runs every source; cell 2 the two ends (frozen and designated), as registered.
_PLAN = (((230, 40.0), ("FZ", "DR", "J01", "J1", "DS")), ((260, 30.0), ("FZ", "DS")))
CELLS: list[JCell] = [JCell(f"JA{b}F{f:g}{s}", b, f, s) for (b, f), srcs in _PLAN for s in srcs]


def predictions() -> list[dict[str, object]]:
    """Per cell: the root of (G5) and the law (G9) at ε = 0.05 (the same for every source)."""
    rows = []
    for c in CELLS:
        rho, tau0 = uc.dcf_constants(EPS, uc.A80211A)
        rows.append(
            {
                "cell": c.name,
                "frame_bytes": c.frame_bytes,
                "fps": c.fps,
                "source": c.source,
                "tf_us": round(c.tf_s * 1e6, 3),
                "law_valid": c.tf_s > 2 * tau0,
                "root": uc.n_root(c.fps, c.tf_s, EPS, uc.A80211A),
                "law": uc.n_law(c.fps, c.tf_s, EPS, uc.A80211A),
            }
        )
    return rows


def per_seed(name: str) -> list[float]:
    """Each seed's own crossing of 0.95, interpolated between its bracketing node counts
    (reported: the spread that frozen phases make bimodal)."""
    path = RAW / f"uj_{name.lower()}_runs.csv"
    by: dict[int, dict[int, float]] = {}
    with path.open() as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            by.setdefault(int(r["seed"]), {})[int(r["n_nodes"])] = float(r["delivered_frac"])
    out = []
    for curve in by.values():
        ns = sorted(curve)
        for lo, hi in zip(ns, ns[1:], strict=False):
            dl, dh = curve[lo], curve[hi]
            if dl >= 1 - EPS > dh:
                out.append(lo + (dl - (1 - EPS)) * (hi - lo) / (dl - dh))
                break
    return out


def score() -> list[dict[str, object]]:
    """Each cell: ns-3's 30-seed crossing against the root and the law. Scored for the non-frozen
    sources as two claims: S, the root at or below ns-3; A, the root and the law within ±5 %."""
    pred = {r["cell"]: r for r in predictions()}
    rows = []
    for c in CELLS:
        summary = RAW / f"uj_{c.name.lower()}.csv"
        lines = [ln for ln in summary.read_text().splitlines() if not ln.startswith("#")]
        cross = next(r for r in csv.DictReader(lines) if r["n_nodes"] == "CROSSING@0.95")
        ns3 = float(cross["delivered_mean"])
        p = pred[c.name]
        root_err = (float(str(p["root"])) - ns3) / ns3
        law_err = (float(str(p["law"])) - ns3) / ns3
        seeds = per_seed(c.name)
        scored = not SOURCES[c.source].frozen
        s_held = root_err <= 0  # claim S, the safe side
        a_held = abs(root_err) <= TOL and abs(law_err) <= TOL  # claim A, the accuracy
        held = s_held and a_held  # the registration: a cell holds if both hold
        rows.append(
            {
                "cell": c.name,
                "source": c.source,
                "ns3_crossing": ns3,
                "ci_lo": float(cross["delivered_min"]),
                "ci_hi": float(cross["delivered_max"]),
                "seeds": int(cross["seeds"]),
                "root": p["root"],
                "root_err_pct": 100 * root_err,
                "law": p["law"],
                "law_err_pct": 100 * law_err,
                "s_held": (int(s_held) if scored else "reported"),
                "a_held": (int(a_held) if scored else "reported"),
                "held": (int(held) if scored else "reported"),
                "seed_crossings": len(seeds),
                "seed_min": min(seeds) if seeds else "",
                "seed_max": max(seeds) if seeds else "",
                "seed_sd": st.stdev(seeds) if len(seeds) > 1 else "",
            }
        )
    return rows


_BYTES = ("frame_bytes", "frameSize", "frame_size", "payload_bytes", "bytes", "payload")
_FPS = ("fps", "frames_per_s", "framesPerSec", "frame_rate", "frames_per_sec")


def scan_prior(root: Path = REPO / "results") -> list[tuple[str, str, int, float]]:
    """Every stored CSV row whose (bytes, frames/s) equals a cell's, whatever its PHY."""
    wanted = {(c.frame_bytes, c.fps): c.name for c in CELLS}
    hits = []
    for path in sorted(root.rglob("*.csv")):
        if path.name.startswith("uj_"):
            continue  # this test's own results
        text = "".join(
            ln
            for ln in path.read_text(errors="replace").splitlines(keepends=True)
            if not ln.startswith("#")
        )
        reader = csv.DictReader(io.StringIO(text))
        cols = reader.fieldnames or []
        bcol = next((x for x in _BYTES if x in cols), None)
        fcol = next((x for x in _FPS if x in cols), None)
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
    lines = [
        "| cell | frame | frames/s | source | T_f (µs) | **root of (G5)** | **law (G9)** |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in predictions():
        lines.append(
            f"| {r['cell']} | {r['frame_bytes']} B | {r['fps']:g} | {r['source']} | "
            f"{r['tf_us']:g} | **{float(str(r['root'])):.2f}** | "
            f"**{float(str(r['law'])):.2f}** |"
        )
    return "\n".join(lines)


def _write(rows: list[dict[str, object]], path: Path, run: str) -> None:
    from authbc.bench import provenance

    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


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
    if "--score" in sys.argv:
        rows = score()
        _write(rows, OUT, "uj_scored")
        scored = [r for r in rows if r["held"] != "reported"]
        print(f"{sum(int(str(r['held'])) for r in scored)} of {len(scored)} held")
        for r in rows:
            print(
                f"  {r['cell']}: ns-3 {r['ns3_crossing']:.2f} ({r['ci_lo']:.2f}-{r['ci_hi']:.2f})"
                f"  root {r['root_err_pct']:+.2f} %  law {r['law_err_pct']:+.2f} %  {r['held']}"
            )
        return
    for r in predictions():
        print(
            f"{r['cell']:14s} T_f {r['tf_us']:7.1f} us  root {float(str(r['root'])):7.3f}  "
            f"law {float(str(r['law'])):7.3f}  law valid {r['law_valid']}"
        )


if __name__ == "__main__":
    main()
