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


# --------------------------------------------------------------------------- the spec documents
# ⚠️ Added 2026-08-27. Until today EVERY staleness guard in this repo parsed `paper/main.tex`.
# The spec documents were outside the P8 paper audit's scope, so the August corrections (F28/F30/
# F38, S3, S3b) reached the paper and never reached docs/00-07 or TRADEOFFS.md — leaving a dated
# fault line at ~2026-07-30. Three defect classes had survived there for three weeks:
#   * the pre-F30 capacity crossing 233/116 (current: 213/100);
#   * docs/02 §9c's LoRa table, verbatim the PURGED 3-seed run;
#   * retracted finding F18, alive in docs/OPEN_ITEMS.md — its THIRD recurrence.
# A guard that reads one file proves one file. These read the specs.

SPEC_DOCS = [
    "00_PROJECT_CHARTER.md", "01_SYSTEM_MODEL_ARCHITECTURE.md",
    "02_MATHEMATICAL_FOUNDATIONS.md", "04_EVALUATION_PLAN.md",
    "05_REPRODUCTION_GUIDE.md", "06_AGENT_KNOWLEDGE_BASE.md",
    "README.md", "TRADEOFFS.md", "OPEN_ITEMS.md",
]


def _rows(name: str) -> list[dict[str, str]]:
    """A raw CSV as dicts, provenance `#` lines stripped."""
    import csv
    text = (REPO / "results" / "raw" / name).read_text()
    body = [ln for ln in text.splitlines(True) if not ln.startswith("#")]
    return list(csv.DictReader(body))


def _spec_text() -> list[tuple[str, str]]:
    """Live prose only.

    ⚠️ Blockquoted lines are stripped. A correction note must *quote* the value it retracts in
    order to name it, and CLAUDE.md requires retractions stay visible — so a guard that read them
    would forbid the practice it exists to protect. Corrections go in `>` blockquotes; anything
    asserting a live number does not.
    """
    return [(n, _live_prose((REPO / "docs" / n).read_text())) for n in SPEC_DOCS]


def _live_prose(text: str) -> str:
    """Strip correction notes, which must quote the retracted value in order to name it.

    Two forms, because a markdown table cell cannot contain a blockquote:
      * blockquote lines  — `> ⚠️ **Corrected 2026-08-27.** ... read 233/116 ...`
      * inline italics    — `*(Corrected 2026-08-27; the ≈2.8× factor was ...)*`
    Anything else is a live claim and is checked.
    """
    kept = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(">"))
    return re.sub(r"\*\([^()]*?(?:orrected|retracted|pre-F30|purged)[^()]*?\)\*", " ", kept)


def _envelope_v95() -> dict[str, int]:
    """N_max at the V>=0.95 mean criterion, keyed by the artifact's own verdict label."""
    out = {}
    for r in _rows("capacity_envelope.csv"):
        if r["n_local"] == "ENVELOPE" and r["n_max_v95_mean"]:
            out[r["binds"]] = int(r["n_max_v95_mean"])
    return out


class TestSpecDocsMatchArtifacts:
    """docs/00-07 and TRADEOFFS state numbers too, and nothing checked them until 2026-08-27."""

    def test_no_spec_doc_quotes_the_pre_f30_capacity_crossing(self):
        """233/116 are the pre-F30 values. The artifact says 213/100."""
        env = _envelope_v95()
        relaxed = env["optimized delta/B @250ms"]
        compliant = env["optimized delta/B @3GPP100ms/50Hz"]
        assert (relaxed, compliant) == (213, 100), (
            f"capacity_envelope.csv moved to ({relaxed}, {compliant}); "
            "update this guard deliberately"
        )
        bad = []
        for name, text in _spec_text():
            for stale, live in ((233, relaxed), (116, compliant)):
                # "N <= 233" / "N_max = 233" / "N≤233" — a capacity claim, not an incidental integer
                if re.search(rf"N\s*(?:_max)?\s*(?:≤|<=|=|→|->)\s*\*{{0,2}}{stale}\b", text):
                    bad.append(f"{name}: quotes N={stale}, artifact says {live}")
        assert not bad, (
            "the pre-F30 capacity crossing is back in the spec docs:\n  " + "\n  ".join(bad)
        )

    def test_no_spec_doc_revives_the_retracted_optimism_claim(self):
        """⚠️ F18 is retracted. Bor2017 is the MORE OPTIMISTIC model above the crossover."""
        who = {r["n_devices"]: r["who_is_optimistic"] for r in _rows("lora_external_check.csv")}
        assert who.get("50") == "Bor2017", (
            f"lora_external_check.csv now says {who.get('50')} — "
            "re-derive before touching this test"
        )
        bad = [name for name, text in _spec_text()
               if re.search(r"(we|our\s+\w+)\s+(?:is|are)\s+\w*\s*more optimistic", text, re.I)]
        assert not bad, (
            "retracted finding F18 ('we are the more optimistic model vs Bor') is back in: "
            + ", ".join(bad)
            + ". The artifact has who_is_optimistic=Bor2017 at every N>=3."
        )

    def test_lora_table_in_docs02_is_not_the_purged_three_seed_run(self):
        """docs/02 §9c was *verbatim* lora_capacity_3seed_SUPERSEDED.csv until 2026-08-27."""
        purged = {r["n_devices"]: r["delivered_frac"]
                  for r in _rows("lora_capacity_3seed_SUPERSEDED.csv")}
        text = _live_prose((REPO / "docs" / "02_MATHEMATICAL_FOUNDATIONS.md").read_text())
        # 0.2532 / 0.5795 / 0.7731 are the 3-seed values at N=50/20/10 and appear nowhere else.
        fingerprints = [f"{float(purged[n]):.4f}" for n in ("10", "20", "50")]
        found = [f for f in fingerprints if f in text]
        assert not found, (
            f"docs/02 still carries the purged 3-seed LoRa figures {found}. "
            "Rebuild the table from results/raw/lora_capacity.csv (30 seeds, jittered). "
            "⚠️ lora_capacity_30seed.csv is the NO-JITTER CONTROL despite its name."
        )

    def test_lora_n_max_is_never_quoted_as_five(self):
        """F28 corrected N_max 5 -> 3; S3 then bounded it as 3, 95 % CI [2, 3]."""
        rows = {r["n_devices"]: r for r in _rows("lora_capacity.csv")}
        assert float(rows["3"]["delivered_frac"]) >= 0.95 > float(rows["5"]["delivered_frac"]), (
            "lora_capacity.csv no longer puts the V>=0.95 crossing between N=3 and N=5"
        )
        bad = [name for name, text in _spec_text()
               if re.search(r"N_max\s*=\s*\*{0,2}5\b", text)]
        assert not bad, (
            "N_max = 5 is the purged 3-seed value; the 30-seed run gives 3 (95 % CI [2, 3]). In: "
            + ", ".join(bad)
        )

    def test_u_crossing_matches_the_delay_artifact(self):
        """S3b: the V=0.95 crossing is 2.435, interpolated. U~2.80 is the pre-F30 value."""
        rows = [r for r in _rows("ns3_delay_ci.csv")]
        below = max((r for r in rows if float(r["delivered_frac"]) >= 0.95),
                    key=lambda r: float(r["channel_util"]))
        above = min((r for r in rows if float(r["delivered_frac"]) < 0.95),
                    key=lambda r: float(r["channel_util"]))
        u0, v0 = float(below["channel_util"]), float(below["delivered_frac"])
        u1, v1 = float(above["channel_util"]), float(above["delivered_frac"])
        crossing = u0 + (v0 - 0.95) / (v0 - v1) * (u1 - u0)
        assert abs(crossing - 2.435) < 0.01, f"artifact now crosses at U={crossing:.3f}"
        bad = [name for name, text in _spec_text()
               if re.search(r"U\s*(?:≈|~|\\approx)\s*\*{0,2}2\.8", text)]
        assert not bad, (
            f"U~2.80 is the pre-F30 crossing; ns3_delay_ci.csv interpolates {crossing:.3f}. In: "
            + ", ".join(bad)
        )

    def test_ns3_version_in_the_agent_knowledge_base(self):
        """D4 was amended 3.41 -> 3.48 on 2026-07-29; docs/06 still gave 3.41 build steps."""
        kb = (REPO / "docs" / "06_AGENT_KNOWLEDGE_BASE.md").read_text()
        assert "ns-3.48" in kb, "docs/06 no longer names the 3.48 tree it tells you to build"
        assert not re.search(r"wget\s+\S*ns-allinone-3\.41", kb), (
            "docs/06 still instructs a fresh machine to build ns-3.41; D4 was amended to 3.48"
        )
