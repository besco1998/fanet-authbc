"""The access-rule model's two artifacts (docs/02 §6g; docs/NMAX_DIRECT_EXPECTATIONS.md, F5).

`dcf_model_vs_ns3.csv` compares the model with every point ns-3 has run; it is not a prediction
and is not held to be one. `dcf_model_predictions.csv` is: it was committed before the ns-3 runs
it predicts, so what is held here is that it says what was registered and that the plans run
exactly the node counts it names.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
sys.path.insert(0, str(REPO / "ns3"))
_spec = importlib.util.spec_from_file_location("dcf_model_check",
                                               REPO / "analysis" / "dcf_model_check.py")
assert _spec and _spec.loader
check = importlib.util.module_from_spec(_spec)
sys.modules["dcf_model_check"] = check
_spec.loader.exec_module(check)

from authbc.bench.stats import interpolated_crossing  # noqa: E402


def _rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in (RAW / name).read_text().splitlines()
                               if not ln.startswith("#")))


COMPARED = _rows("dcf_model_vs_ns3.csv")
POINTS = [r for r in COMPARED if r["n_nodes"] != "CROSSING"]
CROSSINGS = {r["cell"]: r for r in COMPARED if r["n_nodes"] == "CROSSING"}
PREDICTED = {r["case"]: r for r in _rows("dcf_model_predictions.csv")}


class TestTheComparisonWithEverySimulatedPoint:
    def test_it_covers_every_configuration_ns3_has_run_at_the_designated_source(self) -> None:
        ns3, crossing = check.ns3_designated()
        assert set(CROSSINGS) == set(ns3) == set(crossing) and len(CROSSINGS) == 18
        assert {(r["cell"], int(r["n_nodes"])) for r in POINTS} == \
            {(cell, n) for cell, pts in ns3.items() for n in pts}

    def test_the_ns3_column_is_the_summarys(self) -> None:
        ns3, crossing = check.ns3_designated()
        for r in POINTS:
            assert float(r["ns3_delivered"]) == ns3[r["cell"]][int(r["n_nodes"])]
        for cell, r in CROSSINGS.items():
            assert float(r["ns3_crossing"]) == crossing[cell]

    def test_each_model_crossing_is_the_crossing_of_its_own_points(self) -> None:
        for cell, r in CROSSINGS.items():
            means = {int(p["n_nodes"]): float(p["model_delivered"]) for p in POINTS
                     if p["cell"] == cell}
            x = interpolated_crossing(means, check.V_TARGET)
            assert x is not None and abs(x - float(r["model_crossing"])) <= 0.011, cell
            error = 100 * (float(r["model_crossing"]) / float(r["ns3_crossing"]) - 1)
            # both columns are rounded to two places: half a hundredth of a node is 0.02 %
            assert error == pytest.approx(float(r["crossing_error_pct"]), abs=0.03), cell

    def test_what_the_documents_say_about_it(self) -> None:
        errors = [float(r["crossing_error_pct"]) for r in CROSSINGS.values()]
        assert (min(errors), max(errors)) == (-1.2, 0.63)
        assert round(sum(abs(e) for e in errors) / len(errors), 1) == 0.5
        assert len(POINTS) == 153
        assert max(abs(float(r["difference"])) for r in POINTS) == pytest.approx(0.0023, abs=5e-5)

    def test_ties_are_more_than_half_of_the_loss_everywhere(self) -> None:
        shares = [float(r["model_tie_share"]) for r in POINTS]
        assert 0.5 < min(shares) and max(shares) < 0.86

    @pytest.mark.frozen
    @pytest.mark.parametrize("cell, n", [("SW", 29), ("A", 32)])
    def test_a_point_recomputes_to_the_committed_value(self, cell: str, n: int) -> None:
        got = check.model_means([(cell, n, check.model.W0)], workers=2)
        (row,) = [r for r in POINTS if (r["cell"], r["n_nodes"]) == (cell, str(n))]
        key = (cell, n, check.model.W0)
        assert round(got[key]["delivered"], 5) == float(row["model_delivered"])


class TestTheRegisteredPredictions:
    def test_six_cases_as_registered(self) -> None:
        assert list(PREDICTED) == [c.name for c in check.CASES] and len(PREDICTED) == 6
        want = {"C, window doubled": 39.09, "D, window doubled": 139.03, "C, 10 % loss": 46.77,
                "D, 10 % loss": 165.30, "C, 2 % loss": 22.49, "D, 2 % loss": 79.65}
        assert {k: float(r["model_crossing"]) for k, r in PREDICTED.items()} == want

    def test_the_band_is_three_percent_either_side(self) -> None:
        for r in PREDICTED.values():
            x = float(r["model_crossing"])
            assert float(r["band_lo"]) == pytest.approx(0.97 * x, abs=0.011)
            assert float(r["band_hi"]) == pytest.approx(1.03 * x, abs=0.011)

    def test_every_registered_grid_brackets_its_band(self) -> None:
        for case in check.CASES:
            r = PREDICTED[case.name]
            assert r["ns3_grid"].split() == [str(n) for n in case.ns3_grid]
            assert case.ns3_grid[0] <= float(r["band_lo"])
            assert float(r["band_hi"]) <= case.ns3_grid[-1]

    @pytest.mark.parametrize("stem, plan", [("ns3_rule_levels", "plan_rule_levels.txt"),
                                            ("ns3_rule_cw31", "plan_rule_cw31.txt")])
    def test_the_plans_run_exactly_the_registered_node_counts(self, stem: str,
                                                              plan: str) -> None:
        import run_nmax_direct as drv

        planned = {cell: sorted(ns) for cell, source, ns in drv.read_plan(
            REPO / "experiments" / "nmax-direct" / plan) if source == "period"}
        registered: dict[str, list[int]] = {}
        for case in check.CASES:
            if case.stem == stem:
                registered.setdefault(case.cell, []).extend(case.ns3_grid)
        assert planned == {cell: sorted(ns) for cell, ns in registered.items()}


class TestScoringRefusesAnUnfinishedCampaign:
    def test_a_case_without_its_runs_file_is_not_scored(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(check, "RAW", tmp_path)
        assert check.ns3_crossing(check.CASES[0]) == (None, {})

    def test_node_counts_short_of_thirty_runs_do_not_enter(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(check, "RAW", tmp_path)
        case = check.CASES[0]
        lines = ["cell,n_nodes,seed,delivered_frac"]
        lines += [f"C,38,{s},0.96" for s in range(1, 31)]
        lines += [f"C,40,{s},0.94" for s in range(1, 30)]            # one seed missing
        (tmp_path / f"{case.stem}_runs.csv").write_text("\n".join(lines) + "\n")
        crossing, means = check.ns3_crossing(case)
        assert crossing is None and list(means) == [38]
