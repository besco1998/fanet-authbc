"""U-F (predictions/UF.md): the radius rule, and the driver runs the registered configurations.

The table itself needs the twin's placements (ns-3), absent in CI; its lines are checked against
the registration where the twin is built.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def uf():
    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO / "ns3"))
    return _load("uf", REPO / "analysis" / "uf.py")


def test_the_radius_keeps_every_pair_32_db_over_the_floor(uf) -> None:
    for alpha, r in uf.RADIUS_M.items():
        assert r == uf.largest_radius(alpha)
        assert uf.rx_dbm(2 * r, alpha) >= -50.0
        assert uf.rayleigh_link_loss(uf.rx_dbm(2 * r, alpha)) < 0.001


def test_sixteen_configurations_and_the_outlier(uf) -> None:
    assert len(uf.CONFIGS) == 16 and len({c.name for c in uf.CONFIGS}) == 16
    assert uf.OUTLIER in uf.CONFIGS
    assert uf.rx_dbm(uf.OUTLIER_M, 3) == pytest.approx(-78.62, abs=0.01)


def test_the_driver_runs_them(uf) -> None:
    ru = _load("run_unified_for_uf", REPO / "ns3" / "run_unified.py")
    for c in uf.CONFIGS:
        a = ru.CELLS[c.name].args()
        assert f"--pathLossExp={c.alpha}" in a and ("--nakagamiM=1" in a) == c.fading
        assert "--perNode=1" in a and "--perPair=1" in a and "--txPowerDbm=40.0" in a
    assert "--outlierM=250.0" in ru.CELLS["FOUT"].args()
