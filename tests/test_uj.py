"""U-J's cells, predictions and scorer (analysis/uj.py): the runner's cells are U-J's, the frozen
source is the strictly periodic OnOff source, and the scorer reads a known crossing back."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "ns3"), str(REPO / "src")]

import run_unified as ru  # noqa: E402
import uj  # noqa: E402

from authbc.models import unified_capacity as uc  # noqa: E402


class TestTheCells:
    def test_the_runner_holds_every_cell_with_its_source(self) -> None:
        for c in uj.CELLS:
            args = ru.CELLS[c.name].args()
            assert f"--frameSize={c.frame_bytes}" in args
            assert f"--framesPerSec={c.fps!r}" in args
            src = uj.SOURCES[c.source]
            jitter = [a for a in args if a.startswith("--txJitterMs=")]
            if src.frozen:
                assert jitter == [], "frozen phases: the OnOff source, no jitter option"
            elif src.jitter_ms is None:
                assert jitter == [f"--txJitterMs={ru.one_period_ms(c.fps)!r}"]
            else:
                assert jitter == [f"--txJitterMs={src.jitter_ms!r}"]
            skew = [a for a in args if a.startswith("--txSkewPpm=")]
            assert skew == ([f"--txSkewPpm={src.skew_ppm!r}"] if src.skew_ppm else [])
            assert not any(a.startswith("--standard=") for a in args), "802.11a, the default"

    def test_a_skew_always_has_a_jitter_as_the_scenario_requires(self) -> None:
        for s in uj.SOURCES.values():
            if s.skew_ppm:
                assert s.jitter_ms is not None and s.jitter_ms > 0

    def test_existing_cells_are_unchanged(self) -> None:
        assert ru.CELLS["C"].args() == [
            "--frameSize=146",
            "--framesPerSec=50.0",
            "--txJitterMs=20.0",
        ]

    def test_the_cells_are_new(self) -> None:
        assert uj.scan_prior() == []


class TestThePredictions:
    def test_root_and_law_are_the_model_code(self) -> None:
        for r in uj.predictions():
            c = next(x for x in uj.CELLS if x.name == r["cell"])
            assert r["root"] == uc.n_root(c.fps, c.tf_s, uj.EPS, uc.A80211A)
            assert r["law"] == uc.n_law(c.fps, c.tf_s, uj.EPS, uc.A80211A)
            assert r["law_valid"] is True


class TestTheScore:
    def _files(self, tmp: Path, name: str, crossing: float, seeds: dict[int, dict[int, float]]):
        (tmp / f"uj_{name.lower()}.csv").write_text(
            "cell,n_nodes,seeds,delivered_mean,delivered_min,delivered_max,delivered_stdev\n"
            f"{name},CROSSING@0.95,30,{crossing},{crossing - 0.2},{crossing + 0.2},bracketed\n"
        )
        rows = ["cell,n_nodes,seed,delivered_frac"]
        rows += [f"{name},{n},{s},{d}" for s, curve in seeds.items() for n, d in curve.items()]
        (tmp / f"uj_{name.lower()}_runs.csv").write_text("\n".join(rows) + "\n")

    def test_held_needs_the_safe_side_and_frozen_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(uj, "RAW", tmp_path)
        pred = {r["cell"]: float(str(r["root"])) for r in uj.predictions()}
        curve = {1: {30: 0.96, 34: 0.94}, 2: {30: 0.97, 34: 0.955, 36: 0.93}}
        for c in uj.CELLS:
            # root 2 % below ns-3 everywhere except one jittered cell, where ns-3 is below the root
            ns3 = pred[c.name] / {"J1": 1.01, "J01": 0.93}.get(c.source, 0.98)
            self._files(tmp_path, c.name, ns3, curve)
        rows = {r["cell"]: r for r in uj.score()}
        for r in rows.values():
            src = uj.SOURCES[r["source"]]
            if src.frozen:
                assert r["held"] == "reported"
            elif r["source"] == "J01":
                assert r["s_held"] == 1 and r["a_held"] == 0 and r["held"] == 0, "7 % below"
            elif r["source"] == "J1":
                assert r["held"] == 0 and r["s_held"] == 0, "above ns-3 is not the safe side"
                assert r["a_held"] == 1, "within 5 %, so only S fails"
            else:
                assert r["held"] == 1 and r["s_held"] == 1 and r["a_held"] == 1
            assert r["seed_crossings"] == 2
        r = rows["JA230F40DS"]
        assert r["seed_min"] == pytest.approx(32.0) and r["seed_max"] == pytest.approx(34.4)
