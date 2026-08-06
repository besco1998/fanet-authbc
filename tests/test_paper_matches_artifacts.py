"""The paper's capacity table must equal the generated artifact (audit S3b).

**Why this file exists.** `tab:envelope`'s $V{\\geq}0.95$ column was hand-written in LaTeX and was
never derived by any generator. When F30 corrected the measured crossing from U = 2.797 to 2.435,
the prose was updated to 213/100 but **the table was not** — it kept saying 233/116, and the paper
contradicted itself for weeks with every gate green. Nothing could have caught it, because nothing
compared the two.

This parses the table straight out of `paper/main.tex` and checks every number against
`results/raw/capacity_envelope.csv`. A stale figure in either place now fails the suite.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TEX = REPO / "paper" / "main.tex"
CSV = REPO / "results" / "raw" / "capacity_envelope.csv"

# paper row label -> the `binds` label of the generated ENVELOPE row it must match
ROW_TO_CONFIG = {
    (r"\textbf{optimized} delta/B", 50, 100): "optimized delta/B @3GPP100ms/50Hz",
    ("A+CBOR (Pillar-1)", 50, 100): "A+CBOR Pillar-1 @3GPP100ms/50Hz",
    ("optimized delta/B", 20, 250): "optimized delta/B @250ms",
    ("A+CBOR (Pillar-1)", 20, 250): "A+CBOR Pillar-1 @250ms",
    ("A+JSON (naive)", 20, 250): "A+JSON naive @250ms",
    ("optimized delta/B", 20, 100): "optimized delta/B @3GPP100ms/20Hz",
    ("optimized delta/B", 10, 100): "optimized delta/B @3GPP100ms/10Hz",
}


def _envelope_rows() -> dict[str, dict[str, str]]:
    rows = csv.DictReader([ln for ln in CSV.read_text().splitlines() if not ln.startswith("#")])
    return {r["binds"]: r for r in rows if r["n_local"] == "ENVELOPE"}


def _paper_table() -> dict[tuple[str, int, int], tuple[int, int, int, int]]:
    """Parse tab:envelope -> {(label, lambda, d_max_ms): (u_lt_1, v95_mean, per_run_lo, hi)}."""
    tex = TEX.read_text()
    start = tex.index(r"\label{tab:envelope}")
    body = tex[start : tex.index(r"\end{tabular}", start)]
    out = {}
    for line in body.splitlines():
        line = line.strip()
        if not line.endswith(r"\\") or line.startswith(r"\multicolumn") or "&" not in line:
            continue
        cells = [c.strip() for c in line.removesuffix(r"\\").split("&")]
        if len(cells) != 7:
            continue
        label, lam, dmax, _b, u1, v95, per_run = cells
        if not lam.isdigit():
            continue
        u1_v = int(re.sub(r"[^0-9]", "", u1))
        v95_v = int(re.sub(r"[^0-9]", "", v95))
        lo, hi = (int(x) for x in per_run.split("--"))
        out[(label, int(lam), int(dmax))] = (u1_v, v95_v, lo, hi)
    return out


@pytest.fixture(scope="module")
def paper_rows():
    rows = _paper_table()
    assert len(rows) == len(ROW_TO_CONFIG), (
        f"parsed {len(rows)} table rows, expected {len(ROW_TO_CONFIG)} — the table structure "
        f"changed and this test's mapping must be updated with it"
    )
    return rows


@pytest.mark.parametrize("key", list(ROW_TO_CONFIG))
def test_every_paper_row_matches_the_generated_envelope(key, paper_rows):
    gen = _envelope_rows()[ROW_TO_CONFIG[key]]
    u1, v95, lo, hi = paper_rows[key]
    assert u1 == int(gen["n_max_u_lt_1"]), f"{key}: U<1 column stale"
    assert v95 == int(gen["n_max_v95_mean"]), f"{key}: V>=0.95 (mean) column stale"
    assert lo == int(gen["n_max_v95_strict_lo"]), f"{key}: per-run lower bound stale"
    assert hi == int(gen["n_max_v95_strict_hi"]), f"{key}: per-run upper bound stale"


class TestTheClaimsMadeAboutTheTable:
    """The prose quotes ratios and endpoints derived from these rows; pin those too."""

    def test_the_compliant_and_relaxed_headline_pairs(self):
        gen = _envelope_rows()
        assert int(gen["optimized delta/B @3GPP100ms/50Hz"]["n_max_v95_mean"]) == 100
        assert int(gen["optimized delta/B @250ms"]["n_max_v95_mean"]) == 213
        tex = TEX.read_text()
        assert r"$213 \to 100$" in tex, "the 213->100 compliance-cost sentence drifted"
        assert "116" not in tex.replace("1160", ""), \
            "the superseded 116 figure is back in the paper"

    def test_the_four_quoted_ratios_are_what_the_artifact_gives(self):
        gen = _envelope_rows()

        def ratio(opt: str, base: str, col: str) -> float:
            return int(gen[opt][col]) / int(gen[base][col])

        comp = ("optimized delta/B @3GPP100ms/50Hz", "A+CBOR Pillar-1 @3GPP100ms/50Hz")
        relx = ("optimized delta/B @250ms", "A+CBOR Pillar-1 @250ms")
        assert ratio(*comp, "n_max_u_lt_1") == pytest.approx(1.94, abs=0.01)
        assert ratio(*comp, "n_max_v95_mean") == pytest.approx(3.23, abs=0.01)
        assert ratio(*relx, "n_max_u_lt_1") == pytest.approx(3.22, abs=0.01)
        assert ratio(*relx, "n_max_v95_mean") == pytest.approx(2.42, abs=0.01)

    def test_the_advantage_survives_the_criterion_choice(self):
        """Reporting both only helps if the conclusion survives either reading. Check that."""
        gen = _envelope_rows()
        pairs = [("optimized delta/B @3GPP100ms/50Hz", "A+CBOR Pillar-1 @3GPP100ms/50Hz"),
                 ("optimized delta/B @250ms", "A+CBOR Pillar-1 @250ms")]
        ratios = [int(gen[o][c]) / int(gen[b][c])
                  for o, b in pairs
                  for c in ("n_max_u_lt_1", "n_max_v95_mean",
                            "n_max_v95_strict_lo", "n_max_v95_strict_hi")]
        assert min(ratios) > 1.9, "the co-design advantage must hold under every criterion"
        assert max(ratios) < 3.3


# --------------------------------------------------------------------------- LoRa arm (F38/F39)
LORA = {
    "aloha": REPO / "results" / "raw" / "lora_capacity_ci.csv",
    "eu": REPO / "results" / "raw" / "lora_capacity_eu.csv",
    "goursaud": REPO / "results" / "raw" / "lora_capacity_goursaud.csv",
}


def _lora(arm: str) -> dict[int, dict[str, str]]:
    rows = csv.DictReader([ln for ln in LORA[arm].read_text().splitlines()
                           if not ln.startswith("#")])
    return {int(r["n_devices"]): r for r in rows}


def _d(arm: str, n: int) -> float:
    return float(_lora(arm)[n]["delivered_frac"])


class TestTheLoRaPassagesMatchTheArtifacts:
    """⚠️ These exist because three separate LoRa numbers went stale in the paper unnoticed.

    "N_max moves only from 5 to 8" survived F30 changing the baseline 5 -> 3, and the capture and
    gateway figures survived F38 re-running their artifacts at 30 seeds. Nothing compared the paper
    to the CSVs for this arm, so nothing caught any of it. Now something does.
    """

    def test_capture_gain_figures(self):
        tex = TEX.read_text()
        pts = (_d("goursaud", 8) - _d("aloha", 8)) * 100
        ratio = _d("goursaud", 50) / _d("aloha", 50)
        assert rf"raises delivery by ${pts:.1f}$ points at $N{{=}}8$" in tex, (
            f"paper's capture gain at N=8 drifted; artifact says {pts:+.1f} pts"
        )
        assert rf"by ${ratio:.2f}\times$ at $N{{=}}50$" in tex, (
            f"paper's capture ratio at N=50 drifted; artifact says {ratio:.2f}x"
        )

    def test_gateway_versus_peer_figures(self):
        tex = TEX.read_text()
        ratio = _d("eu", 50) / _d("aloha", 50)
        assert rf"${ratio:.2f}\times$ at $N{{=}}50$" in tex
        assert rf"(${_d('aloha', 50):.4f} \rightarrow {_d('eu', 50):.4f}$)" in tex
        assert rf"still ${_d('eu', 100):.4f}$ at $N{{=}}100$" in tex

    def test_the_eu_crossing_values(self):
        tex = TEX.read_text()
        assert rf"$N{{=}}8$ with ${_d('eu', 8):.4f}$" in tex
        assert rf"fails at $N{{=}}10$ with ${_d('eu', 10):.4f}$" in tex

    def test_the_periodic_escape_cross_check_quotes_the_measured_value(self):
        assert rf"against ${_d('aloha', 8):.3f}$ measured" in TEX.read_text()

    def test_the_superseded_n_max_baseline_of_5_is_gone(self):
        """F30 moved the ALOHA N_max 5 -> 3; the 'from 5 to 8' sentence outlived it by weeks."""
        tex = TEX.read_text()
        assert r"moves only from 5 to 8" not in tex, "the superseded 'from 5 to 8' sentence is back"
        assert r"moves only from 3 to 8" in tex


class TestTheAblationClaimsMatchTheModel:
    """F39: the abstract and intro claimed all four axes couple; the ablation says two do."""

    def test_the_paper_no_longer_claims_the_knobs_are_inseparable(self):
        tex = TEX.read_text()
        assert "these knobs are not separable" not in tex, (
            "the falsified 'not separable' thesis statement is back -- encoding is exactly additive"
        )

    def test_the_placement_closed_form_is_stated(self):
        assert r"g_a(1{-}1/b)" in TEX.read_text() or r"g_a(1-1/b)" in TEX.read_text()
