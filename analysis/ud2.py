#!/usr/bin/env python3
"""U-D2: (G25) where U-D's Poisson model failed — 802.11b, windows 8, 16 and 32, loss targets 2, 5
and 10 % (predictions/UD2.md; decided by Mohamed on 2026-11-28, docs/DECISIONS.md).

U-D (2026-11-17) found the Poisson root of (G5) 5.0–6.3 % below ns-3 at 15–37 stations and failed
its ±5 % band at 8 of 9 cells. U-D stays failed as registered. (G25), written afterwards for
periodic sources, was registered on new cells in U-G25, but at 802.11b only at W = 32 and
ε = 2 and 5 %. U-D2 tests it on new cells at the windows and the target U-D failed at.

**The cells:** 802.11b at 1 Mb/s, long preamble, the designated source (each frame at an instant
drawn anew in its period); frames of 200 B at 10/s and 320 B at 8/s; W = 8, 16 and 32 as
`--cwMin` = W − 1. Each cell is crossed at 0.98, 0.95 and 0.90.

    python analysis/ud2.py              -> the predictions, printed
    python analysis/ud2.py --scan       -> every stored CSV row at a cell's (bytes, frames/s)
    python analysis/ud2.py --markdown   -> the registration's table
    python analysis/ud2.py --score      -> results/raw/ud2_scored.csv
"""

from __future__ import annotations

import csv
import io
import sys
from dataclasses import dataclass, replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.models import periodic_capacity as pc  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

EPS = (0.02, 0.05, 0.10)
TOL = 0.05
U_CHECKED = 0.78  # (G25)'s range at 802.11b as U-G25H stated it; past it, +1.16 to +2.41 %
RAW = REPO / "results" / "raw"
OUT = RAW / "ud2_scored.csv"


@dataclass(frozen=True)
class D2Cell:
    name: str
    frame_bytes: int
    fps: float
    w: int

    @property
    def access(self) -> uc.Access:
        return replace(uc.A80211B, w=self.w)

    @property
    def tf_s(self) -> float:
        return uc.airtime_s(phy.DSSS_1M, self.frame_bytes)


CELLS: list[D2Cell] = [
    D2Cell(f"QB{b}F{f:g}W{w}", b, f, w) for b, f in ((200, 10.0), (320, 8.0)) for w in (8, 16, 32)
]


def predictions() -> list[dict[str, object]]:
    """Per cell and target: the (G25) root (scored) and the Poisson root of (G5) (reported)."""
    rows = []
    for c in CELLS:
        for eps in EPS:
            g25 = pc.n_root_periodic(c.fps, c.tf_s, eps, c.access)
            poisson = uc.n_root(c.fps, c.tf_s, eps, c.access)
            rows.append(
                {
                    "cell": c.name,
                    "frame_bytes": c.frame_bytes,
                    "fps": c.fps,
                    "w": c.w,
                    "tf_us": round(c.tf_s * 1e6, 3),
                    "eps": eps,
                    "g25_root": g25,
                    "poisson_root": poisson,
                    "u_at_root": g25 * c.fps * c.tf_s,
                    "past_range": g25 * c.fps * c.tf_s > U_CHECKED,
                }
            )
    return rows


def score() -> list[dict[str, object]]:
    """Each (cell, ε): ns-3's 30-seed crossing and interval against the registered (G25) root."""
    pred = {(r["cell"], r["eps"]): r for r in predictions()}
    rows = []
    for c in CELLS:
        summary = RAW / f"ud2_{c.name.lower()}.csv"
        lines = [ln for ln in summary.read_text().splitlines() if not ln.startswith("#")]
        for r in csv.DictReader(lines):
            if not r["n_nodes"].startswith("CROSSING@"):
                continue
            eps = round(1 - float(r["n_nodes"].split("@")[1]), 2)
            p = pred[(c.name, eps)]
            ns3 = float(r["delivered_mean"])
            err = (float(str(p["g25_root"])) - ns3) / ns3
            rows.append(
                {
                    "cell": c.name,
                    "w": c.w,
                    "eps": eps,
                    "ns3_crossing": ns3,
                    "ci_lo": float(r["delivered_min"]),
                    "ci_hi": float(r["delivered_max"]),
                    "seeds": int(r["seeds"]),
                    "bracketed": r["delivered_stdev"],
                    "g25_root": p["g25_root"],
                    "g25_err_pct": 100 * err,
                    "held": int(abs(err) <= TOL),
                    "side": ""
                    if abs(err) <= TOL
                    else ("optimistic" if err > 0 else "conservative"),
                    "poisson_root": p["poisson_root"],
                    "past_range": p["past_range"],
                    "poisson_err_pct": 100 * (float(str(p["poisson_root"])) - ns3) / ns3,
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
        if path.name.startswith("ud2_"):
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
        "| cell | frame | frames/s | W | T_f (µs) | ε | **(G25) root** | Poisson root "
        "| u at the root |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in predictions():
        lines.append(
            f"| {r['cell']} | {r['frame_bytes']} B | {r['fps']:g} | {r['w']} | "
            f"{r['tf_us']:g} | {r['eps']:g} | **{float(str(r['g25_root'])):.2f}** | "
            f"{float(str(r['poisson_root'])):.2f} | {float(str(r['u_at_root'])):.2f}"
            f"{' (past 0.78)' if r['past_range'] else ''} |"
        )
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
    if "--score" in sys.argv:
        from authbc.bench import provenance

        rows = score()
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": "ud2_scored"}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        OUT.write_text(buf.getvalue())
        print(f"{sum(int(str(r['held'])) for r in rows)} of {len(rows)} held")
        for r in rows:
            print(
                f"  {r['cell']} eps {r['eps']}: ns-3 {r['ns3_crossing']:.3f} "
                f"({r['ci_lo']:.3f}-{r['ci_hi']:.3f})  G25 {float(str(r['g25_root'])):.2f} "
                f"{r['g25_err_pct']:+.2f} %  Poisson {r['poisson_err_pct']:+.2f} %"
            )
        return
    for r in predictions():
        print(
            f"{r['cell']:12s} T_f {r['tf_us']:8.1f} us  eps {r['eps']:.2f}  "
            f"G25 {float(str(r['g25_root'])):7.3f}  Poisson {float(str(r['poisson_root'])):7.3f}"
        )


if __name__ == "__main__":
    main()
