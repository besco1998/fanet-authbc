#!/usr/bin/env python3
"""Direction C survey harness — does the ns-3 LoRa literature report replication?

⚠️ **The protocol was fixed and committed BEFORE this ran**: `docs/DIRECTION_C_SURVEY_PROTOCOL.md`,
commit `eb3eda5`, which contains no data. The keyword set below is a transcription of §3 of that
document and **must not be edited to change an outcome** — if it needs to change, amend the protocol
in its own commit first and say why.

**What this does and does not decide.** It performs the mechanical part: extract text, apply the
fixed keyword set, report every hit with surrounding context. It does **not** decide the verdict for
a paper with hits — §3 requires each hit to be adjudicated by hand, because the pilot already
produced a false positive ("Hybrid Automatic Repeat reQuest" matching `repeat`) and five `average`
hits that referred to the traffic model rather than to averaging over runs. Adjudications are passed
in via `--adjudicated` so they land in the artifact instead of someone's memory.

⚠️ **The failure mode this is built to prevent.** A scanned, image-only PDF yields zero keyword hits
for reasons that have nothing to do with the authors. Scoring it `NONE` would manufacture support
for our own hypothesis, and it is the single most likely way this survey could produce a false
result. Extraction under `MIN_CHARS` is therefore reported `UNREADABLE` and **excluded from the
denominator** — never silently counted as "no replication reported".

Writes results/raw/direction_c_survey.csv.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402

# Transcribed verbatim from PROTOCOL §3. Fixed in advance; not tunable.
KEYWORDS = re.compile(
    r"\b(seeds?|repetitions?|repeat(?:ed|s)?|replicat\w*|Monte.?Carlo|averaged over|"
    r"confidence intervals?|standard deviations?|error ?bars?|independent runs?|"
    r"simulation runs?|\d+\s+(?:runs?|trials?|experiments?))\b",
    re.I,
)
MIN_CHARS = 2000          # PROTOCOL §3: below this the text is UNREADABLE, not evidence
CONTEXT = 90


def sweep(pdf: Path) -> dict:
    """Mechanical part only: characters extracted, hits, and their contexts."""
    from pypdf import PdfReader

    try:
        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
    except Exception as exc:  # a corrupt PDF is unreadable, not a negative result
        return {"chars": 0, "hits": [], "error": type(exc).__name__ + ": " + str(exc)[:80]}
    flat = " ".join(text.split())
    hits = []
    for m in KEYWORDS.finditer(flat):
        hits.append(" ".join(
            flat[max(0, m.start() - CONTEXT): m.start() + len(m.group()) + CONTEXT].split()))
    # de-duplicate identical contexts without losing order
    return {"chars": len(flat), "hits": list(dict.fromkeys(hits)), "error": ""}


def verdict(chars: int, hits: list[str], adjudication: str | None) -> str:
    """PROTOCOL §3. UNREADABLE wins over everything; a hit needs human adjudication."""
    if chars < MIN_CHARS:
        return "UNREADABLE"
    if not hits:
        return "NONE"
    if adjudication in {"REPORTS", "NONE"}:
        return adjudication
    return "NEEDS_ADJUDICATION"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=REPO / "docs" / "literature",
                    help="directory of PDFs to sweep")
    ap.add_argument("--manifest", type=Path,
                    default=REPO / "docs" / "direction_c_corpus.json",
                    help="{stem: {ns3: bool, pilot: bool, adjudication: REPORTS|NONE|null}}")
    ap.add_argument("--out", default="direction_c_survey.csv")
    a = ap.parse_args()

    manifest = json.loads(a.manifest.read_text()) if a.manifest.exists() else {}
    rows = []
    for stem, meta in sorted(manifest.items()):
        pdf = a.corpus / f"{stem}.pdf"
        if not pdf.exists():
            print(f"  MISSING  {stem}")
            continue
        s = sweep(pdf)
        v = verdict(s["chars"], s["hits"], meta.get("adjudication"))
        rows.append({
            "paper": stem,
            "ns3": int(bool(meta.get("ns3"))),
            "pilot": int(bool(meta.get("pilot"))),
            "chars_extracted": s["chars"],
            "keyword_hits": len(s["hits"]),
            "verdict": v,
            "adjudication_note": meta.get("note", ""),
            "hit_contexts": " || ".join(s["hits"][:6]),
            "extract_error": s["error"],
        })
        print(f"  {v:<18} {stem:<52} chars={s['chars']:>7} hits={len(s['hits'])}")

    if not rows:
        raise SystemExit("empty corpus — populate the manifest first")

    counted = [r for r in rows if r["verdict"] in {"REPORTS", "NONE"}]
    none_n = sum(1 for r in counted if r["verdict"] == "NONE")
    unread = sum(1 for r in rows if r["verdict"] == "UNREADABLE")
    pending = sum(1 for r in rows if r["verdict"] == "NEEDS_ADJUDICATION")
    print(f"\ncorpus {len(rows)}  |  counted {len(counted)}  |  UNREADABLE {unread} (excluded)"
          f"  |  awaiting adjudication {pending}")
    if counted:
        print(f"NONE (no replication reported): {none_n}/{len(counted)} "
              f"= {100 * none_n / len(counted):.1f} %")
        print("PROTOCOL falsification threshold: H1 unsupported if REPORTS >= 25 % "
              f"-> REPORTS = {100 * (len(counted) - none_n) / len(counted):.1f} %")
    if pending:
        print(f"⚠️ {pending} paper(s) have hits and are NOT yet adjudicated — the percentage above "
              f"is provisional until every hit is read in context.")

    out = REPO / "results" / "raw" / a.out
    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "direction_c_survey",
            "protocol": "docs/DIRECTION_C_SURVEY_PROTOCOL.md (committed eb3eda5, data-free)",
            "config_hash": provenance.config_hash(
                {"keywords": KEYWORDS.pattern, "min_chars": MIN_CHARS,
                 "corpus": sorted(manifest)})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    buf.write("# ⚠️ UNREADABLE rows are EXCLUDED from the denominator (protocol §3):\n")
    buf.write("#    a scanned PDF yields zero hits for reasons unrelated to its authors.\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    print(f"\nwrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
