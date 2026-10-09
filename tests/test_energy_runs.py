"""The energy runs of 2026-10-09 against what was registered for them (analysis/energy_runs.py).

hw/BENCH_SESSION.md, committed in a38994f before the first run; finding F79. Held here: that
the ranges scored are the ranges registered, in a commit that holds no run; that every reduced
file is what the reducer gives from its capture and manifest; that the table is what the script
gives; that every window was valid by the board's own record; and what the documents quote.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
import statistics as st
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "results" / "hw" / "energy" / "e2e_2026-10-09"
RIG = REPO / "results" / "hw" / "energy" / "rig"
sys.path.insert(0, str(REPO / "hw"))


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runs = _module("energy_runs", REPO / "analysis" / "energy_runs.py")
capture = _module("ina219_capture", REPO / "hw" / "ina219_capture.py")
NAMES = tuple(runs.REGISTERED)
TABLE = {r["run"]: r for r in csv.DictReader(
    ln for ln in runs.OUT.read_text().splitlines() if not ln.startswith("#"))}
SHEET = (REPO / "hw" / "BENCH_SESSION.md").read_text(encoding="utf-8")
NUMBERS = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                          (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")))
REGISTRATION = "a38994f"


def _rows(path: Path) -> list[dict[str, str]]:
    body = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout


class TestTheRegistrationPrecededTheData:
    def test_the_ranges_are_in_a_commit_that_holds_no_run(self) -> None:
        sheet = _git("show", f"{REGISTRATION}:hw/BENCH_SESSION.md")
        for needle in ("113–125 µJ per record", "(146–179)", "(256–313)",
                       "115–127 µJ per record", "0.72–0.79 W", "0.70–0.80 W",
                       "If the control is outside its range, stop"):
            assert needle in sheet, needle
        assert "e2e_2026-10-09" not in _git("ls-tree", "-r", "--name-only", REGISTRATION)

    def test_the_ranges_scored_are_the_ranges_registered(self) -> None:
        assert {k: v[1] for k, v in runs.REGISTERED.items()} == {
            "control_cbor": (113.0, 125.0), "lean_b4": (146.0, 179.0),
            "lean_b1": (256.0, 313.0), "ajson_r10": (115.0, 127.0)}
        assert runs.POWER_RANGE_W == (0.70, 0.80)

    def test_the_rig_had_passed_its_check_before_the_first_run(self) -> None:
        report = json.loads((RIG / "rigcheck-20261009T051248Z.json").read_text())
        assert report["passed"] is True and report["channel"] == 2
        first = json.loads((RUNS / "manifest_control_cbor.json").read_text())
        assert "20261009T051248Z" < first["run_utc"]          # the run is stamped at its end


class TestTheFilesAreWhatTheScriptsGive:
    @pytest.mark.parametrize("name", NAMES)
    def test_the_reduction_from_the_capture_and_the_manifest_on_channel_two(
            self, name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        capture.reduce(RUNS / f"manifest_{name}.json", RUNS / f"samples_{name}.csv", 2,
                       tmp_path / "out.csv")
        capsys.readouterr()
        assert _rows(tmp_path / "out.csv") == _rows(RUNS / f"energy_{name}.csv")

    def test_the_table(self) -> None:
        assert [{k: str(v) for k, v in r.items()} for r in runs.collect()] == list(TABLE.values())


class TestEveryWindowWasValid:
    @pytest.mark.parametrize("name", NAMES)
    def test_by_the_firmwares_flags_and_the_kernels_count(self, name: str) -> None:
        manifest = json.loads((RUNS / f"manifest_{name}.json").read_text())
        assert manifest["host"] == "authbc-pi4b" and manifest["python"] == "3.12.13"
        assert manifest["gpio_backend"] != "none"
        assert len(manifest["windows"]) == 2 * manifest["reps"]
        for w in manifest["windows"]:
            assert w["throttle_clean"] is True
            for state in (w["before"], w["after"]):
                assert state["throttled"] == "throttled=0x0"
                assert state["undervoltage_events"] == "0"
                assert state["governor"] == "performance"

    @pytest.mark.parametrize("name", NAMES)
    def test_sixty_second_windows_by_the_meters_clock_too(self, name: str) -> None:
        manifest = json.loads((RUNS / f"manifest_{name}.json").read_text())
        marked: list[list[dict[str, str]]] = []
        inside = False
        for r in capture._read_samples(RUNS / f"samples_{name}.csv"):
            if r["window"] == "1":
                if not inside:
                    marked.append([])
                marked[-1].append(r)
            inside = r["window"] == "1"
        assert len(marked) == len(manifest["windows"])
        for seg, w in zip(marked, manifest["windows"], strict=True):
            by_meter = (int(seg[-1]["ms"]) - int(seg[0]["ms"]) + 20) / 1000.0
            assert by_meter == pytest.approx(w["duration_s"], rel=0.002)

    @pytest.mark.parametrize("name", NAMES)
    def test_every_idle_window_within_a_fifth_of_a_watt_of_the_others(self, name: str) -> None:
        idle = [float(r["p_idle_w"]) for r in _rows(RUNS / f"energy_{name}.csv")]
        assert max(idle) - min(idle) < 0.2
        assert TABLE[name]["reps_clean"] == TABLE[name]["reps_metered"]


class TestWhatCameOut:
    """Every range registered in a38994f, against the table."""

    def test_every_run_is_inside_its_range_of_energy_and_of_power(self) -> None:
        for name in NAMES:
            row = TABLE[name]
            assert row["inside_registered"] == row["power_inside_registered"] == "1", name
            assert row["reportable"] == "1"
            assert float(row["registered_lo"]) <= float(row["uj_per_record_median"]) \
                <= float(row["registered_hi"])

    def test_the_control_is_two_percent_from_julys_row_on_the_other_rig(self) -> None:
        uj, watts = runs.july_baseline()
        control = TABLE["control_cbor"]
        assert float(control["uj_per_record_median"]) / uj == pytest.approx(0.978, abs=0.002)
        assert float(control["added_power_w_median"]) / watts == pytest.approx(0.976, abs=0.003)
        assert NUMBERS["enCtlVsJuly"] == "2.2" and NUMBERS["enCtlMeas"] == "116.2"

    def test_the_lean_sender_within_five_percent_of_its_timed_prediction_and_below_it(self) -> None:
        for name, predicted in (("lean_b4", 162.55), ("lean_b1", 284.08)):
            row = TABLE[name]
            assert float(row["script_predicted_uj_per_record"]) == pytest.approx(predicted,
                                                                                 abs=0.01)
            assert 0.95 < float(row["metered_over_predicted"]) < 1.0
        assert (NUMBERS["enLeanGap"], NUMBERS["enLeanOneGap"]) == ("$-$4.4", "$-$3.9")

    def test_batching_saves_forty_three_percent_as_the_timing_said(self) -> None:
        four, one = (float(TABLE[n]["uj_per_record_median"]) for n in ("lean_b4", "lean_b1"))
        assert 0.35 <= 1 - four / one <= 0.50                       # the registered range
        assert NUMBERS["enLeanSavePct"] == f"{100 * (1 - four / one):.0f}" == "43"

    def test_the_lean_sender_costs_2_7_times_the_first_formats(self) -> None:
        first = float(NUMBERS["enDesignMeas"])
        assert NUMBERS["enLeanOverFirst"] == \
            f"{float(TABLE['lean_b4']['uj_per_record_median']) / first:.1f}" == "2.7"

    def test_why_the_meter_is_below_the_prediction(self) -> None:
        """One busy core adds 0.72–0.74 W here against the constant 0.749; and with four
        records to a frame the metered loop runs a frame 3 % faster than the timed one."""
        for name in ("control_cbor", "lean_b4", "lean_b1"):
            assert 0.72 <= float(TABLE[name]["added_power_w_median"]) <= 0.74
        timed_ms = {4: 0.8680983, 1: 0.3792808}
        in_loop = {b: 1e3 * b / float(TABLE[f"lean_b{b}"]["records_per_s"]) for b in (4, 1)}
        assert 1 - in_loop[4] / timed_ms[4] == pytest.approx(0.030, abs=0.003)
        assert abs(1 - in_loop[1] / timed_ms[1]) < 0.005

    def test_the_json_row_has_ten_usable_repetitions_at_last(self) -> None:
        row = TABLE["ajson_r10"]
        assert (row["reps_metered"], row["reps_clean"]) == ("10", "10")

    def test_the_controls_second_repetition_is_the_one_the_logins_disturbed(self) -> None:
        reps = [float(r["energy_per_op_uj"]) for r in _rows(RUNS / "energy_control_cbor.csv")]
        assert reps.index(max(reps)) == 1 and max(reps) - st.median(reps) > 4.0
        record = re.sub(r"\s+", " ", (RUNS / "README.md").read_text())
        assert "because of the person running it" in record


class TestWhatTheDocumentsQuote:
    PAPER = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
    CODESIGN = re.sub(r"\s+", " ", (REPO / "thesis" / "ch08_codesign.tex").read_text())
    METHOD = re.sub(r"\s+", " ", (REPO / "thesis" / "ch06_methodology.tex").read_text())

    def test_the_macros_are_the_table(self) -> None:
        for macro, name in (("enCtlMeas", "control_cbor"), ("enLeanMeas", "lean_b4"),
                            ("enLeanOneMeas", "lean_b1"), ("enJsonMeas", "ajson_r10")):
            assert NUMBERS[macro] == f"{float(TABLE[name]['uj_per_record_median']):.1f}"
        power = float(TABLE["control_cbor"]["added_power_w_median"])
        assert NUMBERS["enCtlPower"] == f"{power:.3f}"

    def test_both_tables_carry_the_four_rows_and_say_where_the_lean_ones_come_from(self) -> None:
        for text in (self.PAPER, self.CODESIGN):
            for needle in ("first format, every record signed", "lean format, every record signed",
                           "\\enLeanMeas\\ \\enLeanRange", "\\enLeanOneMeas\\ \\enLeanOneRange",
                           "\\enCtlMeas"):
                assert needle in text, needle
        assert "Lean rows: second board and sensor." in self.PAPER
        assert "Its rows were metered on a second board and sensor" in self.PAPER
        assert "on the second board through the second sensor" in self.CODESIGN

    def test_the_thesis_says_which_is_the_dearer_format_and_what_is_still_unchecked(self) -> None:
        assert "The lean sender costs \\enLeanOverFirst{} times the energy per record" \
            in self.CODESIGN
        assert "bounds their difference and not their common error" in self.CODESIGN
        assert "three times that morning" in self.CODESIGN
        assert "the author's own logins to the board fell in one of its windows" in self.CODESIGN
        assert "this does not exclude it" in self.METHOD

    def test_no_document_still_calls_the_lean_senders_energy_an_estimate(self) -> None:
        assert "not a meter reading" not in self.CODESIGN
        assert "and not metered" not in self.PAPER
