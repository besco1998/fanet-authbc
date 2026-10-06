"""What the 2026-10 artifacts say, held against the model and against the artifacts they extend.

`make verify-frozen` proves each CSV is what the current code produces. These tests prove what the
CSVs *mean*: that the new experiments reproduce every published number they overlap, and that the
statements the paper and thesis draw from them are in the data (docs/04 §2 E6–E13).

Each class is one review comment or audit finding answered.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"


def rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(
        ln for ln in (RAW / name).read_text(encoding="utf-8").splitlines()
        if not ln.startswith("#")))


LADDER = rows("design_ladder.csv")
LOSS = rows("e3_codec_loss.csv")
MATRIX = rows("exclusion_matrix.csv")


def rung(op: str, fmt: str, name: str) -> dict[str, str]:
    (hit,) = [r for r in LADDER if (r["op"], r["format"], r["rung"]) == (op, fmt, name)]
    return hit


# ------------------------------------------------------------------ E6
class TestFrameComponents:
    COMP = rows("frame_components.csv")

    def _one(self, **want: str) -> dict[str, str]:
        (hit,) = [r for r in self.COMP if all(r[k] == v for k, v in want.items())]
        return hit

    def test_integer_keys_take_the_header_from_44_to_23_bytes(self) -> None:
        at = "sender 40000 / one hour at 50 Hz"
        assert self._one(kind="header", format="first", item=at)["mean_bytes"] == "44"
        assert self._one(kind="header", format="lean", item=at)["mean_bytes"] == "23"

    def test_both_headers_are_a_range_six_bytes_wide(self) -> None:
        lo = "sender 0 / record 0"
        assert self._one(kind="header", format="first", item=lo)["mean_bytes"] == "38"
        assert self._one(kind="header", format="lean", item=lo)["mean_bytes"] == "17"

    @pytest.mark.parametrize(("fmt", "at_one_hour", "at_start"), [("first", 44, 38),
                                                                  ("lean", 23, 17)])
    def test_the_field_table_adds_up_to_the_header_at_both_ends_of_the_flight(
            self, fmt: str, at_one_hour: int, at_start: int) -> None:
        fields = [r for r in self.COMP if r["kind"] == "header_field" and r["format"] == fmt]
        assert [r["item"] for r in fields] == ["map", "v", "t", "src", "base_seq", "n", "recs",
                                               "auth"]
        assert sum(int(r["mean_bytes"]) for r in fields) == at_one_hour
        assert sum(int(r["min_bytes"]) for r in fields) == at_start
        grows = {r["item"] for r in fields if r["min_bytes"] != r["max_bytes"]}
        assert grows == {"src", "base_seq"}        # only the two integers that grow in flight

    def test_every_single_bit_flip_of_a_design_frame_is_refused(self) -> None:
        n = {r["item"]: int(r["n"]) for r in self.COMP if r["kind"] == "tamper"}
        assert n["flips"] == 1392 == n["undecodable"] + n["bad_signature"]
        assert n["accepted_altered"] == 0 == n["accepted_unchanged"]

    def test_every_delta_record_of_the_standard_protocol_has_one_size(self) -> None:
        """What the review called 'looks synthetic', stated as a fact about the generator."""
        for fmt, size in (("first", "44"), ("lean", "9")):
            r = self._one(kind="record", format=fmt, item="delta", stride="1")
            assert r["min_bytes"] == r["max_bytes"] == size

    def test_a_delta_measured_50_ms_apart_is_not_the_delta_of_a_slow_link(self) -> None:
        near = self._one(kind="record", format="lean", item="delta", stride="1")
        far = self._one(kind="record", format="lean", item="delta", stride="110")
        assert float(far["mean_bytes"]) / float(near["mean_bytes"]) > 1.5


# ------------------------------------------------------------------ E7 / F46
class TestVerifiabilityWithTheCodecInTheLoop:
    def _row(self, model: str, p: str, ref: str) -> dict[str, str]:
        (hit,) = [r for r in LOSS
                  if (r["loss_model"], r["p"], r["ref_interval"]) == (model, p, ref)]
        return hit

    def test_the_measurement_agrees_with_the_closed_form_wherever_it_can_test_it(self) -> None:
        tested = [r for r in LOSS if int(r["frames_lost"]) >= 5 and float(r["V_se"]) > 0]
        assert len(tested) >= 40
        for r in tested:
            z = (float(r["V_meas"]) - float(r["V_theory"])) / float(r["V_se"])
            assert abs(z) <= 3.0, f"{r['loss_model']} p={r['p']} R={r['ref_interval']}: z={z:.2f}"

    def test_self_contained_frames_lose_exactly_what_the_channel_loses(self) -> None:
        for r in LOSS:
            if r["ref_interval"] == "1":
                assert r["frames_desync"] == "0"
                assert float(r["V_meas"]) == pytest.approx(
                    1 - int(r["frames_lost"]) / int(r["frames_sent"]), abs=1e-5)

    def test_the_published_design_misses_its_own_target_at_its_own_loss_budget(self) -> None:
        """One keyframe per four frames at p = 0.05: 0.881 by the closed form, and the measured
        interval lies wholly below 0.95."""
        r = self._row("iid", "0.05", "4")
        assert float(r["V_theory"]) == pytest.approx(0.8811, abs=1e-4)
        assert float(r["V_ci_hi"]) < 0.95 and r["meets_target"] == "0"

    def test_at_the_design_loss_only_self_contained_frames_meet_the_target(self) -> None:
        for model in ("iid", "gilbert"):
            passing = {r["ref_interval"] for r in LOSS
                       if (r["loss_model"], r["p"], r["meets_target"]) == (model, "0.05", "1")}
            assert passing == {"1"}

    def test_a_looser_loss_admits_a_longer_interval(self) -> None:
        def longest(p: str) -> int:
            return max(int(r["ref_interval"]) for r in LOSS
                       if r["loss_model"] == "iid" and r["p"] == p and r["meets_target"] == "1")
        assert [longest(p) for p in ("0.02", "0.01", "0.00023")] == [4, 8, 16]

    def test_bursts_cost_a_dependent_design_less_than_independent_loss(self) -> None:
        for p in ("0.01", "0.02", "0.05", "0.1"):
            for ref in ("2", "4", "8", "16"):
                assert float(self._row("gilbert", p, ref)["V_theory"]) > \
                    float(self._row("iid", p, ref)["V_theory"])

    def test_what_a_longer_interval_buys_in_bytes_is_small(self) -> None:
        """43.25 B/record alone against 39.73 at sixteen frames: 3.5 B for a 30-point loss of V."""
        b = {r["ref_interval"]: float(r["bytes_per_rec"]) for r in LOSS
             if r["loss_model"] == "iid" and r["p"] == "0.05"}
        assert b["1"] == pytest.approx(43.25, abs=0.01)
        assert 3.4 < b["1"] - b["16"] < 3.6


# ------------------------------------------------------------------ E8 / review 2.1, 2.3, 2.4
class TestTheLadderReproducesWhatWasPublished:
    ENVELOPE = {r["binds"]: r for r in rows("capacity_envelope.csv") if r["n_local"] == "ENVELOPE"}
    E5 = {r["role"]: r for r in rows("e5_codesign.csv")}

    @pytest.mark.parametrize("op,label", [
        ("adopted", "A+CBOR Pillar-1 @3GPP100ms/50Hz"), ("relaxed", "A+CBOR Pillar-1 @250ms")])
    def test_the_baseline_rung_is_the_published_baseline(self, op: str, label: str) -> None:
        r, e = rung(op, "first", "inline-1"), self.ENVELOPE[label]
        assert (r["n_max_u_lt_1"], r["n_max_v95"]) == (e["n_max_u_lt_1"], e["n_max_v95_mean"])
        assert float(r["bytes_per_rec"]) == pytest.approx(float(self.E5["A+CBOR"]["bytes_per_rec"]))
        assert float(r["energy_uj"]) == pytest.approx(float(self.E5["A+CBOR"]["energy_uj"]),
                                                      abs=1e-3)

    @pytest.mark.parametrize("op,label", [
        ("adopted", "optimized delta/B @3GPP100ms/50Hz"), ("relaxed", "optimized delta/B @250ms")])
    def test_the_published_design_rung_is_the_published_design(self, op: str, label: str) -> None:
        r, e = rung(op, "first", "batch-delta-published"), self.ENVELOPE[label]
        assert (r["n_max_u_lt_1"], r["n_max_v95"]) == (e["n_max_u_lt_1"], e["n_max_v95_mean"])
        # 72.0 B/record: the published mean has 63 keyframes per 1000 records, the model 62.5
        assert float(r["bytes_per_rec"]) == pytest.approx(
            float(self.E5["optimized"]["bytes_per_rec"]), abs=0.01)
        assert float(r["energy_uj"]) == pytest.approx(float(self.E5["optimized"]["energy_uj"]),
                                                      abs=0.01)

    def test_and_shows_that_design_did_not_meet_v(self) -> None:
        r = rung("adopted", "first", "batch-delta-published")
        assert (r["V"], r["meets_v"], r["ref_interval"]) == ("0.8811", "0", "4")


class TestTheDesignAtTheAdoptedPoint:
    def test_the_headline_table_is_at_the_point_the_abstract_names(self) -> None:
        """Review 2.1: 50 records/s and 100 ms, where four records take 80 ms to fill."""
        for fmt in ("first", "lean"):
            r = rung("adopted", fmt, "batch-delta")
            assert (r["lambda_rec_per_s"], r["d_max_ms"], r["batch"]) == ("50", "100.0", "4")
            assert 80.0 < float(r["latency_ms"]) < 81.0 and r["meets_d_max"] == "1"
            assert rung("adopted", fmt, "inline-1")["latency_ms"].startswith("20.")

    def test_bytes_per_record_and_the_saving_in_each_format(self) -> None:
        first = float(rung("adopted", "first", "batch-delta")["bytes_per_rec"])
        lean = float(rung("adopted", "lean", "batch-delta")["bytes_per_rec"])
        assert (first, lean) == (74.963, 43.25)
        base_first = float(rung("adopted", "first", "inline-1")["bytes_per_rec"])
        base_lean = float(rung("adopted", "lean", "inline-1")["bytes_per_rec"])
        assert 100 * (1 - first / base_first) == pytest.approx(56.98, abs=0.01)
        assert 100 * (1 - lean / base_lean) == pytest.approx(70.33, abs=0.01)

    def test_every_rung_but_the_published_one_decodes_frame_by_frame(self) -> None:
        for r in LADDER:
            if r["rung"] not in ("batch-delta-published", "SEARCH_OPTIMUM"):
                assert (r["V"], r["meets_v"], r["ref_interval"]) == ("0.95", "1", "1")

    def test_an_exhaustive_search_returns_the_reported_design(self) -> None:
        for op in ("adopted", "relaxed"):
            for fmt in ("first", "lean"):
                best, design = rung(op, fmt, "SEARCH_OPTIMUM"), rung(op, fmt, "batch-delta")
                assert (best["placement"], best["batch"], best["ref_interval"]) == ("B", "4", "1")
                assert float(best["bytes_per_rec"]) == pytest.approx(
                    float(design["bytes_per_rec"]), abs=0.01)

    def test_lean_sizes_are_emitted_frames_and_first_format_sizes_a_byte_model(self) -> None:
        assert rung("adopted", "lean", "batch-delta")["sized_from"] == "emitted frames"
        assert rung("adopted", "lean", "inline-1")["sized_from"] == "emitted frames"
        assert rung("adopted", "first", "batch-delta")["sized_from"] == "byte model"

    def test_certificates_add_a_fifth_of_a_certificate_and_four_fifths_of_a_digest_per_frame(
            self) -> None:
        per_frame = (162 + 4 * 8) / 5
        for r in LADDER:
            if r["rung"] != "SEARCH_OPTIMUM":
                assert float(r["bytes_per_rec_with_cert"]) == pytest.approx(
                    (float(r["frame_bytes"]) + per_frame) / int(r["batch"]), abs=1e-3)


class TestCapacityIsSeparatedByCause:
    """Review 2.4a and 2.4b: the gain, one step at a time."""

    ORDER = ("inline-1", "inline-b", "batch-cbor", "batch-delta")

    def test_each_step_of_the_first_format_adds_neighbours_at_both_thresholds(self) -> None:
        for op in ("adopted", "relaxed"):
            for col in ("n_max_u_lt_1", "n_max_v95"):
                ns = [int(rung(op, "first", r)[col]) for r in self.ORDER]
                assert ns == sorted(ns) and len(set(ns)) == 4

    def test_the_three_steps_at_the_adopted_point(self) -> None:
        ns = [int(rung("adopted", "first", r)["n_max_v95"]) for r in self.ORDER]
        assert ns == [31, 49, 79, 97]

    def test_sharing_a_frame_is_not_most_of_the_gain(self) -> None:
        """The review expected 'mostly fewer frames'. Amortising the signature is as large."""
        ns = [int(rung("adopted", "first", r)["n_max_v95"]) for r in self.ORDER]
        share, sign, delta = ns[1] / ns[0], ns[2] / ns[1], ns[3] / ns[2]
        assert share == pytest.approx(1.58, abs=0.01) and sign == pytest.approx(1.61, abs=0.01)
        assert delta == pytest.approx(1.23, abs=0.01)

    @pytest.mark.parametrize("fmt,lo,hi", [("first", 1.89, 3.13), ("lean", 2.60, 4.18)])
    def test_the_advantage_over_one_record_per_frame_is_a_range(self, fmt: str, lo: float,
                                                               hi: float) -> None:
        ratios = [int(rung(op, fmt, "batch-delta")[c]) / int(rung(op, fmt, "inline-1")[c])
                  for op in ("adopted", "relaxed") for c in ("n_max_u_lt_1", "n_max_v95")]
        assert min(ratios) == pytest.approx(lo, abs=0.01)
        assert max(ratios) == pytest.approx(hi, abs=0.01)

    def test_against_inline_signing_that_already_shares_a_frame_it_is_at_most_twofold(
            self) -> None:
        ratios = [int(rung(op, "first", "batch-delta")[c]) / int(rung(op, "first", "inline-b")[c])
                  for op in ("adopted", "relaxed") for c in ("n_max_u_lt_1", "n_max_v95")]
        assert min(ratios) == pytest.approx(1.42, abs=0.01)
        assert max(ratios) == pytest.approx(1.98, abs=0.01)


class TestReceiverCpu:
    """Review 2.4c: a receiver verifies the whole neighbourhood."""

    def test_the_design_uses_about_a_third_to_a_half_of_one_core_at_its_limit(self) -> None:
        assert float(rung("adopted", "first", "batch-delta")["cpu_pct_at_n_v95"]) == \
            pytest.approx(32.46, abs=0.01)
        assert float(rung("adopted", "lean", "batch-delta")["cpu_pct_at_n_v95"]) == \
            pytest.approx(47.67, abs=0.01)

    def test_one_core_serves_296_batched_neighbours_and_77_inline_ones(self) -> None:
        assert rung("adopted", "first", "batch-delta")["n_cpu_one_core"] == "296"
        assert rung("adopted", "first", "inline-1")["n_cpu_one_core"] == "77"

    def test_the_cpu_binds_in_exactly_one_row(self) -> None:
        bound = [(r["op"], r["format"], r["rung"]) for r in LADDER
                 if r.get("binds_at_v95") == "cpu"]
        assert bound == [("adopted", "lean", "inline-b")]
        r = rung("adopted", "lean", "inline-b")
        assert (r["n_max_v95"], r["n_cpu_one_core"], r["n_feasible_v95"]) == ("80", "77", "77")

    def test_no_published_row_changes(self) -> None:
        for op in ("adopted", "relaxed"):
            for name in ("inline-1", "batch-delta-published"):
                r = rung(op, "first", name)
                assert r["binds_at_v95"] == "channel" and r["n_feasible_v95"] == r["n_max_v95"]


# ------------------------------------------------------------------ E9 / F47, review 2.2
class TestExclusionOverAllTwelveDataRates:
    def _cell(self, dr: int, auth: int, design: str) -> dict[str, str]:
        (hit,) = [r for r in MATRIX if (r["dr"], r["auth_bytes"], r["design"]) ==
                  (str(dr), str(auth), design)]
        return hit

    def test_there_are_twelve_data_rates_not_seven(self) -> None:
        assert sorted({int(r["dr"]) for r in MATRIX}) == list(range(12))

    def test_a_64_byte_signature_alone_overflows_five_of_them(self) -> None:
        over = sorted(int(r["dr"]) for r in MATRIX if r["design"] == "lean"
                      and r["auth_bytes"] == "64" and r["signature_alone_overflows"] == "1")
        assert over == [0, 1, 2, 8, 10]

    @pytest.mark.parametrize("design", ["first", "lean"])
    def test_eight_cannot_carry_one_self_contained_chained_signed_frame(self, design: str) -> None:
        verdicts = {int(r["dr"]): r["verdict"] for r in MATRIX
                    if r["design"] == design and r["auth_bytes"] == "64"}
        excluded = sorted(d for d, v in verdicts.items() if v == "excluded")
        assert excluded == [0, 1, 2, 3, 8, 9, 10, 11]
        assert sorted(d for d, v in verdicts.items() if v == "feasible") == [4, 5, 6, 7]

    def test_dr3_is_excluded_under_the_lean_header_whatever_the_telemetry(self) -> None:
        """The abstract said an integer-keyed header rescues DR3. It does not (audit F47).

        Even a frame of zeros from node 0 is 124 B: no content fits a 115 B payload.
        """
        cell = self._cell(3, 64, "lean")
        assert cell["verdict"] == "excluded"
        assert int(cell["frame_floor_bytes"]) == 124 > 115
        assert int(cell["frame_min_bytes"]) == 134

    def test_the_64_byte_exclusions_never_rest_on_the_generator(self) -> None:
        """Every one is against the format's floor, so different telemetry cannot undo it."""
        for r in MATRIX:
            if r["auth_bytes"] == "64" and r["design"] in ("first", "lean") \
                    and r["verdict"] != "feasible":
                assert r["verdict"] == "excluded"
                assert int(r["frame_floor_bytes"]) > int(r["payload_not_repeater"])

    def test_it_fits_only_if_the_chain_link_is_taken_off_the_air(self) -> None:
        cell = self._cell(3, 64, "lean without on-air chain link")
        assert cell["verdict"] == "feasible" and int(cell["frame_max_bytes"]) == 112

    def test_a_48_byte_signature_misses_the_115_byte_rates_by_three_bytes(self) -> None:
        """⚠️ Not an exclusion, and not to be counted as one.

        A frame of zeros would fit (108 B); this telemetry's smallest frame is 118 B. Three bytes
        is inside what a format change or a different payload could recover, so the verdict says
        which of the two it is.
        """
        for dr in (3, 9, 11):
            cell = self._cell(dr, 48, "lean")
            assert cell["verdict"] == "excluded for this telemetry"
            floor, smallest = int(cell["frame_floor_bytes"]), int(cell["frame_min_bytes"])
            assert (floor, smallest) == (108, 118) and floor <= 115 < smallest
        for dr in (0, 1, 2, 8, 10):
            cell = self._cell(dr, 48, "lean")
            assert cell["verdict"] == "excluded" and cell["signature_alone_overflows"] == "0"

    def test_a_chained_frame_does_not_fit_51_bytes_under_any_authenticator(self) -> None:
        """Header and chain link alone are 51-58 B: even a 13 B tag leaves no room for a record."""
        for dr in (0, 1, 2, 8, 10):
            cell = self._cell(dr, 13, "lean")
            assert cell["verdict"] == "excluded" and int(cell["frame_floor_bytes"]) == 72

    def test_a_symmetric_tag_fits_the_115_byte_rates(self) -> None:
        assert self._cell(3, 13, "lean")["verdict"] == "feasible"
        assert self._cell(3, 13, "first")["verdict"] == "marginal"

    def test_the_repeater_table_changes_no_verdict(self) -> None:
        assert all(r["verdict"] == r["verdict_repeater"] for r in MATRIX)


# ------------------------------------------------------------------ E10 / review 4.9
class TestFreshnessBudget:
    BUDGET = rows("freshness_budget.csv")

    def _row(self, op: str, scheme: str, stat: str) -> dict[str, str]:
        (hit,) = [r for r in self.BUDGET if (r["op"], r["scheme"], r["channel_stat"]) ==
                  (op, scheme, stat)]
        return hit

    def test_the_worst_measured_case_leaves_sixteen_milliseconds(self) -> None:
        r = self._row("adopted", "ed25519", "delay_max_ms")
        assert (r["fill_ms"], r["channel_ms"], r["verify_ms"]) == ("80.0", "3.4907", "0.2595")
        assert (r["total_ms"], r["margin_ms"], r["meets_d_max"]) == ("83.75", "16.25", "1")

    def test_verification_is_a_third_of_a_percent_of_the_budget_for_ed25519(self) -> None:
        assert float(self._row("adopted", "ed25519", "delay_mean_ms")["verify_ms"]) < 0.3

    def test_bls_spends_nearly_nine_milliseconds_of_it(self) -> None:
        r = self._row("adopted", "bls", "delay_max_ms")
        assert float(r["verify_ms"]) == pytest.approx(8.61, abs=0.01) and float(r["margin_ms"]) < 8

    def test_the_channel_term_is_the_most_loaded_point_under_the_measured_ceiling(self) -> None:
        assert {r["channel_util_measured_at"] for r in self.BUDGET} == {"2.2299"}


# ------------------------------------------------------------------ E11 / F48
class TestLoraBudget:
    LORA = rows("lora_budget.csv")
    CODESIGN = rows("lora_codesign.csv")

    def _row(self, dr: int, table: str, design_prefix: str) -> dict[str, str]:
        (hit,) = [r for r in self.LORA if r["dr"] == str(dr) and r["payload_table"] == table
                  and r["design"].startswith(design_prefix)]
        return hit

    def test_the_published_row_reproduces_the_frozen_lora_artifact(self) -> None:
        pub = self._row(5, "not repeater compatible", "first; link per frame; AS PUBLISHED")
        (frozen,) = [r for r in self.CODESIGN if (r["dr"], r["placement"], r["chain_mode"],
                                                 r["scheme"], r["on_pareto"]) ==
                     ("5", "B", "per_frame", "ed25519", "1") and r["batch"] == "7"]
        assert (pub["batch"], float(pub["frame_bytes"])) == ("7", float(frozen["frame_bytes"]))
        assert float(pub["lambda_rec_per_s"]) == pytest.approx(float(frozen["lambda_rec_per_s"]),
                                                              abs=1e-4)

    def test_corrected_the_first_format_carries_five_records_not_seven(self) -> None:
        fixed = self._row(5, "not repeater compatible", "first; link per frame; frames decode")
        assert fixed["batch"] == "5" and float(fixed["lambda_rec_per_s"]) == pytest.approx(0.1267)
        assert 17.0 < float(fixed["delta_bytes"]) < 19.0        # not the 13 B measured at 50 ms

    def test_the_lean_format_carries_eight(self) -> None:
        lean = self._row(5, "not repeater compatible", "lean")
        assert lean["batch"] == "8" and float(lean["lambda_rec_per_s"]) == pytest.approx(0.2002)

    def test_each_delta_is_measured_near_the_spacing_the_batch_implies(self) -> None:
        for r in self.LORA:
            if "AS PUBLISHED" not in r["design"]:
                spacing, measured = float(r["record_spacing_s"]), float(r["delta_measured_at_s"])
                assert abs(measured - spacing) / spacing < 0.25, r["design"]

    def test_every_corrected_frame_fits_its_payload_limit(self) -> None:
        for r in self.LORA:
            assert float(r["frame_bytes"]) <= int(r["payload_limit"])


# ------------------------------------------------------------------ E12 / review 4.7
class TestPhySweep:
    PHY = rows("phy_sweep.csv")

    def test_only_the_simulated_phy_is_marked_validated(self) -> None:
        assert {(r["channel"], r["rate_mbps"]) for r in self.PHY if r["validated"] == "1"} == \
            {("20MHz", "6")}

    def test_the_validated_rows_equal_the_ladder(self) -> None:
        for fmt in ("first", "lean"):
            (r,) = [x for x in self.PHY if (x["channel"], x["rate_mbps"], x["format"]) ==
                    ("20MHz", "6", fmt)]
            assert r["n_max_baseline"] == rung("adopted", fmt, "inline-1")["n_max_u_lt_1"]
            assert r["n_max_design"] == rung("adopted", fmt, "batch-delta")["n_max_u_lt_1"]

    def test_the_slowest_rate_of_each_channel_is_the_least_favourable_to_the_design(self) -> None:
        for width in ("20MHz", "10MHz"):
            for fmt in ("first", "lean"):
                series = sorted((float(r["rate_mbps"]), float(r["ratio"])) for r in self.PHY
                                if r["channel"] == width and r["format"] == fmt)
                ratios = [x for _, x in series]
                assert ratios == sorted(ratios)

    def test_fixed_cost_is_two_fifths_of_the_baseline_frame_at_the_validated_phy(self) -> None:
        (r,) = [x for x in self.PHY if (x["channel"], x["rate_mbps"], x["format"]) ==
                ("20MHz", "6", "first")]
        assert (r["fixed_cost_us"], r["fixed_share_of_baseline_pct"]) == ("173.17", "42.3")


# ------------------------------------------------------------------ E13 / review 4.1
class TestEnergyTable:
    ENERGY = {r["configuration"].split(":")[0]: r for r in rows("energy_table.csv")}

    def test_the_metered_sender_energy_of_design_and_baseline(self) -> None:
        d, b = self.ENERGY["design"], self.ENERGY["baseline"]
        assert (d["sender_uj_per_rec_median"], d["sender_uj_per_rec_min"],
                d["sender_uj_per_rec_max"]) == ("58.383", "58.102", "59.339")
        assert b["sender_uj_per_rec_median"] == "118.825"
        assert d["reps_clean"] == b["reps_clean"] == "5"

    def test_the_model_is_low_by_the_documented_seven_to_fourteen_percent(self) -> None:
        for r in self.ENERGY.values():
            assert 7.0 <= float(r["sender_residual_pct"]) <= 14.5

    def test_the_configuration_with_a_contaminated_idle_baseline_is_not_reported(self) -> None:
        naive = self.ENERGY["naive"]
        assert (naive["reps_metered"], naive["reps_clean"], naive["reportable"]) == ("5", "2", "0")
        assert all(r["reportable"] == "1" for k, r in self.ENERGY.items() if k != "naive")

    def test_the_end_to_end_figures_are_the_frozen_e5_ones(self) -> None:
        e5 = {r["role"]: r["energy_uj"] for r in rows("e5_codesign.csv")}
        assert float(self.ENERGY["design"]["end_to_end_model_uj_per_rec"]) == float(e5["optimized"])
        assert float(self.ENERGY["baseline"]["end_to_end_model_uj_per_rec"]) == float(e5["A+CBOR"])
