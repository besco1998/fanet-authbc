"""Documented counts must equal reality (audit I5).

**Why this file exists.** `docs/NEXT_STEPS.md` is the designated session entry point, and it went
stale **three times in two days** — including twice at my own hand, immediately after I rewrote it
*because* it was stale. `CLAUDE.md`'s status board and the literature register drifted the same way.
Every instance had the same shape: a doc asserts a count, the code moves, nothing compares
them.

That is the identical failure that produced four contradictions between `paper/main.tex` and the
artifacts, and it was closed there by `test_paper_matches_artifacts.py` parsing the LaTeX and
checking it against the CSVs. This does the same for the docs.

⚠️ The point is not tidiness. A stale entry point sends the next session to redo finished work —
the 2026-08-06 version listed all of Tier 1 as pending after it was complete.

Each claim below is `(regex over a doc, a cheap ground truth)`. Adding a new asserted count to a doc
without adding it here just recreates the hole, so prefer *not* stating a number over stating an
unchecked one.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CLAUDE = REPO / "CLAUDE.md"
NEXT = REPO / "docs" / "NEXT_STEPS.md"
LITREG = REPO / "docs" / "literature" / "README.md"


def _claim(path: Path, pattern: str) -> int | None:
    """The single integer a doc asserts for `pattern`, or None if the claim is absent."""
    m = re.search(pattern, path.read_text())
    return int(m.group(1)) if m else None


def _collected(marker: str) -> int:
    """Ground truth for test counts: ask pytest, do not guess."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", marker, "--collect-only", "-q", "--no-cov",
         "-p", "no:cacheprovider"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    return sum(int(m) for m in re.findall(r": (\d+)$", out, re.M))


# --------------------------------------------------------------------------- cheap ground truths
def _references() -> int:
    bbl = REPO / "paper" / "main.bbl"
    if not bbl.exists():
        pytest.skip("paper/main.bbl absent — build the paper first")
    return bbl.read_text().count(r"\bibitem")


def _pdfs() -> int:
    return len(list((REPO / "docs" / "literature").glob("*.pdf")))


def _highest_finding() -> int:
    return max(int(m) for m in re.findall(
        r"^## F(\d+)", (REPO / "docs" / "audits" / "model_provenance.md").read_text(), re.M))


def _abstract_words() -> int:
    tex = (REPO / "paper" / "main.tex").read_text()
    i, j = tex.index(r"\begin{abstract}"), tex.index(r"\end{abstract}")
    stripped = re.sub(r"\\[a-zA-Z]+\*?(\[[^]]*\])?({[^}]*})?", " ", tex[i:j])
    return len(stripped.split())


class TestStatusBoardCounts:
    """CLAUDE.md's status board is read at the start of every session."""

    def test_reference_count(self):
        claimed = _claim(CLAUDE, r"\*\*(\d+) refs\*\*")
        assert claimed is not None, "the status board stopped stating a reference count"
        assert claimed == _references(), (
            f"status board says {claimed} refs, paper/main.bbl has {_references()}"
        )

    def test_findings_range(self):
        """⚠️ This said F1--F34 while the register had reached F41."""
        claimed = _claim(CLAUDE, r"Findings \*\*F1[–-]F(\d+)\*\*")
        assert claimed is not None, "the status board stopped stating the findings range"
        assert claimed == _highest_finding(), (
            f"status board says findings run to F{claimed}, "
            f"model_provenance.md reaches F{_highest_finding()}"
        )

    def test_abstract_word_count(self):
        claimed = _claim(CLAUDE, r"abstract \*\*(\d+) w\*\*")
        if claimed is None:
            pytest.skip("status board does not state an abstract length")
        assert abs(claimed - _abstract_words()) <= 3, (
            f"status board says {claimed} words, abstract has {_abstract_words()}"
        )


class TestLiteratureRegisterCount:
    def test_pdf_count(self):
        """⚠️ The register claimed 20 PDFs while 25 sat on disk, five with no entry."""
        claimed = _claim(LITREG, r"\*\*(\d+) PDFs")
        assert claimed is not None, "the register stopped stating a PDF count"
        assert claimed == _pdfs(), f"register says {claimed} PDFs, {_pdfs()} are on disk"


class TestPickUpGuideCounts:
    """⚠️ docs/NEXT_STEPS.md is the designated entry point and has gone stale three times."""

    def test_frozen_gate_size(self):
        claimed = _claim(NEXT, r"the (\d+)-test frozen gate")
        assert claimed is not None, "the pick-up guide stopped stating the frozen-gate size"
        assert claimed == _collected("frozen"), (
            f"guide says a {claimed}-test frozen gate, pytest collects {_collected('frozen')}"
        )

    def test_fast_suite_size(self):
        claimed = _claim(NEXT, r"(\d+) fast tests")
        assert claimed is not None, "the pick-up guide stopped stating the fast-suite size"
        assert claimed == _collected("not frozen"), (
            f"guide says {claimed} fast tests, pytest collects {_collected('not frozen')}"
        )

    def test_reference_count_matches_the_status_board(self):
        """The two documents must not disagree with each other either."""
        guide = _claim(NEXT, r"References \*\*(\d+)\*\*")
        if guide is None:
            pytest.skip("the guide does not state a reference count")
        assert guide == _references(), (
            f"guide says {guide} references, paper/main.bbl has {_references()}"
        )
