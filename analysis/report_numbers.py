#!/usr/bin/env python3
"""Every result the model report prints, computed from the stored files, rounded once
(docs/reports/2026-11-27_model_report/). The report never types a result by hand: it uses the
macros this script writes to `numbers.tex`, and `provenance.csv` names each macro's source file and
registration.

    python analysis/report_numbers.py
        -> docs/reports/2026-11-27_model_report/numbers.tex and provenance.csv
"""

from __future__ import annotations

import csv
import re
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

RAW = REPO / "results" / "raw"
OUT = REPO / "docs" / "reports" / "2026-11-27_model_report"


def rows(name: str) -> list[dict[str, str]]:
    with (RAW / name).open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def truthy(v: str) -> bool:
    return v.strip() in ("True", "1", "true")


def f1(x: float) -> str:
    return f"{x:.1f}"


def f2(x: float) -> str:
    return f"{x:.2f}"


def signed(x: float, d: int = 1) -> str:
    return f"{x:+.{d}f}".replace("-", "\\textminus{}")


def collect() -> list[tuple[str, str, str, str]]:
    """(macro, value as typeset, source file, registration/where)."""
    out: list[tuple[str, str, str, str]] = []

    def put(name: str, value: str, src: str, where: str) -> None:
        out.append((name, value, src, where))

    # ---- the ns-3 scorecard: (G9) and the root of (G5) against stored capacities ----------
    sc = [r for r in rows("unified_model_vs_ns3.csv") if r["law_err_pct"] and r["ns3"]]
    src = "unified_model_vs_ns3.csv"
    law = [float(r["law_err_pct"]) for r in sc if truthy(r["law_valid"])]
    root = [float(r["root_err_pct"]) for r in sc]
    put("scRows", str(len(sc)), src, "analysis/score_unified_model.py")
    put("scLawRows", str(len(law)), src, "law_valid rows")
    put("scLawIn", str(sum(abs(x) <= 5 for x in law)), src, "|err| <= 5 %")
    put("scRootIn", str(sum(abs(x) <= 5 for x in root)), src, "|err| <= 5 %")
    put("scLawMeanAbs", f1(st.mean(abs(x) for x in law)), src, "mean |err|")
    put("scRootMeanAbs", f1(st.mean(abs(x) for x in root)), src, "mean |err|")
    put("scLawSafe", str(sum(x <= 0 for x in law)), src, "err <= 0 (model below ns-3)")
    put("scRootSafe", str(sum(x <= 0 for x in root)), src, "err <= 0")
    put("scRootOut", str(sum(abs(x) > 5 for x in root)), src, "|err| > 5 %")
    put("scRootOutSafe", str(sum(x < -5 for x in root)), src, "err < -5 % (conservative)")
    put("scLawOut", str(sum(abs(x) > 5 for x in law)), src, "law: |err| > 5 %")
    put("scLawOutSafe", str(sum(x < -5 for x in law)), src, "law: err < -5 %")
    opt = [r for r in sc if truthy(r["law_valid"]) and float(r["law_err_pct"]) > 5]
    put("scLawOptN", str(len(opt)), src, "law: err > +5 % (optimistic)")
    put(
        "scLawOptErr",
        signed(max(float(r["law_err_pct"]) for r in opt)),
        src,
        f"law: worst optimistic miss, cell {opt[0]['cell']} jitter {opt[0]['jitter_ms']}",
    )
    for std, tag in (("80211a", "A"), ("80211p", "P"), ("80211b", "B")):
        sub = [float(r["root_err_pct"]) for r in sc if r["standard"] == std]
        put(f"sc{tag}Rows", str(len(sub)), src, std)
        put(f"sc{tag}RootIn", str(sum(abs(x) <= 5 for x in sub)), src, std)
        put(f"sc{tag}RootMin", signed(min(sub)), src, std)
        put(f"sc{tag}RootMax", signed(max(sub)), src, std)

    # ---- (G25): new cells, and past occupancy 0.78 -----------------------------------------
    ug = rows("ug25_scored.csv")
    g25 = [float(r["g25_err_pct"]) for r in ug]
    poi = [float(r["poisson_err_pct"]) for r in ug]
    put("ugCells", str(len(ug)), "ug25_scored.csv", "prereg-UG25")
    put("ugHeld", str(sum(truthy(r["held"]) for r in ug)), "ug25_scored.csv", "prereg-UG25")
    put("ugMin", signed(min(g25)), "ug25_scored.csv", "(G25) error")
    put("ugMax", signed(max(g25)), "ug25_scored.csv", "(G25) error")
    put("ugPoiMin", signed(min(poi)), "ug25_scored.csv", "Poisson error")
    put("ugPoiMax", signed(max(poi)), "ug25_scored.csv", "Poisson error")
    uh = rows("ug25h_scored.csv")
    e = [float(r["g25_err_pct"]) for r in uh]
    occ = [float(r["occupancy_at_ns3"]) for r in uh]
    put("uhCells", str(len(uh)), "ug25h_scored.csv", "prereg-UG25H")
    put("uhMin", signed(min(e), 2), "ug25h_scored.csv", "(G25) error")
    put("uhMax", signed(max(e), 2), "ug25h_scored.csv", "(G25) error")
    put("uhOccMin", f2(min(occ)), "ug25h_scored.csv", "occupancy at ns-3's crossing")
    put("uhOccMax", f2(max(occ)), "ug25h_scored.csv", "occupancy at ns-3's crossing")

    # ---- capture in ns-3: U-CAP2, U-F, UF2 -------------------------------------------------
    cap = rows("ucap2_scored.csv")
    put("capTrials", str(len(cap)), "ucap2_scored.csv", "prereg-UCAP2")
    put("capHeld", str(sum(truthy(r["held"]) for r in cap)), "ucap2_scored.csv", "prereg-UCAP2")
    uf = rows("uf_scored.csv")
    put("ufConfigs", str(len(uf)), "uf_scored.csv", "prereg-UF")
    put("ufAvgHeld", str(sum(truthy(r["g23_held"]) for r in uf)), "uf_scored.csv", "(G23)")
    put("ufWorstHeld", str(sum(truthy(r["g24_held"]) for r in uf)), "uf_scored.csv", "(G24)")
    u2 = rows("uf2_scored.csv")
    put("ufTwoClaims", str(len(u2)), "uf2_scored.csv", "prereg-UF2")
    put("ufTwoHeld", str(sum(truthy(r["held"]) for r in u2)), "uf2_scored.csv", "prereg-UF2")
    for key, tag in (("(a)", "A"), ("statistic 2", "Win"), ("statistic 1", "Pool")):
        v = [float(r["err_pct"]) for r in u2 if r["claim"].startswith(key)]
        put(f"ufTwo{tag}Min", signed(min(v), 2), "uf2_scored.csv", key)
        put(f"ufTwo{tag}Max", signed(max(v), 2), "uf2_scored.csv", key)

    # ---- the finite-station form, and LoRa's duty cycle ------------------------------------
    fs = rows("ufs_scored.csv")
    put("fsCells", str(len(fs)), "ufs_scored.csv", "prereg-UFS")
    put("fsHeld", str(sum(truthy(r["held"]) for r in fs)), "ufs_scored.csv", "prereg-UFS")
    c7 = rows("uc7_scored.csv")
    put("lrCells", str(len(c7)), "uc7_scored.csv", "prereg-UC7")
    put("lrHeld", str(sum(truthy(r["held"]) for r in c7)), "uc7_scored.csv", "prereg-UC7")

    # ---- the batching gain (G12) against ns-3 ----------------------------------------------
    c2 = [r for r in rows("unified_c2_scored.csv") if r["gain_err_pct"]]
    if c2:
        g = [float(r["gain_err_pct"]) for r in c2]
        put(
            "gainMaxAbs",
            f1(max(abs(x) for x in g)),
            "unified_c2_scored.csv",
            "batching gain (G12), reported, not scored",
        )
    c2x = [r for r in rows("unified_c2_scored.csv") if r["kind"] == "crossing"]
    put("ucTwoClaims", str(2 * len(c2x)), "unified_c2_scored.csv", "prereg-UC2, law and root")
    put(
        "ucTwoHeld",
        str(sum(truthy(r["law_held"]) + truthy(r["root_held"]) for r in c2x)),
        "unified_c2_scored.csv",
        "prereg-UC2, law and root",
    )
    # ---- the 802.11b arm (U-D): D1 small swarms, D2 batching --------------------------------
    ud = rows("unified_d_scored.csv")
    d1b = [r for r in ud if r["item"] == "D1" and r["cell"].startswith("Pb1B")]
    d1d = [r for r in ud if r["item"] == "D1" and r["cell"].startswith("Pb1D")]
    d2 = [r for r in ud if r["item"] == "D2"]
    src = "unified_d_scored.csv"
    put(
        "udBScored",
        str(sum(r["root_verdict"] in ("held", "failed") for r in d1b)),
        src,
        "prereg-UD, Pb1B root",
    )
    put("udBHeld", str(sum(r["root_verdict"] == "held" for r in d1b)), src, "prereg-UD, Pb1B root")
    put("udDCells", str(len(d1d)), src, "prereg-UD, Pb1D")
    put(
        "udDRootFailed",
        str(sum(r["root_verdict"] == "failed" for r in d1d)),
        src,
        "prereg-UD, Pb1D root",
    )
    put(
        "udDLawFailed",
        str(sum(r["law_verdict"] == "failed" for r in d1d)),
        src,
        "prereg-UD, Pb1D law",
    )
    rd = [float(r["root_err_pct"]) for r in d1d]
    put("udDRootMin", signed(min(rd)), src, "Pb1D root error")
    put("udDRootMax", signed(max(rd)), src, "Pb1D root error")
    put(
        "udBelow",
        str(sum(float(r["root_err_pct"]) < 0 for r in d1b + d1d)),
        src,
        "D1 crossings with the model below ns-3",
    )
    put("udDOneAll", str(len(d1b + d1d)), src, "D1 crossings")
    put("udTwoCells", str(len(d2)), src, "prereg-UD, D2")
    put(
        "udTwoHeld",
        str(sum(r["root_verdict"] == "held" and r["law_verdict"] == "held" for r in d2)),
        src,
        "prereg-UD, D2 law and root",
    )
    gb = [float(r["gain_err_pct"]) for r in ud if r["item"].startswith("D2 gain")]
    put("gainBMaxAbs", f1(max(abs(x) for x in gb)), src, "802.11b gain (G12), reported")
    # ---- the loss expression term by term (U-C1 at 802.11a, D3 at 802.11b) -----------------
    for name, tag in (("unified_c1_scored.csv", "ucOne"), ("unified_d3_scored.csv", "udThree")):
        t = rows(name)
        put(f"{tag}Held", str(sum(truthy(r["held"]) for r in t)), name, "terms, a, K, p")
        put(f"{tag}Cases", str(len(t)), name, "terms, a, K, p")
        tot = [r for r in t if r["quantity"] == "p"]
        put(f"{tag}PHeld", str(sum(truthy(r["held"]) for r in tot)), name, "the total p")
        put(f"{tag}PCases", str(len(tot)), name, "the total p")
        e = [float(r["pred_vs_meas_pct"]) for r in tot]
        put(f"{tag}PMin", signed(min(e)), name, "the total p: model against ns-3 (%)")
        put(f"{tag}PMax", signed(max(e)), name, "the total p: model against ns-3 (%)")
    # ---- design rules: key records (U-C3), fragments (U-C4, U-C4S), best batch (U-C5-D1) ----
    c34 = [r for r in rows("unified_c34_scored.csv") if r["law_verdict"]]
    k = [r for r in c34 if r["item"] == "C3"]
    put(
        "ucThreeHeld",
        str(sum(r["root_verdict"] == "held" and r["law_verdict"] == "held" for r in k)),
        "unified_c34_scored.csv",
        "prereg-UC3",
    )
    put("ucThreeCells", str(len(k)), "unified_c34_scored.csv", "prereg-UC3")
    fr = [r for r in c34 if r["item"] == "C4"]
    put(
        "ucFourRootFailed",
        str(sum(r["root_verdict"] == "failed" for r in fr)),
        "unified_c34_scored.csv",
        "prereg-UC4, back-to-back fragments",
    )
    put("ucFourCells", str(len(fr)), "unified_c34_scored.csv", "prereg-UC4")
    sb = rows("unified_c4sb_scored.csv")
    sp = [r for r in sb if r["item"] == "C4S"]
    put(
        "ucFourSHeld",
        str(sum(r["verdict"] == "held" for r in sp)),
        "unified_c4sb_scored.csv",
        "prereg-UC4S, spread fragments",
    )
    put("ucFourSCells", str(len(sp)), "unified_c4sb_scored.csv", "prereg-UC4S")
    c5 = [r for r in rows("c5_d1_scored.csv") if r["ns3_crossing"]]
    best = max(c5, key=lambda r: float(r["ns3_crossing"]))
    put("ucFiveBest", best["b"], "c5_d1_scored.csv", "prereg-UC5D1: ns-3's best batch")
    pbest = max(c5, key=lambda r: float(r["predicted_root"]))
    put("ucFivePred", pbest["b"], "c5_d1_scored.csv", "prereg-UC5D1: the model's best batch")
    # ---- loss on air (W3a) -------------------------------------------------------------------
    w3 = [r for r in rows("w3a_w3a_2026-11-06.csv") if r["what"].startswith("W3a-")]
    put("wtHeld", str(sum(truthy(r["held"]) for r in w3)), "w3a_w3a_2026-11-06.csv", "prereg-W3a")
    put("wtClaims", str(len(w3)), "w3a_w3a_2026-11-06.csv", "prereg-W3a")

    # ---- hardware ----------------------------------------------------------------------------
    w1e = [r for r in rows("w1e_w1e_2026-11-05.csv") if r["what"] == "contention"]
    put("weHeld", str(sum(truthy(r["held"]) for r in w1e)), "w1e_w1e_2026-11-05.csv", "prereg-W1e")
    put("wePoints", str(len(w1e)), "w1e_w1e_2026-11-05.csv", "prereg-W1e")
    for run, tag in (("w1i_w1j_2026-11-06_run.csv", "J"), ("w1i_w1k_2026-11-06_run.csv", "K")):
        r = next(x for x in rows(run) if x["what"] == "ratio")
        put(f"ratio{tag}", f2(float(r["measured"])), run, "AUTHBC / per-record, hardware")
        if tag == "J":
            put("ratioModel", f2(float(r["predicted"])), run, "AUTHBC / per-record, model")
            put("ratioLo", f2(float(r["band_lo"])), run, "registered band")
            put("ratioHi", f2(float(r["band_hi"])), run, "registered band")
        for grp, gt in (("AUTHBC", "Auth"), ("per-record", "Per")):
            x = next(y for y in rows(run) if y["what"] == "crossing" and y["group"] == grp)
            put(f"cross{gt}{tag}", f1(float(x["measured"])), run, f"{grp} crossing, hardware")
            if tag == "J":
                put(f"cross{gt}Model", f1(float(x["predicted"])), run, f"{grp} crossing, model")
    out += hardware()
    out += comparisons()
    out += quoted()
    return out


def comparisons() -> list[tuple[str, str, str, str]]:
    """Ratios and spans the report's prose states, computed from the same files."""
    out: list[tuple[str, str, str, str]] = []

    def put(name: str, value: str, src: str, where: str) -> None:
        out.append((name, value, src, where))

    fs = rows("ufs_scored.csv")
    g5 = [float(r["g5_err_pct"]) for r in fs]
    put("fsGFiveMin", f"{min(g5):.0f}", "ufs_scored.csv", "(G5) over ns-3's loss, 3-5 stations (%)")
    put("fsGFiveMax", f"{max(g5):.0f}", "ufs_scored.csv", "(G5) over ns-3's loss, 3-5 stations (%)")
    miss = next(
        r
        for r in rows("w1e_w1e_2026-11-05.csv")
        if r["what"] == "contention" and not truthy(r["held"])
    )
    pr = float(miss["predicted"])
    put(
        "weMissRatio",
        f2(float(miss["measured"]) / pr),
        "w1e_w1e_2026-11-05.csv",
        f"the miss, {miss['group']}: measured over predicted",
    )
    put(
        "weMissTop",
        f2(float(miss["band_hi"]) / pr),
        "w1e_w1e_2026-11-05.csv",
        "the band's top over predicted",
    )
    run = "w1i_w1j_2026-11-06_run.csv"
    for grp, tag in (("AUTHBC", "Auth"), ("per-record", "Per")):
        x = next(y for y in rows(run) if y["what"] == "crossing" and y["group"] == grp)
        e = 100 * (float(x["measured"]) / float(x["predicted"]) - 1)
        put(f"cross{tag}Err", signed(e), run, f"{grp}: hardware over the model (%)")
    r = next(x for x in rows(run) if x["what"] == "ratio")
    put(
        "ratioErr",
        signed(100 * (float(r["measured"]) / float(r["predicted"]) - 1)),
        run,
        "ratio: hardware over the model (%)",
    )
    # W1r: the pairs with the Pi 3, hardware over ns-3, both settings
    ratios = []
    for x in rows("w1r_w1r_2026-11-22.csv"):
        if x["what"] == "point" and x["item"][:2] in ("AC", "BC"):
            ratios += [float(v) for v in re.findall(r"hardware ÷ ns-3 ([\d.]+)", x["predicted"])]
    put("twPiThreeLo", f1(min(ratios)), "w1r_w1r_2026-11-22.csv", "AC, BC: hardware / ns-3, min")
    put("twPiThreeHi", f1(max(ratios)), "w1r_w1r_2026-11-22.csv", "AC, BC: hardware / ns-3, max")
    # the same pairs, W1r against W1e
    e1 = {
        x["group"]: float(x["measured"])
        for x in rows("w1e_w1e_2026-11-05.csv")
        if x["what"] == "contention"
    }
    r1 = {}
    for x in rows("w1r_w1r_2026-11-22.csv"):
        if x["what"] == "point":
            m = re.match(r"([\d.]+) ", x["measured"])
            if m is None:
                raise ValueError(x["measured"])
            r1[x["item"].split(" (")[0]] = float(m.group(1))
    sess = [r1[k] / e1[k] for k in r1 if k[:2] in ("AC", "BC")]
    put("twSessMax", f1(max(sess)), "w1r + w1e scored files", "AC, BC: W1r over W1e, max")
    # the trio at occupancy 0.5: every prediction inside its range, and both sessions
    p = next(x for x in rows("w1r_predictions.csv") if x["group"] == "ABC" and x["u"] == "0.5")
    ev = next(
        float(x["model_loss"])
        for x in rows("w1e_predictions.csv")
        if x["what"] == "contention" and x["group"] == "ABC" and x["u"] == "0.5"
    )
    trio = [
        float(p["finite_w32"]),
        ev,
        float(p["ns3_s9d28_equal"]),
        e1["ABC at 87/s"],
        r1["ABC at 87/s"],
    ]
    put("twTrioLo", f"{100 * min(trio):.2f}", "w1r_predictions + w1e/w1r", "trio, u 0.5: min (%)")
    put("twTrioHi", f"{100 * max(trio):.2f}", "w1r_predictions + w1e/w1r", "trio, u 0.5: max (%)")
    # the worked example's two configurations: the capacity ratio D/C
    sc = {
        x["cell"]: x
        for x in rows("unified_model_vs_ns3.csv")
        if x["source_file"] == "ns3_nmax_direct" and x["note"] == "designated source"
    }
    for col, tag in (("law", "Law"), ("ns3", "Ns")):
        put(
            f"wkRatio{tag}",
            f1(float(sc["D"][col]) / float(sc["C"][col])),
            "unified_model_vs_ns3.csv",
            f"capacity of D over C, {col}",
        )
    # the TP-Link sniffer's misses, every window of S0, D1a, D1b, P1 and C1
    import s0_diag

    hw = REPO / "results" / "hw" / "frame_campaign"
    comp = [
        float(str(x["sniffer"]))
        for f in ("s0_2026-11-23", "d1a_2026-11-23", "d1b_2026-11-23", "p1x_2026-11-27")
        for x in s0_diag.rows(hw / f)
        if x.get("sniffer") not in (None, "")
    ]
    comp += [float(x["completeness"]) for x in rows("c1_c1_2026-11-27.csv") if x["completeness"]]
    put(
        "snifMissMin",
        f1(100 * (1 - max(comp))),
        "session folders + c1_c1_2026-11-27.csv",
        "the sniffer's smallest miss, any window (%)",
    )
    put(
        "snifMissMax",
        f1(100 * (1 - min(comp))),
        "session folders + c1_c1_2026-11-27.csv",
        "the sniffer's largest miss, any window (%)",
    )
    from authbc.models import unified_capacity as uc

    rho, tau0 = uc.dcf_constants(0.05, uc.A80211A)
    put("kRhoA", f"{rho:.3f}", "authbc.models.unified_capacity", "rho* at 802.11a, eps 0.05")
    put("kTauA", f"{tau0 * 1e6:.0f}", "authbc.models.unified_capacity", "tau0 at 802.11a (us)")
    # V1a: the closed form as stated against the radios (predictions/V1a.md)
    src = "v1a_v1a_2026-11-28.csv + v1a_predictions.csv"
    pts = v1a_points()
    put("vaPoints", str(len(pts)), src, "prereg-V1a")
    va = rows("v1a_v1a_2026-11-28.csv")
    put(
        "vaHeld",
        str(sum(r["held"] == "True" for r in va if r["what"] == "point")),
        src,
        "prereg-V1a, finite-station form at 15 %",
    )
    for p, tag in zip(pts, "ABC", strict=True):
        put(f"vaLoss{tag}", f"{100 * p['loss']:.3f}", src, f"measured loss less b, u = {p['u']}")
        put(f"vaLo{tag}", f"{100 * p['lo']:.3f}", src, f"95 % interval, u = {p['u']}")
        put(f"vaHi{tag}", f"{100 * p['hi']:.3f}", src, f"95 % interval, u = {p['u']}")
        put(f"vaFin{tag}", f"{100 * p['finite']:.3f}", src, f"finite-station form, u = {p['u']}")
        put(f"vaNs{tag}", f"{100 * p['ns3']:.3f}", src, f"ns-3, standard rule, u = {p['u']}")
        put(
            f"vaErr{tag}",
            signed(100 * (p["finite"] / p["loss"] - 1)),
            src,
            f"finite-station error, u = {p['u']}",
        )
    fac = [p["loss"] / p["finite"] for p in pts]
    put("vaFacMin", f2(min(fac)), src, "radios over the finite-station form, min")
    put("vaFacMax", f2(max(fac)), src, "radios over the finite-station form, max")
    sim = [p["loss"] / p[k] for p in pts for k in ("ns3", "event")]
    put("vaSimMin", f2(min(sim)), src, "radios over ns-3 / event simulation (standard), min")
    put("vaSimMax", f2(max(sim)), src, "radios over ns-3 / event simulation (standard), max")
    g5 = [100 * (p["g5"] / p["loss"] - 1) for p in pts]
    put(
        "vaGfiveMin", signed(min(g5), 0), src, "(G5) against the radios, outside its range, min (%)"
    )
    put("vaGfiveMax", signed(max(g5), 0), src, "(G5) against the radios, max (%)")
    bg = next(r for r in va if r["what"] == "background b")
    put("vaBg", f2(100 * float(bg["measured"])), src, "background b (%)")
    links = [float(r["measured"]) for r in va if r["what"] == "link loss alone"]
    put("vaLinkMax", f2(100 * max(links)), src, "worst link loss alone (%)")
    # UD2: (G25) where UD failed (predictions/UD2.md); macro names hold no digits, so "udQ"
    q = rows("ud2_scored.csv")
    src = "ud2_scored.csv"
    put("udQCrossings", str(len(q)), src, "prereg-UD2")
    put("udQHeld", str(sum(r["held"] == "1" for r in q)), src, "prereg-UD2, (G25) at 5 %")
    e = [float(r["g25_err_pct"]) for r in q]
    put("udQMin", signed(min(e), 2), src, "(G25) error, min (%)")
    put("udQMax", signed(max(e), 2), src, "(G25) error, max (%)")
    pe = [float(r["poisson_err_pct"]) for r in q]
    put("udQPoiMin", signed(min(pe)), src, "Poisson error, min (%)")
    put("udQPoiMax", signed(max(pe)), src, "Poisson error, max (%)")
    put("udQPoiOut", str(sum(abs(x) > 5 for x in pe)), src, "Poisson outside 5 %")
    past = [r for r in q if r["past_range"] == "True"]
    put("udQPast", str(len(past)), src, "crossings past occupancy 0.78")
    put("udQPastHeld", str(sum(r["held"] == "1" for r in past)), src, "of them held")
    # UJ: the safe-side claim by traffic source (predictions/UJ.md)
    uj = rows("uj_scored.csv")
    src = "uj_scored.csv"
    sc = [r for r in uj if r["s_held"] != "reported"]
    put("ujScored", str(len(sc)), src, "prereg-UJ, non-frozen cells")
    put("ujSHeld", str(sum(r["s_held"] == "1" for r in sc)), src, "prereg-UJ, claim S")
    put("ujAHeld", str(sum(r["a_held"] == "1" for r in sc)), src, "prereg-UJ, claim A")
    e = [float(r["root_err_pct"]) for r in sc]
    put("ujRootMin", signed(min(e)), src, "root error, non-frozen (%)")
    put("ujRootMax", signed(max(e)), src, "root error, non-frozen (%)")
    fz = [r for r in uj if r["s_held"] == "reported"]
    fe = [float(r["root_err_pct"]) for r in fz]
    put("ujFzRootMin", signed(min(fe), 2), src, "root error, frozen (%)")
    put("ujFzRootMax", signed(max(fe), 2), src, "root error, frozen (%)")
    fl = [float(r["law_err_pct"]) for r in fz]
    put("ujFzLawMin", signed(min(fl), 2), src, "law error, frozen (%)")
    put("ujFzLawMax", signed(max(fl), 2), src, "law error, frozen (%)")
    by = {r["cell"]: float(r["ns3_crossing"]) for r in uj}
    drops = [100 * (1 - by[f"JA{c}FZ"] / by[f"JA{c}DS"]) for c in ("230F40", "260F30")]
    put("ujFzDrop", f1(st.mean(drops)), src, "frozen against designated, ns-3 capacity (%)")
    c1 = {x["window"]: x for x in rows("c1_c1_2026-11-27.csv")}
    put(
        "cExtraC",
        f"{
            float(c1['21_Q3_600fps']['gap_floor_us'])
            - float(c1['03_Q1_600fps']['gap_floor_us']):.0f}",
        "c1_c1_2026-11-27.csv",
        "the Pi 3's floor less the Pi 4s'",
    )
    return out


def v1a_points() -> list[dict[str, float]]:
    """Per occupancy: the measured loss and its interval (V1a's scored file, unrounded columns)
    beside the stored predictions (results/raw/v1a_predictions.csv)."""
    pred = {int(r["fps_per_board"]): r for r in rows("v1a_predictions.csv")}
    out = []
    for r in rows("v1a_v1a_2026-11-28.csv"):
        if r["what"] != "point":
            continue
        m = re.match(r"ABC at (\d+)/s \(u = ([\d.]+)\)", r["item"])
        if m is None:
            raise ValueError(r)
        p = pred[int(m.group(1))]
        out.append(
            {
                "u": float(m.group(2)),
                "fps": float(m.group(1)),
                "loss": float(r["loss"]),  # the unrounded columns, never the text
                "lo": float(r["ci_lo"]),
                "hi": float(r["ci_hi"]),
                "finite": float(p["finite_w32"]),
                "ns3": float(p["ns3_standard"]),
                "event": float(p["event_standard"]),
                "g5": float(p["g5_w32"]),
            }
        )
    return out


def _field(text: str, pattern: str) -> list[str]:
    m = re.search(pattern, text)
    if m is None:
        raise ValueError(f"no match for {pattern!r} in {text!r}")
    return list(m.groups())


def hardware() -> list[tuple[str, str, str, str]]:
    """The hardware sessions' numbers, from their scored files."""
    out: list[tuple[str, str, str, str]] = []

    def put(name: str, value: str, src: str, where: str) -> None:
        out.append((name, value, src, where))

    # W1p: the saturated pair against the two window settings derived from W1f
    w1p = rows("w1p_w1p_2026-11-22.csv")
    loss = next(r for r in w1p if r["what"].startswith("pair loss"))["measured"]
    fps = next(r for r in w1p if r["what"].startswith("pair frames/s"))["measured"]
    put("wpLoss", loss.split()[0], "w1p_w1p_2026-11-22.csv", "prereg-W1p")
    put("wpFps", fps.split()[0], "w1p_w1p_2026-11-22.csv", "prereg-W1p")
    for r in (x for x in w1p if x["what"] == "family consistent"):
        pl, rate = _field(r["predicted"], r"([\d.]+), ([\d.]+)/s")
        tag = "Twenty" if r["item"] == "s20d50" else "Nine"
        put(f"wp{tag}Loss", f"{float(pl):.3f}", "w1p_w1p_2026-11-22.csv", "ns-3 prediction")
        put(f"wp{tag}Fps", f"{float(rate):.0f}", "w1p_w1p_2026-11-22.csv", "ns-3 prediction")
    # W1q: capture steps (the main session and the optional step's view)
    # the main session's valid steps, and from the view only the optional step (the view repeats
    # the main session's rows, which must not be counted twice)
    held = total = 0
    scored = [r for r in rows("w1q_w1q_2026-11-22.csv") if r["what"] == "step"]
    scored += [r for r in rows("w1q_w1q_view.csv") if r["what"] == "optional step, pi-B receives"]
    for r in scored:
        if r["held"].startswith("weak"):
            for part in r["held"].split(","):
                total += 1
                held += part.strip().endswith("True")
    put("wqHeld", str(held), "w1q_w1q_2026-11-22.csv + w1q_w1q_view.csv", "prereg-W1q")
    put("wqScored", str(total), "w1q_w1q_2026-11-22.csv + w1q_w1q_view.csv", "prereg-W1q")
    st3 = next(r for r in rows("w1q_w1q_2026-11-22.csv") if r["item"].startswith("3 dB"))
    d, q = _field(st3["measured"], r"ΔRSSI \+([\d.]+) dB; q_A ([\d.]+)")
    put("wqThreeDelta", d, "w1q_w1q_2026-11-22.csv", "the 3 dB step")
    put("wqThreeQ", q, "w1q_w1q_2026-11-22.csv", "the 3 dB step")
    # W1r: points inside the hardware's 95 % interval, per setting
    w1r = {
        r["item"].split(" (")[0]: r for r in rows("w1r_w1r_2026-11-22.csv") if r["what"] == "point"
    }
    pred = {(r["group"], r["fps_per_board"]): r for r in rows("w1r_predictions.csv")}
    inside = {"s20d50": 0, "s9d28": 0}
    for key, r in w1r.items():
        g, f = key.split(" at ")
        clo, chi = (float(x) for x in _field(r["measured"], r"\(([\d.-]+)-([\d.]+)\)"))
        p = pred[(g, f.removesuffix("/s"))]
        for fam in inside:
            ends = [float(p[f"ns3_{fam}_equal"])]
            if p.get(f"ns3_{fam}_rayleigh_capture"):
                ends.append(float(p[f"ns3_{fam}_rayleigh_capture"]))
            inside[fam] += min(ends) <= chi and max(ends) >= clo
    put("wrPoints", str(len(w1r)), "w1r_w1r_2026-11-22.csv", "prereg-W1r")
    put("wrInTwenty", str(inside["s20d50"]), "w1r_w1r_2026-11-22.csv", "slot 20 / DIFS 50")
    put("wrInNine", str(inside["s9d28"]), "w1r_w1r_2026-11-22.csv", "slot 9 / DIFS 28")
    # W1s: the last session's three parts
    w1s = rows("w1s_w1s_2026-11-23.csv")
    curve = next(r for r in w1s if r["what"] == "A: the curve")["item"]
    a_held, a_scored = _field(curve, r"(\d+) of (\d+)")
    put("wsCurveHeld", a_held, "w1s_w1s_2026-11-23.csv", "prereg-W1s, part A")
    put("wsCurveScored", a_scored, "w1s_w1s_2026-11-23.csv", "prereg-W1s, part A")
    pair = next(r for r in w1s if r["what"] == "B: pair (95 % interval)")["measured"]
    bl, bf = _field(pair, r"loss ([\d.]+) .*?; ([\d.]+) \(")
    put("wsPairLoss", bl, "w1s_w1s_2026-11-23.csv", "prereg-W1s, part B")
    put("wsPairFps", bf, "w1s_w1s_2026-11-23.csv", "prereg-W1s, part B")
    for r in (x for x in w1s if x["what"] == "B: family consistent"):
        sl, rate = _field(r["predicted"], r"([\d.]+), ([\d.]+)/s")
        tag = "Twenty" if r["item"] == "s20d50" else "Nine"
        put(f"ws{tag}Loss", sl, "w1s_w1s_2026-11-23.csv", "ns-3, re-derived windows")
        put(f"ws{tag}Fps", rate, "w1s_w1s_2026-11-23.csv", "ns-3, re-derived windows")
    dc = next(r for r in w1s if "(primary)" in r["what"])["measured"]
    dd, cc = _field(dc, r"d ([\d.]+) us; c ([\d.]+) us")
    put("wsD", f"{float(dd):.0f}", "w1s_w1s_2026-11-23.csv", "prereg-W1s, part C")
    put("wsC", f"{float(cc):.0f}", "w1s_w1s_2026-11-23.csv", "prereg-W1s, part C")
    # S0: the sniffer gate
    s0r = rows("s0_s0_2026-11-23.csv")
    comp = {
        r["item"].split(",")[0]: r["measured"] for r in s0r if r["what"] == "capture completeness"
    }
    put("sgA", f"{float(comp['node 1']):.3f}", "s0_s0_2026-11-23.csv", "prereg-S0")
    put("sgB", f"{float(comp['node 2']):.3f}", "s0_s0_2026-11-23.csv", "prereg-S0")
    put("sgC", f"{float(comp['node 3']):.3f}", "s0_s0_2026-11-23.csv", "prereg-S0")
    falls = [float(r["measured"]) for r in s0r if r["what"] == "signal follows set power"]
    put("sgFalls", ", ".join(f"{x:.1f}" for x in falls), "s0_s0_2026-11-23.csv", "prereg-S0")
    # C1: the radios' timing (saturated Q and back-to-back K windows)
    c1 = [r for r in rows("c1_c1_2026-11-27.csv") if r["window"] != "airtime fit"]

    def sub(label: str) -> list[dict[str, str]]:
        return [r for r in c1 if r["window"].split("_")[1] == label]

    for n, tag in (("1", "A"), ("2", "B"), ("3", "C")):
        qs = sub(f"Q{n}")
        share = [float(r["share_no_backoff"]) for r in qs]
        w = [int(r["w_minus_1"]) for r in qs if r["w_minus_1"]]
        put(
            f"cFloor{tag}",
            f"{float(qs[0]['gap_floor_us']):.0f}",
            "c1_c1_2026-11-27.csv",
            "prereg-C1 (calibration)",
        )
        put(f"cShareMin{tag}", f"{min(share):.2f}", "c1_c1_2026-11-27.csv", "prereg-C1")
        put(f"cShareMax{tag}", f"{max(share):.2f}", "c1_c1_2026-11-27.csv", "prereg-C1")
        put(
            f"cShareK{tag}",
            f"{float(sub(f'K{n}')[0]['share_no_backoff']):.2f}",
            "c1_c1_2026-11-27.csv",
            "prereg-C1, back-to-back",
        )
        put(f"cWmin{tag}", str(min(w)), "c1_c1_2026-11-27.csv", "prereg-C1")
        put(f"cWmax{tag}", str(max(w)), "c1_c1_2026-11-27.csv", "prereg-C1")
    fits = {r["sender"]: r for r in rows("c1_c1_2026-11-27.csv") if r["window"] == "airtime fit"}
    put(
        "cSlope",
        f"{float(fits['1']['slope_us_per_byte']):.2f}",
        "c1_c1_2026-11-27.csv",
        "airtime fit",
    )
    put("cInterA", f"{float(fits['1']['intercept_us']):.0f}", "c1_c1_2026-11-27.csv", "airtime fit")
    put("cInterC", f"{float(fits['3']['intercept_us']):.0f}", "c1_c1_2026-11-27.csv", "airtime fit")
    return out


# Results that exist only in the model document: its event simulation's script is not in the
# repository, so these are quoted from it, with their section.
QUOTED = {
    "evRootWorst": ("6.5", "§6: the root of (G5), N ≥ 19, worst error (%)"),
    "evRootSmall": ("9", "§6: the root of (G5), N ≈ 8–14, worst error (%)"),
    "evSafe": ("44", "§6: cases on the conservative side"),
    "evCases": ("45", "§6: cases"),
    "evSatErr": ("3", "§6: the saturation law (G11) against the event simulation, worst (%)"),
    "evGainErr": ("2", "§6: the gain (G12) against the event simulation, worst (%)"),
    "evCapErr": ("3.1", "§8.4: the law with the capture target against the event simulation (%)"),
    "evRuleVar": ("5", "§6: capacity moves by up to this with the reading of the access rule (%)"),
    "evRatioVar": ("2", "§6: the design ratio moves by up to this with the rule (%)"),
    "evVarS": ("1", "§7: ns-3's rule (variant S) against rule A, capacity (%)"),
    "fragBurstMin": ("1.7", "§5 R4: back-to-back fragments' loss over (G5), ns-3 (times)"),
    "fragBurstMax": ("2.3", "§5 R4: back-to-back fragments' loss over (G5), ns-3 (times)"),
    "fragCapMin": ("35", "§5 R4: capacity below (G18), back to back (%)"),
    "fragCapMax": ("62", "§5 R4: capacity below (G18), back to back (%)"),
    "fragSpread": ("3", "§5 R4: spread fragments against (G18), ns-3 (%)"),
    "burstFixMin": ("63", "§5 R4 / §10.2: share of the excess removed by the burst correction (%)"),
    "burstFixMax": ("75", "§5 R4 / §10.2: share of the excess removed by the burst correction (%)"),
    "keyRatio": ("0.88", "§5 R3: B(eps_r)/B(eps) for DCF at eps 0.05, r = 2"),
    "keyShare": ("12", "§5 R3: the share of channel cost a key record must exceed (%)"),
    "capGain": ("15", "§8.4: capacity gain from capture at 4 dB, event simulation (%)"),
    "smallMin": ("5", "§7: the Poisson model's deficit, periodic, 5-11 stations (%)"),
    "smallMax": ("11", "§7: the same, upper end (%)"),
}


# W1r's ns-3 windows, inferred from each board's one-sender cycle at registration (its script
# `uh.board_windows` wrote them into the registration, not into a results file).
QUOTED_W1R = {
    "wrWinPi": ("4", "predictions/W1r.md: W of pi-A and pi-B inferred at slot 20 us"),
    "wrWinPiThree": ("51", "predictions/W1r.md: W of the Pi 3 inferred at slot 20 us"),
}


# Values stated in a registration's outcome or in a script's record, with that file as source.
QUOTED_OTHER = {
    "sZeroMeanMin": ("0.03", "predictions/S0.md", "sniffer's mean interval against the cycle (%)"),
    "sZeroMeanMax": ("0.25", "predictions/S0.md", "sniffer's mean interval against the cycle (%)"),
    "wOneBErr": ("1", "analysis/dsss_hardware.py", "W1b: the event model against ns-3 (%)"),
}
QUOTED_DOC = {
    "fOneFortyMin": ("3.6", "§10.3 (F140): (G25)'s error with capture, occupancy 0.84-0.87 (%)"),
    "fOneFortyMax": ("5.5", "§10.3 (F140): the same, upper end (%)"),
    "evTwoFrame": ("95", "§8.1: collided frames in two-frame collisions at capacity (%)"),
    "rQueueErr": ("0.07", "§10.1: R against a queue simulation, 8 or more others"),
}


def quoted() -> list[tuple[str, str, str, str]]:
    doc = "docs/revision/unified_closed_form_model.md"
    out = [(k, v, doc, w) for k, (v, w) in QUOTED.items()]
    out += [(k, v, doc, w) for k, (v, w) in QUOTED_DOC.items()]
    out += [(k, v, "predictions/W1r.md", w) for k, (v, w) in QUOTED_W1R.items()]
    out += [(k, v, s, w) for k, (v, s, w) in QUOTED_OTHER.items()]
    return out


def write(out: Path = OUT) -> list[tuple[str, str, str, str]]:
    """numbers.tex, provenance.csv and the generated tables, into `out`."""
    import report_tables  # the tables use this module's readers; imported here to avoid a cycle

    out.mkdir(parents=True, exist_ok=True)
    found = collect()
    names = [n for n, _v, _s, _w in found]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise ValueError(f"macros defined twice: {sorted(dup)}")
    tex = ["% Generated by analysis/report_numbers.py from results/raw; do not edit by hand."]
    tex += [f"\\newcommand{{\\{n}}}{{{v}}}" for n, v, _s, _w in found]
    (out / "numbers.tex").write_text("\n".join(tex) + "\n")
    with (out / "provenance.csv").open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["macro", "value", "source", "where"])
        w.writerows(found)
    report_tables.write_tables(out / "tables", found)
    return found


def main() -> None:
    for n, v, s, _w in write():
        print(f"\\{n} = {v}   ({s})")


if __name__ == "__main__":
    main()
