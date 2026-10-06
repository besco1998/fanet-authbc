"""Unit tests of the frame-level experiment runners (docs/04 §2 E6–E13).

The full runs are held byte-identical to their artifacts by the frozen gate
(`tests/integration/test_frozen_reproducibility.py`) and the artifacts' scientific content by
`tests/test_frame_artifacts.py`. These test the pieces, on inputs small enough to check by hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from authbc.bench import frame_experiments as fx
from authbc.bench.experiments import all_runners, load_config
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record
from authbc.models import frame as frame_model
from authbc.placement import wire_v2


class TestLossProcesses:
    def test_independent_loss_has_the_requested_rate(self) -> None:
        lost = fx._loss_mask(np.random.default_rng(1), 200_000, 0.05, "iid", 4.0)
        assert lost.mean() == pytest.approx(0.05, abs=0.002)

    def test_burst_loss_has_the_same_mean_rate_and_the_requested_burst_length(self) -> None:
        lost = fx._loss_mask(np.random.default_rng(1), 400_000, 0.05, "gilbert", 4.0)
        assert lost.mean() == pytest.approx(0.05, abs=0.003)
        edges = np.flatnonzero(np.diff(lost.astype(int)) == 1).size      # bursts that start
        assert lost.sum() / edges == pytest.approx(4.0, abs=0.15)

    def test_an_unknown_model_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown loss model"):
            fx._loss_mask(np.random.default_rng(1), 10, 0.05, "pareto", 4.0)

    def test_the_closed_forms_are_the_frame_models(self) -> None:
        assert fx._theory("iid", 0.05, 4, 4.0) == frame_model.verifiability(0.05, 4)
        assert fx._theory("gilbert", 0.05, 4, 4.0) == frame_model.verifiability_gilbert(
            0.05, 4.0, 4)


class TestTheLossExperimentOnASmallStream:
    CFG = {"batch": 4, "frames_per_seed": 32, "seeds": [1, 2], "epsilon": 0.05,
           "ref_intervals": [1, 4], "loss_models": ["iid"], "p_values": [0.0, 0.25],
           "mean_burst_frames": 4.0, "base_seed": 7}

    def test_without_loss_every_record_is_verified_at_any_interval(self) -> None:
        rows = [r for r in fx.run_loss_codec(self.CFG) if r["p"] == 0.0]
        assert [r["V_meas"] for r in rows] == [1.0, 1.0]
        assert all(r["frames_lost"] == 0 and r["frames_desync"] == 0 for r in rows)

    def test_a_lost_frame_costs_more_when_frames_depend_on_each_other(self) -> None:
        alone, grouped = (r for r in fx.run_loss_codec(self.CFG) if r["p"] == 0.25)
        assert alone["ref_interval"] == 1 and alone["frames_desync"] == 0
        # the artifact rounds V to five places, hence the 1e-5
        assert alone["V_meas"] == pytest.approx(
            1.0 - alone["frames_lost"] / alone["frames_sent"], abs=1e-5)
        assert grouped["frames_desync"] > 0
        assert grouped["V_meas"] == pytest.approx(
            1.0 - (grouped["frames_lost"] + grouped["frames_desync"]) / grouped["frames_sent"],
            abs=1e-5)

    def test_it_is_deterministic(self) -> None:
        assert fx.run_loss_codec(self.CFG) == fx.run_loss_codec(self.CFG)


class TestCapacityAndCpuHelpers:
    def test_n_max_reproduces_the_published_envelope(self) -> None:
        assert fx.n_max(50, 4, 288.0, 1.0, 400) == 35
        assert fx.n_max(50, 4, 288.0, 2.435, 400) == 100
        assert fx.n_max(50, 1, 174.252, 2.435, 400) == 31

    def test_n_max_is_zero_when_two_nodes_already_overflow(self) -> None:
        assert fx.n_max(5000, 1, 1400.0, 1.0, 50) == 0

    def test_cpu_demand_of_one_neighbour_by_hand(self) -> None:
        """12.5 frames/s × 259.5 µs + 50 records/s × 2.75 µs = 3.381 ms of CPU per second."""
        per = fx.cpu_seconds_per_neighbour(50, 4, 1, 259.5e-6, 2.75e-6)
        assert per == pytest.approx(3.381e-3, abs=1e-6)
        # signing every record quadruples the verifications, not the hashes
        assert fx.cpu_seconds_per_neighbour(50, 4, 4, 259.5e-6, 2.75e-6) == pytest.approx(
            4 * 12.5 * 259.5e-6 + 50 * 2.75e-6)

    def test_the_freshness_rule_stops_at_four_records_at_both_operating_points(self) -> None:
        """Five records fill in exactly D_max, so any airtime at all rejects them."""
        frame_of = lambda b: 100.0 + 45.0 * b                                    # noqa: E731
        assert fx._freshness_batch(50, 0.100, frame_of) == 4
        assert fx._freshness_batch(20, 0.250, frame_of) == 4
        assert fx._freshness_batch(10, 0.100, frame_of) == 1

    def test_latency_is_fill_time_plus_airtime(self) -> None:
        assert fx._latency_s(50, 4, 288.0) == pytest.approx(0.080 + 490e-6, abs=5e-6)


class TestVerdicts:
    def test_the_four_grades(self) -> None:
        """Arguments: the format's floor, the measured smallest and largest frame, the limit."""
        assert fx._verdict(124, 134, 147, 115) == "excluded"
        assert fx._verdict(108, 118, 131, 115) == "excluded for this telemetry"
        assert fx._verdict(94, 106, 117, 115) == "marginal"
        assert fx._verdict(89, 99, 112, 115) == "feasible"
        assert fx._verdict(115, 115, 115, 115) == "feasible"       # meeting the limit fits


class TestTheFloorIsAnEmittedFrame:
    """Exclusion is claimed against the smallest frame a format can emit, so that frame is built."""

    def _zero_record(self) -> Record:
        return Record(src=0, seq=0, ts=0, prev_hash=bytes(32),
                      pl=dict.fromkeys(wire_v2.PAYLOAD_FIELDS, 0))

    def test_the_lean_floor_is_the_length_of_a_signed_frame_of_zeros(self) -> None:
        sk, pk = Ed25519Scheme().keygen(seed=bytes(32))
        frame = wire_v2.build_B_v2([self._zero_record()], sk)
        data = wire_v2.encode_frame_v2(frame)
        assert wire_v2.verify_v2(wire_v2.decode_frame_v2(data), pk)
        assert len(data) == fx._floor_frames(64)["lean"] == 124

    def test_by_hand(self) -> None:
        """map 1 + 8 keys + v, t, src, base_seq, n at one byte each = 14; link 2 + 32;
        nine one-byte varints behind a one-byte prefix = 10; signature 2 + 64."""
        assert 14 + 34 + 10 + 66 == 124

    def test_no_record_of_the_generator_is_smaller_than_the_floor(self) -> None:
        for sig in (64, 48, 13):
            floors, (lo, _) = fx._floor_frames(sig), fx._lean_one_record_range(sig)
            assert floors["lean"] < lo
            assert floors["lean"] - floors["lean without on-air chain link"] == 35

    def test_a_13_byte_tag_saves_one_more_byte_through_its_shorter_prefix(self) -> None:
        assert fx._floor_frames(64)["lean"] - fx._floor_frames(13)["lean"] == 51 + 1
        assert fx._floor_frames(64)["first"] - fx._floor_frames(13)["first"] == 51 + 1
        assert fx._floor_frames(64)["first"] - fx._floor_frames(48)["first"] == 16


class TestRegistration:
    def test_every_new_experiment_is_reachable_from_the_one_entry_point(self) -> None:
        runners = all_runners()
        for name in fx.RUNNERS:
            assert name in runners and load_config(name)["experiment"] == name

    def test_no_new_artifact_shadows_an_old_one(self) -> None:
        from authbc.bench.experiments import _RUNNERS
        assert not {r.out for r in fx.RUNNERS.values()} & {r.out for r in _RUNNERS.values()}
