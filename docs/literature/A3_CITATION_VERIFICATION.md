# A3 — citation verification report

*Every `[VERIFY]` placeholder in `paper/refs.bib` is now a real source. This file records **how each
was verified**, and it is complete: the two paywalled sources it originally flagged were supplied by
Mohamed and have since been read.*

Date: 2026-07-30. Result: **`paper/refs.bib` contains 0 `[PLACEHOLDER]` entries and the compiled PDF
contains 0 `[VERIFY]` markers.** Paper builds at 9 pages, 0 undefined references. **Every source
cited is held in this directory and has been read.**

---

## Method

For each placeholder I found a candidate primary source, then confirmed its bibliographic fields
against the **Crossref record for its DOI** — not against a search-engine summary. Crossref is the
registrar's own metadata, so author list, venue, volume, page range and year come from the publisher
rather than from a third-party description. The exact query used was:

```bash
curl -s -H "Accept: application/json" "https://api.crossref.org/works/<DOI>"
```

This matters because of the error recorded in F18 the same day: a sentence quoted correctly from a
PDF was attributed to the wrong figure, and the conclusion inverted. Metadata from the registrar
removes that class of mistake for the *bibliographic* fields. It does **not** remove it for the
*claims*, which is why the third column below says whether I have read the source.

---

## The three replacements

### 1. `verify_batch_verify` → `zhang2008batch`

**Zhang, Lu, Lin, Ho & Shen, "An Efficient Identity-Based Batch Verification Scheme for Vehicular
Sensor Networks", IEEE INFOCOM 2008, pp. 246–250.** DOI `10.1109/INFOCOM.2008.58`

| | |
|---|---|
| Crossref | ✅ all fields confirmed — authors, venue, pages 246–250, year 2008 |
| PDF held | ✅ **yes** — `zhang2008_ib_batch_verification_vanet.pdf`, supplied by Mohamed (institutional access) after this report first flagged it |
| Claim verified **from the PDF** | *"an RSU can verify multiple received signatures at the same time such that the total verification time can be dramatically reduced"* — quoted directly |
| Confidence | **Verified.** The abstract also supplies a sharper contrast we now use: their deadline is DSRC's **300 ms**, and their batching is **receiver-side** (V2I, the RSU verifies) where ours is **sender-side**. Complementary, not competing |

✅ **Resolved.** The paper is held and the abstract read; the Related Work sentence now quotes it and
states the receiver-vs-sender distinction explicitly.

### 2. `verify_uav_blockchain` → `mehta2020blockchainuav`

**Mehta, Gupta & Tanwar, "Blockchain Envisioned UAV Networks: Challenges, Solutions, and
Comparisons", Computer Communications 151:518–538, 2020.** DOI `10.1016/j.comcom.2020.01.023`

| | |
|---|---|
| Crossref | ✅ all fields confirmed — 3 authors, vol. 151, pp. 518–538, 2020 |
| PDF held | ✅ **yes** — `mehta2020_blockchain_uav_survey.pdf`, supplied by Mohamed. Front matter confirms *Computer Communications 151 (2020) 518–538*, matching Crossref exactly |
| Claim in our paper | cited as a **survey**: *"UAV-blockchain systems, surveyed in [x], place telemetry or attestations on such a chain"* |
| Confidence | **High.** It is cited only as a pointer to the subfield, which is what a survey is for — the weakest possible use of a citation, deliberately |

✅ **Held.** Nothing load-bearing rests on it — it is a subfield pointer. If you prefer a different
survey, swapping it changes no result.

### 3. `verify_delta_telemetry` → `pelkonen2015gorilla`

**Pelkonen, Franklin, Teller, Cavallaro, Huang, Meza & Veeraraghavan, "Gorilla: A Fast, Scalable,
In-Memory Time Series Database", PVLDB 8(12):1816–1827, 2015.** DOI `10.14778/2824032.2824078`

| | |
|---|---|
| Crossref | ✅ all fields confirmed — 7 authors, vol. 8, pp. 1816–1827, 2015 |
| PDF held | ✅ **yes** — `pelkonen2015_gorilla_tsdb.pdf` (open access from vldb.org) |
| Claim verified **from the PDF** | *"we aggressively leverage compression techniques such as delta-of-delta timestamps and XOR'd floating point values to reduce Gorilla's storage footprint by 10x"* — quoted directly |
| Confidence | **Verified.** Read, quoted, and stored |

**One honest difference stated in the paper** rather than glossed: Gorilla is a database and can
chain deltas indefinitely; a lossy broadcast link cannot, so we re-anchor on a keyframe every K
records and pay the size for loss independence. Gorilla does not face that constraint, so it is
prior art for *delta coding of telemetry*, not for our keyframe scheme.

### 4. `verify_fanet_auth` → **deleted**

An orphan: it was defined in `refs.bib` and **cited nowhere** in `main.tex`. Removed rather than
filled, because inventing a use for a citation is worse than not having it.

---

## What you need to check yourself

**Nothing outstanding.** Both paywalled sources were supplied by Mohamed after this report first
flagged them, verified against their Crossref records, and the Zhang claim is now quoted from the
PDF rather than paraphrased from the title. Every source cited in the paper is now held and read.

Everything else in `paper/refs.bib` is either a standard (RFC/3GPP/IEEE/Semtech), a source whose PDF
is in this directory and has been read, or a foundational paper whose cited content is
title-level (Bianchi, Nakamoto, BLS).

---

## What is still not a citation problem but looks like one

**T6 and T2a carry no novelty claim**, so they need no supporting citation beyond the prior art that
demoted them (`gundogan2021firmware` for T6; for T2a the disposition is recorded in `OPEN_ITEMS` A6
with no citation, because the finding is that the result is *standard*, and standard results are
attributed to the field, not to a paper).
