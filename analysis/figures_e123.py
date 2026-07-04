"""Regenerate the E1–E3 figures from FROZEN raw only (docs/04 §5, P4 step 6).

Reads results/raw/e{1,2,3}_*.csv (never recomputes data), writes results/figures/*.png, and
appends provenance rows to results/PROVENANCE.md. Figures are byte-stable: Agg backend, no
timestamp metadata, fixed dpi/fonts — regenerating twice yields identical bytes.

Run: `make figures` or `python analysis/figures_e123.py`.
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


def load(name: str) -> tuple[list[dict], dict]:
    meta: dict[str, str] = {}
    data_lines: list[str] = []
    for line in (RAW / name).read_text().splitlines(keepends=True):
        if line.startswith("#"):
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
        else:
            data_lines.append(line)
    return list(csv.DictReader(io.StringIO("".join(data_lines)))), meta


def _cap(meta: dict, extra: str) -> str:
    return f"config_hash={meta.get('config_hash', '?')} · {extra}"


def fig_e1() -> str:
    rows, meta = load("e1_dominance.csv")
    encs = [r["encoding"] for r in rows]
    phis = [float(r["phi_pct"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(encs, phis, color=["#c44", "#48c", "#4a4", "#a4a"])
    for bar, phi in zip(bars, phis, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, phi + 0.8, f"{phi:.1f}%", ha="center")
    ax.set_ylabel("auth fraction φ = g/(s+g), g=64  [%]")
    ax.set_title("E1 — overhead dominance (inline per-record, measured)")
    ax.set_ylim(0, max(phis) + 8)
    fig.text(0.5, -0.03, _cap(meta, "seeds 1–30 · inline placement A"), ha="center", fontsize=8)
    out = FIGS / "fig_e1_dominance.png"
    fig.savefig(out, **_SAVE)
    plt.close(fig)
    return out.name


def fig_e2() -> str:
    rows, meta = load("e2_batching.csv")
    fig, ax = plt.subplots(figsize=(6, 4))
    sub = [r for r in rows if r["mtu"] == "1500" and r["placement"] == "B"
           and r["encoding"] == "cbor"]
    sub.sort(key=lambda r: int(r["b"]))
    bs = [int(r["b"]) for r in sub]
    perrec = [float(r["bytes_per_rec"]) for r in sub]
    s = float(sub[0]["s"])
    a_formula = float(sub[0]["A_formula"])
    ax.plot(bs, perrec, "o-", label="measured on-air bytes/rec (B, CBOR)")
    ax.axhline(s, ls=":", color="gray", label=f"payload s={s:.1f}")
    ax.axhline(s * a_formula, ls="--", color="#c44", label=f"s·A asymptote (A={a_formula:.3f})")
    ax.set_xlabel("batch size b")
    ax.set_ylabel("on-air bytes / record")
    ax.set_title("E2 — batching cure (self-batch, M=1500)")
    ax.legend(fontsize=8)
    fig.text(0.5, -0.03, _cap(meta, "A = M/(M−H_f−g_a)"), ha="center", fontsize=8)
    out = FIGS / "fig_e2_batching.png"
    fig.savefig(out, **_SAVE)
    plt.close(fig)
    return out.name


def fig_e3() -> str:
    rows, meta = load("e3_loss.csv")
    p = "0.05"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    for plc, color in (("B", "#48c"), ("D", "#c44")):
        sub = sorted((r for r in rows if r["p"] == p and r["placement"] == plc),
                     key=lambda r: int(r["b"]))
        bs = [int(r["b"]) for r in sub]
        vm = [float(r["V_meas"]) for r in sub]
        vt = [float(r["V_theory"]) for r in sub]
        ax1.plot(bs, vm, "o", color=color, ms=4, label=f"{plc} measured")
        ax1.plot(bs, vt, "-", color=color, lw=1, label=f"{plc} theory")
    ax1.axhline((1 - 0.05) ** 2, ls=":", color="gray", label="V=(1−p)²")
    ax1.set_xlabel("batch size b")
    ax1.set_ylabel("verifiability V")
    ax1.set_title(f"E3 — V vs b (p={p})")
    ax1.legend(fontsize=7)
    # Pareto (bytes/rec, V): B should sit up-and-left of D once D spans >1 frame
    for plc, color, mk in (("B", "#48c", "o"), ("D", "#c44", "s")):
        sub = [r for r in rows if r["p"] == p and r["placement"] == plc]
        ax2.scatter([float(r["bytes_per_rec"]) for r in sub],
                    [float(r["V_meas"]) for r in sub], c=color, marker=mk, s=18, label=plc)
    ax2.set_xlabel("on-air bytes / record")
    ax2.set_ylabel("verifiability V")
    ax2.set_title("E3 — (bytes, V) Pareto")
    ax2.legend(fontsize=8)
    fig.text(0.5, -0.02, _cap(meta, "seeds 1–30 · bootstrap 95% CI"), ha="center", fontsize=8)
    out = FIGS / "fig_e3_frontier.png"
    fig.savefig(out, **_SAVE)
    plt.close(fig)
    return out.name


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    made = [fig_e1(), fig_e2(), fig_e3()]
    prov = REPO / "results" / "PROVENANCE.md"
    hashes = {n: hashlib.sha256((FIGS / n).read_bytes()).hexdigest()[:16] for n in made}
    lines = ["# Results provenance — figure → source raw → sha256\n",
             "\n| figure | source raw | sha256(16) |\n|---|---|---|\n"]
    src = {"fig_e1_dominance.png": "e1_dominance.csv", "fig_e2_batching.png": "e2_batching.csv",
           "fig_e3_frontier.png": "e3_loss.csv"}
    for n in made:
        lines.append(f"| {n} | results/raw/{src[n]} | {hashes[n]} |\n")
    prov.write_text("".join(lines))
    print(f"wrote {len(made)} figures to {FIGS}; provenance -> {prov}")


if __name__ == "__main__":
    main()
