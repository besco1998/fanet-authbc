#!/usr/bin/env python3
"""Check every bibliography entry against its registry record (`make verify-citations`).

**Why this exists (audit F49, 2026-10-06).** Two entries of `paper/refs.bib` carried the wrong
authors: one paper was attributed to the authors of a *different* paper on the same topic, and it
had been cited under the wrong name in the paper, the thesis, the code and seven documents for two
months; the other listed four authors who did not write it. Both had been read, both were recorded
as "verified", and the paper said so in a paragraph. A check that is performed by reading is
performed once; this one is a program, so it is performed every time.

What it compares, per entry:

* an entry with a `doi` — authors (family names, in order), title and year against Crossref, or
  against DataCite when Crossref does not hold the DOI;
* an entry with an arXiv `eprint` — authors and title against the arXiv API;
* anything else (a standard, a datasheet, source code, a web page) cannot be checked against a
  registry, and says so: it must carry a `held` field naming the document that was read.

It writes `results/raw/citation_check.csv`. `tests/test_citations.py` then holds, offline, that
every entry has a passing row and that no entry has been edited since its row was written.

This needs the network, so it is not part of `make all`; the offline test is.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIB = REPO / "paper" / "refs.bib"
OUT = REPO / "results" / "raw" / "citation_check.csv"
USER_AGENT = "authbc-citation-check/1.0 (https://github.com/besco1998/fanet-authbc)"
TITLE_MATCH_MIN = 0.9
FIELDS = ["key", "kind", "identifier", "registry", "authors_bib", "authors_registry",
          "authors_match", "title_match", "year_bib", "years_registry", "year_match", "status",
          "fingerprint"]


# --------------------------------------------------------------------------- bib parsing
def _strip_tex(text: str) -> str:
    """LaTeX markup removed and accents folded, for comparison only."""
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)          # \emph, \u, \texttt …
    text = re.sub(r"\\.", "", text)                       # \" \' \^ …
    text = text.replace("{", "").replace("}", "").replace("~", " ")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", _strip_tex(text).lower()).split())


def _field(entry: str, name: str) -> str:
    """Value of a `name = {…}` field, braces balanced, whitespace collapsed."""
    m = re.search(r"(?<![\w-])" + re.escape(name) + r"\s*=\s*\{", entry)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(entry) and depth:
        depth += {"{": 1, "}": -1}.get(entry[i], 0)
        i += 1
    return " ".join(entry[m.end():i - 1].split())


def parse_bib(text: str) -> dict[str, dict[str, str]]:
    """key → {type, author, title, year, doi, eprint, held, note} for every entry."""
    entries: dict[str, dict[str, str]] = {}
    for block in re.split(r"\n(?=@)", text):
        m = re.match(r"@(\w+)\{([^,\s]+),", block)
        if not m:
            continue
        entries[m.group(2)] = {"type": m.group(1).lower(), **{
            f: _field(block, f) for f in ("author", "title", "year", "doi", "eprint", "held",
                                          "note", "registryauthors")}}
    return entries


def _split_authors(author_field: str) -> list[str]:
    """Split on ` and ` outside braces — `{{Standards and Technology}}` is ONE author."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(author_field):
        ch = author_field[i]
        depth += {"{": 1, "}": -1}.get(ch, 0)
        if depth == 0 and author_field.startswith(" and ", i):
            parts.append(author_field[start:i])
            start = i = i + 5
            continue
        i += 1
    parts.append(author_field[start:])
    return [p.strip() for p in parts if p.strip()]


def people(author_field: str) -> list[tuple[str, str]]:
    """Normalised (family, given) pairs of a BibTeX author list (`Family, Given and …`)."""
    out = []
    for person in _split_authors(author_field):
        if person.startswith("{"):                 # a braced corporate author has no given name
            out.append((_norm(person), ""))
            continue
        family, _, given = person.partition(",")
        out.append((_norm(family), _norm(given)))
    return out


def family_names(author_field: str) -> list[str]:
    return [family for family, _ in people(author_field)]


def fingerprint(entry: dict[str, str]) -> str:
    """Changes whenever a field this check compares is edited."""
    blob = "|".join(_norm(entry[f]) for f in ("author", "title", "year")) \
        + "|" + entry["doi"].lower() + "|" + entry["eprint"]
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def kind_of(entry: dict[str, str]) -> str:
    return "doi" if entry["doi"] else "arxiv" if entry["eprint"] else "document"


# --------------------------------------------------------------------------- registries
def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def crossref(doi: str) -> dict | None:
    try:
        msg = json.loads(_get("https://api.crossref.org/works/" + urllib.parse.quote(doi)))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    m = msg["message"]
    years = {str(m[k]["date-parts"][0][0]) for k in ("issued", "published", "published-print",
                                                     "published-online")
             if m.get(k, {}).get("date-parts", [[None]])[0][0]}
    return {"registry": "crossref",
            "authors": [(a.get("family") or a.get("name", ""), a.get("given", ""))
                        for a in m.get("author", [])],
            "title": " ".join(m.get("title", [])), "years": sorted(years)}


def datacite(doi: str) -> dict | None:
    try:
        attrs = json.loads(_get("https://api.datacite.org/dois/" + urllib.parse.quote(doi)))[
            "data"]["attributes"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return {"registry": "datacite",
            "authors": [(c.get("familyName") or c.get("name", ""), c.get("givenName", ""))
                        for c in attrs["creators"]],
            "title": attrs["titles"][0]["title"], "years": [str(attrs["publicationYear"])]}


def arxiv(eprint: str) -> dict | None:
    root = ET.fromstring(_get("http://export.arxiv.org/api/query?id_list="
                              + urllib.parse.quote(eprint)))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = root.find("a:entry", ns)
    if entry is None or entry.find("a:title", ns) is None:
        return None
    return {"registry": "arxiv",
            "authors": [(a.findtext("a:name", "", ns), "")
                        for a in entry.findall("a:author", ns)],
            "title": entry.findtext("a:title", "", ns),
            "years": sorted({entry.findtext("a:published", "", ns)[:4],
                             entry.findtext("a:updated", "", ns)[:4]})}


# --------------------------------------------------------------------------- comparison
def authors_match(bib_people: list[tuple[str, str]],
                  registry_people: list[tuple[str, str]]) -> bool:
    """Same people in the same order: family names equal, and given names agree on their initial.

    Registries are not uniform: Crossref sometimes stores a full name in the family field and
    arXiv only ever has full names, so a bib family name matches when it ENDS the registry's
    name, and whatever precedes it is then taken as the given name. A corporate author matches
    when the registry's name BEGINS with it ("… and Technology (US)"). The initial is compared
    because a family name alone let "Tito-Lara, Jhon" stand for "Tito-Lara, Mateo" (F49).
    """
    if len(bib_people) != len(registry_people):
        return False
    for (b_family, b_given), (r_name, r_given) in zip(bib_people, registry_people, strict=True):
        r_family, r_given = _norm(r_name), _norm(r_given)
        if r_family != b_family:
            if r_family.endswith(" " + b_family):
                r_given = r_given or r_family[: -len(b_family)].strip()
            elif not (not b_given and r_family.startswith(b_family + " ")):
                return False
        if b_given and r_given and b_given[0] != r_given[0]:
            return False
    return True


def title_match(bib_title: str, registry_title: str) -> float:
    """Share of the registry title's words that the bib title also has."""
    b, r = set(_norm(bib_title).split()), set(_norm(registry_title).split())
    return len(b & r) / len(r) if r else 0.0


def check(key: str, entry: dict[str, str]) -> dict[str, str]:
    kind = kind_of(entry)
    row = {"key": key, "kind": kind, "identifier": entry["doi"] or entry["eprint"],
           "registry": "", "authors_bib": "; ".join(family_names(entry["author"])),
           "authors_registry": "", "authors_match": "", "title_match": "",
           "year_bib": entry["year"], "years_registry": "", "year_match": "",
           "fingerprint": fingerprint(entry)}
    if kind == "document":
        row["status"] = "document" if entry["held"] else "UNVERIFIABLE"
        row["identifier"] = entry["held"]
        return row
    rec = (crossref(entry["doi"]) or datacite(entry["doi"])) if kind == "doi" \
        else arxiv(entry["eprint"])
    if rec is None:
        row["status"] = "NOT FOUND"
        return row
    # A registry record can lack a field (a standard has no personal authors; one proceedings
    # record here has no year). A missing field is reported as not comparable, never as a match.
    # `registryauthors` is the one sanctioned exception: where a registry abbreviates a name the
    # document spells out, the entry states the registry's form and that is what is compared.
    # The test requires such an entry to name the held document its real spelling was read from.
    claimed = people(entry["registryauthors"] or entry["author"])
    a_ok = authors_match(claimed, rec["authors"]) if rec["authors"] else None
    y_ok = entry["year"] in rec["years"] if rec["years"] else None
    t = title_match(entry["title"], rec["title"])
    row.update(registry=rec["registry"],
               authors_registry="; ".join(" ".join(x for x in (g, f) if x)
                                          for f, g in rec["authors"]),
               authors_match=_flag(a_ok), title_match=f"{t:.2f}",
               years_registry="/".join(rec["years"]), year_match=_flag(y_ok),
               status="ok" if a_ok is not False and y_ok is not False and t >= TITLE_MATCH_MIN
               and (a_ok or y_ok) else "MISMATCH")
    return row


def _flag(ok: bool | None) -> str:
    return "n/a" if ok is None else str(int(ok))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bib", type=Path, default=BIB)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    rows = []
    for key, entry in parse_bib(args.bib.read_text(encoding="utf-8")).items():
        row = check(key, entry)
        rows.append(row)
        flag = "  " if row["status"] in ("ok", "document") else "!!"
        print(f"{flag} {key:<32} {row['kind']:<9} {row['status']:<12} {row['identifier'][:60]}")
        if row["status"] == "MISMATCH":
            print(f"      bib      : {row['authors_bib']}  ({row['year_bib']})")
            print(f"      registry : {row['authors_registry']}  ({row['years_registry']})"
                  f"  title match {row['title_match']}")
        if row["kind"] != "document":
            time.sleep(0.25)                      # be polite to the registries

    buf = io.StringIO()
    buf.write(f"# run=citation_check\n# checked={dt.date.today().isoformat()}\n"
              f"# bib={args.bib.relative_to(REPO)}\n")
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    args.out.write_text(buf.getvalue(), encoding="utf-8")
    bad = [r["key"] for r in rows if r["status"] not in ("ok", "document")]
    print(f"\nwrote {args.out}: {len(rows)} entries, "
          f"{sum(r['status'] == 'ok' for r in rows)} verified against a registry, "
          f"{sum(r['status'] == 'document' for r in rows)} documents, {len(bad)} failing")
    if bad:
        print("FAILING: " + ", ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
