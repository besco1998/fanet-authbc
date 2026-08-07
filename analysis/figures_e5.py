"""E5 co-design figure from frozen results/raw/e5_codesign.csv (T5, docs/04 §2).

Stacked on-air bytes/record (payload s + auth overhead) for the optimizer's byte-optimal config
vs the baselines (A+JSON, A+CBOR, D-over-agg), annotated with V and the ≥40 % auth-byte-cut result.
Byte-stable (Agg, no-timestamp metadata); appends a PROVENANCE.md row.
"""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
FIGS = REPO / "results" / "figures"
_SAVE = {"dpi": 110, "bbox_inches": "tight", "metadata": {"Software": None}}
_ORDER = ["A+JSON", "A+CBOR", "D-overagg", "optimized"]


def load() -> tuple[dict[str, dict], dict]:
    data = [ln for ln in (RAW / "e5_codesign.csv").read_text().splitlines(keepends=True)
            if not ln.startswith("#")]
    rows = {r["role"]: r for r in csv.DictReader(io.StringIO("".join(data)))}
    sc = rows["SUCCESS_CRITERION"]
    return rows, sc


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    rows, sc = load()
    labels = [r for r in _ORDER if r in rows]
    payload = [float(rows[r]["s"]) for r in labels]
    overhead = [float(rows[r]["auth_overhead_bytes"]) for r in labels]
    vs = [float(rows[r]["V"]) for r in labels]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, payload, color="#88b", label="payload s")
    ax.bar(labels, overhead, bottom=payload, color="#c44", label="on-air auth overhead")
    for i, (p, o, v) in enumerate(zip(payload, overhead, vs, strict=True)):
        ax.text(i, p + o + 4, f"auth {o:.1f} B\nV={v:.3f}", ha="center", fontsize=8)
    ax.set_ylabel("on-air bytes / record")
    cut = float(sc["auth_cut_pct"])
    ok = "PASS" if int(sc["pass"]) else "FAIL"
    ax.set_title(f"E5 co-design (T5): optimized cuts auth bytes {cut:.1f}% vs A+CBOR "
                 f"at V≥0.95, p=0.05 [{ok}]")
    ax.legend(fontsize=8)
    ax.set_ylim(0, max(p + o for p, o in zip(payload, overhead, strict=True)) + 40)
    opt = rows["optimized"]
    fig.text(0.5, -0.03,
             f"optimized = {opt['encoding']}+{opt['scheme']}+placement {opt['placement']} "
             f"b={opt['batch']} · timings and both power figures measured on Raspberry Pi 4 (D8)",
             ha="center", fontsize=8)
    out = FIGS / "fig_e5_codesign.png"
    fig.savefig(out, **_SAVE)
    plt.close(fig)

    sha = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    prov = REPO / "results" / "PROVENANCE.md"
    lines = [ln for ln in prov.read_text().splitlines(keepends=True) if out.name not in ln]
    prov.write_text("".join(lines) + f"| {out.name} | results/raw/e5_codesign.csv | {sha} |\n")
    print(f"wrote {out.name} (sha {sha}); auth cut {cut:.1f}% [{ok}]")


if __name__ == "__main__":
    main()
