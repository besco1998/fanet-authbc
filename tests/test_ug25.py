"""U-G25 (predictions/UG25.md): the registered predictions come from the module, and the driver
runs exactly the registered cells.

* every (G25) and Poisson root in the registration's table is what `analysis/ug25.py` computes
  from `authbc.models.periodic_capacity`, to the digits printed;
* `ns3/run_unified.py` defines the same eight cells (PHY, bytes, frames/s) as `analysis/ug25.py`;
* the co-waiting prediction R·K reduces to K where R = 1.
"""
from __future__ import annotations

import importlib.util
import re
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
def ug25():
    return _load("ug25", REPO / "analysis" / "ug25.py")


def test_the_registered_table_is_generated(ug25) -> None:
    reg = (REPO / "predictions" / "UG25.md").read_text()
    for line in ug25.markdown().splitlines()[2:]:
        assert line in reg, line


def test_the_registered_roots_to_the_digits(ug25) -> None:
    reg = (REPO / "predictions" / "UG25.md").read_text()
    rows = re.findall(r"\| (G[AB]\d+F\d+) \| \w+ \| \d+ B \| \S+ \| \S+ \| (0\.0[25]) \| "
                      r"\*\*([\d.]+)\*\* \| ([\d.]+) \|", reg)
    assert len(rows) == 16
    want = {(r["cell"], f"{r['eps']:g}"): r for r in ug25.predictions()}
    for cell, eps, g25, poisson in rows:
        r = want[(cell, eps)]
        assert f"{r['g25_root']:.2f}" == g25 and f"{r['poisson_root']:.2f}" == poisson


def test_the_driver_runs_the_registered_cells(ug25) -> None:
    sys.path.insert(0, str(REPO / "ns3"))
    ru = _load("run_unified_for_ug25", REPO / "ns3" / "run_unified.py")
    mode = {"80211b": "DsssRate1Mbps", "80211a": "OfdmRate6Mbps"}
    for name, c in ug25.CELLS.items():
        d = ru.CELLS[name]
        assert (d.standard, d.mode, d.frame_bytes, d.fps) == (c.standard, mode[c.standard],
                                                              c.frame_bytes, c.fps)
        assert not d.extra and not d.verify


def test_co_waiting_prediction_is_k_when_r_is_one(ug25) -> None:
    c = ug25.CELLS["GB120F15"]
    k, rk = ug25.predicted_k(c, 30, 0.05)
    from authbc.models import periodic_capacity as pc
    acc, nu = c.access, 29 * c.fps
    a = nu * (c.tf_s - acc.delta_s) * (1 - 0.05 / 2)
    assert rk == pytest.approx(pc.r_bb(29, a + nu * acc.difs_s) * k)
    assert 0 < rk < k
