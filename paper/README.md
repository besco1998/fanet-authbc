# paper/ — IEEEtran draft (auto-generated from the frozen results)

`main.tex` is the LaTeX rendering of `docs/TECHNICAL_NARRATIVE.md` (problem, theory T1–T5,
implementation, results, reproducibility, limitations) plus a Related-Work section. Figures are pulled
from `../results/figures/` at build time; every number traces to a frozen `results/raw/*.csv`.

## Build
```bash
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main   # -> main.pdf (4 pp.)
```
Requires TeX Live with `IEEEtran.cls` (texlive-publishers), amsmath, booktabs, graphicx, hyperref.

## ⚠️ Before submission — verify the citations
`refs.bib` splits into two blocks:
- **Verified foundational** refs (Bianchi, BLS/BGLS, Ed25519, ECDSA/FIPS, CBOR, Nakamoto, NS-3, MessagePack).
- **`[VERIFY]` placeholders** for the domain-specific FANET-auth / UAV-blockchain / VANET-batch /
  delta-telemetry literature. These are **not real citations** — replace each with a verified primary
  source (and only then cite any numbers from them). They render with a visible `[PLACEHOLDER]/[VERIFY]`
  marker so an unverified reference is never mistaken for a real one.
