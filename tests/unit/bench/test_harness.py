"""Trust the harness before measuring crypto (docs/03 §3 P1b step 5).

Validates timers.time_op on a known-cost function (time scales with work) and stats.bootstrap_ci
(brackets the median, seeded → reproducible). Uses lowered floors so the test stays fast.
"""

from __future__ import annotations

from authbc.bench import provenance
from authbc.bench.stats import bootstrap_ci, summarize
from authbc.bench.timers import time_op

# tiny floors — exercise the harness logic without the 200 ms / 10k-op production floors
_FAST = {"warmup": 1000, "reps": 60, "batch": 20, "min_ops": 400, "min_total_ns": 0}


def _work(n: int) -> int:
    total = 0
    for i in range(n):
        total += i * i
    return total


def test_timer_scales_with_work() -> None:
    """A 5× heavier op must measure clearly slower (harness reflects real cost).

    Work sizes are large enough that the loop dominates lambda/call overhead, so the ratio
    tracks the real 5× rather than being compressed by fixed per-call cost.
    """
    light = time_op(lambda: _work(2000), **_FAST)
    heavy = time_op(lambda: _work(10000), **_FAST)
    # Use the MINIMUM batch-sample: the fastest observed run is the least contaminated by
    # scheduler preemption, so the ratio is stable under WSL's uncontrolled governor (whereas
    # the median can be dragged up by a single noisy batch). Real 5× ⇒ safely > 2.5×.
    lo = min(light.samples_ns)
    hi = min(heavy.samples_ns)
    assert hi > lo * 2.5, f"expected ~5x, got heavy={hi:.0f}ns light={lo:.0f}ns"
    # checksum was accumulated (outputs used → no dead-code elimination)
    assert heavy.checksum != 0
    assert heavy.n_ops >= 400


def test_timer_warmup_floor_enforced() -> None:
    import pytest

    with pytest.raises(ValueError):
        time_op(lambda: None, warmup=10)


def test_bootstrap_brackets_median_and_is_seeded() -> None:
    samples = list(range(100))  # median 49.5
    lo, hi = bootstrap_ci(samples, resamples=2000, seed=1)
    assert lo <= 49.5 <= hi
    assert hi > lo  # non-zero width
    # seeded → reproducible; a CI that moved across identical seeds would be a bug (Law 6)
    assert bootstrap_ci(samples, resamples=2000, seed=1) == (lo, hi)


def test_bootstrap_degenerate_constant() -> None:
    lo, hi = bootstrap_ci([5.0] * 20, resamples=500, seed=3)
    assert lo == hi == 5.0


def test_summary_and_provenance() -> None:
    s = summarize([1.0, 2.0, 3.0, 4.0, 5.0], seed=0, resamples=1000)
    assert s.ci_lo <= s.median <= s.ci_hi and s.n == 5
    env = provenance.env_block()
    assert env["python"].startswith("3.12") and "cbor2" in env
    assert provenance.config_hash({"a": 1, "b": 2}) == provenance.config_hash({"b": 2, "a": 1})


class TestTheHeaderDescribesTheMachineThatMadeTheFile:
    """Until 2026-10-09 a file made on a board said `governor=WSL, governor uncontrolled` and
    `cpu=unknown` beside the true values the board script prepends (finding F78)."""

    def test_a_board_reports_its_own_governor(self, tmp_path, monkeypatch) -> None:
        exposed = tmp_path / "scaling_governor"
        exposed.write_text("performance\n")
        monkeypatch.setattr(provenance, "GOVERNOR_FILE", exposed)
        assert provenance.governor() == "performance"
        assert provenance.env_block()["governor"] == "performance"

    def test_a_machine_that_exposes_none_keeps_the_old_note_word_for_word(
            self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(provenance, "GOVERNOR_FILE", tmp_path / "absent")
        assert provenance.governor() == "WSL, governor uncontrolled"

    def test_the_processor_is_named_on_x86_and_on_a_raspberry_pi(self) -> None:
        x86 = "processor\t: 0\nmodel name\t: Intel(R) Core(TM) i5-14400F\nflags\t: fpu\n"
        board = ("processor\t: 0\nBogoMIPS\t: 108.00\nHardware\t: BCM2835\n"
                 "Model\t\t: Raspberry Pi 4 Model B Rev 1.4\n")
        assert provenance.model_in_cpuinfo(x86) == "Intel(R) Core(TM) i5-14400F"
        assert provenance.model_in_cpuinfo(board) == "Raspberry Pi 4 Model B Rev 1.4"
        assert provenance.model_in_cpuinfo("processor\t: 0\n") is None
