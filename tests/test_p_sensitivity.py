"""Does the co-design selection depend on the assumed loss probability p? (item O2 / Tier-2 #5)

`p = 0.05` is justified by mechanism in `OPEN_ITEMS` B4 but is not a measured value for our link,
and every feasibility verdict in the 802.11 arm rests on it. These tests pin what the sweep in
`analysis/sensitivity_p.py` established:

1. the selected configuration is **invariant** across the entire feasible range of p, so the
   co-design conclusion does not depend on the constant; and
2. feasibility requires **p ≤ ε identically** — which makes the adopted point (p = ε = 0.05) a
   zero-margin boundary case, and is a property of the *requirement*, not a defect in the design.
"""

from __future__ import annotations

import pytest

from authbc.bench.experiments import _measured_inputs, load_config
from authbc.models import optimizer
from authbc.models.optimizer import Placement, verifiability


@pytest.fixture(scope="module")
def solver():
    cfg = load_config("e5")
    encs, schemes = _measured_inputs(cfg)
    plat = optimizer.Platform(p_cpu_w=cfg["p_cpu_w"], p_radio_w=cfg["p_radio_w"],
                              t_hash_s=cfg["t_hash_ns"] * 1e-9,
                              frame_hdr_bytes=cfg["h_f"], mtu_bytes=cfg["mtu"])

    def solve(p: float, eps: float = 0.05):
        con = optimizer.Constraints(epsilon=eps, p_loss=p, lam=cfg["lam"],
                                    n_local=cfg["n_local"])
        return optimizer.solve(encs, schemes, list(Placement), cfg["batches"], plat, con)

    return solve


class TestTheSelectionDoesNotDependOnP:
    """The robustness result: an unsourced constant that changes nothing is not load-bearing."""

    @pytest.mark.parametrize("p", [0.00023, 0.001, 0.01, 0.03, 0.045, 0.05])
    def test_same_configuration_is_selected_across_the_feasible_range(self, solver, p):
        res = solver(p)
        assert res.feasible, f"p={p} should be feasible (p <= eps)"
        best = min(res.feasible, key=lambda c: (c.bytes_per_record, c.energy_j))
        assert (best.encoding, best.scheme, str(best.placement), best.batch) == (
            "delta", "ed25519", "B", 4)
        assert best.bytes_per_record == pytest.approx(71.998, abs=0.01)


class TestFeasibilityRequiresPBelowEpsilon:
    """⚠️ An identity, and the reason the adopted point has zero margin in the model."""

    def test_nothing_is_feasible_once_p_exceeds_epsilon(self, solver):
        assert not solver(0.051).feasible, "p > eps must make the target unreachable"

    def test_the_boundary_is_exactly_p_equals_epsilon(self, solver):
        assert solver(0.05).feasible, "p == eps is satisfiable exactly (V = 0.95 >= 0.95)"
        assert not solver(0.0501).feasible

    def test_why_it_is_an_identity_not_a_measurement(self):
        """Placement B attains V = 1-p, and no placement beats it, so V>=1-eps iff p<=eps.

        D fragments a block across n frames and needs all of them, giving (1-p)^n <= 1-p. So the
        best achievable verifiability at any p is 1-p, and the feasibility test reduces to a
        comparison between p and epsilon. Asserting it here stops the cliff at p=0.051 from being
        mistaken for an empirical finding about our design.
        """
        p = 0.05
        assert verifiability(Placement.B, 1, p) == pytest.approx(1 - p)
        for n in (1, 2, 4, 8):
            assert verifiability(Placement.D, n, p) <= verifiability(Placement.B, n, p) + 1e-12
