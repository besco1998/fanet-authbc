"""The model report's generated tables (docs/reports/2026-11-27_model_report/tables/*.tex).

Written by `analysis/report_numbers.py`, from the stored results only: every result cell is read
from a file and rounded once. The model's own values (the constants, the worked example) are
computed by `authbc.models.unified_capacity`, the code the ns-3 tests scored
(docs/revision/unified_closed_form_model.md, Eqs. G6–G9).
"""

from __future__ import annotations

import re
from pathlib import Path

from report_numbers import REPO, rows, signed, truthy

from authbc.models import unified_capacity as uc

PRED = REPO / "predictions"

_UNI = {
    "−": "\\textminus{}",
    "–": "--",
    "—": "---",
    "≤": "$\\le$",
    "≥": "$\\ge$",
    "Δ": "$\\Delta$",
    "σ": "$\\sigma$",
    "ρ": "$\\rho$",
    "ε": "$\\varepsilon$",
    "≈": "$\\approx$",
    "…": "\\ldots{}",
    "→": "$\\to$",
    "µ": "$\\mu$",
    "μ": "$\\mu$",
    "×": "$\\times$",
    "±": "$\\pm$",
    "÷": "$\\div$",
    "·": "$\\cdot$",
    "’": "'",
    " ": "~",
    " ": "\\,",
}


def tex(s: str) -> str:
    """A stored text cell, typeset: LaTeX's special characters escaped, symbols mapped."""
    for a, b in (("&", "\\&"), ("%", "\\%"), ("#", "\\#"), ("_", "\\_"), ("$", "\\$")):
        s = s.replace(a, b)
    s = s.replace(">=", "$\\ge$").replace("<=", "$\\le$")
    return "".join(_UNI.get(c, c) for c in s)


def pct(x: float, d: int = 1) -> str:
    return signed(x, d)


def registered(test: str) -> str:
    """The registration date written in predictions/<test>.md ("Registered YYYY-MM-DD")."""
    m = re.search(r"Registered (\d{4}-\d{2}-\d{2})", (PRED / f"{test}.md").read_text())
    if m is None:
        raise ValueError(f"predictions/{test}.md has no registration date")
    return m.group(1)


def table(spec: str, head: str, body: list[str], long: bool = False) -> str:
    """A booktabs table body (the float and caption are the report's)."""
    if long:
        return "\n".join(
            [
                f"\\begin{{longtable}}{{{spec}}}",
                "\\caption{\\longcap}\\\\",  # the caption text is the report's
                "\\toprule",
                head + " \\\\",
                "\\midrule\\endfirsthead",
                "\\toprule",
                head + " \\\\",
                "\\midrule\\endhead",
                "\\bottomrule\\endfoot",
                *[b + " \\\\" for b in body],
                "\\end{longtable}",
            ]
        )
    return "\n".join(
        [
            f"\\begin{{tabular}}{{{spec}}}",
            "\\toprule",
            head + " \\\\",
            "\\midrule",
            *[b + " \\\\" for b in body],
            "\\bottomrule",
            "\\end{tabular}",
        ]
    )


# ---- the model's constants, (G6)-(G8), per standard and loss target -------------------------
STANDARDS = (
    ("802.11a, 20 MHz", uc.A80211A),
    ("802.11p, 10 MHz", uc.A80211P),
    ("802.11b, DSSS", uc.A80211B),
)
EPS = (0.02, 0.05, 0.10)


def t_constants() -> str:
    body = []
    for name, a in STANDARDS:
        cells = [
            name,
            f"{a.slot_s * 1e6:.0f}",
            f"{a.difs_s * 1e6:.0f}",
            str(a.w),
            f"{a.delta_s * 1e6:.0f}",
        ]
        for e in EPS:
            rho, tau0 = uc.dcf_constants(e, a)
            cells.append(f"{rho:.3f} / {tau0 * 1e6:.1f}")
        body.append(" & ".join(cells))
    head = (
        "Standard & $\\slot$ (\\textmu s) & DIFS (\\textmu s) & $\\Wnd$ & $\\delta$ (\\textmu s) & "
        + " & ".join(f"$\\eps={e:.2f}$" for e in EPS)
    )
    return table("lrrrrccc", head, body)


# ---- the worked example: configurations C and D at 802.11a, step by step -------------------
def t_worked() -> str:
    sc = {
        r["cell"]: r
        for r in rows("unified_model_vs_ns3.csv")
        if r["source_file"] == "ns3_nmax_direct" and r["note"] == "designated source"
    }
    a, eps = uc.A80211A, 0.05
    rho, tau0 = uc.dcf_constants(eps, a)
    kappa = 1 - eps / 2
    cols = []
    for cell in ("C", "D"):
        r = sc[cell]
        f, tf = float(r["frames_per_s"]), float(r["tf_us"]) * 1e-6
        per = kappa * (tf - a.delta_s) + tau0
        law, root = uc.n_law(f, tf, eps, a), uc.n_root(f, tf, eps, a)
        if abs(law - float(r["law"])) > 5e-3 or abs(root - float(r["root"])) > 5e-3:
            raise ValueError(f"cell {cell}: the stored model values differ from the code")
        ns3 = float(r["ns3"])
        cols.append(
            [
                r["frame_bytes"],
                f"{f:g}",
                f"{tf * 1e6:.0f}",
                f"{rho:.3f}",
                f"{tau0 * 1e6:.1f}",
                f"{kappa:.3f}",
                f"{per * 1e6:.1f}",
                f"{f * per:.5f}",
                f"{law:.1f}",
                f"{root:.1f}",
                f"{ns3:.2f}",
                pct(100 * (law - ns3) / ns3),
                pct(100 * (root - ns3) / ns3),
            ]
        )
    labels = [
        "frame size (B)",
        "frames per second per station, $f$",
        "airtime $\\Tf$ (\\textmu s)",
        "$\\rhostar$, \\eqref{eq:G6}",
        "$\\tauzero$ (\\textmu s), \\eqref{eq:G8}",
        "$\\kappa=1-\\eps/2$",
        "$\\kappa(\\Tf-\\delta)+\\tauzero$ (\\textmu s)",
        "$f[\\kappa(\\Tf-\\delta)+\\tauzero]$",
        "$\\Nmax$ by the law \\eqref{eq:G9}",
        "$\\Nmax$ by the root of \\eqref{eq:G5}",
        "$\\Nmax$ in ns-3 (30 seeds)",
        "error of the law (\\%)",
        "error of the root (\\%)",
    ]
    body = [f"{lab} & {c} & {d}" for lab, c, d in zip(labels, cols[0], cols[1], strict=True)]
    head = "Step & C: one record per frame & D: four records per frame"
    return table("lrr", head, body)


# ---- every registered test the report uses ---------------------------------------------------
def t_registered(v: dict[str, str]) -> str:
    us = "\\,\\textmu s"
    tests = [
        (
            "UC1",
            "ns-3",
            "\\eqref{eq:G5} term by term, 802.11a",
            f"total $p$ {v['ucOnePHeld']} of {v['ucOnePCases']}; all quantities {v['ucOneHeld']} "
            f"of {v['ucOneCases']}: the split into causes fails",
        ),
        (
            "UC2",
            "ns-3",
            "capacity at 16--64 records per frame",
            f"{v['ucTwoHeld']} of {v['ucTwoClaims']} held",
        ),
        (
            "UD",
            "ns-3",
            "the model at 802.11b, 1\\,Mb/s",
            f"8--14 stations {v['udBHeld']} of {v['udBScored']}; 15--37 stations: root failed "
            f"{v['udDRootFailed']} of {v['udDCells']} (safe side, {v['udDRootMin']} to "
            f"{v['udDRootMax']}\\,\\%); batching {v['udTwoHeld']} of {v['udTwoCells']}; the loss "
            f"itself pessimistic by {v['udThreePMin']} to {v['udThreePMax']}\\,\\% (D3)",
        ),
        (
            "UC3",
            "ns-3",
            "a key record once in $r$ frames",
            f"{v['ucThreeHeld']} of {v['ucThreeCells']} held",
        ),
        (
            "UC4",
            "ns-3",
            "a signed unit over $n$ frames, back to back",
            f"root failed at {v['ucFourRootFailed']} of {v['ucFourCells']}: outside the model",
        ),
        (
            "UC4S",
            "ns-3",
            "the same, frames spread over the period",
            f"{v['ucFourSHeld']} of {v['ucFourSCells']} held",
        ),
        (
            "UC5D1",
            "ns-3",
            "the best batch under bit errors, \\eqref{eq:G19}",
            f"held: best batch {v['ucFiveBest']}, predicted {v['ucFivePred']}",
        ),
        (
            "UCAP2",
            "ns-3",
            "ns-3's capture rule, per collision",
            f"{v['capHeld']} of {v['capTrials']} held",
        ),
        (
            "UG25",
            "ns-3",
            "the sending pattern, \\eqref{eq:G25}",
            f"{v['ugHeld']} of {v['ugCells']} held",
        ),
        (
            "UFS",
            "ns-3",
            "the finite-station form, 3--5 stations",
            f"{v['fsHeld']} of {v['fsCells']} held ($\\pm15\\,\\%$ on the loss)",
        ),
        (
            "UF",
            "ns-3",
            "capacity with capture, \\eqref{eq:G23}--\\eqref{eq:G24}",
            f"failed: average {v['ufAvgHeld']} of {v['ufConfigs']}, every sender "
            f"{v['ufWorstHeld']} of {v['ufConfigs']}",
        ),
        (
            "UC7",
            "ns-3",
            "LoRa duty cycle, \\eqref{eq:G20}",
            f"{v['lrHeld']} of {v['lrCells']} held",
        ),
        (
            "UG25H",
            "ns-3",
            "\\eqref{eq:G25} past occupancy 0.78",
            f"measured once: optimistic by {v['uhMin']} to {v['uhMax']}\\,\\%",
        ),
        (
            "UF2",
            "ns-3",
            "capture, corrected: \\eqref{eq:G22a}, \\eqref{eq:G24a}",
            f"{v['ufTwoHeld']} of {v['ufTwoClaims']} held, all on the safe side",
        ),
        (
            "W1e",
            "hardware",
            "contention, 2 and 3 radios (frame burst on)",
            f"{v['weHeld']} of {v['wePoints']} held",
        ),
        (
            "W1j",
            "hardware",
            "capacity ratio, 4 radios",
            f"held: {v['ratioJ']} against {v['ratioModel']} (band {v['ratioLo']}--{v['ratioHi']})",
        ),
        ("W1k", "hardware", "the same, repeated", f"held: {v['ratioK']}"),
        (
            "W3a",
            "hardware",
            "loss on air, traced frame by frame",
            f"{v['wtHeld']} of {v['wtClaims']} held",
        ),
        ("W1p", "hardware", "the contention window, two settings", "failed: neither setting fits"),
        (
            "W1q",
            "hardware",
            "capture against signal difference",
            f"{v['wqHeld']} of {v['wqScored']} held; capture is gradual",
        ),
        (
            "W1r",
            "hardware",
            "contention, frame burst off",
            f"reported: in ns-3's interval at {v['wrInTwenty']} ($\\slot=20$) and {v['wrInNine']} "
            f"($\\slot=9$) of {v['wrPoints']}",
        ),
        (
            "W1s",
            "hardware",
            "capture curve; window re-derived once",
            f"curve {v['wsCurveHeld']} of {v['wsCurveScored']} (not used); window not identified",
        ),
        (
            "S0",
            "hardware",
            "the sniffer's gate",
            f"failed: recorded {v['sgA']}, {v['sgB']}, {v['sgC']} of frames (needs 0.99)",
        ),
        ("P1", "hardware", "the sniffer at another placement", "did not reach 0.99"),
        (
            "C1",
            "hardware",
            "each radio's own timing (calibration)",
            f"DIFS {v['cFloorA']}{us}, slot 20{us}; Pi 4s skip the backoff in "
            f"{v['cShareMinA']}--{v['cShareMaxB']} of frames",
        ),
        ("S0b", "hardware", "a second sniffer's gate", "registered; waits for the adapter"),
    ]
    tests.sort(key=lambda t: (registered(t[0]), t[1] != "ns-3"))
    body = [f"{t} & {registered(t)} & {w} & {what} & {res}" for t, w, what, res in tests]
    head = "Test & Registered & Where & What it tests & Result"
    return table(
        ">{\\raggedright}p{1.2cm}p{1.65cm}>{\\raggedright}p{1.35cm}"
        ">{\\raggedright}p{4.15cm}>{\\raggedright\\arraybackslash}p{5.55cm}",
        head,
        body,
    )


# ---- full version: every stored capacity against the model ----------------------------------
STD = {"80211a": "a", "80211p": "p", "80211b": "b"}


def t_scorecard() -> str:
    body = []
    for r in rows("unified_model_vs_ns3.csv"):
        if not (r["law_err_pct"] and r["ns3"]):
            continue
        law = pct(float(r["law_err_pct"])) if truthy(r["law_valid"]) else "--"
        body.append(
            " & ".join(
                [
                    tex(r["source_file"]).replace("\\_", "\\_\\allowbreak{}"),
                    tex(r["cell"]),
                    STD[r["standard"]],
                    r["window"],
                    r["eps"],
                    f"{float(r['frames_per_s']):g}",
                    f"{float(r['tf_us']):.0f}",
                    tex(r["jitter_ms"]).replace("\\_", "\\_\\allowbreak{}"),
                    r["ns3"],
                    law,
                    pct(float(r["root_err_pct"])),
                ]
            )
        )
    head = (
        "Source & Cell & Std & $\\Wnd$ & $\\eps$ & $f$ & $\\Tf$ (\\textmu s) & Jitter & "
        "ns-3 $\\Nmax$ & Law (\\%) & Root (\\%)"
    )
    return table(">{\\raggedright}p{2.7cm}lclllr>{\\raggedright}p{2.2cm}rrr", head, body, True)


def t_ud() -> str:
    body = []
    for r in rows("unified_d_scored.csv"):
        if r["item"] not in ("D1", "D2"):
            continue
        body.append(
            " & ".join(
                [
                    r["item"],
                    r["cell"],
                    r["window"],
                    r["eps"],
                    f"{r['ns3']} ({r['ci_lo']}--{r['ci_hi']})",
                    pct(float(r["law_err_pct"])),
                    tex(r["law_verdict"].replace(" (< 8 stations)", "")),
                    pct(float(r["root_err_pct"])),
                    tex(r["root_verdict"].replace(" (< 8 stations)", "")),
                ]
            )
        )
    head = (
        "Item & Cell & $\\Wnd$ & $\\eps$ & ns-3 $\\Nmax$ (95\\,\\% CI) & Law (\\%) & & Root (\\%) &"
    )
    return table("lllllrlrl", head, body)


def t_ug25() -> str:
    body = []
    for r in rows("ug25_scored.csv"):
        body.append(
            " & ".join(
                [
                    r["cell"],
                    STD[r["standard"]],
                    r["eps"],
                    f"{float(r['ns3_crossing']):.2f} ({r['ci_lo']}--{r['ci_hi']})",
                    f"{float(r['g25_root']):.2f}",
                    pct(float(r["g25_err_pct"])),
                    pct(float(r["poisson_err_pct"])),
                    "yes" if truthy(r["held"]) else "no",
                ]
            )
        )
    for r in rows("ug25h_scored.csv"):
        body.append(
            " & ".join(
                [
                    r["cell"],
                    "b",
                    r["eps"],
                    f"{float(r['ns3_crossing']):.2f} ({r['ci_lo']}--{r['ci_hi']})",
                    f"{float(r['g25_root']):.2f}",
                    pct(float(r["g25_err_pct"])),
                    pct(float(r["poisson_err_pct"])),
                    f"occ.\\ {float(r['occupancy_at_ns3']):.2f}",
                ]
            )
        )
    head = (
        "Cell & Std & $\\eps$ & ns-3 $\\Nmax$ (95\\,\\% CI) & \\eqref{eq:G25} & Error (\\%) & "
        "Poisson (\\%) & Held"
    )
    return table("llllrrrl", head, body)


def t_uf2() -> str:
    body = []
    for r in rows("uf2_scored.csv"):
        body.append(
            " & ".join(
                [
                    r["config"],
                    tex(r["claim"]),
                    f"{float(r['ns3_crossing']):.2f}",
                    f"{float(r['predicted']):.2f}",
                    pct(float(r["err_pct"]), 2),
                    "yes" if truthy(r["held"]) else "no",
                ]
            )
        )
    head = "Configuration & Claim & ns-3 & Model & Error (\\%) & Held"
    return table("llrrrl", head, body)


def t_ufs() -> str:
    body = []
    for r in rows("ufs_scored.csv"):
        body.append(
            " & ".join(
                [
                    r["cell"],
                    r["n_nodes"],
                    f"{float(r['occupancy']):.1f}",
                    f"{100 * float(r['ns3_loss']):.3f} ({100 * float(r['ci_lo']):.3f}--"
                    f"{100 * float(r['ci_hi']):.3f})",
                    f"{100 * float(r['finite']):.3f}",
                    pct(float(r["finite_err_pct"])),
                    pct(float(r["g5_err_pct"])),
                    pct(float(r["g25_err_pct"])),
                    "yes" if truthy(r["held"]) else "no",
                ]
            )
        )
    head = (
        "Cell & $N$ & $\\occ$ & ns-3 loss, \\% (95\\,\\% CI) & Finite (\\%) & Error (\\%) & "
        "\\eqref{eq:G5} (\\%) & \\eqref{eq:G25} (\\%) & Held"
    )
    return table("lllllrrrl", head, body)


def t_uc7() -> str:
    body = []
    for r in rows("uc7_scored.csv"):
        body.append(
            " & ".join(
                [
                    r["cell"],
                    r["n_max_predicted"],
                    r["n_max_measured"],
                    f"{float(r['crossing']):.2f}" if r["crossing"] else "--",
                    "yes" if truthy(r["held"]) else "no",
                ]
            )
        )
    head = "Cell & Model $\\Nmax$ & ns-3 $\\Nmax$ & ns-3 crossing & Held"
    return table("lrrrl", head, body)


# ---- full version: the hardware sessions ------------------------------------------------------
def t_w1e() -> str:
    body = []
    for r in rows("w1e_w1e_2026-11-05.csv"):
        if r["what"] != "contention":
            continue
        body.append(
            " & ".join(
                [
                    tex(r["group"]),
                    f"{100 * float(r['measured']):.3f}",
                    f"{100 * float(r['predicted']):.3f}",
                    f"{100 * float(r['band_lo']):.3f}--{100 * float(r['band_hi']):.3f}",
                    "yes" if truthy(r["held"]) else "\\textbf{no}",
                ]
            )
        )
    head = "Radios and rate & Measured loss (\\%) & Model (\\%) & Band (\\%) & Held"
    return table("lrrcl", head, body)


def t_w1r() -> str:
    body = []
    for r in rows("w1r_w1r_2026-11-22.csv"):
        if r["what"] != "point":
            continue
        m = re.match(r"([\d.]+) \(([\d.]+)-([\d.]+)\)", r["measured"])
        if m is None:
            raise ValueError(r["measured"])
        loss, lo, hi = (100 * float(x) for x in m.groups())
        fam = re.findall(r"(s20d50|s9d28): ([\d.]+)(?: to ([\d.]+))?", r["predicted"])

        def show(x: tuple[str, str, str]) -> str:
            a = f"{100 * float(x[1]):.3f}"
            return a if not x[2] else f"{a}--{100 * float(x[2]):.3f}"

        body.append(
            " & ".join(
                [tex(r["item"]), f"{loss:.3f} ({lo:.3f}--{hi:.3f})", show(fam[0]), show(fam[1])]
            )
        )
    head = (
        "Radios, rate (occupancy) & Hardware loss, \\% (95\\,\\% CI) & ns-3, $\\slot=20$ (\\%) & "
        "ns-3, $\\slot=9$ (\\%)"
    )
    return table("llll", head, body)


def t_threeway() -> str:
    """Contention at two and three radios: the closed forms, the event model, ns-3, hardware.

    The closed forms and ns-3 are W1r's registered predictions (reported, not scored); the event
    model is W1e's registered row (W1c's); the hardware is W1e (frame burst on) and W1r (off).
    """
    pred = {(r["group"], r["fps_per_board"]): r for r in rows("w1r_predictions.csv")}
    ev = {
        (r["group"], r["fps_per_board"]): float(r["model_loss"])
        for r in rows("w1e_predictions.csv")
        if r["what"] == "contention"
    }
    hw_e = {
        r["group"]: float(r["measured"])
        for r in rows("w1e_w1e_2026-11-05.csv")
        if r["what"] == "contention"
    }
    hw_r = {}
    for r in rows("w1r_w1r_2026-11-22.csv"):
        if r["what"] == "point":
            m = re.match(r"([\d.]+) ", r["measured"])
            if m is None:
                raise ValueError(r["measured"])
            hw_r[r["item"].split(" (")[0]] = float(m.group(1))
    body = []
    for (g, f), p in sorted(
        pred.items(), key=lambda kv: (float(kv[1]["u"]), len(kv[0][0]), kv[0][0])
    ):
        key = f"{g} at {f}/s"
        fin = f"{100 * float(p['finite_w32']):.2f}" if p["finite_w32"] else "--"
        body.append(
            " & ".join(
                [
                    g,
                    f"{float(p['u']):.2f}",
                    f,
                    f"{100 * float(p['g5_w32']):.2f}",
                    f"{100 * float(p['g25_w32']):.2f}",
                    fin,
                    f"{100 * ev[(g, f)]:.2f}",
                    f"{100 * float(p['ns3_s20d50_equal']):.2f}",
                    f"{100 * float(p['ns3_s9d28_equal']):.2f}",
                    f"{100 * hw_e[key]:.2f}",
                    f"{100 * hw_r[key]:.2f}",
                ]
            )
        )
    head = (
        "Radios & $\\occ$ & $f$ & \\eqref{eq:G5} & \\eqref{eq:G25} & Finite & Event model & "
        "ns-3, $\\slot=20$ & ns-3, $\\slot=9$ & W1e & W1r"
    )
    return table("lrrrrrrrrrr", head, body)


def _names(s: str) -> str:
    """The sessions' files call the boards nodes 1-3; the report calls them by name."""
    for n, name in (("node 1", "pi-A"), ("node 2", "pi-B"), ("node 3", "the Pi 3")):
        s = s.replace(n, name)
    return s


def t_steps(name: str, what: tuple[str, ...]) -> str:
    """The capture sessions' steps, their stored text cells as written."""
    body = []
    for r in rows(name):
        if r["what"] not in what:
            continue
        cells = (r["item"] or r["what"], r["measured"], r["held"])
        body.append(" & ".join(tex(_names(x)) for x in cells))
    head = "Step & Measured & Held"
    return table(
        ">{\\raggedright}p{2.6cm}>{\\raggedright}p{9.2cm}>{\\raggedright\\arraybackslash}p{2.6cm}",
        head,
        body,
    )


def t_c1() -> str:
    body = []
    for r in rows("c1_c1_2026-11-27.csv"):
        kind = r["window"].split("_")[1][0] if "_" in r["window"] else ""
        if kind not in ("R", "Q", "K"):
            continue
        body.append(
            " & ".join(
                [
                    tex(r["window"].rsplit("_", 1)[0]),  # the rate is in the caption
                    {"1": "pi-A", "2": "pi-B", "3": "Pi 3"}[r["sender"]],
                    r["payload"],
                    f"{float(r['completeness']):.3f}",
                    f"{float(r['gap_floor_us']):.0f}",
                    r["lattice_us"],
                    f"{float(r['share_no_backoff']):.3f} "
                    f"({float(r['strict_share_no_backoff']):.3f})",
                    r["w_minus_1"],
                    f"{100 * float(r['share_beyond_scan']):.2f}",
                ]
            )
        )
    fits = [r for r in rows("c1_c1_2026-11-27.csv") if r["window"] == "airtime fit"]
    for r in fits:
        who = {"1": "pi-A", "2": "pi-B", "3": "Pi 3"}[r["sender"]]
        body.append(
            f"\\multicolumn{{9}}{{l}}{{airtime fit, {who}: slope "
            f"{float(r['slope_us_per_byte']):.2f}\\,\\textmu s/B, intercept "
            f"{float(r['intercept_us']):.1f}\\,\\textmu s}}"
        )
    head = (
        "Window & Sender & Payload (B) & Recorded & Floor (\\textmu s) & Lattice (\\textmu s) & "
        "No backoff (strict) & $\\Wnd-1$ & $>128$ slots (\\%)"
    )
    return table("llrrrrlrr", head, body)


def breakable(s: str) -> str:
    """A typeset path or name that may break after an underscore or a slash."""
    return s.replace("\\_", "\\_\\allowbreak{}").replace("/", "/\\allowbreak{}")


def t_provenance(found: list[tuple[str, str, str, str]]) -> str:
    body = [
        f"\\texttt{{\\textbackslash {n}}} & {v} & "
        f"\\texttt{{{breakable(tex(s))}}} & {breakable(tex(w))}"
        for n, v, s, w in found
    ]
    head = "Macro & Value & File & Registration or meaning"
    return table(
        ">{\\raggedright}p{3.0cm}>{\\raggedright}p{2.0cm}>{\\raggedright}p{4.6cm}"
        ">{\\raggedright\\arraybackslash}p{4.6cm}",
        head,
        body,
        True,
    )


def write_tables(out: Path, found: list[tuple[str, str, str, str]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    v = {n: val for n, val, _s, _w in found}
    tables = {
        "constants": t_constants(),
        "worked": t_worked(),
        "registered": t_registered(v),
        "scorecard": t_scorecard(),
        "ud": t_ud(),
        "ug25": t_ug25(),
        "uf2": t_uf2(),
        "ufs": t_ufs(),
        "uc7": t_uc7(),
        "w1e": t_w1e(),
        "w1r": t_w1r(),
        "threeway": t_threeway(),
        "w1q": t_steps("w1q_w1q_2026-11-22.csv", ("step",)),
        "w1s": t_steps("w1s_w1s_2026-11-23.csv", ("A: anchor (W1q's 0 dB step again)", "A: step")),
        "s0": t_steps(
            "s0_s0_2026-11-23.csv",
            ("capture completeness", "TSFT start-to-start", "signal follows set power"),
        ),
        "c1": t_c1(),
        "provenance": t_provenance(found),
    }
    head = "% Generated by analysis/report_numbers.py from results/raw; do not edit by hand.\n"
    for name, body in tables.items():
        (out / f"{name}.tex").write_text(head + body + "\n")
