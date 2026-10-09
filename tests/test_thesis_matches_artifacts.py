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


# every generated macro, as the documents print it
NUMBERS = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                          (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")))

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
        assert "This is derived and not simulated" in LOWRATE
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


class TestTheRecordOfTheOpeningChapterNamesItsChainLink:
    """The first-format record sizes include the record's own 32 B link (review 2.3)."""

    def test_the_figures_typed_in_three_chapters_follow_from_the_measured_record(self) -> None:
        from authbc.bench import framesizes

        delta = round(framesizes.measured_sizes()["delta"])
        data, link, sig = delta - 32, 32, 64
        assert (delta, data) == (45, 13)
        assert round(100 * link / delta) == 71
        assert (link + sig, delta + sig) == (96, 109)
        assert round(100 * (link + sig) / (delta + sig)) == 88
        intro, bytes_ = _text("ch01_introduction.tex"), _text("ch07_bytes.tex")
        assert "The data are $13$\\,B." in intro
        assert "signature and link are $96$ of $109$\\,B" in intro
        for needle in ("$13$\\,B of telemetry", "$71\\%$", "$96$ of $109$\\,B, $88\\%$"):
            assert needle in bytes_, needle
        assert "$s$ includes the record's own $32$\\,B chain link" in _text("ch04_theory.tex")

    def test_the_ladder_marks_every_size_that_is_not_an_emitted_frame(self) -> None:
        codesign = _text("ch08_codesign.tex")
        assert "a chain link in every record}$^\\dagger$" in codesign
        assert "no delta$^\\dagger$" in codesign
        assert "all lean sizes are emitted frames" not in codesign


class TestTheBoundaryIsStatedWithItsScope:
    """The review found "no choice of cryptography helps" contradicted by the paper's own 48 B
    row. The paper lost the phrase in October; the thesis kept it in four places until the
    revision was audited again (F55)."""

    @pytest.mark.parametrize("chapter", ["front.tex", "ch01_introduction.tex",
                                         "ch02_background.tex", "ch12_conclusions.tex"])
    def test_no_chapter_says_the_boundary_is_independent_of_the_cryptography(
            self, chapter: str) -> None:
        text = _text(chapter)
        for phrase in ("no choice of existing cryptography", "no choice of \\emph{existing}",
                       "no choice of existing, standardised cryptography",
                       "no choice of those components helps"):
            assert phrase not in text, phrase

    def test_the_abstract_does_not_call_a_record_with_its_chain_link_the_payload(self) -> None:
        assert "$45$--$190$" not in _text("front.tex")


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


# --------------------------------------------------------------------------- audit of 2026-10-08
# Added with the passages they hold. That audit read the built thesis whole and found typed
# statements that had gone stale or had never been right (a boundary computed with a header of
# 40 B and printed beside "H_f = 44"; "any batching needs Λ ≥ 1/D_max"; a mobility test cited
# in the conclusions and reported nowhere). Everything it then typed is pinned here.
def _hw(name: str) -> list[dict[str, str]]:
    path = REPO / "results" / "hw" / "energy" / "e2e" / name
    return list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))


class TestTheBindingConstraintFigures:
    """thesis ch. 4, T2a: the boundary s < (M − H_f − g_a)/(b_fresh + 1)."""

    THEORY = _text("ch04_theory.tex")
    M, HF, GA = 1500, 44, 64

    def test_the_802_11_boundary_is_computed_with_the_measured_header(self) -> None:
        assert f"{(self.M - self.HF - self.GA) / 6:.1f}" == "232.0"
        assert "$s < 1392/6 = 232.0$" in self.THEORY and "232.7" not in self.THEORY

    def test_the_boundary_with_the_batch_the_design_uses(self) -> None:
        assert f"{(self.M - self.HF - self.GA) / 5:.1f}" == "278.4"
        assert "$1392/5 = 278.4$" in self.THEORY

    def test_the_low_rate_boundary_and_amplification(self) -> None:
        assert f"{(242 - self.HF - self.GA) / 6:.1f}" == "22.3"
        assert f"{242 / (242 - self.HF - self.GA):.2f}" == "1.81"
        assert "$s < 134/6 = 22.3$" in self.THEORY and "$A = 242/134 = 1.81$" in self.THEORY

    def test_five_records_do_not_meet_the_deadline_and_four_do(self) -> None:
        from authbc.models import optimizer

        assert optimizer.freshness_batch_bound(50, 0.100) == 5      # the fill-time ceiling
        region = {(r["lambda_rec_per_s"], r["d_max_ms"]): int(r["b"])
                  for r in _rows("operating_region.csv")}
        assert region[("50", "100")] == 4                           # what the search admits

    def test_batching_needs_more_than_two_records_per_deadline(self) -> None:
        """ch. 3 said "any batching needs Λ ≥ 1/D_max". At 100 ms it needs more than 20 Hz."""
        region = {float(r["lambda_rec_per_s"]): int(r["b"])
                  for r in _rows("operating_region.csv") if r["d_max_ms"] == "100"}
        assert region[10.0] == region[20.0] == 1 and region[21.0] == 2
        assert r"needs $\Lambda_i > 2/\Dmax$" in _text("ch03_system_model.tex")


class TestWhichCeilingBindsPerEncoding:
    def test_json_is_frame_limited_at_576_and_the_text_says_so(self) -> None:
        binds = {(r["mtu"], r["encoding"]): r["binds"] for r in _rows("e2_batching.csv")
                 if r["binds"]}
        assert binds[("576", "json")] == "mtu"
        assert {binds[("576", e)] for e in ("cbor", "msgpack", "delta")} == {"freshness"}
        assert {binds[("1500", e)] for e in ("json", "cbor", "msgpack", "delta")} == {"freshness"}
        assert "JSON at $191$\\,B is still limited by the frame there" in _text("ch07_bytes.tex")


class TestTheSchemeCrossoverParagraph:
    """thesis ch. 8, E4: eighty cells, Ed25519 in every one."""

    CODESIGN = _text("ch08_codesign.tex")
    CELLS = _rows("e4_crossover.csv")

    def test_eighty_cells_and_one_winner(self) -> None:
        assert len(self.CELLS) == 80 and "eighty cells" in self.CODESIGN
        assert {r["winner_plausible"] for r in self.CELLS} == {"ed25519"}

    def test_own_records_never_break_even(self) -> None:
        assert {r["kappa_star_med"] for r in self.CELLS if float(r["rho"]) == 0.0} == {"inf"}

    def test_the_most_favourable_cell(self) -> None:
        (best,) = [r for r in self.CELLS
                   if (r["rho"], r["b"], r["lambda"]) == ("1.0", "32", "50")]
        assert float(best["delta_bytes"]) == 61.0 and "$61$\\,B per record" in self.CODESIGN
        assert round(float(best["radio_saving_us"])) == 81
        assert round(float(best["extra_cpu_us_med"]) / 1000, 1) == 2.6
        finite = [float(r["kappa_star_med"]) for r in self.CELLS if r["kappa_star_med"] != "inf"]
        assert round(min(finite), 1) == round(float(best["kappa_star_med"]), 1) == 31.6
        assert "$31.6$ times" in self.CODESIGN

    def test_the_measured_power_ratio(self) -> None:
        import yaml

        cfg = yaml.safe_load((REPO / "experiments" / "design-ladder" / "config.yaml").read_text())
        assert (cfg["p_radio_w"], cfg["p_cpu_w"]) == (0.218, 0.749)
        assert round(cfg["p_radio_w"] / cfg["p_cpu_w"], 2) == 0.29
        assert "$0.29$ ($0.218$\\,W against $0.749$\\,W)" in self.CODESIGN

    def test_bls_cannot_keep_up_from_200_records_per_second(self) -> None:
        slow = {r["lambda"] for r in self.CELLS if r["bls_verify_ok"] == "False"}
        assert slow == {"200", "800", "2000"}


class TestTheMobilitySubsection:
    """thesis ch. 10: the test the conclusions had cited without its being reported anywhere."""

    ARMS = {(r["matrix"], r["mobility_model"], r["speed_mps"]): r
            for r in _rows("lora_mobility.csv")}

    def _capture(self, model: str, speed: str) -> dict[str, str]:
        return self.ARMS[("goursaud", model, speed)]

    def test_every_row_of_the_table(self) -> None:
        static = float(self._capture("static", "0.0")["delivered_mean"])
        for model, speed, label, shift, moved in (
                ("gaussmarkov", "5.0", "Gauss--Markov, $5$\\,m/s", "$-0.24$", "965"),
                ("gaussmarkov", "20.0", "Gauss--Markov, $20$\\,m/s", "$-0.03$", "967"),
                ("rwp", "20.0", "Random Waypoint, $20$\\,m/s", "$+0.36$", "816")):
            r = self._capture(model, speed)
            mean, sd = float(r["delivered_mean"]), float(r["delivered_stdev"])
            row = (f"{label} & {mean:.4f} & {sd:.3f} & {shift}\\,pp & ${moved}$\\,m")
            assert re.sub(r"\s+", " ", row) in re.sub(r"\s+", " ", LOWRATE), row
            assert f"{100 * (mean - static):+.2f}" == shift.strip("$")
            assert round(float(r["mean_displacement_m"])) == int(moved)
        assert f"static & {static:.4f} & 0.063" in re.sub(r"\s+", " ", LOWRATE)

    def test_no_arm_is_distinguishable_from_the_static_one(self) -> None:
        static = self._capture("static", "0.0")
        for key in (("gaussmarkov", "5.0"), ("gaussmarkov", "20.0"), ("rwp", "20.0")):
            arm = self._capture(*key)
            diff = float(arm["delivered_mean"]) - float(static["delivered_mean"])
            se = math.sqrt((float(arm["delivered_stdev"]) ** 2
                            + float(static["delivered_stdev"]) ** 2) / 30)
            assert abs(diff) / float(static["delivered_stdev"]) <= 0.06
            assert abs(diff / se) <= 0.22

    def test_without_capture_the_arms_are_identical(self) -> None:
        rows = [r for key, r in self.ARMS.items() if key[0] == "aloha"]
        assert len(rows) == 4 and len({r["delivered_mean"] for r in rows}) == 1

    def test_the_conclusions_point_at_it(self) -> None:
        assert r"\Cref{sec:lora-mobility}" in _text("ch12_conclusions.tex")


class TestTheEnergyUncertaintyBudget:
    """thesis ch. 6: every size in the table, from the repetitions on file."""

    METHOD = _text("ch06_methodology.tex")

    @staticmethod
    def _stats(name: str) -> tuple[float, float]:
        rows = _hw(name)
        idle = [float(r["p_idle_w"]) for r in rows]
        energy = sorted(float(r["energy_per_op_uj"]) for r in rows)
        median = energy[len(energy) // 2]
        return 1000 * (max(idle) - min(idle)), 50 * (energy[-1] - energy[0]) / median

    def test_idle_drift_and_repeatability_of_the_two_reported_rows(self) -> None:
        drift_d, half_d = self._stats("energy_d1.csv")
        drift_b, half_b = self._stats("energy_d1_baseline.csv")
        assert (round(drift_d), round(drift_b)) == (5, 9)
        assert "$5$--$9$\\,mW" in self.METHOD
        assert (round(half_b, 1), round(half_d, 1)) == (0.6, 1.1)
        assert "half-range $0.6\\%$ and $1.1\\%$" in self.METHOD

    def test_the_row_that_is_not_reported_was_contaminated(self) -> None:
        idle = [float(r["p_idle_w"]) for r in _hw("energy_ajson.csv")]
        assert 0.45 < max(idle) - min(idle) < 0.55
        assert sum(x > min(idle) + 0.2 for x in idle) == 3
        assert "three of its five repetitions" in self.METHOD

    def test_no_calibration_against_a_reference_is_on_file_and_the_text_says_so(self) -> None:
        """If a calibration record appears, the sentence must change with it."""
        headers = "".join(p.read_text() for p in
                          (REPO / "results" / "hw" / "energy" / "e2e").glob("*.csv"))
        assert "calib" not in headers.lower()
        assert "was not recorded for these runs" in self.METHOD


class TestTheWorkedFrame:
    """thesis ch. 5: a frame cut into fields by a script, from bytes the library emitted."""

    def _module(self):  # noqa: ANN202
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "worked_frame", REPO / "analysis" / "worked_frame.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_the_committed_table_is_what_the_script_writes(self) -> None:
        assert (THESIS / "tab_worked_frame.tex").read_text() == self._module().render(), (
            "thesis/tab_worked_frame.tex is stale — run analysis/worked_frame.py")

    def test_the_rows_add_up_to_the_frame_and_to_the_byte_budget(self) -> None:
        table, total = self._module().rows()
        assert sum(n for *_rest, n in table) == total == 156
        by_field: dict[str, int] = {}
        for _hex, field, _what, n in table:
            by_field[field.split(":")[0]] = by_field.get(field.split(":")[0], 0) + n
        header = sum(by_field[k] for k in ("(map)", "v", "t", "src", "base\\_seq", "n",
                                            "recs", "auth"))
        assert (header, by_field["link"] + 32, by_field["delta"]) == (23, 35, 9)
        text = _text("ch05_implementation.tex")
        assert "$23 + 35 + 64 = 122$" in text and "takes $25$\\,B here" in text
        assert by_field["keyframe"] == 25


class TestTheRegistrationsOfAppendixB:
    """Every commit the table names exists and precedes the commit this test runs on."""

    APPENDIX = (THESIS / "appB_preregistrations.tex").read_text()

    def test_each_named_commit_is_in_the_history(self) -> None:
        import subprocess

        named = sorted(set(re.findall(r"\\texttt\{([0-9a-f]{7})\}", self.APPENDIX)))
        assert len(named) == 18
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=REPO,
                                 capture_output=True, text=True).stdout.strip()
        assert shallow == "false", (
            "this test needs the full history: fetch with depth 0 (CI does)")
        for commit in named:
            done = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                                  cwd=REPO, capture_output=True)
            assert done.returncode == 0, f"{commit} is not an ancestor of HEAD"

    def test_the_chapter_counts_what_the_table_holds(self) -> None:
        assert self.APPENDIX.count(r"\textbf{failed}") == 6
        assert self.APPENDIX.count(r"\textbf{refuted}") == 1
        assert self.APPENDIX.count(r"\textbf{not scored}") == 1
        assert self.APPENDIX.count(r"\emph{registered,") == 0      # every one has been run
        assert "Three to five boards: not run" in self.APPENDIX    # … one of them in part
        assert "Of its eighteen entries, seven failed" in _text("ch06_methodology.tex")
        assert "Of the eighteen registrations" in _text("ch11_reproducibility.tex")
        assert "seven failed in whole or in part" in _text("ch11_reproducibility.tex")


class TestTheLibraryIsTheSizeTheChapterSays:
    def test_nearly_eight_thousand_lines(self) -> None:
        lines = sum(len(p.read_text().splitlines())
                    for p in (REPO / "src" / "authbc").rglob("*.py"))
        assert 7500 <= lines < 8000, f"ch. 5 says 'nearly eight thousand lines'; it is {lines}"


# --------------------------------------------------------------------------- 2026-10-09
class TestTheWorkedExamplesOfChapter4:
    THEORY = _text("ch04_theory.tex")

    def test_the_batching_example(self) -> None:
        m, hf, ga, s = 1500, 44, 64, 45
        b = (m - hf - ga) // s
        assert b == 30 and f"{(hf + ga) / b:.1f}" == "3.6" and f"{s + (hf + ga) / b:.1f}" == "48.6"
        assert f"{m / (m - hf - ga):.3f}" == "1.078" and f"{s + (hf + ga) / 4:.1f}" == "72.0"
        for needle in ("$\\bmaxx = \\lfloor 1392/45 \\rfloor = 30$", "$108/30 = 3.6$\\,B",
                       "$48.6$\\,B", "$A = 1500/1392 = 1.078$", "$108/4 = 27$\\,B", "$72.0$\\,B"):
            assert needle in self.THEORY, needle

    def test_the_scheme_example_is_a_row_of_the_crossover_artifact(self) -> None:
        (row,) = [r for r in _rows("e4_crossover.csv")
                  if (r["rho"], r["b"], r["lambda"]) == ("1.0", "4", "50")]
        assert float(row["delta_bytes"]) == 40.0 == 64 - 96 / 4
        assert round(float(row["radio_saving_us"])) == 53
        assert round(float(row["extra_cpu_us_med"]) / 1000, 1) == 3.7
        assert round(float(row["kappa_star_med"])) == 69
        for needle in ("$\\Delta = 64 - 96/4 = 40$\\,B", "$\\SI{53}{\\micro\\second}$ of",
                       "$3.7$\\,ms more processor time", "more than $69$ times",
                       "the ratio is $0.29$"):
            assert needle in self.THEORY, needle


class TestTheRegisteredContentionExperimentAsTheThesisQuotesIt:
    """thesis ch. 9 quotes six of the twelve registered predictions and the ns-3 cross-check."""

    VALIDATION = _text("ch09_validation.tex")
    PREDICTED = {(r["nodes"], r["occupancy_target"]): r
                 for r in _rows("contention_hw_predictions.csv")}

    def test_the_six_predictions_quoted(self) -> None:
        def losses(n: str) -> list[str]:
            return [f"{100 * float(self.PREDICTED[(n, u)]['predicted_loss']):.2f}"
                    for u in ("0.5", "0.7", "0.85")]

        assert losses("2") == ["0.29", "0.64", "1.40"] and losses("3") == ["0.66", "1.52", "3.00"]
        assert "losses of $0.29$, $0.64$ and $1.40\\%$; with three, $0.66$, $1.52$ and $3.00\\%$" \
            in self.VALIDATION

    def test_the_cross_check_as_quoted(self) -> None:
        check = _rows("contention_hw_ns3_check.csv")
        two = [1 - float(r["ns3_over_model"]) for r in check if r["nodes"] == "2"]
        assert (round(100 * min(two)), round(100 * max(two))) == (9, 18)
        assert all(abs(float(r["ns3_over_model"]) - 1) <= 0.055
                   for r in check if r["nodes"] != "2")
        assert "within $5\\%$ at three to five nodes and is $9$--$18\\%$ below it at two" \
            in self.VALIDATION

    def test_the_bands_tabulated_are_the_registered_ones(self) -> None:
        bands = [(f"{100 * float(self.PREDICTED[('2', u)]['band_lo']):.2f}",
                  f"{100 * float(self.PREDICTED[('2', u)]['band_hi']):.2f}")
                 for u in ("0.5", "0.7", "0.85")]
        assert bands == [("0.18", "0.40"), ("0.39", "0.89"), ("0.85", "1.95")]
        # 0.185 % is printed as 0.19: the table rounds half up, the format above to even
        for lo, hi in (("0.19", "0.40"), ("0.39", "0.89"), ("0.85", "1.95")):
            assert f"${lo}$--${hi}$" in self.VALIDATION


class TestTheContentionExperimentAsItCameOut:
    """thesis ch. 9, Appendix B and the paper against the boards' files of 2026-10-09.

    Three registrations (456a4e7, 06f1bfa, 9a85afa). Until that day a test here asserted that
    no such file existed while the appendix said "not yet run"."""

    VALIDATION = _text("ch09_validation.tex")
    APPENDIX = (THESIS / "appB_preregistrations.tex").read_text()
    HW = REPO / "results" / "hw" / "channel"

    @classmethod
    def _scored(cls, tag: str = "") -> dict[int, dict[str, str]]:
        name = "contention_2nodes" + (f"_{tag}" if tag else "") + ".csv"
        return {int(r["rate_fps_per_node"]): r for r in csv.DictReader(
            ln for ln in (cls.HW / name).read_text().splitlines() if not ln.startswith("#"))}

    @classmethod
    def _saturated(cls, tag: str) -> list[float]:
        return [float(r["loss"]) for r in csv.DictReader(
            ln for ln in (cls.HW / f"saturated_2nodes_{tag}.csv").read_text().splitlines()
            if not ln.startswith("#"))]

    def test_the_reduced_files_are_what_the_reducer_gives_from_the_boards_files(self) -> None:
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location(
            "contention_hw_for_thesis", REPO / "analysis" / "contention_hw.py")
        assert spec and spec.loader
        hw = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = hw
        spec.loader.exec_module(hw)

        def stored(name: str) -> list[dict[str, str]]:
            return list(csv.DictReader(ln for ln in (self.HW / name).read_text().splitlines()
                                       if not ln.startswith("#")))

        def as_text(rows: list[dict]) -> list[dict[str, str]]:
            return [{k: str(v) for k, v in r.items()} for r in rows]

        for folder, tag in (("contention_2", ""), ("contention_2_fb_off", "_fb_off"),
                            ("contention_2_fb_on_repeat", "_fb_on_repeat")):
            windows = hw.windows([self.HW / folder / "node1", self.HW / folder / "node2"], 2)
            assert as_text(windows) == stored(f"contention_2nodes{tag}_windows.csv")
            assert as_text(hw.score(windows)) == stored(f"contention_2nodes{tag}.csv")
        for folder, tag in (("saturated_2_fb_off", "fb_off"), ("saturated_2_fb_on", "fb_on")):
            rows = hw.saturated([self.HW / folder / "node1", self.HW / folder / "node2"], 2)
            assert as_text(rows) == stored(f"saturated_2nodes_{tag}.csv")

    def test_every_window_of_the_three_sessions_was_usable(self) -> None:
        for tag in ("", "fb_off", "fb_on_repeat"):
            rows = self._scored(tag)
            assert sorted(rows) == [124, 174, 211]
            assert all(r["windows"] == "4" and r["usable_windows"] == "4" for r in rows.values())
        assert "twelve windows, all of them usable" in self.VALIDATION

    def test_the_registered_run_held_at_two_loads_and_failed_at_the_third(self) -> None:
        first = self._scored()
        assert [first[k]["inside_band"] for k in (124, 174, 211)] == ["True", "True", "False"]
        ratio = float(first[211]["measured_loss"]) / float(first[211]["predicted_loss"])
        assert f"{ratio:.2f}" == NUMBERS["hwContHighRatio"] == "0.46"
        assert "held at the first two loads and failed at the third" in self.VALIDATION
        assert "held at two loads, \\textbf{failed} at the third" in self.APPENDIX

    def test_the_follow_up_failed_as_the_thesis_says(self) -> None:
        off, repeat, first = self._scored("fb_off"), self._scored("fb_on_repeat"), self._scored()
        # P2: off, the highest load is under a band that begins at 0.848 %
        assert first[211]["band_lo"] == "0.00848" and "begins at $0.848\\%$" in self.VALIDATION
        assert off[211]["inside_band"] == "False"
        assert float(off[211]["measured_loss"]) < float(off[211]["band_lo"])
        # P3: the repeat was to land in 0.47–0.81 % at the highest load, and did not
        assert float(repeat[211]["measured_loss"]) > 0.0081
        # P4: off at least 1.5 times on — not against the first run, and not against the repeat
        assert float(off[211]["measured_loss"]) / float(first[211]["measured_loss"]) < 1.5
        assert float(off[211]["measured_loss"]) < float(repeat[211]["measured_loss"])
        assert "against the repeat it is no larger at all" in self.VALIDATION
        assert "all four \\textbf{failed}, two of them at the highest load only" in self.APPENDIX
        # P1 is held by tests/test_frame_spacing_hw.py; the band is quoted here
        assert "$2.070$--$2.095$\\,ms per frame" in self.VALIDATION

    def test_windows_scatter_more_than_independent_pairs_would(self) -> None:
        import statistics as st

        loss = []
        for name in ("contention_2nodes_windows.csv", "contention_2nodes_fb_off_windows.csv",
                     "contention_2nodes_fb_on_repeat_windows.csv"):
            loss += [(1 - float(r["delivered_frac"]), int(r["sent"])) for r in csv.DictReader(
                ln for ln in (self.HW / name).read_text().splitlines() if not ln.startswith("#"))
                if r["rate_fps_per_node"] == "211"]
        assert len(loss) == 12
        observed = 100 * st.stdev(x for x, _ in loss)
        # frames lost two at a time, the pairs Poisson: sd of the loss = 2·sqrt(pairs)/sent
        mean, sent = st.mean(x for x, _ in loss), st.mean(n for _, n in loss)
        poisson = 100 * 2 * (mean * sent / 2) ** 0.5 / sent
        assert f"{observed:.2f}" == NUMBERS["hwPoolSdHigh"] == "0.20"
        assert f"{poisson:.2f}" == "0.13" and "would give $0.13$" in self.VALIDATION

    def test_two_saturated_radios_lose_what_the_rule_says_within_six_percent(self) -> None:
        import statistics as st

        standard = 2 * (1 / 16) / (1 + 1 / 16)        # tau = 2/17: one event in 16 is a collision
        assert f"{100 * standard:.1f}" == NUMBERS["hwSatStd"] == "11.8"
        assert (f"{100 * 0.6 * standard:.1f}", f"{100 * 1.4 * standard:.1f}") == ("7.1", "16.5")
        for tag, macro in (("fb_off", "hwSatOff"), ("fb_on", "hwSatOn")):
            values = self._saturated(tag)
            assert len(values) == 8
            mean = st.mean(values)
            assert f"{100 * mean:.1f}" == NUMBERS[macro]
            assert 0.6 * standard <= mean <= 1.4 * standard
            assert abs(mean / standard - 1) < 0.06
        assert "within $6\\%$" in self.VALIDATION and "$7.1$--$16.5\\%$" in self.VALIDATION
        assert "the expectation of $7\\%$ was wrong" in self.VALIDATION

    def test_the_thesis_does_not_claim_a_capacity_or_a_cause(self) -> None:
        assert "\\textbf{No capacity was measured.}" in self.VALIDATION
        assert "that it is the cause has not been shown" in self.VALIDATION
        assert "has no demonstrated effect on the loss between two boards" in self.VALIDATION

    def test_the_withdrawn_airtime_figure_is_withdrawn_in_view(self) -> None:
        assert "A figure withdrawn" in self.VALIDATION and "$0.36\\%$" in self.VALIDATION
        for name in ("ch09_validation.tex", "ch12_conclusions.tex", "ch01_introduction.tex"):
            assert "hwAirtime" not in _text(name)
        assert "hwAirtime" not in (REPO / "paper" / "main.tex").read_text()


class TestAnAggregateSignatureSchemeReadAtItsSource:
    """Finding F68. Reading Wang et al. showed that "n messages cost n times one" is true of what
    the signers send and not of what an aggregator forwards."""

    # The two figures are that paper's own (its §VII); the file is held locally, with its hash in
    # docs/literature/HELD_LOCALLY.csv, and the register records which parts of it were read.

    def test_both_documents_state_the_scope_of_the_claim(self) -> None:
        background = _text("ch02_background.tex")
        assert "$388$\\,B, and the aggregate of a hundred is $784$\\,B" in background
        assert "it does not touch the link on which each signer first sends" in background
        paper = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text())
        assert "388\\,B for a single signature and 784\\,B for the aggregate of a hundred" in paper
        for text in (background, paper):
            assert "the cost of $n$ messages is $n$ times the cost of one" not in text
            assert "none reduces what is sent" not in text


class TestSupersededResultsLiveInTheirAppendix:
    """Three results were corrected. What was first reported is kept — in Appendix C, not among
    the current results (audit of 2026-10-08; moved 2026-10-09)."""

    APPENDIX = _text("appC_superseded.tex")

    def test_the_results_chapters_show_no_superseded_figure(self) -> None:
        for chapter in ("ch08_codesign.tex", "ch10_lowrate.tex"):
            text = _text(chapter)
            for figure in ("fig_e5_codesign.png", "fig_envelope.png", "fig_lora_chain.png"):
                assert figure not in text, (chapter, figure)
            assert "\\label{tab:envelope}" not in text

    def test_the_appendix_keeps_all_of_them(self) -> None:
        for needle in ("fig_e5_codesign.png", "fig_envelope.png", "fig_lora_chain.png",
                       "\\label{tab:envelope}", "\\label{sec:envelope-history}",
                       "163--201", "\\textbf{It failed.}"):
            assert needle in self.APPENDIX, needle

    def test_the_chapters_point_at_it(self) -> None:
        assert "\\Cref{sec:envelope-history}" in _text("ch08_codesign.tex")
        assert "\\Cref{app:superseded}" in _text("ch10_lowrate.tex")
        assert "\\input{appC_superseded}" in (THESIS / "main.tex").read_text()
