"""Every bibliography entry is checked by a program, and stays checked (audit F49, 2026-10-06).

Four entries of `paper/refs.bib` carried wrong metadata. One paper was cited under the names of
the authors of a *different* paper — in the paper, the thesis, the code and seven documents — for
two months; another listed four authors who did not write it. Each had been read, each was
recorded as verified, and the paper said so in a paragraph.

`analysis/verify_citations.py` (`make verify-citations`) compares each entry with its registry
record and writes `results/raw/citation_check.csv`. That needs the network. These tests do not:
they hold that the recorded check covers every entry, passed, and is not stale.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BIB = REPO / "paper" / "refs.bib"
ARTIFACT = REPO / "results" / "raw" / "citation_check.csv"

_spec = importlib.util.spec_from_file_location("verify_citations",
                                               REPO / "analysis" / "verify_citations.py")
assert _spec and _spec.loader
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)

LITERATURE = REPO / "docs" / "literature"
# Sources that are held and read but not redistributed here (decision of 2026-10-07): file ->
# its manifest row. A fresh clone does not have them; the author's machine does.
HELD_LOCALLY = {r["file"]: r for r in csv.DictReader(
    ln for ln in (LITERATURE / "HELD_LOCALLY.csv").read_text(encoding="utf-8").splitlines()
    if not ln.startswith("#"))}

ENTRIES = vc.parse_bib(BIB.read_text(encoding="utf-8"))
ROWS = {r["key"]: r for r in csv.DictReader(
    ln for ln in ARTIFACT.read_text(encoding="utf-8").splitlines() if not ln.startswith("#"))}


class TestTheRecordedCheckIsCompleteAndCurrent:
    def test_it_covers_exactly_the_entries_in_the_bibliography(self) -> None:
        unchecked, gone = sorted(set(ENTRIES) - set(ROWS)), sorted(set(ROWS) - set(ENTRIES))
        assert not unchecked and not gone, (
            f"run `make verify-citations`: unchecked {unchecked}, no longer in the bib {gone}")

    @pytest.mark.parametrize("key", sorted(ENTRIES))
    def test_the_entry_passed(self, key: str) -> None:
        assert ROWS[key]["status"] in ("ok", "document"), (
            f"{key}: {ROWS[key]['status']} — bib says [{ROWS[key]['authors_bib']}], "
            f"the registry says [{ROWS[key]['authors_registry']}]")

    @pytest.mark.parametrize("key", sorted(ENTRIES))
    def test_the_entry_has_not_been_edited_since_it_was_checked(self, key: str) -> None:
        assert ROWS[key]["fingerprint"] == vc.fingerprint(ENTRIES[key]), (
            f"{key} was edited after its last check; run `make verify-citations`")

    def test_an_entry_with_an_identifier_was_checked_against_a_registry(self) -> None:
        for key, entry in ENTRIES.items():
            if entry["doi"] or entry["eprint"]:
                assert ROWS[key]["status"] == "ok" and ROWS[key]["registry"], key


class TestWhatCannotBeCheckedSaysSo:
    """A standard, a datasheet, source code or a web page has no registry record."""

    def test_such_an_entry_names_the_document_that_was_read(self) -> None:
        for key, entry in ENTRIES.items():
            if vc.kind_of(entry) == "document":
                assert entry["held"], f"{key} has no doi, no eprint and no `held` field"

    def test_a_held_file_is_in_the_repository_or_in_the_manifest_of_what_is_not(self) -> None:
        for key, entry in ENTRIES.items():
            held = entry["held"]
            if held and not held.startswith(("web:", "software:")):
                path = REPO / held
                assert path.is_file() or path.name in HELD_LOCALLY, (
                    f"{key}: held file {held} is neither in the repo nor in HELD_LOCALLY.csv")


class TestWhatIsHeldButNotRedistributed:
    """Eleven PDFs were kept out of the public repository on 2026-10-07; more, read on
    2026-10-08 and 2026-10-09, joined them — the last four for the related-work gaps a review
    of the paper named (audit F83). "Held and read" must
    still be checkable: the manifest gives each file's SHA-256, and wherever the file is present
    it has to be that file."""

    def test_the_manifest_is_well_formed(self) -> None:
        assert len(HELD_LOCALLY) == 24
        for name, row in HELD_LOCALLY.items():
            assert name.endswith(".pdf") and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), name
            assert int(row["bytes"]) > 0 and row["obtain_from"] and row["document"], name
            assert row["bib_key"] in ENTRIES, f"{name} names a bibliography key that is gone"

    def test_a_file_that_is_present_is_the_file_that_was_read(self) -> None:
        for name, row in HELD_LOCALLY.items():
            path = LITERATURE / name
            if path.is_file():
                data = path.read_bytes()
                assert (hashlib.sha256(data).hexdigest(), len(data)) == \
                    (row["sha256"], int(row["bytes"])), f"{name} is not the manifest's document"

    def test_none_of_them_is_tracked_and_all_are_ignored(self) -> None:
        tracked = subprocess.run(["git", "ls-files", "docs/literature"], cwd=REPO,
                                 capture_output=True, text=True)
        if tracked.returncode != 0:
            pytest.skip("not a git checkout")
        names = {Path(p).name for p in tracked.stdout.split()}
        assert not names & set(HELD_LOCALLY), "a file that is not to be redistributed is tracked"
        ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
        assert all(f"docs/literature/{name}" in ignore for name in HELD_LOCALLY)

    def test_a_registry_name_override_is_backed_by_the_document(self) -> None:
        """`registryauthors` exists for a registry that abbreviates a name; it must not become a
        way to make any entry pass, so the true spelling has to be readable from a held file."""
        overridden = [k for k, e in ENTRIES.items() if e["registryauthors"]]
        assert overridden == ["sobati2025fragmentsec"]
        for key in overridden:
            assert (REPO / ENTRIES[key]["held"]).is_file()


class TestNothingInternalIsPrinted:
    """A `note` field is typeset in the reference list (review comment 6.3)."""

    WORKFLOW = re.compile(r"verified|held|prior art|docs/|\bPDF\b|\d{4}-\d{2}-\d{2}", re.I)

    def test_no_note_carries_a_working_remark(self) -> None:
        for key, entry in ENTRIES.items():
            assert not self.WORKFLOW.search(entry["note"]), f"{key}: note = {entry['note']!r}"

    def test_no_comparison_operator_is_left_in_text_mode(self) -> None:
        """`<` in a note printed as an inverted exclamation mark in reference [29]."""
        for key, entry in ENTRIES.items():
            assert "<" not in entry["note"] and ">" not in entry["note"], key


class TestTheFourCorrectedEntries:
    def test_the_lora_scalability_paper_is_haxhibeqiri_et_al(self) -> None:
        assert vc.family_names(ENTRIES["haxhibeqiri2017lora"]["author"]) == [
            "haxhibeqiri", "van den abeele", "moerman", "hoebeke"]
        assert "bor2017lora" not in ENTRIES

    def test_the_clas_paper_is_li_et_al(self) -> None:
        assert vc.family_names(ENTRIES["li2025clas"]["author"]) == ["li", "shen", "huang", "wu"]
        assert "plos2025clas" not in ENTRIES

    def test_the_interference_paper_lists_all_four_authors_by_their_names(self) -> None:
        assert vc.people(ENTRIES["titolara2025interference"]["author"]) == [
            ("tito lara", "mateo"), ("dominguez limaico", "mauricio"), ("maya olalla", "edgar"),
            ("cuzme rodriguez", "fabian")]

    def test_the_ndss_paper_has_its_full_title(self) -> None:
        assert ENTRIES["ndss2024pqv2v"]["title"].startswith("When Cryptography Needs a Hand")

    def test_the_wrong_name_is_gone_from_everything_that_is_built_or_run(self) -> None:
        offenders = []
        for path in [*REPO.glob("paper/*.tex"), *REPO.glob("thesis/*.tex"),
                     *REPO.glob("src/authbc/**/*.py"), *REPO.glob("experiments/**/*.yaml")]:
            text = path.read_text(encoding="utf-8")
            # the code keeps ONE dated correction note that names the old attribution
            text = re.sub(r"⚠️ Corrected 2026-10-06 \(audit F49\).*?`bor2017_\*`\.", "", text,
                          flags=re.S)
            if re.search(r"\bBor\b|bor2017|plos2025clas", text):
                offenders.append(str(path.relative_to(REPO)))
        assert not offenders, f"the retracted attribution is back in {offenders}"

    def test_the_paper_does_not_claim_a_check_it_cannot_have_made(self) -> None:
        """The removed paragraph said every Related Work reference was confirmed against
        Crossref; 14 of the 18 references that section cited had no DOI recorded."""
        tex = (REPO / "paper" / "main.tex").read_text(encoding="utf-8")
        assert "Crossref" not in tex and "Citation integrity" not in tex


class TestEveryCitedKeyExists:
    @pytest.mark.parametrize("tex", sorted(
        str(p.relative_to(REPO)) for p in [*REPO.glob("paper/*.tex"), *REPO.glob("thesis/*.tex")]))
    def test_no_citation_points_at_a_missing_entry(self, tex: str) -> None:
        text = (REPO / tex).read_text(encoding="utf-8")
        cited = {k.strip() for group in re.findall(r"\\cite\{([^}]*)\}", text)
                 for k in group.split(",")}
        assert cited <= set(ENTRIES), f"{tex} cites unknown keys {sorted(cited - set(ENTRIES))}"


class TestTheComparisonCatchesWhatItWasBuiltFor:
    """The checker is the guard, so it is tested against the defects that motivated it."""

    def test_the_authors_of_a_different_paper(self) -> None:
        bib = vc.people("Bor, Martin and Roedig, Utz and Voigt, Thiemo and Alonso, Juan M.")
        reg = [("Haxhibeqiri", "Jetmir"), ("Van den Abeele", "Floris"), ("Moerman", "Ingrid"),
               ("Hoebeke", "Jeroen")]
        assert not vc.authors_match(bib, reg)

    def test_a_wrong_given_name_under_the_right_family_name(self) -> None:
        assert not vc.authors_match(vc.people("Tito-Lara, Jhon"), [("Tito-Lara", "Mateo")])
        assert vc.authors_match(vc.people("Tito-Lara, Mateo"), [("Tito-Lara", "Mateo")])

    def test_a_truncated_author_list(self) -> None:
        assert not vc.authors_match(vc.people("Maya-Olalla, Edgar and others"),
                                    [("Maya-Olalla", "Edgar"), ("Cuzme-Rodríguez", "Fabián")])

    def test_a_shortened_title(self) -> None:
        assert vc.title_match(
            "Practical Post-Quantum Authentication for Vehicle-to-Vehicle Communications",
            "When Cryptography Needs a Hand: Practical Post-Quantum Authentication for V2V "
            "Communications") < vc.TITLE_MATCH_MIN

    def test_registry_conventions_that_are_not_defects(self) -> None:
        # a full name stored in the family field (Crossref), and full names only (arXiv)
        assert vc.authors_match(vc.people("Wong, Chung Kei and Lam, Simon S."),
                                [("Chung Kei Wong", ""), ("Lam", "S.S.")])
        assert vc.authors_match(vc.people("Al majmaie, Sufian"), [("Sufian Al majmaie", "")])
        # accents and LaTeX markup
        assert vc.authors_match(vc.people(r'G{\"u}ndo{\u{g}}an, Cenk'), [("Gündoğan", "Cenk")])
        # a corporate author whose name contains " and "
        nist = vc.people("{{National Institute of Standards and Technology}}")
        assert nist == [("national institute of standards and technology", "")]
        assert vc.authors_match(nist, [("National Institute of Standards and Technology (US)", "")])

    def test_a_fingerprint_moves_with_every_compared_field(self) -> None:
        base = dict(ENTRIES["bianchi2000"])
        for field, value in (("author", "Someone, Else"), ("title", "Another title"),
                             ("year", "1999"), ("doi", "10.1/x")):
            assert vc.fingerprint({**base, field: value}) != vc.fingerprint(base)


class TestTheFourSourcesAReviewNamedAsMissing:
    """Audit F83 (open item G34). A review of the paper listed four bodies of work a networking
    reviewer would look for. Each was obtained from an open copy and read before it was cited.
    Held here: that each is cited for what its register entry says was read in it, with the
    figure or the words quoted from it, and that what was NOT obtained is not cited."""

    PAPER = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
    BACKGROUND = re.sub(r"\s+", " ", (REPO / "thesis" / "ch02_background.tex").read_text())
    THEORY = re.sub(r"\s+", " ", (REPO / "thesis" / "ch04_theory.tex").read_text())
    REGISTER = (LITERATURE / "README.md").read_text(encoding="utf-8")
    KEYS = ("skordoulis2008aggregation", "pannetrat2003multicast", "strohmeier2015adsb",
            "yates2021aoi")

    def test_each_is_held_read_and_cited_in_both_documents(self) -> None:
        thesis = self.BACKGROUND + self.THEORY
        held = {row["bib_key"] for row in HELD_LOCALLY.values()}
        for key in self.KEYS:
            assert key in ENTRIES and key in held, key
            assert f"{key}}}" in self.PAPER and f"{key}}}" in thesis, key
        assert self.REGISTER.count("`READ 2026-10-09`") >= 4

    def test_aggregation_is_cited_for_excluding_broadcast_in_its_own_words(self) -> None:
        assert "whose aggregates are addressed to one receiver and exclude " \
               "broadcast~\\cite{skordoulis2008aggregation}" in self.PAPER
        assert '"Thus, broadcasting or multicasting is not allowed" (p. 44)' in self.REGISTER
        assert "broadcasting or multicasting is not allowed" in self.BACKGROUND

    def test_the_erasure_code_scheme_is_cited_with_a_figure_of_its_table(self) -> None:
        """Its Table 1: 128 B signature, 16 B hashes, blocks of 16 packets, 5 % loss: 10 B."""
        assert "for 10\\,B per packet in blocks of sixteen at 5\\% loss and a latency of one " \
               "block~\\cite{pannetrat2003multicast}" in self.PAPER
        assert "**10 B per packet for blocks of 16 at p = 0.05**" in self.REGISTER

    def test_ads_b_is_cited_for_its_fifty_six_bits(self) -> None:
        assert "its 112-bit messages leave 56 bits for data" in self.PAPER
        assert '"only the 56 bit ME field can be used to transmit arbitrary data" (p. 2)' \
            in self.REGISTER

    def test_the_freshness_bound_is_named_a_peak_age_only_where_no_frame_is_lost(self) -> None:
        assert "the bound is on the \\emph{peak age} of information~\\cite{yates2021aoi} at a " \
               "receiver that loses no frame" in self.PAPER
        assert "exactly, when no frame is lost" in self.THEORY
        assert "It does not change the convention; it says what the convention bounds." \
            in self.THEORY
        assert "it is not a result of ours" in self.REGISTER

    def test_what_was_not_obtained_is_not_cited(self) -> None:
        """Kaul et al. 2012 and Park et al. 2003 are closed access; the survey and Pannetrat &
        Molva stand in their place, and the register says so."""
        bib = (REPO / "paper" / "refs.bib").read_text(encoding="utf-8")
        for doi in ("10.1109/INFCOM.2012.6195689", "10.1145/762476.762480"):
            assert doi not in bib
            assert doi in self.REGISTER
        assert "SAIDA, which was not obtained for this thesis" in self.BACKGROUND


class TestTheClosedFormIsQuotedFromTheGeneratedNumbers:
    """Open item G33: in docs/02 and under test since follow-up F5; in the paper since F83."""

    def test_the_paper_gives_the_exact_form_and_both_figures(self) -> None:
        paper = re.sub(r"\s+", " ", (REPO / "paper" / "main.tex").read_text(encoding="utf-8"))
        numbers = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                                  (REPO / "paper" / "numbers.tex").read_text(encoding="utf-8")))
        assert (numbers["closedWorst"], numbers["closedMean"]) == ("5.5", "2.3")
        assert "with the detection term and nothing fitted, solving it for 5\\% gives the " \
               "\\modelCells{} crossings within \\closedWorst\\% (mean \\closedMean\\%)" in paper
        assert "$\\rho\\,[1-(1-1/W)^{\\rho/(1-\\rho)}]$" in paper
