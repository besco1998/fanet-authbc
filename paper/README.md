# paper/ — the two papers

| file | what it is | build |
|---|---|---|
| `main.tex` | **The results paper.** The AUTHBC frame, the design ladder, loss, capacity, the low-rate exclusion, comparison with published schemes | `make paper` |
| `methods.tex` | **The methods paper.** Nine ways this study produced a wrong number, with the guard that caught each — six found by self-audit, three by an outside reader | `make paper-methods` |
| `numbers.tex` | ⚠️ **Generated — do not edit.** Every result either paper prints | written by `analysis/paper_numbers.py` |
| `fig_system.tex` | The frame, drawn to scale (TikZ) | included by `main.tex` |
| `refs.bib` | The bibliography, shared with the thesis | checked by `make verify-citations` |
| `SUBMISSION_CHECKLIST.md` | What must be true before either is sent anywhere | — |

## The paper has no typed results

A number typed into LaTeX is a copy, and copies drifted here three times. Every result is a macro
(`\bprLeanDesign`, `\nmaxLeanDesign`, …) defined in `numbers.tex`, which
`analysis/paper_numbers.py` writes from the files in `../results/`. A sentence that states a
verdict rather than a number — "eight of twelve", "does not meet the target" — is checked by the
same script, which stops if the artifact no longer says so.

* Change a result → re-run its experiment, then `make paper`. Never edit `numbers.tex`.
* `make paper` regenerates the numbers and the two figures the paper draws from artifacts, builds
  the PDF, and fails on an undefined reference or an undefined macro.
* `tests/test_paper_numbers.py` fails if `numbers.tex` is stale, if a macro is defined and used
  nowhere, if a result is typed into `main.tex`, or if a phrase this project has had to retract
  comes back.

## Citations

Every entry of `refs.bib` is compared with its Crossref, DataCite or arXiv record by
`analysis/verify_citations.py` (family names in order, initials, title, year); an entry with no
registry record names the held document it was checked against in a `held` field. The result is
`../results/raw/citation_check.csv`, and `tests/test_citations.py` fails if it does not cover
every entry. Sources and the role each plays: `../docs/literature/README.md`.

⚠️ A source is not cited unless it is held and has been read. Held does not mean redistributed:
eleven sources are on the author's machine only, listed with their SHA-256 in
`../docs/literature/HELD_LOCALLY.csv`. One exception is open and stated:
Kurkowski et al. 2005 in `methods.tex` is quoted only through a held paper that reports it
(`../docs/OPEN_ITEMS.md`, G8).

## Requirements

TeX Live with `IEEEtran.cls` (texlive-publishers), amsmath, booktabs, graphicx, hyperref, tikz.
