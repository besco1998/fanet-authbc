"""Every figure the paper includes must be regenerable from the frozen CSVs (audit I6).

**Why this file exists.** `fig_e5_codesign.png` shipped in the paper for ten days plotting
H_f = 40 B after B1 measured it at 44 B. Its caption said "104 B to 26.0 B" while the
table beside it said 108 to 27.0, and nothing compared them. Two further figures (`e4_crossover`,
`fig_envelope`) were equally stale.

The cause was structural: the frozen gate re-derives CSVs, and `make figures` regenerated only the
E1--E3 subset, so the other four generators were never run by any gate. A figure could therefore
drift from the data it claims to plot while every check passed --- the same shape as the four
paper-vs-artifact contradictions, one layer further out.

⚠️ This test asserts *regenerability*, not byte-equality of the committed PNGs. Matplotlib output is
not portable across versions, so byte-comparing images would fail for reasons unrelated to
correctness. What it checks is that every generator still runs against the current frozen data and
produces every figure the paper cites --- which is what would have caught the H_f drift.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FIGDIR = REPO / "results" / "figures"
GENERATORS = [
    "figures_e123.py",
    "figures_e4.py",
    "figures_e5.py",
    "figures_envelope_lora.py",
    "figures_ns3.py",
    "figures_nmax.py",
]


def _figures_cited_by_the_paper() -> set[str]:
    tex = (REPO / "paper" / "main.tex").read_text()
    return set(re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", tex))


def test_every_figure_the_paper_cites_exists():
    missing = sorted(f for f in _figures_cited_by_the_paper() if not (FIGDIR / f).exists())
    assert not missing, f"paper cites figures that are not in results/figures/: {missing}"


def test_the_paper_cites_its_two_data_figures():
    """The exclusion and the capacity search each have a figure drawn from their artifact.

    (Until 2026-10 this test required `fig_envelope.png`, the capacity envelope computed from one
    load ceiling. The direct search replaced that envelope — docs/NMAX_DIRECT_EXPECTATIONS.md —
    and the figure went with it; the thesis keeps it, labelled as the approximation it is.)
    """
    cited = _figures_cited_by_the_paper()
    for required in ("fig_t6_exclusion.png", "fig_nmax_direct.png"):
        assert required in cited, f"{required} is generated but no longer cited by the paper"


@pytest.mark.frozen
@pytest.mark.parametrize("generator", GENERATORS)
def test_generator_still_runs_against_the_frozen_data(generator, tmp_path):
    """A generator that no longer runs cannot keep its figure honest."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "analysis" / generator)],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, (
        f"{generator} failed against the current frozen CSVs — a figure in the paper is no longer "
        f"reproducible:\n{proc.stderr[-600:]}"
    )


@pytest.mark.frozen
def test_make_figures_covers_every_generator():
    """⚠️ `make figures` ran only figures_e123 for weeks, which is how three figures went stale."""
    makefile = (REPO / "Makefile").read_text()
    block = makefile.split("figures:", 1)[1].split("\n\n", 1)[0]
    uncovered = [g for g in GENERATORS if g not in block]
    assert not uncovered, (
        f"`make figures` does not run {uncovered} — those figures can drift from the data silently"
    )


def _generator_sources() -> dict[str, str]:
    return {g: (REPO / "analysis" / g).read_text() for g in GENERATORS}


def test_no_generator_hardcodes_a_stale_ns3_version():
    """⚠️ `fig_ns3_bianchi.png` said "NS-3 3.41" while the paper said 3.48 in four places.

    The paper's own Limitations section documents the 3.41->3.48 migration and reports that
    marginal-link figures moved substantially because of it, so the figure was labelling the
    data with the version it was NOT produced under.
    """
    tex = (REPO / "paper" / "main.tex").read_text()
    # "ns-3.48" is the release's own name; "NS-3 3.48" is how the generators label it
    paper_versions = {a or b for a, b in
                      re.findall(r"(?i)\bns-(3\.\d+)|\bns-3[~ ]v?(3\.\d+)", tex)}
    assert paper_versions, "the paper no longer states which ns-3 release produced its results"
    current = max(paper_versions, key=lambda v: tuple(int(x) for x in v.split(".")))
    bad = []
    for name, src in _generator_sources().items():
        for v in set(re.findall(r"NS-3 (\d+\.\d+)", src)):
            if v != current:
                bad.append(f"{name} hardcodes NS-3 {v}; the paper's current version is {current}")
    assert not bad, "\n".join(bad)


def test_no_generator_carries_a_pending_phase_note():
    """⚠️ `fig_e5_codesign.png` footed "energy/power are nominal (pending P7)" long after P7 closed.

    The paper states both power figures are measured on the Pi 4 (decision D8), so the figure
    contradicted the text it sat beside — and understated the work.
    """
    bad = [f"{name}: {m.group(0)!r}"
           for name, src in _generator_sources().items()
           for m in re.finditer(r"pending P\d+|are nominal", src)]
    assert not bad, (
        "figure captions still advertise unfinished phases:\n" + "\n".join(bad)
    )


def test_the_naive_factor_is_derived_not_hardcoded():
    """It read "16x" for weeks after the 30-seed regeneration moved it to 17.3x."""
    src = _generator_sources()["figures_ns3.py"]
    assert not re.search(r"fails, \d+(\.\d+)?x at N=\d+", src), (
        "figures_ns3.py hardcodes the naive-reduction factor again; derive it from the CSV"
    )
