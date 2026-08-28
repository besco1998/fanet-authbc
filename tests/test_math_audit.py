"""Math audit 2026-08-28 — the conventions and limits that decide headline claims.

Every finding pinned here was found by RE-DERIVING a quantity rather than re-reading the
project's conclusion about it. None was a wrong number; each is a convention or a limit that
was never written down, and in three cases the unstated choice happens to favour our own claim.

Expected values below are hand-computed from the equations or from a discrete-event simulation
written for the purpose — never by calling the module under test back on itself (docs/05 §9).
"""

from __future__ import annotations

import csv
import random
import statistics as st
from pathlib import Path

import pytest

from authbc.models import bianchi, broadcast_dcf, energy, lora, optimizer
from authbc.models.energy import EnergyConfig, Placement
from authbc.placement import framer

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"


def _rows(name: str) -> list[dict[str, str]]:
    text = (RAW / name).read_text()
    return list(csv.DictReader(ln for ln in text.splitlines(True) if not ln.startswith("#")))


def _cfg(b: int, s: float = 45.0) -> EnergyConfig:
    return EnergyConfig(placement=Placement.B, batch=b, record_bytes=s,
                        auth_bytes=64.0, frame_hdr_bytes=44.0, n_frames=1)


# ===================================================================== A2 — freshness convention
class TestFreshnessConvention:
    """b/Λ and (b−1)/Λ are DIFFERENT quantities; docs/02 §7 names one and computes the other."""

    @staticmethod
    def _simulate(b: int, lam: float, n_frames: int = 20_000,
                  poisson: bool = False, seed: int = 1) -> tuple[float, float]:
        """(mean batch-window duration, mean oldest-record age) by discrete-event simulation."""
        rng = random.Random(seed)
        dt = 1.0 / lam
        windows, ages = [], []
        t = 0.0
        for _ in range(n_frames):
            open_t, arrivals = t, []
            for _ in range(b):
                t += dt if not poisson else rng.expovariate(lam)
                arrivals.append(t)
            windows.append(arrivals[-1] - open_t)
            ages.append(arrivals[-1] - arrivals[0])
        return st.fmean(windows), st.fmean(ages)

    @pytest.mark.parametrize("b", [1, 2, 4, 5, 8])
    @pytest.mark.parametrize("lam", [20.0, 50.0])
    def test_both_closed_forms_match_simulation(self, b: int, lam: float) -> None:
        """Deterministic arrivals: window = b/Λ exactly, oldest-record age = (b−1)/Λ exactly."""
        window, age = self._simulate(b, lam, poisson=False)
        assert window == pytest.approx(b / lam, rel=1e-9)
        assert age == pytest.approx((b - 1) / lam, rel=1e-9, abs=1e-12)

    @pytest.mark.parametrize("b", [2, 4, 5])
    def test_poisson_arrivals_give_the_same_means(self, b: int) -> None:
        """Erlang(b, Λ) has mean b/Λ; Erlang(b−1, Λ) has mean (b−1)/Λ. 2 % at 20k frames."""
        lam = 50.0
        window, age = self._simulate(b, lam, n_frames=20_000, poisson=True)
        assert window == pytest.approx(b / lam, rel=0.02)
        assert age == pytest.approx((b - 1) / lam, rel=0.02)

    def test_the_module_exposes_both_and_they_differ_by_one_gap(self) -> None:
        lam = 50.0
        for b in (1, 2, 4, 5):
            w = energy.batch_window_s(_cfg(b), lam)
            a = energy.oldest_record_age_s(_cfg(b), lam)
            assert w - a == pytest.approx(1.0 / lam, rel=1e-12)

    def test_freshness_delay_uses_the_worst_case_and_is_an_upper_bound(self) -> None:
        """D(b) must bound the oldest record's true end-to-end latency, never understate it."""
        lam = 50.0
        for b in (1, 2, 4, 5, 8):
            cfg = _cfg(b)
            true_e2e = (energy.oldest_record_age_s(cfg, lam)
                        + energy.radio_airtime_s(cfg)
                        + energy.queueing_delay_s(cfg, lam))
            assert energy.freshness_delay_s(cfg, lam) >= true_e2e

    def test_the_convention_is_worth_one_batch_step_at_both_operating_points(self) -> None:
        """⚠️ Documents the cost of the choice: b=4 worst-case vs b=5 under the tight reading."""
        for lam, d_max in ((50.0, 0.100), (20.0, 0.250)):
            worst = max(b for b in range(1, 12)
                        if energy.freshness_delay_s(_cfg(b), lam) <= d_max)
            tight = max(b for b in range(1, 12)
                        if (energy.oldest_record_age_s(_cfg(b), lam)
                            + energy.radio_airtime_s(_cfg(b))
                            + energy.queueing_delay_s(_cfg(b), lam)) <= d_max)
            assert (worst, tight) == (4, 5), (
                f"Λ={lam}: worst-case admits b={worst}, tight reading admits b={tight}. "
                f"The published headline (72.0 B/record, −58.68 %) is the b=4 column; b=5 "
                f"gives 66.6 B/record and −61.78 %."
            )

    def test_the_docs02_7a_knife_edge_is_a_worst_case_figure_not_a_design_fact(self) -> None:
        """docs/02 §7a: 'at Λ=20.0 the b=2 frame takes 100.37 ms, 0.37 ms over, so b collapses'.

        True under the worst case. Under the oldest-record reading the same frame is 50.37 ms and
        sits comfortably inside 100 ms — so the fragility is a property of the convention.
        """
        lam, cfg = 20.0, _cfg(2)
        assert energy.freshness_delay_s(cfg, lam) == pytest.approx(0.10037, abs=5e-5)
        tight = (energy.oldest_record_age_s(cfg, lam) + energy.radio_airtime_s(cfg)
                 + energy.queueing_delay_s(cfg, lam))
        assert tight == pytest.approx(0.05037, abs=5e-5)
        assert tight < 0.100 < energy.freshness_delay_s(cfg, lam)


# ===================================================================== A1 — the E5 criterion
class TestSuccessCriterionIsAnIdentity:
    """⚠️ The pre-registered ≥40 % criterion reduces to 1 − 1/b and could not have failed."""

    def test_auth_cut_is_exactly_one_minus_one_over_b(self) -> None:
        """A carries g_a + H_f per record; B carries (g_a + H_f)/b. The ratio is 1 − 1/b."""
        for g_a in (48.0, 64.0, 96.0):
            for h_f in (38.0, 44.0, 81.0):
                for b in range(1, 33):
                    a = optimizer.frame_auth_bytes(Placement.A, 1, g_a) + h_f
                    opt = (optimizer.frame_auth_bytes(Placement.B, b, g_a) + h_f) / b
                    assert (a - opt) / a == pytest.approx(1.0 - 1.0 / b, rel=1e-12)

    def test_the_forty_percent_threshold_is_satisfied_by_any_b_at_least_two(self) -> None:
        assert 1.0 - 1.0 / 1 < 0.40
        assert 1.0 - 1.0 / 2 >= 0.40
        for b in range(2, 64):
            assert 1.0 - 1.0 / b >= 0.40

    def test_the_artifact_agrees_the_criterion_is_the_identity(self) -> None:
        row = next(r for r in _rows("e5_codesign.csv") if r["role"] == "SUCCESS_CRITERION")
        opt = next(r for r in _rows("e5_codesign.csv") if r["role"] == "optimized")
        assert float(row["auth_cut_pct"]) == pytest.approx(
            100.0 * (1.0 - 1.0 / int(opt["batch"])), abs=0.01)

    def test_the_verifiability_half_is_satisfied_by_construction(self) -> None:
        """V = 1 − p for A/B/C regardless of encoding, batch or scheme (audit E17)."""
        for plc in (Placement.A, Placement.B, Placement.C):
            for n in (1, 2, 8):
                assert optimizer.verifiability(plc, n, 0.05) == pytest.approx(0.95)


# ===================================================================== A3 — H_f is a range
class TestFrameHeaderIsARange:
    def test_the_documented_44_reproduces_at_realistic_field_magnitudes(self) -> None:
        assert framer.measure_frame_header_bytes(4) == framer.H_F == 44

    def test_it_falls_to_38_for_a_fresh_low_id_node(self) -> None:
        assert framer.measure_frame_header_bytes(4, src=0, base_seq=0) == 38
        assert framer.frame_header_bytes_range(4) == (38, 44)

    def test_the_b24_step_is_real_and_is_two_bytes(self) -> None:
        assert framer.measure_frame_header_bytes(23) == 44
        assert framer.measure_frame_header_bytes(24) == 46

    def test_dr3_exclusion_is_conditional_on_h_f_at_least_39(self) -> None:
        """⚠️ THE headline: 'four of seven EU868 rates excluded' holds only for H_f ≥ 39 B.

        DR0–DR2 are unconditional (64 B signature will not fit a 51 B payload at ANY header
        size). DR3 turns on the header, and H_f = 44 is the TOP of the measured 38–44 range —
        i.e. the value most favourable to the exclusion, since s_max = M − H_f − g_a.
        """
        m, g_a, s_min = lora.EU868_DATA_RATES[3].max_app_payload, 64.0, 13.0
        assert m == 115
        for h_f in (36, 37, 38):
            assert optimizer.exclusion_tier(m, g_a, h_f, s_min) is None, (
                f"at H_f={h_f} DR3 is FEASIBLE and the headline is three of seven, not four")
        for h_f in (39, 40, 44):
            assert optimizer.exclusion_tier(m, g_a, h_f, s_min) == "encoding"

    def test_dr0_to_dr2_are_unconditional_at_every_header_size(self) -> None:
        for h_f in (0, 38, 44, 200):
            for dr in (0, 1, 2):
                m = lora.EU868_DATA_RATES[dr].max_app_payload
                assert optimizer.exclusion_tier(m, 64.0, h_f, 13.0) == "signature"


# ===================================================================== A4 — s depends on run length
class TestRecordSizeDependsOnRunLength:
    """⚠️ s is not a property of the encoding alone; its bootstrap CI is ~150x too narrow."""

    @staticmethod
    def _mean_size(name: str, seed: int, n: int) -> float:
        from authbc.bench import telemgen
        from authbc.encodings.registry import new_encoder
        enc = new_encoder(name)
        recs = list(telemgen.stream(seed, n))
        return sum(len(enc.encode(r)) for r in recs) / n

    def test_variable_length_encodings_grow_with_the_window(self) -> None:
        """seq and ts grow with the index and canonical CBOR/JSON charge for the extra digits."""
        for name in ("json", "cbor", "msgpack"):
            short, long_ = self._mean_size(name, 1, 1000), self._mean_size(name, 1, 10_000)
            assert long_ - short > 1.5, f"{name}: expected growth, got {long_ - short:+.3f} B"

    def test_delta_is_flat_because_it_encodes_differences(self) -> None:
        short, long_ = self._mean_size("delta", 1, 1000), self._mean_size("delta", 1, 10_000)
        assert abs(long_ - short) < 0.2

    def test_the_systematic_term_dwarfs_the_reported_confidence_interval(self) -> None:
        """E1 quotes cbor as 66.252 [66.239, 66.266] — ±0.02 B of SEED variation.

        The dependence on `records_per_seed` is ~2.7 B, roughly 150x wider. The interval is
        correct for what it measures and misleading about what it appears to measure.
        """
        row = next(r for r in _rows("e1_dominance.csv") if r["encoding"] == "cbor")
        ci_width = float(row["ci_hi"]) - float(row["ci_lo"])
        systematic = self._mean_size("cbor", 1, 10_000) - self._mean_size("cbor", 1, 1000)
        assert ci_width < 0.05
        assert systematic / ci_width > 50, (
            f"CI width {ci_width:.4f} B vs systematic window term {systematic:.3f} B")

    def test_the_direction_is_conservative_for_the_headline(self) -> None:
        """A longer flight inflates the CBOR baseline and leaves delta alone, so the reported
        saving is the pessimistic end. Stated so nobody 'fixes' it in the flattering direction."""
        base_short = 44 + 64 + self._mean_size("cbor", 1, 1000)
        base_long = 44 + 64 + self._mean_size("cbor", 1, 10_000)
        opt = self._mean_size("delta", 1, 1000) + (64 + 44) / 4
        assert (1 - opt / base_long) > (1 - opt / base_short)


# ===================================================================== channel math vs simulation
class TestChannelMathAgainstSimulation:
    """Three independent implementations of the same physics must agree."""

    def test_ofdm_ppdu_matches_the_hand_derived_802_11a_timing(self) -> None:
        import math
        for nbytes in (14, 72, 288, 1436):
            n_sym = math.ceil((16 + 8 * nbytes + 6) / (6e6 * 4e-6))
            assert bianchi.ofdm_ppdu(nbytes) == pytest.approx(20e-6 + n_sym * 4e-6, rel=1e-12)
        assert bianchi.ofdm_ppdu(1436) == pytest.approx(1940e-6, rel=1e-12)
        assert bianchi.ofdm_ppdu(14) == pytest.approx(44e-6, rel=1e-12)

    @pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
    def test_ma_chen_closed_form_matches_the_slot_exact_simulator(self, n: int) -> None:
        """dcf_ladder was written BEFORE Ma & Chen was found and shares none of its assumptions."""
        from authbc.sim import dcf_ladder
        L = 1400.0
        tb = bianchi.t_broadcast(L)
        closed = broadcast_dcf.solve(n, L, tb, w0=bianchi.W, slot_s=bianchi.SLOT)
        sim = dcf_ladder.run(n, w=bianchi.W, busy_periods=60_000, t_busy_s=tb,
                             slot_s=bianchi.SLOT, payload_bytes=L, seed=1)
        rel = abs(sim.throughput_bps - closed.throughput_bps) / closed.throughput_bps
        assert rel < 0.02, f"N={n}: closed form and slot-exact sim differ by {100*rel:.2f} %"

    def test_bianchi_fixed_point_residual_is_negligible(self) -> None:
        for n in (1, 2, 5, 10, 20, 35, 50, 100, 500):
            assert bianchi.fixed_point_residual(bianchi.solve(n, 1400.0)) < 1e-11

    def test_tau_is_continuous_through_the_removable_singularity(self) -> None:
        """⚠️ p_c crosses 1/2 for N ≳ 21, so the solver walks through this neighbourhood."""
        lim = bianchi.tau_of_pc(0.5)
        assert lim == pytest.approx(4.0 / (2 * bianchi.W + 2 + bianchi.W * bianchi.M), rel=1e-12)
        for eps in (1e-3, 1e-6, 1e-9):
            assert bianchi.tau_of_pc(0.5 - eps) == pytest.approx(lim, rel=1e-2)
            assert bianchi.tau_of_pc(0.5 + eps) == pytest.approx(lim, rel=1e-2)
        assert bianchi.solve(35, 1400.0).p_c > 0.5
        assert bianchi.solve(50, 1400.0).p_c > 0.5


# ===================================================================== N_max search soundness
class TestNmaxSearchIsSound:
    """The envelope breaks on the first violating N. That is only valid if U(n) is monotone."""

    def test_saturation_throughput_is_NOT_monotone_in_n(self) -> None:
        """Real property of Ma & Chen's CFP series, reproduced by NS-3 and the slot-exact sim.

        Each freeze stage contributes an n·τ(1−τ)^(n−1) hump peaking at n ≈ W₀^(i+1)/2, so S(n)
        dips and recovers. Recorded because it looks like a bug and is not.
        """
        tb = bianchi.t_broadcast(288.0)
        s = [broadcast_dcf.solve(n, 288.0, tb, w0=bianchi.W, slot_s=bianchi.SLOT).throughput_bps
             for n in range(2, 200)]
        rising = any(y > x for x, y in zip(s, s[1:], strict=False))
        assert rising, "S(n) is monotone — re-derive this test"

    @pytest.mark.parametrize("lam,b,frame", [(20.0, 4, 288.0), (20.0, 1, 174.252),
                                             (50.0, 4, 288.0), (10.0, 1, 153.0)])
    def test_channel_utilisation_is_strictly_increasing_so_the_break_is_safe(
            self, lam: float, b: int, frame: float) -> None:
        """⚠️ Safe by arithmetic, not by construction: the explicit factor n in the numerator
        outruns the CFP recovery in S(n). Pinned so a change to W₀ or frame size cannot silently
        make the first-failure search under-report N_max."""
        us = [optimizer.channel_utilisation(n, lam, b, frame) for n in range(2, 401)]
        assert all(y > x for x, y in zip(us, us[1:], strict=False))


# ===================================================================== Bor comparison
class TestBorComparisonIsQuotedHonestly:
    def test_their_n_max_sits_inside_their_own_fits_unreliable_region(self) -> None:
        assert lora.bor2017_n_max(0.95) == 4
        assert lora.bor2017_loss_pct(0.0) == pytest.approx(1.7833, abs=1e-3)
        assert lora.bor2017_intercept_share(4) > 0.35

    def test_removing_the_intercept_widens_the_gap_rather_than_closing_it(self) -> None:
        """Conservative direction: the honest correction favours THEM, so quoting 4 is safe."""
        b0 = lora.bor2017_loss_pct(0.0)
        assert lora.bor2017_loss_pct(5) - b0 < 5.0

    def test_the_pessimism_ratio_changes_sign_and_must_not_be_quoted_as_one_number(self) -> None:
        """⚠️ At N=2 WE are the more optimistic model — in the region deciding N_max."""
        art = {r["n_devices"]: r for r in _rows("lora_external_check.csv")
               if r["n_devices"].isdigit()}
        r2 = lora.bor2017_pessimism_ratio(float(art["2"]["authbc_ns3_loss_pct"]), 2)
        r50 = lora.bor2017_pessimism_ratio(float(art["50"]["authbc_ns3_loss_pct"]), 50)
        assert r2 < 1.0 < r50
        assert art["2"]["who_is_optimistic"] == "AUTHBC"
        assert art["50"]["who_is_optimistic"] == "Bor2017"


# ===================================================================== M4 — U ceiling invariance
class TestUCrossingIsFrameSizeInvariant:
    """The envelope applies ONE measured U ceiling to frames from 153 B to 299 B.

    Measured at 288 B (`ns3_delay_ci.csv`) and, after M4, at 174 B (`ns3_delay_174B.csv`) — the
    A+CBOR Pillar-1 frame that produces the baselines the capacity ratios divide by. Prediction
    committed data-free in `docs/M4_EXPECTATIONS.md` (`84adb92`) before either arm was compared.
    """

    @staticmethod
    def _crossing(name: str, target: float = 0.95) -> tuple[float, float]:
        """(interpolated crossing U, its standard error) from a delay artifact."""
        import math
        rs = sorted(_rows(name), key=lambda r: float(r["channel_util"]))
        lo = [r for r in rs if float(r["delivered_frac"]) >= target][-1]
        hi = [r for r in rs if float(r["delivered_frac"]) < target][0]
        u0, v0 = float(lo["channel_util"]), float(lo["delivered_frac"])
        u1, v1 = float(hi["channel_util"]), float(hi["delivered_frac"])
        crossing = u0 + (v0 - target) / (v0 - v1) * (u1 - u0)
        slope = (v1 - v0) / (u1 - u0)
        sem_v = math.hypot(*[float(r["delivered_stdev"]) / math.sqrt(int(r["seeds"]))
                             for r in (lo, hi)])
        return crossing, abs(sem_v / slope)

    def test_the_published_crossing_is_still_2_435(self) -> None:
        c, _ = self._crossing("ns3_delay_ci.csv")
        assert c == pytest.approx(2.435, abs=0.01)

    def test_the_174B_arm_lands_inside_the_pre_registered_band(self) -> None:
        """⚠️ The load-bearing prediction: 2.1-2.8. Outside it, the envelope would need a
        per-configuration crossing and tab:envelope's absolute N_max column would move."""
        c, _ = self._crossing("ns3_delay_174B.csv")
        assert 2.1 <= c <= 2.8, (
            f"174 B crosses at U={c:.3f}, outside the pre-registered 2.1-2.8. The universal "
            f"ceiling in experiments/capacity/config.yaml is no longer justified — re-derive "
            f"tab:envelope per configuration (docs/M4_EXPECTATIONS.md)."
        )

    def test_the_two_crossings_are_statistically_indistinguishable(self) -> None:
        """⚠️ The shift is 0.45 sigma. Do NOT report its DIRECTION as a finding — the design
        has no power to resolve the sign, which is recorded as a flaw in the pre-registration."""
        import math
        c288, s288 = self._crossing("ns3_delay_ci.csv")
        c174, s174 = self._crossing("ns3_delay_174B.csv")
        sigma = abs(c174 - c288) / math.hypot(s288, s174)
        assert sigma < 2.0, (
            f"the crossings now differ by {sigma:.2f} sigma across a 1.66x frame-size change. "
            f"If this becomes resolvable the universal U ceiling needs re-examining."
        )

    def test_both_arms_still_deliver_above_98_percent_at_u_equals_one(self) -> None:
        """The result that withdrew theorem T7 must not be frame-size specific."""
        for name in ("ns3_delay_ci.csv", "ns3_delay_174B.csv"):
            near = min(_rows(name), key=lambda r: abs(float(r["channel_util"]) - 1.0))
            assert float(near["delivered_frac"]) >= 0.98

    def test_the_threshold_straddling_reproduces_at_the_second_frame_size(self) -> None:
        """S3b was not an artifact of 288 B: at 174 B, U=2.321 has mean 0.9529 and 13/30 fail."""
        straddle = [r for r in _rows("ns3_delay_174B.csv")
                    if float(r["delivered_frac"]) >= 0.95 and int(r["seeds_failing_v"]) > 5]
        assert straddle, "no row now clears V on the mean while failing it on a third of seeds"
