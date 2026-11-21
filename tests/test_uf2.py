"""U-F2 (analysis/uf2.py, ns3/run_uf2.py): the registered configurations and the run plumbing."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

import run_unified as ru  # noqa: E402
import uf2  # noqa: E402


class TestThePlumbing:
    def test_a_dotted_cell_name_keeps_its_result_path(self) -> None:
        """2026-11-21: with_suffix turned EB100F12.5P3R_n42_s31 into EB100F12.csv."""
        p = Path("/x") / "EB100F12.5P3R_n42_s31"
        assert ru.result_path(p) == Path("/x/EB100F12.5P3R_n42_s31.csv")
        assert ru.result_path(Path("/x/GB120F15_n30_s1")) == Path("/x/GB120F15_n30_s1.csv")

    def test_every_configuration_is_a_cell_with_the_registered_channel(self) -> None:
        for c in uf2.CONFIGS:
            args = ru.CELLS[c.name].args()
            assert f"--radiusM={c.radius_m!r}" in args and f"--pathLossExp={c.alpha}" in args
            assert ("--nakagamiM=1" in args) == c.fading and "--perNode=1" in args


class TestTheRegistration:
    def test_every_scored_root_is_at_occupancy_at_most_0_78(self) -> None:
        for r in uf2.registered().values():
            assert float(r["occupancy"]) <= uf2.MAX_OCCUPANCY

    def test_the_seeds_are_new(self) -> None:
        assert min(uf2.SEEDS) > 30 and uf2.PLACEMENT_SEED not in uf2.SEEDS

    def test_each_pooled_residual_is_within_the_stated_bound(self) -> None:
        for r in uf2.registered().values():
            assert float(r["residual_pct"]) <= 100 * uf2.RESIDUAL + 1e-9
