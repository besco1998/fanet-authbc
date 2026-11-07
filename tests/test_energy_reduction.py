"""The published energy figures, re-derived from the meter's raw captures (finding F78).

The energy table of the paper is built from `results/hw/energy/e2e/energy_*.csv`. Those files
are the output of `hw/ina219_capture.py --reduce` on a capture of the meter and the manifest the
board wrote. Until 2026-10-09 no test ran that reduction: a change to the reducer, or a stored
file edited by hand, would have gone unseen. Held here: every stored file is exactly what the
reducer gives from the raw files beside it; one repetition recomputed without the reducer; and
the checks of the captures themselves that the audit of that day made by hand.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import statistics as st
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ENERGY = REPO / "results" / "hw" / "energy"
E2E = ENERGY / "e2e"
sys.path.insert(0, str(REPO / "hw"))

_spec = importlib.util.spec_from_file_location("ina219_capture", REPO / "hw" / "ina219_capture.py")
assert _spec and _spec.loader
capture = importlib.util.module_from_spec(_spec)
sys.modules["ina219_capture"] = capture
_spec.loader.exec_module(capture)

# reduced file -> (manifest, samples): the four configurations of the energy table
RUNS = {
    "energy_d1.csv": ("manifest_d1_reduced.json", "samples_d1.csv"),
    "energy_d1_baseline.csv": ("manifest_d1_baseline_reduced.json", "samples_d1_baseline.csv"),
    "energy_ajson.csv": ("manifest_ajson.json", "samples_ajson.csv"),
    "energy_doveragg.csv": ("manifest_doveragg.json", "samples_doveragg.csv"),
}


def _rows(path: Path) -> list[dict[str, str]]:
    body = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def _windows(samples: Path) -> list[list[dict[str, str]]]:
    """Runs of samples the sync line marked, in order."""
    out: list[list[dict[str, str]]] = []
    inside = False
    for r in capture._read_samples(samples):
        if r["window"] == "1":
            if not inside:
                out.append([])
            out[-1].append(r)
        inside = r["window"] == "1"
    return out


class TestTheStoredFilesAreWhatTheReducerGives:
    @pytest.mark.parametrize("reduced", sorted(RUNS))
    def test_from_the_capture_and_the_manifest(self, reduced: str, tmp_path: Path,
                                               capsys: pytest.CaptureFixture[str]) -> None:
        manifest, samples = RUNS[reduced]
        capture.reduce(E2E / manifest, E2E / samples, 1, tmp_path / reduced)
        capsys.readouterr()
        assert _rows(tmp_path / reduced) == _rows(E2E / reduced)
        summary = reduced.replace(".csv", "-summary.csv")
        assert (tmp_path / summary).read_text() == (E2E / summary).read_text()

    @pytest.mark.frozen
    def test_the_campaign_of_isolated_operations(self, tmp_path: Path,
                                                 capsys: pytest.CaptureFixture[str]) -> None:
        capture.reduce(ENERGY / "full_manifest.json", ENERGY / "full_samples.csv", 1,
                       tmp_path / "energy-pi4a.csv")
        capsys.readouterr()
        assert _rows(tmp_path / "energy-pi4a.csv") == _rows(ENERGY / "energy-pi4a.csv")


class TestOneRepetitionWithoutTheReducer:
    """The design's first repetition, from the samples and the manifest alone."""

    def test_energy_is_the_power_added_times_the_time_over_the_frames(self) -> None:
        manifest = json.loads((E2E / "manifest_d1_reduced.json").read_text())
        idle, load = _windows(E2E / "samples_d1.csv")[:2]
        added_w = (st.mean(float(r["P1_W"]) for r in load[capture.EDGE_TRIM:])
                   - st.mean(float(r["P1_W"]) for r in idle[capture.EDGE_TRIM:]))
        window = manifest["windows"][1]
        assert window["kind"] == "load" and manifest["windows"][0]["kind"] == "idle"
        joules_per_frame = added_w * window["duration_s"] / window["n_ops"]
        stored = _rows(E2E / "energy_d1.csv")[0]
        # the stored figure is rounded to six decimals of a microjoule
        assert 1e6 * joules_per_frame == pytest.approx(float(stored["energy_per_op_uj"]), abs=5e-7)
        assert added_w == pytest.approx(0.728, abs=0.001)
        # four records to a frame: 58.37 µJ per record, one of the five repetitions whose
        # median is the 58.4 of the paper's table
        assert 1e6 * joules_per_frame / 4 == pytest.approx(58.37, abs=0.01)


class TestTheCapturesThemselves:
    """What made July's rig sound, as numbers — the same quantities hw/rig_check.py judges."""

    @pytest.mark.parametrize("reduced", sorted(RUNS))
    def test_ten_windows_of_sixty_seconds_by_both_clocks(self, reduced: str) -> None:
        manifest = json.loads((E2E / RUNS[reduced][0]).read_text())
        windows = _windows(E2E / RUNS[reduced][1])
        assert len(windows) == len(manifest["windows"]) == 10
        for marked, declared in zip(windows, manifest["windows"], strict=True):
            by_meter = (int(marked[-1]["ms"]) - int(marked[0]["ms"]) + 20) / 1000.0
            assert by_meter == pytest.approx(declared["duration_s"], rel=0.001)   # 0.1 %

    @pytest.mark.parametrize("reduced", sorted(RUNS))
    def test_the_voltage_did_not_move_with_the_sync_line(self, reduced: str) -> None:
        """Idle with the line high against the second before it with the line low: within
        15 mV, the limit of the rig check. On 2026-10-09 a loose ground made this 290 mV."""
        rows = capture._read_samples(E2E / RUNS[reduced][1])
        shifts = []
        for k in range(1, len(rows)):
            if rows[k]["window"] == "1" and rows[k - 1]["window"] == "0":
                before, after = rows[max(0, k - 45):k - 5], rows[k + 5:k + 105]
                if (len(before) == 40 and all(r["window"] == "1" for r in after)
                        and abs(st.mean(float(r["I1_mA"]) for r in after)
                                - st.mean(float(r["I1_mA"]) for r in before)) < 15.0):
                    shifts.append(st.mean(float(r["V1"]) for r in after)
                                  - st.mean(float(r["V1"]) for r in before))
        assert shifts, "no idle window with a quiet second before it"
        assert max(abs(s) for s in shifts) < 0.015

    def test_the_chips_power_register_is_voltage_times_current(self) -> None:
        rows = capture._read_samples(E2E / "samples_d1.csv")
        gap = st.mean(float(r["P1_W"]) - float(r["V1"]) * float(r["I1_mA"]) / 1000.0
                      for r in rows)
        assert abs(gap) < 0.001                      # a milliwatt, on two watts

    def test_no_window_of_the_reported_rows_was_throttled(self) -> None:
        for reduced in ("energy_d1.csv", "energy_d1_baseline.csv"):
            manifest = json.loads((E2E / RUNS[reduced][0]).read_text())
            assert all(w["throttle_clean"] for w in manifest["windows"])
            assert {w["before"]["throttled"] for w in manifest["windows"]} == {"throttled=0x0"}
            assert {w["before"]["governor"] for w in manifest["windows"]} == {"performance"}


class TestTheDesignRunsManifest:
    """Its metadata were entered by hand, two of them wrongly, until 2026-10-09."""

    ORIGINAL = json.loads((E2E / "manifest_1785297440.json").read_text())
    USED = json.loads((E2E / "manifest_d1_reduced.json").read_text())

    def test_no_measured_value_differs_from_the_file_the_run_wrote(self) -> None:
        for wrote, used in zip(self.ORIGINAL["windows"], self.USED["windows"], strict=True):
            for key in ("rep", "n_ops", "checksum", "duration_s", "records", "throttle_clean",
                        "before", "after"):
                assert wrote[key] == used[key], key
        assert self.ORIGINAL["configuration"] == self.USED["configuration"]

    def test_the_run_wrote_no_metadata_and_the_file_says_who_added_it(self) -> None:
        assert "python" not in self.ORIGINAL and "run_utc" not in self.ORIGINAL
        note = self.USED["metadata_note"]
        assert "BY HAND" in note and "3.11.2" in note and "No measured value" in note

    def test_the_time_is_the_one_in_the_original_files_name(self) -> None:
        from datetime import UTC, datetime
        written = datetime.fromtimestamp(1785297440, UTC).strftime("%Y%m%dT%H%M%SZ")
        assert self.USED["run_utc"] == written == "20260729T035720Z"

    def test_the_interpreter_is_the_one_the_other_runs_recorded(self) -> None:
        others = {json.loads((E2E / RUNS[name][0]).read_text())["python"]
                  for name in RUNS if name != "energy_d1.csv"}
        assert others == {"3.12.13"} and self.USED["python"] == "3.12.13"


@pytest.fixture(scope="module")
def manifest_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The manifest of a two-repetition run of the board-side script, a fraction of a second."""
    import subprocess

    out = tmp_path_factory.mktemp("e2e")
    subprocess.run([sys.executable, str(REPO / "hw" / "validate_energy_e2e.py"),
                    "--seconds", "0.4", "--reps", "2", "--out", str(out)],
                   check=True, capture_output=True, timeout=120)
    (path,) = out.glob("manifest_*.json")
    return path


class TestTheBoardsScriptAndTheReducerSpeakOneLanguage:
    """July's first run wrote a manifest the reducer could not read, and it was completed by
    hand. Here the script that runs on the board is run for a second, its manifest is paired
    with a meter capture made up to hold a known power step, and the reducer must return the
    energy that step implies."""

    ADDED_W, IDLE_W = 0.750, 1.900

    def test_the_manifest_has_what_the_reducer_reads(self, manifest_path: Path) -> None:
        manifest = json.loads(manifest_path.read_text())
        assert [w["kind"] for w in manifest["windows"]] == ["idle", "load", "idle", "load"]
        for w in manifest["windows"]:
            assert {"op", "rep", "n_ops", "duration_s", "throttle_clean"} <= set(w)
            assert "undervoltage_events" in w["before"] and "undervoltage_events" in w["after"]
        for key in ("host", "run_utc", "platform", "python"):
            assert manifest[key], f"the run must record its own {key}"
        assert manifest["model_inputs"]["verify"] == "not run, not predicted"

    def test_a_known_power_step_reduces_to_the_energy_it_implies(self, manifest_path: Path,
                                                                 tmp_path: Path,
                                                                 capsys: pytest.CaptureFixture[str]
                                                                 ) -> None:
        manifest = json.loads(manifest_path.read_text())
        lines = ["ms,window,wtrans,V1,I1_mA,P1_W,V2,I2_mA,P2_W,host_utc"]
        ms = 0

        def emit(n: int, window: int, watts: float) -> None:
            nonlocal ms
            for _ in range(n):
                lines.append(f"{ms},{window},0,5.000,{200 * watts:.1f},{watts:.4f},"
                             f"5.2,400.0,2.0800,2026-01-01T00:00:00+00:00")
                ms += 20

        emit(50, 0, self.IDLE_W)
        for w in manifest["windows"]:
            watts = self.IDLE_W + (self.ADDED_W if w["kind"] == "load" else 0.0)
            emit(60, 1, watts)
            emit(50, 0, self.IDLE_W)
        samples = tmp_path / "samples.csv"
        samples.write_text("\n".join(lines) + "\n")
        capture.reduce(manifest_path, samples, 1, tmp_path / "energy.csv")
        capsys.readouterr()
        reduced = _rows(tmp_path / "energy.csv")
        loads = [w for w in manifest["windows"] if w["kind"] == "load"]
        assert len(reduced) == len(loads) == 2
        for row, w in zip(reduced, loads, strict=True):
            assert float(row["delta_p_w"]) == pytest.approx(self.ADDED_W, abs=1e-5)
            assert float(row["energy_per_op_j"]) == pytest.approx(
                self.ADDED_W * w["duration_s"] / w["n_ops"], rel=1e-9)


class TestTheRadiosPowerIsDescribedAsItWasMeasured:
    """0.218 W enters the modelled end-to-end energy. Until 2026-10-09 the thesis called it
    "that of the radio while it receives" and said nothing of how it was got."""

    def test_the_documents_say_what_the_record_says(self) -> None:
        import re

        record = (ENERGY / "p_radio_w.md").read_text()
        assert "channel 1, 2412 MHz" in record and "at 10.9.9.2" in record      # 2.4 GHz, unicast
        assert "2 reps" in record and "reps 0.231 / 0.205" in record
        method = re.sub(r"\s+", " ", (REPO / "thesis" / "ch06_methodology.tex").read_text())
        for needle in ("unicast stream arrived on the $2.4$\\,GHz band", "two repetitions",
                       "$0.205$ and $0.231$\\,W",
                       "It has not been measured in the configuration it is used for"):
            assert needle in method, needle
        paper = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text())
        assert "the radio's power coming from a unicast measurement on another band" in paper
