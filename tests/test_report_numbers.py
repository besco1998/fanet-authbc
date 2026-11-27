"""The model report's numbers (docs/reports/2026-11-27_model_report/): `analysis/report_numbers.py`
must reproduce the committed numbers.tex, provenance.csv and tables/*.tex byte for byte from the
stored results, so that no number in the report can drift from its file or be edited by hand."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "src")]

import report_numbers  # noqa: E402
import report_tables  # noqa: E402

REPORT = REPO / "docs" / "reports" / "2026-11-27_model_report"


def test_generated_files_match_the_committed_ones(tmp_path: Path) -> None:
    report_numbers.write(tmp_path)
    produced = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert produced, "the generator wrote nothing"
    for rel in produced:
        assert (tmp_path / rel).read_bytes() == (REPORT / rel).read_bytes(), str(rel)
    committed = sorted(p.relative_to(REPORT) for p in (REPORT / "tables").glob("*.tex"))
    assert committed == [p for p in produced if p.parts[0] == "tables"]


def test_every_macro_is_defined_once_and_has_a_source() -> None:
    found = report_numbers.collect()
    names = [n for n, _v, _s, _w in found]
    assert len(names) == len(set(names))
    assert all(n.isalpha() for n in names), "LaTeX macro names are letters only"
    assert all(s for _n, _v, s, _w in found), "every number names its file"


def test_every_macro_the_report_uses_is_generated() -> None:
    import re

    tex = (REPORT / "report.tex").read_text()
    defined = {n for n, _v, _s, _w in report_numbers.collect()}
    notation = set(re.findall(r"\\newcommand\{\\(\w+)\}", (REPORT / "notation.tex").read_text()))
    local = set(re.findall(r"\\newcommand\{\\(\w+)\}", tex))
    used = set(re.findall(r"\\([A-Za-z]+)", tex))
    # every result-like macro (a camel-case name the report did not define itself) is generated
    candidates = {u for u in used if re.fullmatch(r"[a-z]+[A-Z]\w*", u)}
    missing = candidates - defined - notation - local - {"iffull", "fulltrue"}
    assert not missing, sorted(missing)


def test_tex_escapes_specials_and_maps_symbols() -> None:
    assert report_tables.tex("5 % & a_b #1") == "5 \\% \\& a\\_b \\#1"
    assert report_tables.tex("Δ ≥ 4 µs") == "$\\Delta$ $\\ge$ 4 $\\mu$s"
    assert report_tables.tex(">= 0.99") == "$\\ge$ 0.99"


def test_the_worked_example_agrees_with_the_stored_model_values() -> None:
    # t_worked raises if the code's (G9) and root differ from the scorecard's stored values
    body = report_tables.t_worked()
    assert "34.5 & 122.9" in body  # (G9) for C and D, as the model document states
