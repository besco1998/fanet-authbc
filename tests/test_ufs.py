"""U-FS (predictions/UFS.md): the registered table is generated from the finite-station module,
and the driver runs exactly those cells, for 100 s each.
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
def ufs():
    sys.path.insert(0, str(REPO / "src"))
    return _load("ufs", REPO / "analysis" / "ufs.py")


def test_the_registered_table_is_generated(ufs) -> None:
    reg = (REPO / "predictions" / "UFS.md").read_text()
    for line in ufs.markdown().splitlines()[2:]:
        assert line in reg, line


def test_the_cells_lie_where_the_form_was_accepted(ufs) -> None:
    assert len(ufs.CELLS) == 12
    assert all(3 <= c.n_nodes <= 5 and c.occupancy <= 0.5 for c in ufs.CELLS)
    for c in ufs.CELLS:
        assert c.n_nodes * c.fps * c.tf_s == pytest.approx(c.occupancy)


def test_the_driver_runs_the_registered_cells(ufs) -> None:
    sys.path.insert(0, str(REPO / "ns3"))
    ru = _load("run_unified_for_ufs", REPO / "ns3" / "run_unified.py")
    for c in ufs.CELLS:
        d = ru.CELLS[c.name]
        assert (d.standard, d.frame_bytes, d.fps, d.sim_s) == (c.standard, c.frame_bytes,
                                                              c.fps, 100.0)
