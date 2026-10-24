"""Record sizes on real flight logs: the artifact, its manifest, and the rule (review 3; D8).

The measurement needs the network, and is not repeated here. What is held:

* the selection rule and the handling of invalid samples, on inputs small enough to read;
* that the artifact is internally consistent and covers exactly the logs the manifest pins;
* that the generator rows, produced by the same sizing code, reproduce the numbers the paper's
  tables already use — so a difference between a real row and a generator row is a difference
  in telemetry, not in arithmetic;
* the outcome of the prediction committed in `docs/PX4_LOGS_EXPECTATIONS.md`.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from statistics import mean

import numpy as np
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"

_spec = importlib.util.spec_from_file_location("px4_log_sizes",
                                               REPO / "analysis" / "px4_log_sizes.py")
assert _spec and _spec.loader
px4 = importlib.util.module_from_spec(_spec)
sys.modules["px4_log_sizes"] = px4
_spec.loader.exec_module(px4)

MANIFEST = yaml.safe_load(px4.MANIFEST.read_text())
ROWS = list(csv.DictReader(ln for ln in px4.OUT.read_text().splitlines()
                           if not ln.startswith("#")))
LOGS = [r for r in ROWS if r["row"] == "log"]
REAL = {int(r["spacing_ms"]): r for r in ROWS if r["row"] == "real logs"}
GEN = {int(r["spacing_ms"]): r for r in ROWS if r["row"] == "generator"}


def _entry(**over: object) -> dict:
    base = {"duration_s": 600, "num_logged_errors": 0, "ver_sw_release": "v1.15.2 255",
            "sys_hw": "PX4_FMU_V6X", "vehicle_uuid": "abc"}
    return {**base, **over}


class TestTheSelectionRule:
    def test_a_plain_flight_is_eligible(self) -> None:
        assert px4.eligible(_entry())

    @pytest.mark.parametrize("over", [
        {"duration_s": 299}, {"duration_s": 901}, {"num_logged_errors": 1},
        {"ver_sw_release": "v1.13.3 255"}, {"ver_sw_release": "v1.18.0 64"},
        {"sys_hw": "PX4_SITL"}, {"vehicle_uuid": ""}, {"ver_sw_release": None},
    ])
    def test_each_clause_excludes(self, over: dict) -> None:
        assert not px4.eligible(_entry(**over))

    def test_twelve_logs_in_the_registered_strata_first_by_id(self) -> None:
        logs = MANIFEST["logs"]
        assert len(logs) == 12 and len({log["sha256"] for log in logs}) == 12
        for stratum, (types, want) in px4.STRATA.items():
            mine = [log for log in logs if log["stratum"] == stratum]
            assert len(mine) == want and all(log["mav_type"] in types for log in mine)
            assert [log["log_id"] for log in mine] == sorted(log["log_id"] for log in mine)

    def test_every_skip_has_a_reason_and_sorts_before_what_replaced_it(self) -> None:
        last = {s: max(log["log_id"] for log in MANIFEST["logs"] if log["stratum"] == s)
                for s in px4.STRATA}
        assert MANIFEST["skipped"]
        for skip in MANIFEST["skipped"]:
            assert skip["reason"] and skip["log_id"] < last[skip["stratum"]]


def _topics(n: int = 400, *, battery: np.ndarray | None = None,
            landed: np.ndarray | None = None) -> dict[str, dict[str, np.ndarray]]:
    """Synthetic topics: 80 s at 5 Hz, moving north at 5 m/s."""
    t = np.arange(n, dtype=np.int64) * 200_000 + 10_000_000
    one = np.ones(n)
    return {
        "vehicle_global_position": {"timestamp": t, "lat": 47.0 + np.arange(n) * 9e-6,
                                    "lon": 8.0 * one, "alt": 500.0 * one},
        "vehicle_local_position": {"timestamp": t, "vx": 5.0 * one, "vy": 0.0 * one,
                                   "vz": 0.0 * one},
        "battery_status": {"timestamp": t, "remaining": 0.8 * one if battery is None else battery},
        "vehicle_status": {"timestamp": t, "nav_state": (14 * one).astype(np.int64)},
        "vehicle_land_detected": {"timestamp": t, "landed": np.zeros(n, dtype=np.uint8)
                                  if landed is None else landed},
    }


class TestRecordsFromALog:
    def test_units_are_the_generators(self) -> None:
        (run,) = px4.flight_runs(_topics(), 200)
        ts, lat, lon, alt, vx, vy, vz, battery, mode = run[0]
        assert (ts, lat, lon, alt) == (10_000, 470_000_000, 80_000_000, 50_000)
        assert (vx, vy, vz, battery, mode) == (500, 0, 0, 80, 14 % 8)
        assert run[1][0] - ts == 200 and run[1][1] - lat == 90      # 9e-6 deg is 90 units

    def test_a_landing_splits_the_flight_and_no_difference_spans_it(self) -> None:
        landed = np.zeros(400, dtype=np.uint8)
        landed[200:230] = 1
        runs = px4.flight_runs(_topics(landed=landed), 200)
        # 399 grid points, not 400: the grid stops before the log's last sample
        assert [len(r) for r in runs] == [200, 169]

    def test_an_invalid_sample_ends_the_run_as_a_landing_does(self) -> None:
        """A NaN cast to an integer is garbage: it would have been sized as a ten-byte field."""
        battery = np.full(400, 0.8)
        battery[100:110] = np.nan
        runs = px4.flight_runs(_topics(battery=battery), 200)
        assert [len(r) for r in runs] == [100, 289]
        assert all(0 <= row[7] <= 100 for run in runs for row in run)

    def test_under_a_minute_of_flight_is_not_a_measurement(self) -> None:
        assert px4.flight_runs(_topics(n=250), 200) == []          # 50 s

    def test_sizes_by_hand(self) -> None:
        """Δts = 200 → 2 B; Δlat = 90 → 2 B; the other seven differences are zero → 1 B each."""
        s = px4.sizes(px4.flight_runs(_topics(), 200))
        assert set(s["lean_delta"]) == {2 + 2 + 7}
        # ts 10 000 → 2 B; lat, lon 5 B and 4 B; alt 50 000 → 3 B; vx 500 → 2 B; five more at 1 B
        assert s["lean_key"][0] == 2 + 5 + 4 + 3 + 2 + 1 + 1 + 1 + 1


class TestTheArtifact:
    def test_it_covers_exactly_the_pinned_logs_at_every_spacing(self) -> None:
        want = {(log["log_id"], str(ms)) for log in MANIFEST["logs"] for ms in px4.SPACINGS_MS}
        assert {(r["log_id"], r["spacing_ms"]) for r in LOGS} == want

    def test_nothing_is_measured_finer_than_the_logs_own_position_rate(self) -> None:
        """Sampling 5 Hz position at 20 Hz would manufacture zero differences."""
        for r in LOGS:
            native = float(r["native_period_ms"])
            assert 195.0 <= native <= 205.0
            assert (r["measured"] == "1") == (int(r["spacing_ms"]) >= 200)
        assert sorted(REAL) == [200, 1000, 5500]

    @pytest.mark.parametrize("spacing", [200, 1000, 5500])
    def test_each_log_counts_once_in_the_pooled_row(self, spacing: int) -> None:
        got = [r for r in LOGS if r["spacing_ms"] == str(spacing)]
        assert len(got) == 12 == int(REAL[spacing]["measured"])
        for column in ("lean_delta_mean", "lean_key_mean", "bytes_per_rec", "saving_pct"):
            assert float(REAL[spacing][column]) == pytest.approx(
                mean(float(r[column]) for r in got), abs=6e-4)

    def test_no_delta_is_under_the_formats_floor(self) -> None:
        """Nine fields at one byte each, and two for a timestamp step of 200 ms or more."""
        assert all(int(r["lean_delta_min"]) >= 10 for r in LOGS if r["measured"] == "1")


class TestTheGeneratorRowsAreTheTablesNumbers:
    """Same sizing code, generator input: these must be the figures already published."""

    def test_at_the_standard_protocol(self) -> None:
        g = GEN[50]
        assert (g["lean_delta_mean"], g["frame_b_mean"], g["frame_1_mean"]) == (
            "9", "172.999", "145.765")
        assert g["bytes_per_rec"] == "43.25" and g["saving_pct"] == "70.33"

    def test_at_the_spacings_frame_components_also_measures(self) -> None:
        comp = {(r["format"], r["item"], r["stride"]): r for r in csv.DictReader(
            ln for ln in (RAW / "frame_components.csv").read_text().splitlines()
            if not ln.startswith("#")) if r["kind"] == "record"}
        for spacing, stride in ((100, "2"), (1000, "20"), (5500, "110")):
            assert float(GEN[spacing]["lean_delta_mean"]) == float(
                comp[("lean", "delta", stride)]["mean_bytes"])
            assert float(GEN[spacing]["first_delta_mean"]) == float(
                comp[("first", "delta", stride)]["mean_bytes"])


class TestTheRegisteredPrediction:
    def test_the_amended_load_bearing_prediction_holds_at_0_2_s(self) -> None:
        delta, saving = float(REAL[200]["lean_delta_mean"]), float(REAL[200]["saving_pct"])
        assert delta == pytest.approx(11.055) and delta <= 13.0
        assert saving == pytest.approx(69.077) and saving >= 68.0

    def test_the_generator_is_within_a_quarter_byte_at_every_matched_spacing(self) -> None:
        for spacing in (200, 1000, 5500):
            gap = float(REAL[spacing]["lean_delta_mean"]) - float(GEN[spacing]["lean_delta_mean"])
            assert abs(gap) < 0.25

    def test_fast_vehicles_sit_above_the_mean_and_one_is_over_13_bytes(self) -> None:
        """⚠️ The mean is not the whole answer; kept as a test so it is not quoted as one."""
        at = {r["log_id"]: float(r["lean_delta_mean"]) for r in LOGS if r["spacing_ms"] == "200"}
        fixed = [at[log["log_id"]] for log in MANIFEST["logs"] if log["stratum"] == "fixed wing"]
        rest = [at[log["log_id"]] for log in MANIFEST["logs"] if log["stratum"] != "fixed wing"]
        assert min(fixed) > max(rest)
        assert max(fixed) == pytest.approx(13.205) and max(fixed) > 13.0

    def test_the_real_keyframe_is_two_bytes_under_the_generators(self) -> None:
        """Predicted 22-25 B; measured 21.98 — recorded as a miss by 0.02 B, not rounded away."""
        real = float(REAL[200]["lean_key_mean"])
        assert real == pytest.approx(21.98) and real < 22.0
        assert float(GEN[200]["lean_key_mean"]) - real > 2.0
