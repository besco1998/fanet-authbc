#!/usr/bin/env python3
"""Every number the paper prints, generated from the artifacts → `paper/numbers.tex`.

**Why this exists.** A number typed into LaTeX is a copy, and copies drift: this project has
shipped a figure plotting a superseded constant, a table one audit behind its CSV, and a count of
"four of seven" that the artifacts had stopped supporting. The paper therefore contains no typed
results. Each is a macro, each macro is defined here from a file in `results/`, and
`tests/test_paper_numbers.py` fails if `numbers.tex` is not what this script writes or if the
paper uses a macro this script does not define.

    python analysis/paper_numbers.py           # write paper/numbers.tex
    python analysis/paper_numbers.py --check   # exit 1 if the file on disk is stale

A value that an artifact does not yet hold stops the script and names itself. `--allow-missing`
writes `??` in its place so a draft can be typeset; the check, and therefore the test suite,
refuses a file that contains one.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))      # nmax_airtime_line, when loaded by a test

import dcf_model_check as modelcheck  # noqa: E402
import nmax_airtime_line as airtime  # noqa: E402
import source_difference as sources  # noqa: E402

from authbc.models import bianchi, broadcast_dcf, lora  # noqa: E402
from authbc.models import frame as frame_model  # noqa: E402

RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw"
OUT = REPO / "paper" / "numbers.tex"

WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve")


def rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in path.read_text(encoding="utf-8").splitlines()
                               if not ln.startswith("#")))


def one(table: list[dict[str, str]], **want: str) -> dict[str, str]:
    hits = [r for r in table if all(r[k] == v for k, v in want.items())]
    if len(hits) != 1:
        raise LookupError(f"expected one row for {want}, found {len(hits)}")
    return hits[0]


MISSING: list[str] = []          # values an artifact does not hold yet (see --allow-missing)


def f(value: float | str, digits: int) -> str:
    if value == "":
        MISSING.append(f"a {digits}-decimal value")
        return "??"
    # Decimal, half up: `f"{145.765:.2f}"` is 145.76, because the float is 145.76499…
    quantum = Decimal(1).scaleb(-digits)
    return str(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def whole(value: str, what: str) -> str:
    """An integer cell of an artifact, or `??` (recorded) if the cell is still empty."""
    if value == "":
        MISSING.append(what)
        return "??"
    return str(int(float(value)))


def thousands(n: int) -> str:
    """12345 -> 12\\,345 (a thin space, as the paper's tables use)."""
    return f"{n:,}".replace(",", "\\,")


def interval(lo: str, hi: str, what: str) -> str:
    if "" in (lo, hi):
        MISSING.append(what)
        return "[??]"
    return f"[{int(float(lo))},\\,{int(float(hi))}]"


# ============================================================================== frames
def frames() -> dict[str, str]:
    comp = rows(RAW / "frame_components.csv")
    at = "sender 40000 / one hour at 50 Hz"
    low = "sender 0 / record 0"
    m: dict[str, str] = {
        "hdrFirst": one(comp, kind="header", format="first", item=at)["mean_bytes"],
        "hdrFirstLo": one(comp, kind="header", format="first", item=low)["mean_bytes"],
        "hdrLean": one(comp, kind="header", format="lean", item=at)["mean_bytes"],
        "hdrLeanLo": one(comp, kind="header", format="lean", item=low)["mean_bytes"],
        "linkField": one(comp, kind="link", format="lean", item="per frame (its own field)")
        ["mean_bytes"],
    }
    for fmt, tag in (("first", "First"), ("lean", "Lean")):
        fld = {r["item"]: r for r in comp if r["kind"] == "header_field" and r["format"] == fmt}

        def span(*names: str, fld: dict = fld) -> str:
            hi = sum(int(fld[n]["mean_bytes"]) for n in names)
            lo = sum(int(fld[n]["min_bytes"]) for n in names)
            return str(hi) if lo == hi else f"{hi} ({lo})"

        m |= {f"fld{tag}Map": span("map"), f"fld{tag}VT": span("v", "t"),
              f"fld{tag}Src": span("src"), f"fld{tag}Seq": span("base_seq"),
              f"fld{tag}N": span("n"), f"fld{tag}Recs": span("recs"),
              f"fld{tag}Auth": span("auth")}
        key = one(comp, kind="record", format=fmt, item="keyframe", stride="1")
        delta = one(comp, kind="record", format=fmt, item="delta", stride="1")
        m |= {f"key{tag}": f(key["mean_bytes"], 1), f"delta{tag}": f(delta["mean_bytes"], 1)}
    # key names of the first header: one byte of CBOR text header plus the name, seven keys
    m["keyNamesFirst"] = str(sum(1 + len(k) for k in
                                 ("v", "t", "src", "base_seq", "n", "recs", "auth")))
    tamper = {r["item"]: int(r["n"]) for r in comp if r["kind"] == "tamper"}
    if tamper["accepted_altered"] or tamper["accepted_unchanged"]:
        raise ValueError("the paper says every single-bit flip is refused; the artifact disagrees")
    m["bitflips"] = thousands(tamper["flips"])
    far = one(comp, kind="record", format="lean", item="delta", stride="110")
    m |= {"deltaLeanFar": f(far["mean_bytes"], 1), "loraSpacing": f(far["spacing_s"], 1)}
    for name, stride in (("Tenth", "2"), ("One", "20"), ("Slow", "330")):   # 0.1 s, 1 s, 16.5 s
        row = one(comp, kind="record", format="lean", item="delta", stride=stride)
        m[f"deltaLean{name}"] = f(row["mean_bytes"], 1)
    # The batch the tight reading of freshness would admit (thesis ch. 4): five records.
    base = one(comp, kind="frame", format="lean", item="self-batch", batch="1", ref_interval="1")
    four = one(comp, kind="frame", format="lean", item="self-batch", batch="4", ref_interval="1")
    five = one(comp, kind="frame", format="lean", item="self-batch", batch="5", ref_interval="1")

    def saving(row: dict[str, str]) -> float:
        return 100 * (1 - float(row["bytes_per_rec"]) / float(base["bytes_per_rec"]))

    m |= {"bprLeanFive": f(five["bytes_per_rec"], 1), "saveLeanFive": f(saving(five), 1),
          "saveFiveGain": f(saving(five) - saving(four), 1)}
    return m | _records_within_the_mtu(comp) | _where_the_link_sits(comp)


def _where_the_link_sits(comp: list[dict[str, str]]) -> dict[str, str]:
    """The three curves of fig_bytes_vs_batch at the adopted batch, and what separates them.

    The text says the first format with one link per frame lands between the two formats at
    every batch above one, and that a link in every record leaves a floor no batch removes.
    """
    def curve(fmt: str, item: str) -> dict[int, float]:
        return {int(r["batch"]): float(r["bytes_per_rec"]) for r in comp
                if (r["kind"], r["format"], r["item"], r["ref_interval"])
                == ("frame", fmt, item, "1")}

    per_record = curve("first", "self-batch (byte model)")
    per_frame = curve("first", "self-batch; one link per frame (byte model)")
    lean = curve("lean", "self-batch")
    if not all(per_record[b] > per_frame[b] > lean[b] for b in lean if b > 1):
        raise ValueError("the text orders the three link placements; the artifact disagrees")
    if not min(per_record.values()) > per_frame[4]:
        raise ValueError("the text says no batch up to twelve brings a per-record link below "
                         "what one link per frame reaches at four records")
    return {"bprFirstLinkFrame": f(per_frame[4], 1),
            "linkMoveSave": f(per_record[4] - per_frame[4], 0),
            "leanHeaderSave": f(per_frame[4] - lean[4], 1),
            "bprFirstTwelve": f(per_record[max(per_record)], 1),
            "curveMaxBatch": str(max(per_record))}


def _records_within_the_mtu(comp: list[dict[str, str]], mtu: int = 1500) -> dict[str, str]:
    """How many records one MTU-sized frame would hold: the ceiling freshness never reaches."""
    out = {}
    for fmt, tag, link in (("first", "First", 0.0), ("lean", "Lean", None)):
        header = float(one(comp, kind="header", format=fmt,
                           item="sender 40000 / one hour at 50 Hz")["mean_bytes"])
        if link is None:
            link = float(one(comp, kind="link", format=fmt,
                             item="per frame (its own field)")["mean_bytes"])
        key = float(one(comp, kind="record", format=fmt, item="keyframe", stride="1")["mean_bytes"])
        delta = float(one(comp, kind="record", format=fmt, item="delta", stride="1")["mean_bytes"])
        layout = frame_model.FlatLayout(fmt, header, link, key, delta)
        b = 1
        while layout.frame_bytes(64, b + 1) <= mtu:
            b += 1
        out[f"mtuRecs{tag}"] = str(b)
    if not int(out["mtuRecsFirst"]) > 4 < int(out["mtuRecsLean"]):
        raise ValueError("the text says freshness, not the MTU, caps the batch at four")
    return out


# ============================================================================== ladder
RUNGS = {  # macro suffix -> (format, rung)
    "FirstBase": ("first", "inline-1"), "FirstInline": ("first", "inline-b"),
    "FirstCbor": ("first", "batch-cbor"), "FirstDesign": ("first", "batch-delta"),
    "LeanBase": ("lean", "inline-1"), "LeanInline": ("lean", "inline-b"),
    "LeanKeys": ("lean", "batch-keys"), "LeanDesign": ("lean", "batch-delta"),
}


def ladder() -> dict[str, str]:
    lad = rows(RAW / "design_ladder.csv")
    cfg = yaml.safe_load((REPO / "experiments" / "design-ladder" / "config.yaml").read_text())
    m: dict[str, str] = {}
    bpr: dict[str, float] = {}
    for tag, (fmt, rung) in RUNGS.items():
        r = one(lad, op="adopted", format=fmt, rung=rung, scheme="ed25519")
        bpr[tag] = float(r["bytes_per_rec"])
        what = f"N_max of {fmt}/{rung} at the adopted point"
        m |= {f"frm{tag}": f(r["frame_bytes"], 1), f"bpr{tag}": f(r["bytes_per_rec"], 2),
              f"cert{tag}": f(r["bytes_per_rec_with_cert"], 2), f"nsat{tag}": r["n_max_u_lt_1"],
              f"nmax{tag}": whole(r["n_max_v95"], what),
              f"ci{tag}": interval(r["n_max_v95_ci_lo"], r["n_max_v95_ci_hi"], what),
              f"cpu{tag}": f(r["cpu_pct_at_n_v95"], 0)}
    m |= {"saveLean": f(100 * (1 - bpr["LeanDesign"] / bpr["LeanBase"]), 1),
          "saveFirst": f(100 * (1 - bpr["FirstDesign"] / bpr["FirstBase"]), 1),
          "leanVsFirstPct": f(100 * (1 - bpr["LeanDesign"] / bpr["FirstDesign"]), 0)}
    ratios: dict[str, tuple[float, float]] = {}
    for tag, fmt in (("First", "first"), ("Lean", "lean")):
        for op, rel in (("adopted", ""), ("relaxed", "Rel")):
            base = one(lad, op=op, format=fmt, rung="inline-1", scheme="ed25519")
            design = one(lad, op=op, format=fmt, rung="batch-delta", scheme="ed25519")
            what = f"N_max of the {fmt} baseline and design at the {op} point"
            if "" in (base["n_max_v95"], design["n_max_v95"]):
                MISSING.append(what)
                m[f"ratio{rel}{tag}"] = "??"
            else:
                m[f"ratio{rel}{tag}"] = f(int(design["n_max_v95"]) / int(base["n_max_v95"]), 1)
            if rel:
                m |= {f"nmaxRel{tag}Base": whole(base["n_max_v95"], what),
                      f"nmaxRel{tag}Design": whole(design["n_max_v95"], what),
                      f"ciRel{tag}Base": interval(base["n_max_v95_ci_lo"],
                                                  base["n_max_v95_ci_hi"], what),
                      f"ciRel{tag}Design": interval(design["n_max_v95_ci_lo"],
                                                    design["n_max_v95_ci_hi"], what)}
        if "??" not in (m[f"ratio{tag}"], m[f"ratioRel{tag}"]):
            ratios[tag] = (float(m[f"ratio{tag}"]), float(m[f"ratioRel{tag}"]))
        # the search must return the rung the paper calls the design, or the paper is wrong
        best = one(lad, op="adopted", format=fmt, rung="SEARCH_OPTIMUM")
        if (best["placement"], best["batch"], best["ref_interval"]) != ("B", "4", "1"):
            raise ValueError(f"the {fmt} search optimum is no longer the reported design")
    if len(ratios) == 2:
        # "nearly the same at both operating points, and larger in the lean format"
        if max(abs(a - b) for a, b in ratios.values()) > 0.2:
            raise ValueError("the text says the ratio hardly changes between operating points")
        if not min(ratios["Lean"]) > max(ratios["First"]):
            raise ValueError("the text says the ratio is larger in the lean format at both points")
    design = one(lad, op="adopted", format="lean", rung="batch-delta", scheme="ed25519")
    inline = one(lad, op="adopted", format="lean", rung="inline-b", scheme="ed25519")
    bls = one(lad, op="adopted", format="lean", rung="batch-delta", scheme="bls")
    base = one(lad, op="adopted", format="lean", rung="inline-1", scheme="ed25519")
    m |= _capacity_steps(base, inline, design)
    m |= _per_run_reading(lad)
    m |= {"ncpuBatch": design["n_cpu_one_core"], "ncpuInline": inline["n_cpu_one_core"],
          "ncpuBls": bls["n_cpu_one_core"],
          "certBytes": str(cfg["cert_bytes"]),
          "certPerFrame": f((cfg["cert_bytes"] + (cfg["cert_period"] - 1)
                             * cfg["cert_digest_bytes"]) / cfg["cert_period"], 1),
          "seeds": "30"}
    return m


def _capacity_steps(base: dict[str, str], inline: dict[str, str],
                    design: dict[str, str]) -> dict[str, str]:
    """The two steps of the lean ladder, and the sentences the paper hangs on them."""
    if "" in (base["n_max_v95"], inline["n_max_v95"], design["n_max_v95"]):
        MISSING.append("N_max of the lean baseline, inline and design rungs")
        return {"stepShareLean": "??", "stepSignLean": "??"}
    share = int(inline["n_max_v95"]) / int(base["n_max_v95"])
    sign = int(design["n_max_v95"]) / int(inline["n_max_v95"])
    if not share > sign:
        raise ValueError("the text calls sharing the frame the larger step; the ladder disagrees")
    if design["binds_at_v95"] != "channel":
        raise ValueError("the text says the channel binds before the CPU for the design")
    if not 90.0 <= float(inline["cpu_pct_at_n_v95"]) <= 100.0:
        raise ValueError("the text says row 6 reaches its channel limit with almost no CPU to "
                         "spare; the ladder disagrees")
    return {"stepShareLean": f(share, 1), "stepSignLean": f(sign, 1)}


def _per_run_reading(lad: list[dict[str, str]]) -> dict[str, str]:
    """N_max if 95 % of individual runs, not their mean, must reach the target (both criteria are
    reported and the mean is the headline: decision of 2026-08-06)."""
    out: dict[str, str] = {}
    gaps = []
    for tag, fmt in (("First", "first"), ("Lean", "lean")):
        for kind, rung in (("Base", "inline-1"), ("Design", "batch-delta")):
            r = one(lad, op="adopted", format=fmt, rung=rung, scheme="ed25519")
            what = f"per-run N_max of {fmt}/{rung} at the adopted point"
            out[f"nrun{tag}{kind}"] = whole(r["n_max_v95_per_run"], what)
            if r["n_max_v95"] and r["n_max_v95_per_run"]:
                gaps.append(int(r["n_max_v95"]) - int(r["n_max_v95_per_run"]))
    if len(gaps) < 4:
        return out | {"nrunGap": "??"}
    if min(gaps) < 0:
        raise ValueError("the per-run reading is the stricter one; the ladder disagrees")
    return out | {"nrunGap": WORDS[max(gaps)]}


# ============================================================================== loss
def loss() -> dict[str, str]:
    table = rows(RAW / "e3_codec_loss.csv")
    m: dict[str, str] = {}
    for word, ref in (("One", "1"), ("Two", "2"), ("Four", "4"), ("Sixteen", "16")):
        r = one(table, loss_model="iid", p="0.05", ref_interval=ref)
        expect_pass = "1" if ref == "1" else "0"
        if r["meets_target"] != expect_pass:
            raise ValueError(f"the loss table says R={ref} "
                             f"{'meets' if expect_pass == '1' else 'misses'} V; the artifact "
                             "disagrees")
        m |= {f"lossBpr{word}": f(r["bytes_per_rec"], 2), f"lossV{word}": f(r["V_meas"], 3),
              f"lossCi{word}": f"[{f(r['V_ci_lo'], 3)},\\,{f(r['V_ci_hi'], 3)}]",
              f"lossTh{word}": f(r["V_theory"], 3)}
        m["lossFrames"] = thousands(int(r["frames_sent"]))
    burst = one(table, loss_model="gilbert", p="0.05", ref_interval="4")
    first = one(table, loss_model="iid", p="0.05", ref_interval="1")
    last = one(table, loss_model="iid", p="0.05", ref_interval="16")
    m |= {"lossVFourBurst": f(burst["V_meas"], 3),
          "lossPrize": f(float(first["bytes_per_rec"]) - float(last["bytes_per_rec"]), 1)}
    # the two cleaner-link statements in the text
    for p, ref in (("0.02", 4), ("0.01", 8)):
        if frame_model.max_ref_interval(float(p), 0.05, (1, 2, 4, 8, 16)) != ref:
            raise ValueError(f"the text says R={ref} is the longest interval at p={p}")
    return m | _length_dependent_loss(table) | _at_the_measured_loss(table)


def _at_the_measured_loss(table: list[dict[str, str]]) -> dict[str, str]:
    """At the loss measured on the bench every reference interval meets the target.

    The text says so, to show that the keyframe in every frame is bought by the specified loss
    budget (p = ε) and not by the link that was measured.
    """
    clean = [r for r in table if r["loss_model"] == "iid" and r["p"] == "0.00023"]
    if not clean or any(r["meets_target"] != "1" for r in clean):
        raise ValueError("the text says every interval meets V at the measured loss rate")
    longest = max(clean, key=lambda r: int(r["ref_interval"]))
    return {"lossCleanR": longest["ref_interval"], "lossCleanV": f(longest["V_theory"], 3)}


def _length_dependent_loss(table: list[dict[str, str]]) -> dict[str, str]:
    """Loss at one bit error rate: the text says the design then misses 0.95 at p = 0.05."""
    at5 = one(table, loss_model="ber", p="0.05", ref_interval="1")
    at2 = one(table, loss_model="ber", p="0.02", ref_interval="1")
    if (at5["meets_target"], at2["meets_target"]) != ("0", "1"):
        raise ValueError("the text says the design misses V at p=0.05 and meets it at p=0.02 "
                         "under length-dependent loss; the artifact disagrees")
    base = float(one(rows(RAW / "design_ladder.csv"), op="adopted", format="lean",
                     rung="inline-1", scheme="ed25519")["frame_bytes"])
    stretch = (float(at5["frame_bytes"]) + bianchi.MAC_OVH_BYTES) / (base + bianchi.MAC_OVH_BYTES)
    p_max = 1.0 - 0.95 ** (1.0 / stretch)     # reference loss at which the design is at 0.95
    return {"lossBerP": f(at5["p_frame"], 3), "lossBerV": f(at5["V_meas"], 3),
            "lossBerTh": f(at5["V_theory"], 3),
            "lossBerCi": f"[{f(at5['V_ci_lo'], 3)},\\,{f(at5['V_ci_hi'], 3)}]",
            "lossBerPmax": f(p_max, 3)}


# ============================================================================== stream schemes
def stream() -> dict[str, str]:
    table = {r["scheme"]: r for r in rows(RAW / "stream_baselines.csv")}
    tags = {"mavlink2": "Mav", "tesla": "Tesla", "gennaro-rohatgi": "Gr", "emss": "Emss",
            "wong-lam-tree": "Wl", "per-record signature": "Sig", "authbc": "Design"}
    if set(table) != set(tags):
        raise ValueError("the stream-scheme table does not list the schemes the paper names")
    m: dict[str, str] = {}
    for scheme, tag in tags.items():
        r = table[scheme]
        what = f"simulated N_max of the {scheme} frame"
        m |= {f"strAuth{tag}": f(r["auth_bytes_per_record"], 0),
              f"strBpr{tag}": f(r["bytes_per_rec"], 1),
              f"strFps{tag}": f(r["frames_per_s"], 1), f"strNsat{tag}": r["n_sat"],
              f"strNmax{tag}": whole(r["n_max_v95"], what),
              f"strCi{tag}": interval(r["n_max_v95_ci_lo"], r["n_max_v95_ci_hi"], what)}
    # the two sentences of the text, held for the saturation bound and for the simulated capacity
    for column, name in (("n_sat", "saturation"), ("n_max_v95", "simulated")):
        if any(r[column] == "" for r in table.values()):
            continue                                  # recorded as missing by `whole` above
        best = max(int(r[column]) for s, r in table.items() if s != "authbc")
        if not best < int(table["authbc"][column]) / 2:
            raise ValueError("the text says no frame-per-record scheme reaches half the "
                             f"design's {name} capacity; the artifact disagrees")
        if best != int(table["mavlink2"][column]):
            raise ValueError(f"the text names the 13 B tag as the best frame-per-record scheme "
                             f"({name})")
    return m


# ============================================================================== freshness
def freshness() -> dict[str, str]:
    table = rows(RAW / "freshness_budget.csv")

    def row(scheme: str, stat: str) -> dict[str, str]:
        return one(table, op="adopted", scheme=scheme, channel_stat=stat)

    mean, pnn, worst = (row("ed25519", s) for s in
                        ("delay_mean_ms", "delay_p99_ms", "delay_max_ms"))
    bls = row("bls", "delay_max_ms")
    if not all(r["meets_d_max"] == "1" for r in (mean, pnn, worst, bls)):
        raise ValueError("the freshness table reports every row inside D_max")
    return {
        "frFill": f(mean["fill_ms"], 0),
        "frChMean": f(mean["channel_ms"], 2), "frChPnn": f(pnn["channel_ms"], 2),
        "frChMax": f(worst["channel_ms"], 2),
        "frVerEd": f(mean["verify_ms"], 2), "frVerBls": f(bls["verify_ms"], 2),
        "frTotMean": f(mean["total_ms"], 1), "frTotPnn": f(pnn["total_ms"], 1),
        "frTotMax": f(worst["total_ms"], 1), "frTotBls": f(bls["total_ms"], 1),
        "frMarMean": f(mean["margin_ms"], 1), "frMarPnn": f(pnn["margin_ms"], 1),
        "frMarMax": f(worst["margin_ms"], 1), "frMarBls": f(bls["margin_ms"], 1),
    }


# ============================================================================== phy, energy
def phy() -> dict[str, str]:
    table = rows(RAW / "phy_sweep.csv")
    ratios = [float(r["ratio"]) for r in table]
    lean = one(table, channel="20MHz", rate_mbps="6", format="lean")
    return {"fixedCost": f(lean["fixed_cost_us"], 0),
            "fixedSharePct": f(lean["fixed_share_of_baseline_pct"], 0),
            "phyRatioLo": f(min(ratios), 1), "phyRatioHi": f(max(ratios), 1)}


def energy() -> dict[str, str]:
    table = rows(RAW / "energy_table.csv")
    design = one(table, encoding="delta", batch="4")
    base = one(table, encoding="cbor", batch="1")
    if not (design["reportable"] == base["reportable"] == "1"):
        raise ValueError("an energy row the paper quotes is not marked reportable")
    m: dict[str, str] = {}
    for tag, r in (("Design", design), ("Base", base)):
        m |= {f"en{tag}Meas": f(r["sender_uj_per_rec_median"], 1),
              f"en{tag}Range": f"[{f(r['sender_uj_per_rec_min'], 1)},\\,"
                               f"{f(r['sender_uj_per_rec_max'], 1)}]",
              f"en{tag}Model": f(r["sender_model_uj_per_rec"], 1),
              f"en{tag}Gap": f(r["sender_residual_pct"], 1),
              f"en{tag}EndToEnd": f(r["end_to_end_model_uj_per_rec"], 1)}
    m["enSavePct"] = f(100 * (1 - float(design["sender_uj_per_rec_median"])
                              / float(base["sender_uj_per_rec_median"])), 0)
    return m


def timings() -> dict[str, str]:
    crypto = {(r["scheme"], r["op"]): float(r["median_ns"])
              for r in rows(HW / "p1_crypto.authbc-pi4a.csv") if not r["agg_b"]}
    cfg = yaml.safe_load((REPO / "experiments" / "design-ladder" / "config.yaml").read_text())
    return {"tSignEd": f(crypto[("ed25519", "sign")] / 1e3, 0),
            "tVerEd": f(crypto[("ed25519", "verify")] / 1e3, 0),
            "tSignEc": f(crypto[("ecdsa_p256", "sign")] / 1e3, 0),
            "tVerEc": f(crypto[("ecdsa_p256", "verify")] / 1e3, 0),
            "tSignBls": f(crypto[("bls", "sign")] / 1e6, 2),
            "tVerBls": f(crypto[("bls", "verify")] / 1e6, 2),
            "tHash": f(cfg["t_hash_ns"] / 1e3, 2)}


# ============================================================================== flight logs
def flight_logs() -> dict[str, str]:
    table = rows(RAW / "px4_log_sizes.csv")
    real = one(table, row="real logs", spacing_ms="200")
    gen = one(table, row="generator", spacing_ms="200")
    logs = [r for r in table if r["row"] == "log" and r["spacing_ms"] == "200"]
    if len(logs) != 12 or any(r["measured"] != "1" for r in logs):
        raise ValueError("the paper says twelve logs were measured at 0.2 s")
    slow = [float(r["lean_delta_mean"]) for r in logs
            if r["stratum"] in ("quadrotor", "hexa/octorotor")]
    fast = [float(r["lean_delta_mean"]) for r in logs if r["stratum"] == "fixed wing"]
    return {"pxRecords": thousands(int(real["records"])),
            "pxDelta": f(real["lean_delta_mean"], 1), "pxDeltaGen": f(gen["lean_delta_mean"], 1),
            "pxKey": f(real["lean_key_mean"], 1), "pxKeyGen": f(gen["lean_key_mean"], 1),
            "pxDeltaSlow": f"{f(min(slow), 1)}--{f(max(slow), 1)}",
            "pxDeltaFast": f(max(fast), 1),
            "pxBpr": f(real["bytes_per_rec"], 1), "pxBprGen": f(gen["bytes_per_rec"], 1),
            "pxSave": f(real["saving_pct"], 1), "pxSaveGen": f(gen["saving_pct"], 1),
            "pxSaveWorst": f(min(float(r["saving_pct"]) for r in logs), 1)}


# ============================================================================== validation
def validation() -> dict[str, str]:
    """Model-vs-ns-3 saturation bands (as tests/test_validation_bands.py) and the hardware check."""
    grouped: dict[tuple[int, str], list[float]] = defaultdict(list)
    for r in rows(RAW / "ns3_matrix.csv"):
        grouped[(int(r["N"]), r["mode"])].append(float(r["goodput_mbps"]))
    dev: dict[str, list[float]] = {"unicast": [], "broadcast": []}
    for (n, mode), values in grouped.items():
        model = (bianchi.solve(n, 1400).throughput_bps if mode == "unicast" else
                 broadcast_dcf.solve(n, 1400, bianchi.t_broadcast(1400), w0=bianchi.W,
                                     slot_s=bianchi.SLOT).throughput_bps) / 1e6
        dev[mode].append(100.0 * (st.mean(values) - model) / model)
    hw = rows(HW / "channel" / "adhoc_sweep_5ghz.csv")
    held = [r for r in hw if r["phase"] == "A"]
    sent = sum(int(r["sent_app"]) for r in held)
    got = sum(int(r["received_unique"]) for r in held)
    # A single transmitter offered more than the channel carries: its achieved rate is the
    # reciprocal of one frame's whole cycle. The prediction is the one written down before the run
    # (results/hw/channel/RESULTS.md): DIFS 34 + preamble 20 + mean backoff 67.5 us + 1400 B at
    # 6 Mb/s.
    measured_ms = 1e3 / max(float(r["achieved_fps"]) for r in hw if r["phase"] == "B")
    predicted_ms = (34 + 20 + 67.5) * 1e-3 + 1400 * 8 / 6e6 * 1e3
    exponent = math.floor(math.log10((sent - got) / sent))
    return {"valUniHi": f(max(dev["unicast"]), 2), "valUniLo": f(-min(dev["unicast"]), 2),
            "valBcast": f(max(abs(d) for d in dev["broadcast"]), 2),
            "hwAirtime": f(measured_ms, 3), "hwAirtimeModel": f(predicted_ms, 3),
            "hwAirtimeGap": f(100 * (measured_ms - predicted_ms) / predicted_ms, 2),
            "hwLossFrames": str(sent - got), "hwSentFrames": thousands(sent),
            "hwLoss": f"{(sent - got) / sent / 10 ** exponent:.1f}\\times10^{{{exponent}}}"}


# ============================================================================== exclusion, LoRa
def exclusion() -> dict[str, str]:
    table = rows(RAW / "exclusion_matrix.csv")

    def cell(auth: str, design: str, dr: str = "3") -> dict[str, str]:
        return one(table, auth_bytes=auth, design=design, dr=dr)

    sig, nolink = cell("64", "lean"), cell("64", "lean without on-air chain link")
    bls, tag = cell("48", "lean"), cell("13", "lean")
    verdicts = {int(r["dr"]): r["verdict"] for r in table
                if r["auth_bytes"] == "64" and r["design"] == "lean"}
    excluded = sorted(d for d, v in verdicts.items() if v == "excluded")
    alone = sorted(int(r["dr"]) for r in table if r["auth_bytes"] == "64"
                   and r["design"] == "lean" and r["signature_alone_overflows"] == "1")
    # the paper's sentences name these sets and these table cells; hold them to the artifact
    if (excluded, alone) != ([0, 1, 2, 3, 8, 9, 10, 11], [0, 1, 2, 8, 10]):
        raise ValueError("the excluded data rates are not the ones the paper names")
    expect = {("64", "lean"): ("excluded", "excluded", "feasible"),
              ("64", "lean without on-air chain link"): ("excluded", "feasible", "feasible"),
              ("48", "lean"): ("excluded", "excluded for this telemetry", "feasible"),
              ("13", "lean"): ("excluded", "feasible", "feasible")}
    for (auth, design), want in expect.items():
        got = tuple(cell(auth, design, dr)["verdict"] for dr in ("0", "3", "4"))
        if got != want:
            raise ValueError(f"Table 'excl' row ({auth} B, {design}) says {want}; artifact {got}")
    floor = int(sig["frame_floor_bytes"])
    link = frame_model.LINK_FIELD_BYTES
    floor_hdr = frame_model.lean_header_bytes(src=0, base_seq=0, n=1, stream_bytes=9)
    floor_rec = floor - floor_hdr - link - 64
    hdr_hi = frame_model.lean_header_bytes(src=40_000, base_seq=180_000, n=1, stream_bytes=25)
    return {
        "exclCount": WORDS[len(excluded)], "exclCountCap": WORDS[len(excluded)].capitalize(),
        "exFloor": str(floor), "exLo": sig["frame_min_bytes"], "exHi": sig["frame_max_bytes"],
        "exFloorHdr": str(floor_hdr), "exFloorRec": str(floor_rec),
        "exFloorNoRec": str(floor - floor_rec),
        "exFloorNoLink": nolink["frame_floor_bytes"], "exLoNoLink": nolink["frame_min_bytes"],
        "exHiNoLink": nolink["frame_max_bytes"],
        "exFloorBls": bls["frame_floor_bytes"], "exLoBls": bls["frame_min_bytes"],
        "exHiBls": bls["frame_max_bytes"],
        "exFloorTag": tag["frame_floor_bytes"], "exLoTag": tag["frame_min_bytes"],
        "exHiTag": tag["frame_max_bytes"],
        "exHdrLinkLo": str(floor_hdr + link), "exHdrLinkHi": str(hdr_hi + link),
    }


def low_rate() -> dict[str, str]:
    budget = rows(RAW / "lora_budget.csv")
    lean = one(budget, dr="5", payload_limit="242", design="lean; frames decode alone")
    first = one(budget, dr="5", payload_limit="242",
                design="first; link per frame; frames decode alone")
    cap = rows(RAW / "lora_capacity.csv")
    passing = [int(r["n_devices"]) for r in cap if r["meets_v"] == "1"]
    n_max = 0
    for n in sorted(int(r["n_devices"]) for r in cap):     # first-failure rule, as everywhere
        if n not in passing:
            break
        n_max = n
    theirs = 0
    while lora.haxhibeqiri2017_loss_pct(theirs + 1) <= 5.0:
        theirs += 1
    at_limit = one(cap, n_devices=str(n_max))
    design = one(rows(RAW / "design_ladder.csv"), op="adopted", format="lean",
                 rung="batch-delta", scheme="ed25519")
    if design["n_max_v95"] == "":
        MISSING.append("N_max of the lean design at the adopted point")
        wifi = "??"
    else:      # records per second a whole neighbourhood offers, to two significant figures
        total = float(design["lambda_rec_per_s"]) * int(design["n_max_v95"])
        wifi = thousands(int(round(total, -2)))
    published = one(budget, dr="5", payload_limit="242", design=(
        "first; link per frame; AS PUBLISHED (13 B bodies and no keyframe)"))
    # The simulator's module carries 222 B at most, so the capacity was simulated at that
    # payload table; the text says the lean frame holds as many records there as were simulated.
    fits_module = one(budget, dr="5", payload_limit="222", design="lean; frames decode alone")
    if fits_module["batch"] != at_limit["batch"]:
        raise ValueError("the simulated LoRa batch is not the lean frame's batch at 222 B")
    if abs(float(fits_module["toa_ms"]) / (float(at_limit["app_period_s"]) * 10) - 1) > 0.02:
        raise ValueError("the simulated LoRa frame's airtime is not the lean frame's within 2%")
    return {"loraSimRecs": WORDS[int(at_limit["batch"])], "loraSimBytes": at_limit["payload_bytes"],
            "loraSimPeriod": f(at_limit["app_period_s"], 0),
            "loraSimRate": f(at_limit["lambda_rec_per_s"], 3),
            "loraRecsLean": lean["batch"], "loraRateLean": f(lean["lambda_rec_per_s"], 2),
            "loraRecsFirst": first["batch"], "loraRateFirst": f(first["lambda_rec_per_s"], 2),
            "loraFrmLean": f(lean["frame_bytes"], 0), "loraFrmFirst": f(first["frame_bytes"], 0),
            "loraRecsPub": published["batch"], "loraFrmPub": f(published["frame_bytes"], 0),
            "loraRatePub": f(published["lambda_rec_per_s"], 3),
            "loraNmax": WORDS[n_max], "loraNmaxExt": WORDS[theirs],
            "loraAgg": f(at_limit["aggregate_rec_per_s"], 1), "wifiAgg": wifi,
            **_lora_capacity_readings(n_max)}


def _lora_capacity_readings(n_max: int) -> dict[str, str]:
    """The interval on the LoRa capacity and its per-run reading, from the artifact's header.

    Both criteria are reported and the mean is the headline (decision of 2026-08-06): at the
    capacity the mean certifies, nine runs of thirty fail the criterion being certified.
    """
    head = dict(ln[2:].split("=", 1) for ln in
                (RAW / "lora_capacity_ci.csv").read_text(encoding="utf-8").splitlines()
                if ln.startswith("# ") and "=" in ln)
    lo, hi = (int(x) for x in head["n_max_ci95"].strip("[]").split(","))
    if int(head["n_max_mean_criterion"]) != n_max or not lo <= n_max <= hi:
        raise ValueError("lora_capacity_ci.csv and lora_capacity.csv disagree on N_max")
    return {"loraNmaxCi": f"[{lo},\\,{hi}]",
            "loraNmaxRun": WORDS[int(head["n_max_strict_criterion"])]}


# ============================================================================== traffic source
def source_study() -> dict[str, str]:
    """What freezing the senders' phases does to one cell (thesis ch. 8 and 11)."""
    direct = rows(RAW / "ns3_nmax_direct.csv")
    frozen = one(direct, cell="A", n_nodes="29", jitter_ms="0", skew_ppm="0")
    redrawn = one(direct, cell="A", n_nodes="29", jitter_ms="20", skew_ppm="0")
    nodes = [float(r["node_delivered_frac"])
             for r in rows(RAW / "ns3_phase_lock_diagnostic.csv")
             if (r["seed"], r["jitter_ms"], r["skew_ppm"], r["n_nodes"]) == ("6", "0", "0", "29")]
    if len(nodes) != 29:
        raise ValueError("the per-node diagnostic no longer holds the run the thesis describes")
    return {"phaseSdFrozen": f(frozen["delivered_stdev"], 3),
            "phaseSdRedrawn": f(redrawn["delivered_stdev"], 4),
            "phaseNodes": str(len(nodes)),
            "phaseSilentNodes": WORDS[sum(x == 0.0 for x in nodes)],
            "phaseCleanNodes": str(sum(x == 1.0 for x in nodes))} | _source_difference(direct)


def _source_difference(direct: list[dict[str, str]]) -> dict[str, str]:
    """Mean delivery under the redrawn source minus the strictly periodic one, where both ran.

    The text says the two agree within the 0.005 registered in follow-up F1 and that every
    crossing is higher under the redrawn source; both are checked here.
    """
    by_point: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    crossing: dict[str, dict[str, float]] = defaultdict(dict)
    for r in direct:
        if r["skew_ppm"] != "0":
            continue
        period_ms = 1000.0 * float(r["batch"]) / float(r["lambda_rec_per_s"])
        source = {0.0: "frozen", period_ms: "redrawn"}.get(float(r["jitter_ms"]))
        if source is None:
            continue
        if r["n_nodes"] == "CROSSING":
            if r["n_cross_interp"]:
                crossing[r["cell"]][source] = float(r["n_cross_interp"])
        else:
            by_point[(r["cell"], r["n_nodes"])][source] = float(r["delivered_mean"])
    diffs = [v["redrawn"] - v["frozen"] for v in by_point.values() if len(v) == 2]
    shifts = [100.0 * (v["redrawn"] / v["frozen"] - 1.0) for v in crossing.values() if len(v) == 2]
    if len(diffs) < 14 or len(shifts) < 6:
        raise ValueError("fewer points were run under both traffic sources than the text says")
    if abs(st.mean(diffs)) > 0.005:
        raise ValueError("the two traffic sources differ by more than the 0.005 the text states")
    if min(shifts) <= 0.0:
        raise ValueError("the text says every crossing is higher under the redrawn source")
    return {"srcPoints": str(len(diffs)), "srcMeanDiff": f(st.mean(diffs), 3),
            "srcShiftLo": f(min(shifts), 0), "srcShiftHi": f(max(shifts), 0)} | _fresh_seeds()


def _fresh_seeds() -> dict[str, str]:
    """Follow-up F4: the same comparison on seeds never used (docs/NMAX_DIRECT_EXPECTATIONS.md).

    The text says the difference seen in the first sample did not replicate, and that strictly
    periodic senders vary far more from run to run. Both are checked.
    """
    samples = sources.by_source(sources.read(sources.FRESH))
    fresh = sources.difference(samples, sources.FRESH_SEEDS)
    first = sources.difference(sources.by_source(sources.read(sources.FIRST)),
                               sources.FIRST_SEEDS)
    if fresh.points != first.points:
        raise ValueError("the fresh-seed sample does not cover the points of the first one")
    if fresh.z >= 1.0:
        raise ValueError("the text says the traffic-source difference did not replicate; "
                         f"z = {fresh.z:.2f} on the fresh seeds")
    ratios = [st.stdev(s["periodic"].values()) / st.stdev(s["redrawn"].values())
              for s in samples.values()]
    if min(ratios) < 3.0:
        raise ValueError("the text says strictly periodic senders vary several times more "
                         "between runs at every point")
    runs = sum(len(v) for s in samples.values() for v in s.values())
    return {"srcFreshD": f(fresh.d, 4), "srcFreshSe": f(fresh.se, 4), "srcFreshZ": f(fresh.z, 1),
            "srcFirstZ": f(first.z, 1), "srcFreshRuns": thousands(runs),
            "srcSpreadLo": f(min(ratios), 0), "srcSpreadHi": f(max(ratios), 0)}


# ============================================================================== capacity rule
def capacity_rule() -> dict[str, str]:
    """The airtime line, calibrated on six cells and scored on the seven it never saw (F2).

    The text says the registered prediction held: every held-out crossing within the tolerance of
    the line, and closer to the line than to the single load ceiling wherever the two differ by
    more than a tenth. If the runs stop saying so, this stops.
    """
    import run_nmax_direct as drv  # ns3/ is put on the path by nmax_airtime_line
    measured = airtime.crossings("period")
    slope, _ = airtime.calibrate(measured)
    predicted = airtime.predictions(slope)
    scored = airtime.held_out_crossings()          # on the grids the test was registered on
    missing = [c for c in airtime.HELD_OUT if c not in scored]
    if missing:
        MISSING.append(f"held-out crossings of cells {', '.join(missing)}")
        names = ["lineA", "lineWorst", "lineFitWorst", "lineCeilWorst", "lineNlo", "lineNhi"]
        names += [f"line{kind}{c}" for c in airtime.HELD_OUT for kind in "PMDC"]
        return dict.fromkeys(names, "??")
    got = {c: float(measured[c]["n_cross_interp"]) for c in airtime.CALIBRATION} \
        | {c: scored[c][0] for c in airtime.HELD_OUT}
    vs_line = {c: 100.0 * (got[c] - predicted[c]) / predicted[c] for c in airtime.HELD_OUT}
    vs_ceiling = {c: 100.0 * (got[c] - drv.CELLS[c].model_n) / drv.CELLS[c].model_n
                  for c in got}
    if max(abs(v) for v in vs_line.values()) > 100.0 * airtime.TOLERANCE:
        raise ValueError("the text says every held-out cell is within the registered tolerance "
                         f"of the airtime line; the runs say {vs_line}")
    if any(abs(vs_line[c]) >= abs(vs_ceiling[c]) for c in airtime.DIAGNOSTIC):
        raise ValueError("the text says the line beats the single ceiling in every diagnostic "
                         "cell; the runs disagree")
    fit = [100.0 * (got[c] / airtime.n_line(
        slope, drv.CELLS[c].fps, bianchi.t_broadcast(drv.CELLS[c].frame_bytes)) - 1.0)
        for c in airtime.CALIBRATION]
    per_cell = {}
    for c in airtime.HELD_OUT:          # prediction, measured, and the two deviations, signed
        per_cell |= {f"lineP{c}": f(predicted[c], 1), f"lineM{c}": f(got[c], 1),
                     f"lineD{c}": signed(vs_line[c]), f"lineC{c}": signed(vs_ceiling[c])}
    stream_cells = _stream_cells_against_the_line()
    tested = list(airtime.CALIBRATION + airtime.HELD_OUT + airtime.STREAM)
    # the neighbourhood sizes the rule was checked at, as the tables print them (N_max, not the
    # interpolated crossing: 28 and 306, where the interpolation gives 29.0 and 308.0)
    n_max = [int(measured[c]["n_max_mean"]) for c in tested if c in measured]
    return per_cell | stream_cells | {
            "lineA": f(slope, 3),
            "lineWorst": f(max(abs(v) for v in vs_line.values()), 1),
            "lineFitWorst": f(max(abs(v) for v in fit), 1),
            "lineCeilWorst": f(max(abs(v) for v in vs_ceiling.values()), 0),
            "lineNlo": str(min(n_max)),
            "lineNhi": str(max(n_max)),
            "lineFrameLo": str(min(drv.CELLS[c].frame_bytes for c in tested)),
            "lineFrameHi": str(max(drv.CELLS[c].frame_bytes for c in tested)),
            "lineFpsLo": f"{min(drv.CELLS[c].fps for c in tested):g}",
            "lineFpsHi": f"{max(drv.CELLS[c].fps for c in tested):g}"}


def _stream_cells_against_the_line() -> dict[str, str]:
    """Follow-up F3: the five stream-scheme frames, predicted with the same slope, then run.

    The text says all five fell inside the registered tolerance and above the line.
    """
    scores = airtime.stream_scores()
    names = [f"line{kind}{c}" for c in airtime.STREAM for kind in "PMD"]
    if set(scores) != set(airtime.STREAM):
        MISSING.append("the crossings of the five stream-scheme cells")
        return dict.fromkeys([*names, "lineStreamWorst", "lineStreamLeast"], "??")
    if not all(s["within_band"] for s in scores.values()):
        raise ValueError("the text says every stream cell is within the registered tolerance")
    if min(s["vs_line_pct"] for s in scores.values()) <= 0:
        raise ValueError("the text says all five stream cells cross above the line")
    out = {}
    for c, s in scores.items():
        out |= {f"lineP{c}": f(s["line"], 1), f"lineM{c}": f(s["measured"], 1),
                f"lineD{c}": signed(s["vs_line_pct"])}
    deviations = [s["vs_line_pct"] for s in scores.values()]
    return out | {"lineStreamWorst": f(max(deviations), 1),
                  "lineStreamLeast": f(min(deviations), 1)}


def capacity_model() -> dict[str, str]:
    """The access-rule model against ns-3 (docs/02 §6g; `results/raw/dcf_model_vs_ns3.csv`).

    The text says an event simulation of the access rule, with nothing fitted, reproduces every
    simulated crossing, and that the slope the airtime line fitted is the tie term at the
    occupancy where loss reaches 5 %. Both are checked here.
    """
    import run_nmax_direct as drv
    table = rows(RAW / "dcf_model_vs_ns3.csv")
    crossings = [r for r in table if r["n_nodes"] == "CROSSING"]
    points = [r for r in table if r["n_nodes"] != "CROSSING"]
    errors = [abs(float(r["crossing_error_pct"])) for r in crossings]
    if {r["cell"] for r in crossings} != set(airtime.crossings("period")):
        raise ValueError("the model comparison does not cover every simulated configuration")
    if max(errors) > 2.0:
        raise ValueError("the text says the access-rule model reproduces every crossing closely")
    occupancy = [(float(r["ns3_crossing"]) - 1) * drv.CELLS[r["cell"]].fps
                 * bianchi.t_broadcast(drv.CELLS[r["cell"]].frame_bytes) for r in crossings]
    rho = st.mean(occupancy)
    slope = rho / (16 * (1 - rho))
    fitted, _ = airtime.calibrate(airtime.crossings("period"))
    if abs(slope - fitted) > 0.002:
        raise ValueError("the text says the fitted slope is the tie term at the mean occupancy "
                         f"of the crossings; {slope:.4f} against {fitted:.4f}")
    ties = [float(r["model_tie_share"]) for r in points]
    return _model_predictions() | {
            "modelCells": str(len(crossings)), "modelPoints": str(len(points)),
            "modelWorst": f(max(errors), 1), "modelMean": f(st.mean(errors), 1),
            "modelMaxDiff": f(max(abs(float(r["difference"])) for r in points), 3),
            "modelTieLo": f(100 * min(ties), 0), "modelTieHi": f(100 * max(ties), 0),
            "modelRho": f(rho, 2), "modelRhoLo": f(min(occupancy), 2),
            "modelRhoHi": f(max(occupancy), 2), "modelSlope": f(slope, 3)}


def _model_predictions() -> dict[str, str]:
    """Follow-up F5: the model's crossings for conditions ns-3 had not been run at.

    The text says every one of the registered predictions fell inside its band. A case whose
    runs are not complete is recorded as missing, so the sentence cannot be printed early.
    """
    scored = {r["case"]: r for r in modelcheck.score()}
    names = ["modelPredCases", "modelPredWorst", "modelPredWindowC", "modelNsWindowC",
             "modelPredWindowD", "modelNsWindowD", "modelBaseC", "modelGainC", "modelGainD"]
    if set(scored) != {c.name for c in modelcheck.CASES}:
        MISSING.append("ns-3 runs for every registered prediction of the access-rule model")
        return dict.fromkeys(names, "??")
    outside = [name for name, r in scored.items() if not r["within_band"]]
    if outside:
        raise ValueError(f"the text says every registered prediction held; outside: {outside}")
    c, d = scored["C, window doubled"], scored["D, window doubled"]
    # the same two configurations at the standard window, read the same way (interpolated)
    base = {r["cell"]: float(r["ns3_crossing"]) for r in rows(RAW / "dcf_model_vs_ns3.csv")
            if r["n_nodes"] == "CROSSING"}
    gain = {cell: 100.0 * (r["ns3"] / base[cell] - 1.0) for cell, r in (("C", c), ("D", d))}
    if not all(5.0 < g < 20.0 for g in gain.values()):
        raise ValueError("the text says doubling the window buys about an eighth more capacity")
    return {"modelBaseC": f(base["C"], 1), "modelGainC": f(gain["C"], 0),
            "modelGainD": f(gain["D"], 0), "modelPredCases": WORDS[len(scored)],
            "modelPredWorst": f(max(abs(r["error_pct"]) for r in scored.values()), 1),
            "modelPredWindowC": f(c["predicted"], 1), "modelNsWindowC": f(c["ns3"], 1),
            "modelPredWindowD": f(d["predicted"], 1), "modelNsWindowD": f(d["ns3"], 1)}


def sitl() -> dict[str, str]:
    """Records at the operating rate and the stream's timing, from PX4 run in simulation.

    The text says every delta record at 20 ms is at the format's floor, that the design costs
    less with these records than with the generator's, and that the stream holds its period far
    more tightly than a send time redrawn each period. Each is checked.
    """
    sizes = {(r["part"], r["spacing_ms"]): r for r in rows(RAW / "px4_sitl_sizes.csv")}
    timing = {r["quantity"]: r for r in rows(RAW / "px4_sitl_stream_timing.csv")}
    whole, compare = sizes[("whole flight", "20")], sizes[("whole flight", "200")]
    floor = one(rows(RAW / "frame_components.csv"), kind="record", format="lean", item="delta",
                stride="1")
    if any((r["lean_delta_min"], r["lean_delta_max"]) != (floor["min_bytes"], floor["max_bytes"])
           for (_, spacing), r in sizes.items() if spacing == "20"):
        raise ValueError("the text says every delta record at 20 ms is at the format's floor")
    design = one(rows(RAW / "design_ladder.csv"), op="adopted", format="lean",
                 rung="batch-delta", scheme="ed25519")
    if not float(whole["bytes_per_rec"]) < float(design["bytes_per_rec"]):
        raise ValueError("the text says the design costs less with the simulated flight's records")
    flight = timing["flight: received, wall clock, clock steps removed"]
    ground = timing["ground: received, monotonic clock"]
    spread = [float(flight["half_p16_p84_ms"]), float(ground["half_p16_p84_ms"])]
    if max(spread) - min(spread) > 0.05 or max(spread) > 1.0:
        raise ValueError("the text gives one spread for the stream's timing, well under 1 ms")
    period = float(timing["flight: stamped (time_boot_ms)"]["mean_ms"])
    if abs(period - 20.0) > 0.05:
        raise ValueError("the text says the stream's period is 20.0 ms on the autopilot's clock")
    fast = sizes[("square_12mps", "20")]
    return {"sitlRecords": thousands(int(whole["records"])),
            "sitlKey": f(whole["lean_key_mean"], 1), "sitlBpr": f(whole["bytes_per_rec"], 2),
            "sitlSpeedMax": f(fast["max_speed_mps"], 0),
            "sitlSpeedFast": f(fast["mean_speed_mps"], 1),
            "sitlCompare": f(compare["lean_delta_mean"], 2),
            "sitlJitter": f(st.mean(spread), 1), "sitlJitterTwo": f(st.mean(spread), 2),
            "sitlSd": f(ground["sd_ms"], 1), "sitlPeriod": f(period, 1),
            "sitlGenPct": f(100 * (1 - float(whole["bytes_per_rec"])
                                   / float(design["bytes_per_rec"])), 1)}


def signed(percent: float) -> str:
    """A deviation with its sign, one decimal, for a table cell."""
    return ("+" if percent >= 0 else "$-$") + f(abs(percent), 1)


SECTIONS = (frames, ladder, loss, stream, freshness, phy, energy, timings, flight_logs,
            validation, exclusion, low_rate, source_study, capacity_rule, capacity_model, sitl)


def macros() -> dict[str, str]:
    out: dict[str, str] = {}
    for section in SECTIONS:
        new = section()
        clash = set(out) & set(new)
        if clash:
            raise ValueError(f"macro defined twice: {sorted(clash)}")
        out |= new
    bad = [name for name in out if not name.isalpha()]
    if bad:
        raise ValueError(f"LaTeX macro names are letters only: {bad}")
    return out


def render() -> str:
    lines = ["% GENERATED by analysis/paper_numbers.py from results/ — do not edit.",
             "% `make paper` rewrites it; tests/test_paper_numbers.py fails if it is stale."]
    lines += [f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in sorted(macros().items())]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if numbers.tex is stale")
    ap.add_argument("--allow-missing", action="store_true",
                    help="write ?? for values no artifact holds yet (drafts only)")
    args = ap.parse_args()
    text = render()
    if MISSING and not (args.allow_missing and not args.check):
        raise SystemExit("no artifact holds these yet:\n  " + "\n  ".join(dict.fromkeys(MISSING)))
    if MISSING:
        print(f"⚠️ DRAFT: {len(set(MISSING))} values written as ??", file=sys.stderr)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            raise SystemExit(f"{OUT.relative_to(REPO)} is stale: run analysis/paper_numbers.py")
        print(f"{OUT.relative_to(REPO)} is current ({text.count('newcommand')} macros)")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({text.count('newcommand')} macros)")


if __name__ == "__main__":
    main()
