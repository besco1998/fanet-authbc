"""The paper prints no typed results (review 2026-10; replaces `test_paper_matches_artifacts.py`).

**Why this file exists, and what it replaced.** The previous paper typed its numbers into LaTeX,
and 44 tests parsed tables and sentences back out to compare them with the artifacts. That caught
drift one table at a time, after someone had thought to write the parser: a capacity table sat two
audits behind its CSV for weeks, and a count of excluded data rates outlived the arithmetic that
produced it. The rewritten paper has no typed results. Every one is a macro, every macro is
defined in `paper/numbers.tex`, and that file is written by `analysis/paper_numbers.py` from
`results/`. So the question "does the paper match the artifacts" reduces to three checks:

* `numbers.tex` is exactly what the generator writes now, with nothing missing;
* the paper contains no decimal number that is not a parameter;
* the generator's own cross-checks pass — where a sentence states a verdict rather than a number
  ("eight of twelve", "R = 4 does not meet V"), the generator refuses to run if the artifact
  no longer says so.

The remaining tests hold the claims the review found overstated or wrong out of the text.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper"

_spec = importlib.util.spec_from_file_location("paper_numbers",
                                               REPO / "analysis" / "paper_numbers.py")
assert _spec and _spec.loader
gen = importlib.util.module_from_spec(_spec)
sys.modules["paper_numbers"] = gen
_spec.loader.exec_module(gen)

TEX = (PAPER / "main.tex").read_text(encoding="utf-8")
FIG = (PAPER / "fig_system.tex").read_text(encoding="utf-8")
NUMBERS = (PAPER / "numbers.tex").read_text(encoding="utf-8")
DEFINED = dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}", NUMBERS))
BODY = "\n".join(ln for ln in TEX.splitlines() if not ln.lstrip().startswith("%"))


def _section(title: str) -> str:
    start = BODY.index(f"\\section{{{title}}}")
    nxt = BODY.find("\\section", start + 10)
    return BODY[start:nxt if nxt > 0 else len(BODY)]


class TestNumbersAreGenerated:
    def test_numbers_tex_is_what_the_generator_writes(self) -> None:
        gen.MISSING.clear()
        fresh = gen.render()
        assert not gen.MISSING, f"no artifact holds: {sorted(set(gen.MISSING))}"
        assert fresh == NUMBERS, "paper/numbers.tex is stale — run analysis/paper_numbers.py"

    def test_no_value_is_a_placeholder(self) -> None:
        assert not [k for k, v in DEFINED.items() if "?" in v]

    def test_every_generated_number_is_used(self) -> None:
        """A number nobody prints is a number nobody will notice going wrong.

        The thesis reads the same file (`make thesis` copies it), so a macro may be its alone.
        """
        thesis = "".join(p.read_text(encoding="utf-8") for p in (REPO / "thesis").glob("ch*.tex"))
        used = set(re.findall(r"\\([A-Za-z]+)", TEX + FIG + thesis))
        assert not sorted(set(DEFINED) - used)

    def test_the_thesis_uses_no_number_the_generator_does_not_define(self) -> None:
        """A thesis macro that looks like a result but is not generated fails the build."""
        thesis = "".join(p.read_text(encoding="utf-8") for p in (REPO / "thesis").glob("*.tex"))
        prefixes = ("nmax", "nsat", "bpr", "frm", "cert", "fld", "hdr", "loss", "px", "lora",
                    "hw", "val", "ratio", "save", "ncpu", "cpu", "ex", "en", "fr")
        looks_generated = {u for u in re.findall(r"\\([A-Za-z]+)", thesis)
                           if u.startswith(prefixes) and any(c.isupper() for c in u)}
        stray = sorted(looks_generated - set(DEFINED) - {"frontmatter", "enspace", "ensuremath"})
        assert not stray, stray

    def test_the_paper_loads_the_generated_file(self) -> None:
        assert "\\input{numbers}" in BODY


class TestNoTypedResults:
    # Parameters, thresholds and names of standards. Anything else with a decimal point is a
    # result and must be a macro.
    ALLOWED = {"0.05", "0.95", "0.02", "0.01", "0.2", "2.5", "97.5", "802.11", "802.15", "3.48"}

    def test_every_decimal_in_the_text_is_a_parameter(self) -> None:
        # in the figure source a length ("1.10cm") or a coordinate ("(0,1.62)") places a box
        drawing = re.sub(r"\(\s*[\d.]+\s*,\s*[\d.]+\s*\)", "", FIG)
        found = {m.group(0) for m in
                 re.finditer(r"(?<![A-Za-z])\d+\.\d+(?!\d*(?:cm|pt|em))", BODY + drawing)}
        assert not sorted(found - self.ALLOWED), (
            "typed results in the paper; define them in analysis/paper_numbers.py instead")

    def test_tables_hold_macros_not_numbers(self) -> None:
        for label in ("tab:ladder", "tab:loss", "tab:fresh", "tab:capacity", "tab:energy",
                      "tab:excl"):
            start = BODY.index(f"\\label{{{label}}}")
            table = BODY[start:BODY.index("\\end{tabular}", start)]
            rows = [ln for ln in table.splitlines() if "&" in ln and ln.rstrip().endswith("\\\\")]
            assert rows, label
            cells = [c.strip() for ln in rows for c in ln.removesuffix("\\\\").split("&")]
            typed = [c for c in cells if re.fullmatch(r"[\d.,]{3,}", c)]
            assert not typed, f"{label} has typed cells {typed}"


class TestWhatTheReviewFoundIsNotInTheText:
    @pytest.mark.parametrize("phrase", [
        "Hardware Validation",          # the title promised a validation the paper does not hold
        "blockchain-grade",
        "Citation integrity",           # a claim that belongs in a check that runs
        "four of seven", "three of seven",   # the data-rate count was of seven; there are twelve
        "misses by six",
        "integer-keyed header",         # "…rescues DR3": withdrawn, audit F47
        "58.7",                         # the saving of a design that did not meet V (F46)
        "pre-registered",               # process history: methods paper and thesis (R12)
        "we resist", "honestly", "the honest", "honest answer",
    ])
    def test_phrase_is_gone(self, phrase: str) -> None:
        assert phrase.lower() not in BODY.lower()

    def test_the_wrong_attributions_are_gone(self) -> None:
        assert not re.search(r"\bBor\b|plos2025clas|bor2017", BODY)
        assert "haxhibeqiri2017lora" in BODY and "li2025clas" in BODY

    def test_rather_than_is_no_longer_a_tic(self) -> None:
        """The review counted it on 45 lines."""
        assert BODY.count("rather than") <= 3

    def test_the_abstract_is_short(self) -> None:
        abstract = BODY[BODY.index("\\begin{abstract}"):BODY.index("\\end{abstract}")]
        words = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", " w ", abstract).split()
        assert len(words) <= 200, len(words)

    def test_authbc_is_defined_where_it_is_first_used_in_the_body(self) -> None:
        intro = _section("Introduction")
        first = intro.index("AUTHBC")
        assert "hash-chained ledger" in intro[first:first + 160]


class TestWhatTheReviewAskedForIsInTheText:
    def test_related_work_covers_stream_signing_and_per_message_practice(self) -> None:
        related = _section("Background and Related Work")
        for key in ("mavlink2signing", "wong1999flows", "gennaro1997streams", "perrig2000emss",
                    "haber1991timestamp", "etsi_ts103097"):
            assert key in related, key

    def test_there_is_a_threat_model_that_says_what_is_not_protected(self) -> None:
        model = _section("System and Threat Model")
        for needle in ("Adversary", "What is protected", "What is not", "Replay", "Equivocation"):
            assert needle in model, needle

    def test_the_exclusion_is_the_first_result(self) -> None:
        """The review asked for it first; an earlier rewrite of this paper put it after 802.11."""
        assert BODY.index("\\section{Low-Rate Links") < BODY.index("\\section{Results on 802.11}")
        abstract = BODY[BODY.index("\\begin{abstract}"):BODY.index("\\end{abstract}")]
        assert abstract.index("\\exclCount") < abstract.index("\\nmaxLeanDesign")

    def test_the_title_keeps_its_framing_and_drops_only_the_validation_it_did_not_hold(
            self) -> None:
        title = BODY[BODY.index("\\title{"):BODY.index("\\author{")]
        assert "Feasibility Boundaries for Authenticated UAV Telemetry" in title
        assert "An Exclusion Bound and a Capacity Envelope" in " ".join(title.split())

    def test_the_body_uses_the_two_nouns_its_title_promises(self) -> None:
        """A title that names something the body never names is how "Hardware Validation" stood
        over a two-node airtime check."""
        body = BODY[BODY.index("\\section{Introduction}"):]
        assert "exclusion bound" in body and "capacity envelope" in body

    def test_the_one_line_message_does_not_overclaim_about_signature_schemes(self) -> None:
        """'No signature scheme changes that' was the over-claim: a 48 B or 13 B authenticator
        changes the exclusion, and BLS is excluded by CPU. The claim is about 64 B schemes."""
        intro = _section("Introduction")
        assert "decide what can run" in intro
        assert "64\\,B" in intro[intro.index("decide what can run"):][:160]

    def test_the_exclusion_states_its_four_scope_conditions(self) -> None:
        low = _section("Low-Rate Links: Where No Batch Helps")
        assert all(f"({roman})" in low for roman in ("i", "ii", "iii", "iv"))
        assert "255" in low                       # the LoRa PHY itself is not excluded

    def test_the_capacity_model_cites_the_broadcast_model_not_the_unicast_one(self) -> None:
        constraints = _section("Constraints")
        channel = constraints[constraints.index("\\textbf{Channel.}"):]
        assert "machen2008" in channel[:900]

    def test_the_clas_table_says_whose_numbers_it_reports(self) -> None:
        start = BODY.index("\\label{tab:clas}")
        table = BODY[BODY.rfind("\\begin{table}", 0, start):BODY.index("\\end{table}", start)]
        assert "as reported in" in table and table.count("$^\\ast$") >= 5

    def test_limitations_say_what_is_simulated_and_what_is_synthetic(self) -> None:
        limits = _section("Limitations")
        for needle in ("Capacities are simulated", "Telemetry is synthetic", "Multi-hop",
                       "Only the sender is metered"):
            assert needle in limits, needle
        # until 2026-10-09 this read "Contention is simulated"; two radios have since been
        # measured, and the limitation is that no capacity has
        assert "between two radios\nonly" in limits or "between two radios only" in limits

    def test_there_is_a_short_ai_statement(self) -> None:
        start = BODY.index("\\section*{Use of Generative AI}")
        statement = BODY[start:BODY.index("\\bibliographystyle", start)]
        assert 10 < len(statement.split()) < 60

    def test_the_abstract_is_about_180_words(self) -> None:
        """The review asked for about 180; the looser bound above let it stand at about 200 as
        printed. This counter gives 179 for the abstract that prints as about 180 words."""
        abstract = BODY[BODY.index("\\begin{abstract}"):BODY.index("\\end{abstract}")]
        plain = re.sub(r"\\[a-zA-Z]+", "w", abstract.replace("\\begin{abstract}", ""))
        assert len(re.sub(r"[{}$~]", " ", plain).split()) <= 185

    def test_captions_are_one_or_two_lines(self) -> None:
        """The review asked for captions of one or two lines. A column holds about eleven words
        a line; the one full-width table holds about twenty-three."""
        too_long = {}
        for caption, label in re.findall(r"\\caption\{(.*?)\}\s*\\label\{([^}]+)\}", BODY, re.S):
            plain = re.sub(r"\\cite\{[^}]*\}", "", caption)
            words = len(re.sub(r"[{}$~]", " ", re.sub(r"\\[a-zA-Z]+", "w", plain)).split())
            if words > (46 if label == "tab:ladder" else 27):
                too_long[label] = words
        assert not too_long, too_long

    def test_the_hash_chain_is_not_credited_to_the_bitcoin_paper(self) -> None:
        related = _section("Background and Related Work")
        assert "haber1991timestamp" in related and "nakamoto2008" not in BODY

    def test_the_ladder_marks_every_size_that_is_not_an_emitted_frame(self) -> None:
        """The caption once said "all lean sizes are emitted frames"; row 7 is a sum of parts,
        and so is every first-format row."""
        ladder = {(r["format"], r["rung"]): r["sized_from"]
                  for r in gen.rows(gen.RAW / "design_ladder.csv")
                  if r["op"] == "adopted" and r["scheme"] == "ed25519"}
        start = BODY.index("\\label{tab:ladder}")
        table = BODY[start:BODY.index("\\end{table*}", start)]
        first_header = table[table.index("First format"):table.index("\\\\", table.index(
            "First format"))]
        assert "$^\\dagger$" in first_header
        assert all(ladder["first", r] != "emitted frames"
                   for r in ("inline-1", "inline-b", "batch-cbor", "batch-delta"))
        marked = {"batch-keys": True, "inline-1": False, "inline-b": False, "batch-delta": False}
        rows_by_rung = dict(zip(("inline-1", "inline-b", "batch-keys", "batch-delta"),
                                re.findall(r"^[5-8] & (.*?) & [14] &", table, re.M), strict=True))
        for rung, is_marked in marked.items():
            assert ("dagger" in rows_by_rung[rung]) is is_marked, rung
            assert (ladder["lean", rung] != "emitted frames") is is_marked, rung

    def test_the_twelve_data_rates_are_named_by_modulation(self) -> None:
        """The review asked for a note on DR7, which is FSK and not LoRa."""
        low = _section("Low-Rate Links: Where No Batch Helps")
        assert "seven LoRa (DR0--DR6), one FSK (DR7) and four LR-FHSS (DR8--DR11)" in low
        kind = {r["dr"]: r["modulation"].strip('"').split()[0]
                for r in gen.rows(gen.RAW / "exclusion_matrix.csv")}
        assert len(kind) == 12
        assert [dr for dr, k in kind.items() if k == "FSK"] == ["7"]
        assert sorted(int(dr) for dr, k in kind.items() if k == "LoRa") == list(range(7))
        assert sorted(int(dr) for dr, k in kind.items() if k == "LR-FHSS") == [8, 9, 10, 11]

    def test_the_lora_capacity_names_the_configuration_that_was_simulated(self) -> None:
        """The paragraph gave the 242 B frame's rate and the 222 B simulation's total, the same
        kind of mismatch the review listed under inconsistencies."""
        low = _section("Low-Rate Links: Where No Batch Helps")
        carry = low[low.index("What the feasible rates carry"):]
        for macro in ("\\loraSimBytes", "\\loraSimRecs", "\\loraSimRate", "222"):
            assert macro in carry, macro
        assert carry.index("\\loraSimRate") < carry.index("\\loraAgg")
