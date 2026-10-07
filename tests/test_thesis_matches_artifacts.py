"""The thesis's low-rate and validation chapters against the artifacts they quote.

**Where these tests came from.** Until 2026-10 the paper carried the LoRa capacity detail, and
`tests/test_paper_matches_artifacts.py` held each quoted figure to its CSV — written after three
separate LoRa numbers had gone stale in the paper unnoticed. The paper was then cut to a matrix
and a paragraph (its results are generated: `tests/test_paper_numbers.py`), and the detail moved
to `thesis/ch10_lowrate.tex`. A guard that stays behind when its text moves guards nothing, so
the guards moved with it.

Corrected results in the thesis are macros from the generated `numbers.tex`. What is checked here
is what is still typed: figures from frozen LoRa artifacts, the stage-1 table of the direct
search, and the copies `make thesis` places beside the chapters.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
THESIS = REPO / "thesis"


def _text(name: str) -> str:
    """A chapter with runs of whitespace collapsed, so a re-wrapped sentence still matches."""
    return re.sub(r"\s+", " ", (THESIS / name).read_text(encoding="utf-8"))


def _rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in (RAW / name).read_text().splitlines()
                               if not ln.startswith("#")))


LOWRATE = _text("ch10_lowrate.tex")
LORA = {"aloha": "lora_capacity_ci.csv", "eu": "lora_capacity_eu.csv",
        "goursaud": "lora_capacity_goursaud.csv"}


def _d(arm: str, n: int) -> float:
    (row,) = [r for r in _rows(LORA[arm]) if int(r["n_devices"]) == n]
    return float(row["delivered_frac"])


class TestTheLoRaPassagesMatchTheArtifacts:
    """⚠️ Three separate LoRa numbers once went stale in prose while every gate was green."""

    def test_capture_gain_figures(self) -> None:
        pts = (_d("goursaud", 8) - _d("aloha", 8)) * 100
        ratio = _d("goursaud", 50) / _d("aloha", 50)
        assert rf"raises delivery by ${pts:.1f}$ points at $N{{=}}8$" in LOWRATE
        assert rf"by ${ratio:.2f}\times$ at $N{{=}}50$" in LOWRATE

    def test_gateway_versus_peer_figures(self) -> None:
        ratio = _d("eu", 50) / _d("aloha", 50)
        assert rf"${ratio:.2f}\times$ at $N{{=}}50$" in LOWRATE
        assert rf"(${_d('aloha', 50):.4f} \rightarrow {_d('eu', 50):.4f}$)" in LOWRATE
        assert rf"still ${_d('eu', 100):.4f}$ at $N{{=}}100$" in LOWRATE

    def test_the_gateway_crossing_values(self) -> None:
        assert rf"$N{{=}}8$ with ${_d('eu', 8):.4f}$" in LOWRATE
        assert rf"fails at $N{{=}}10$ with ${_d('eu', 10):.4f}$" in LOWRATE

    def test_the_periodic_escape_cross_check_quotes_the_measured_value(self) -> None:
        assert rf"against ${_d('aloha', 8):.3f}$ measured" in LOWRATE

    def test_the_peer_cliff(self) -> None:
        assert (rf"delivery is ${_d('aloha', 3):.3f}$ at $N{{=}}3$ and "
                rf"${_d('aloha', 5):.3f}$ at $N{{=}}5$") in LOWRATE

    def test_the_superseded_n_max_baseline_of_5_is_gone(self) -> None:
        assert "moves only from 5 to 8" not in LOWRATE
        assert "moves only from 3 to 8" in LOWRATE


class TestLoraExternalTable:
    """The comparison table once outlived the three-seed run it was built on, and revived a
    retracted claim in one of its rows."""

    def _artifact(self) -> dict[int, tuple[float, float]]:
        return {int(r["n_devices"]): (float(r["authbc_ns3_loss_pct"]),
                                      float(r["haxhibeqiri2017_loss_pct"]))
                for r in _rows("lora_external_check.csv") if r["authbc_ns3_loss_pct"]}

    def _block(self) -> str:
        tex = (THESIS / "ch10_lowrate.tex").read_text(encoding="utf-8")
        start = tex.index(r"\label{tab:lora-external}")
        return tex[start:tex.index(r"\end{tabular}", start)]

    def test_every_cell_matches_the_current_artifact(self) -> None:
        art = self._artifact()
        printed = {int(m.group(1)): (float(m.group(2)), float(m.group(3)))
                   for m in re.finditer(r"^(\d+)\s*&\s*\$([\d.]+)\\%\$\s*&\s*\$([\d.]+)\\%\$",
                                        self._block(), re.M)}
        assert len(printed) >= 6, "could not parse tab:lora-external"
        for n, (ours, theirs) in printed.items():
            assert abs(ours - art[n][0]) <= 0.05 and abs(theirs - art[n][1]) <= 0.05, n

    def test_no_row_revives_the_retracted_optimism_claim(self) -> None:
        """⚠️ F18 is retracted: above the crossover this work is the MORE PESSIMISTIC model."""
        assert "more optimistic" not in self._block()

    def test_n_max_is_three_against_four(self) -> None:
        m = re.search(r"&\s*\\textbf\{(\d+)\}\s*&\s*\\textbf\{(\d+)\}", self._block())
        assert m and (int(m.group(1)), int(m.group(2))) == (3, 4)

    def test_the_source_is_cited_under_its_own_authors(self) -> None:
        assert "haxhibeqiri2017lora" in LOWRATE and not re.search(r"\bBor\b", LOWRATE)


class TestDR6Derivation:
    """DR6 is derived, not simulated, and the text must keep saying so and why."""

    DUTY = 0.009864   # measured duty cycle after jitter (EU868 requires < 1 %)

    def test_closed_form_reproduces_the_measured_dr5_run(self) -> None:
        meas = {int(r["n_devices"]): float(r["delivered_frac"])
                for r in _rows("lora_capacity.csv")}
        worst = max(abs(math.exp(-2 * (n - 1) * self.DUTY) - m)
                    for n, m in meas.items() if 2 <= n <= 10)
        assert worst < 0.01

    def test_closed_form_gives_the_same_n_max_as_the_simulation(self) -> None:
        assert max(n for n in range(1, 40)
                   if math.exp(-2 * (n - 1) * self.DUTY) >= 0.95) == 3

    def test_the_chapter_labels_dr6_as_derived_and_says_why(self) -> None:
        assert "We derive this rather than simulate it" in LOWRATE
        assert r"indexed by \emph{spreading factor alone}" in LOWRATE


class TestTheExclusionIsStatedWithItsHistory:
    """The chapter must carry the corrected result AND the two wrong statements it replaced."""

    def test_all_three_statements_are_recorded(self) -> None:
        for heading in ("First statement", "First correction", "Second correction"):
            assert rf"\paragraph{{{heading}" in LOWRATE, heading
        assert r"\emph{four of seven}" in LOWRATE and r"\emph{three of seven}" in LOWRATE

    def test_the_four_scope_conditions_are_there(self) -> None:
        scope = LOWRATE[LOWRATE.index(r"\subsection{Scope}"):
                        LOWRATE.index(r"\subsection{What each relaxation buys}")]
        assert scope.count(r"\item") == 4 and "255" in scope

    def test_the_twelve_rates_are_partitioned_five_three_four(self) -> None:
        matrix = _rows("exclusion_matrix.csv")
        groups = {"excluded-signature": [], "excluded": [], "feasible": []}
        for r in matrix:
            if r["auth_bytes"] == "64" and r["design"] == "lean":
                key = ("excluded-signature" if r["signature_alone_overflows"] == "1"
                       else r["verdict"])
                groups[key].append(f"DR{r['dr']}")
        for names in groups.values():
            assert ", ".join(sorted(names, key=lambda d: int(d[2:]))) in LOWRATE, names


class TestTheStageOneTable:
    """`ch09`: the six registered cells, strictly periodic source — typed, so checked."""

    def test_every_row_is_the_artifacts_interpolated_crossing(self) -> None:
        cross = {r["config"]: r for r in _rows("ns3_nmax_direct.csv")
                 if r["n_nodes"] == "CROSSING" and (r["jitter_ms"], r["skew_ppm"]) == ("0", "0")
                 and float(r["lambda_rec_per_s"]) == 50.0}
        tex = (THESIS / "ch09_validation.tex").read_text(encoding="utf-8")
        start = tex.index("direct (interpolated)")
        block = tex[start:tex.index(r"\end{tabular}", start)]
        rows = re.findall(r"& (\d+)\\,B, ([\d.]+)/s & (\d+) & ([\d.]+) & \$\\?m?a?t?h?b?f?\{?"
                          r"([+-][\d.]+)\\%", block)
        assert len(rows) == 6, "could not parse the stage-1 table"
        by_frame = {(int(r["frame_bytes"]), float(r["lambda_rec_per_s"]) / int(r["batch"])): r
                    for r in cross.values()}
        for frame, fps, ceiling, direct, deviation in rows:
            art = by_frame[(int(frame), float(fps))]
            assert int(ceiling) == int(art["model_n_max"])
            assert float(direct) == pytest.approx(float(art["n_cross_interp"]), abs=0.06)
            assert float(deviation) == pytest.approx(float(art["deviation_interp_pct"]), abs=0.06)


class TestTheSurveyWithdrawalStaysWithdrawn:
    """The claim was withdrawn on 2026-08-08; these guard the withdrawal wherever it is told."""

    def test_the_null_result_is_still_in_the_repository(self) -> None:
        verdicts = [r["verdict"] for r in _rows("direction_c_survey.csv")]
        counted = [v for v in verdicts if v in {"REPORTS", "NONE"}]
        assert len(counted) >= 23 and counted.count("REPORTS") == 5
        assert (REPO / "docs" / "DIRECTION_C_SURVEY_PROTOCOL.md").exists()

    @pytest.mark.parametrize("path", ["thesis/ch11_reproducibility.tex", "paper/methods.tex"])
    def test_the_point_estimate_is_never_quoted_without_its_interval(self, path: str) -> None:
        tex = (REPO / path).read_text(encoding="utf-8")
        assert "21.7" in tex and "[7.5, 43.7]" in tex
        for banned in ("state no seed count", "none states a seed count",
                       "the hypothesis is supported"):
            assert banned not in tex


class TestCopiesAreCurrent:
    """`make thesis` copies these in; a stale copy typesets yesterday's result."""

    @pytest.mark.parametrize(("copy", "source"), [
        ("thesis/numbers.tex", "paper/numbers.tex"), ("thesis/refs.bib", "paper/refs.bib")])
    def test_text_inputs(self, copy: str, source: str) -> None:
        assert (REPO / copy).read_bytes() == (REPO / source).read_bytes(), (
            f"{copy} is stale — run `make thesis`")

    def test_the_frame_figure_is_the_papers_with_its_float_and_label_changed(self) -> None:
        paper = (REPO / "paper" / "fig_system.tex").read_text(encoding="utf-8")
        expected = paper.replace("\\begin{figure}[t]", "\\begin{figure}[h]") \
            .replace("\\label{fig:system}", "\\label{fig:frame}")
        assert expected != paper, "the paper's figure lost what `make thesis` edits"
        assert (THESIS / "fig_frame.tex").read_text(encoding="utf-8") == expected, (
            "thesis/fig_frame.tex is stale — run `make thesis`")

    def test_every_figure_a_chapter_includes_is_the_generated_one(self) -> None:
        tex = "".join(p.read_text(encoding="utf-8") for p in THESIS.glob("ch*.tex"))
        for name in sorted(set(re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+\.png)\}", tex))):
            assert (THESIS / name).read_bytes() == \
                (REPO / "results" / "figures" / name).read_bytes(), f"thesis/{name} is stale"
