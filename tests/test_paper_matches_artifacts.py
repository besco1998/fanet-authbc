"""The paper's capacity table must equal the generated artifact (audit S3b).

**Why this file exists.** `tab:envelope`'s $V{\\geq}0.95$ column was hand-written in LaTeX and was
never derived by any generator. When F30 corrected the measured crossing from U = 2.797 to 2.435,
the prose was updated to 213/100 but **the table was not** — it kept saying 233/116, and the paper
contradicted itself for weeks with every gate green. Nothing could have caught it, because nothing
compared the two.

This parses the table straight out of `paper/main.tex` and checks every number against
`results/raw/capacity_envelope.csv`. A stale figure in either place now fails the suite.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TEX = REPO / "paper" / "main.tex"
CSV = REPO / "results" / "raw" / "capacity_envelope.csv"

# paper row label -> the `binds` label of the generated ENVELOPE row it must match
ROW_TO_CONFIG = {
    (r"\textbf{optimized} delta/B", 50, 100): "optimized delta/B @3GPP100ms/50Hz",
    ("A+CBOR (Pillar-1)", 50, 100): "A+CBOR Pillar-1 @3GPP100ms/50Hz",
    ("optimized delta/B", 20, 250): "optimized delta/B @250ms",
    ("A+CBOR (Pillar-1)", 20, 250): "A+CBOR Pillar-1 @250ms",
    ("A+JSON (naive)", 20, 250): "A+JSON naive @250ms",
    ("optimized delta/B", 20, 100): "optimized delta/B @3GPP100ms/20Hz",
    ("optimized delta/B", 10, 100): "optimized delta/B @3GPP100ms/10Hz",
}


def _envelope_rows() -> dict[str, dict[str, str]]:
    rows = csv.DictReader([ln for ln in CSV.read_text().splitlines() if not ln.startswith("#")])
    return {r["binds"]: r for r in rows if r["n_local"] == "ENVELOPE"}


def _paper_table() -> dict[tuple[str, int, int], tuple[int, int, int, int]]:
    """Parse tab:envelope -> {(label, lambda, d_max_ms): (u_lt_1, v95_mean, per_run_lo, hi)}."""
    tex = TEX.read_text()
    start = tex.index(r"\label{tab:envelope}")
    body = tex[start : tex.index(r"\end{tabular}", start)]
    out = {}
    for line in body.splitlines():
        line = line.strip()
        if not line.endswith(r"\\") or line.startswith(r"\multicolumn") or "&" not in line:
            continue
        cells = [c.strip() for c in line.removesuffix(r"\\").split("&")]
        if len(cells) != 7:
            continue
        label, lam, dmax, _b, u1, v95, per_run = cells
        if not lam.isdigit():
            continue
        u1_v = int(re.sub(r"[^0-9]", "", u1))
        v95_v = int(re.sub(r"[^0-9]", "", v95))
        lo, hi = (int(x) for x in per_run.split("--"))
        out[(label, int(lam), int(dmax))] = (u1_v, v95_v, lo, hi)
    return out


@pytest.fixture(scope="module")
def paper_rows():
    rows = _paper_table()
    assert len(rows) == len(ROW_TO_CONFIG), (
        f"parsed {len(rows)} table rows, expected {len(ROW_TO_CONFIG)} — the table structure "
        f"changed and this test's mapping must be updated with it"
    )
    return rows


@pytest.mark.parametrize("key", list(ROW_TO_CONFIG))
def test_every_paper_row_matches_the_generated_envelope(key, paper_rows):
    gen = _envelope_rows()[ROW_TO_CONFIG[key]]
    u1, v95, lo, hi = paper_rows[key]
    assert u1 == int(gen["n_max_u_lt_1"]), f"{key}: U<1 column stale"
    assert v95 == int(gen["n_max_v95_mean"]), f"{key}: V>=0.95 (mean) column stale"
    assert lo == int(gen["n_max_v95_strict_lo"]), f"{key}: per-run lower bound stale"
    assert hi == int(gen["n_max_v95_strict_hi"]), f"{key}: per-run upper bound stale"


class TestTheClaimsMadeAboutTheTable:
    """The prose quotes ratios and endpoints derived from these rows; pin those too."""

    def test_the_compliant_and_relaxed_headline_pairs(self):
        gen = _envelope_rows()
        assert int(gen["optimized delta/B @3GPP100ms/50Hz"]["n_max_v95_mean"]) == 100
        assert int(gen["optimized delta/B @250ms"]["n_max_v95_mean"]) == 213
        tex = TEX.read_text()
        assert r"$213 \to 100$" in tex, "the 213->100 compliance-cost sentence drifted"
        assert "116" not in tex.replace("1160", ""), \
            "the superseded 116 figure is back in the paper"

    def test_the_four_quoted_ratios_are_what_the_artifact_gives(self):
        gen = _envelope_rows()

        def ratio(opt: str, base: str, col: str) -> float:
            return int(gen[opt][col]) / int(gen[base][col])

        comp = ("optimized delta/B @3GPP100ms/50Hz", "A+CBOR Pillar-1 @3GPP100ms/50Hz")
        relx = ("optimized delta/B @250ms", "A+CBOR Pillar-1 @250ms")
        assert ratio(*comp, "n_max_u_lt_1") == pytest.approx(1.94, abs=0.01)
        assert ratio(*comp, "n_max_v95_mean") == pytest.approx(3.23, abs=0.01)
        assert ratio(*relx, "n_max_u_lt_1") == pytest.approx(3.22, abs=0.01)
        assert ratio(*relx, "n_max_v95_mean") == pytest.approx(2.42, abs=0.01)

    def test_the_advantage_survives_the_criterion_choice(self):
        """Reporting both only helps if the conclusion survives either reading. Check that."""
        gen = _envelope_rows()
        pairs = [("optimized delta/B @3GPP100ms/50Hz", "A+CBOR Pillar-1 @3GPP100ms/50Hz"),
                 ("optimized delta/B @250ms", "A+CBOR Pillar-1 @250ms")]
        ratios = [int(gen[o][c]) / int(gen[b][c])
                  for o, b in pairs
                  for c in ("n_max_u_lt_1", "n_max_v95_mean",
                            "n_max_v95_strict_lo", "n_max_v95_strict_hi")]
        assert min(ratios) > 1.9, "the co-design advantage must hold under every criterion"
        assert max(ratios) < 3.3


# --------------------------------------------------------------------------- LoRa arm (F38/F39)
LORA = {
    "aloha": REPO / "results" / "raw" / "lora_capacity_ci.csv",
    "eu": REPO / "results" / "raw" / "lora_capacity_eu.csv",
    "goursaud": REPO / "results" / "raw" / "lora_capacity_goursaud.csv",
}


def _lora(arm: str) -> dict[int, dict[str, str]]:
    rows = csv.DictReader([ln for ln in LORA[arm].read_text().splitlines()
                           if not ln.startswith("#")])
    return {int(r["n_devices"]): r for r in rows}


def _d(arm: str, n: int) -> float:
    return float(_lora(arm)[n]["delivered_frac"])


class TestTheLoRaPassagesMatchTheArtifacts:
    """⚠️ These exist because three separate LoRa numbers went stale in the paper unnoticed.

    "N_max moves only from 5 to 8" survived F30 changing the baseline 5 -> 3, and the capture and
    gateway figures survived F38 re-running their artifacts at 30 seeds. Nothing compared the paper
    to the CSVs for this arm, so nothing caught any of it. Now something does.
    """

    def test_capture_gain_figures(self):
        tex = TEX.read_text()
        pts = (_d("goursaud", 8) - _d("aloha", 8)) * 100
        ratio = _d("goursaud", 50) / _d("aloha", 50)
        assert rf"raises delivery by ${pts:.1f}$ points at $N{{=}}8$" in tex, (
            f"paper's capture gain at N=8 drifted; artifact says {pts:+.1f} pts"
        )
        assert rf"by ${ratio:.2f}\times$ at $N{{=}}50$" in tex, (
            f"paper's capture ratio at N=50 drifted; artifact says {ratio:.2f}x"
        )

    def test_gateway_versus_peer_figures(self):
        tex = TEX.read_text()
        ratio = _d("eu", 50) / _d("aloha", 50)
        assert rf"${ratio:.2f}\times$ at $N{{=}}50$" in tex
        assert rf"(${_d('aloha', 50):.4f} \rightarrow {_d('eu', 50):.4f}$)" in tex
        assert rf"still ${_d('eu', 100):.4f}$ at $N{{=}}100$" in tex

    def test_the_eu_crossing_values(self):
        tex = TEX.read_text()
        assert rf"$N{{=}}8$ with ${_d('eu', 8):.4f}$" in tex
        assert rf"fails at $N{{=}}10$ with ${_d('eu', 10):.4f}$" in tex

    def test_the_periodic_escape_cross_check_quotes_the_measured_value(self):
        assert rf"against ${_d('aloha', 8):.3f}$ measured" in TEX.read_text()

    def test_the_superseded_n_max_baseline_of_5_is_gone(self):
        """F30 moved the ALOHA N_max 5 -> 3; the 'from 5 to 8' sentence outlived it by weeks."""
        tex = TEX.read_text()
        assert r"moves only from 5 to 8" not in tex, "the superseded 'from 5 to 8' sentence is back"
        assert r"moves only from 3 to 8" in tex


class TestTheAblationClaimsMatchTheModel:
    """F39: the abstract and intro claimed all four axes couple; the ablation says two do."""

    def test_the_paper_no_longer_claims_the_knobs_are_inseparable(self):
        tex = TEX.read_text()
        assert "these knobs are not separable" not in tex, (
            "the falsified 'not separable' thesis statement is back -- encoding is exactly additive"
        )

    def test_the_placement_closed_form_is_stated(self):
        assert r"g_a(1{-}1/b)" in TEX.read_text() or r"g_a(1-1/b)" in TEX.read_text()


class TestAbstractRatioRange:
    """⚠️ The capacity-ratio RANGE is a flagged number, and the status board had it wrong.

    CLAUDE.md instructed quoting "the range 1.9--3.3x" and listed the four combinations as
    1.94/2.24/3.22/3.31. Recomputing from `capacity_envelope.csv` on 2026-08-07 gives
    1.94/3.23/3.22/2.42 -- so two of the four listed values were wrong and the upper end of the
    range was overstated. The paper's abstract was right; the standing instruction file was not,
    which is the worse of the two places for an error to live.

    Nothing checked it, because the ratio is not printed in any table -- it is derived in prose
    from two table cells. This is the prose/data boundary the methods companion argues for, so it
    gets an invariant.
    """

    BASELINE_BYTES = 174.252   # A+CBOR (Pillar-1), inline, b=1
    OPTIMIZED_BYTES = 71.998   # delta / self-batch b=4

    def _ratios(self) -> list[float]:
        rows = list(_envelope_rows().values())
        out = []
        for lam in ("20", "50"):
            def pick(byts, lam=lam):  # bind the loop variable, not the closure cell
                return next(r for r in rows
                            if r["lambda_rec_per_s"] == lam
                            and abs(float(r["bytes_per_rec"]) - byts) < 1e-3)
            base, opt = pick(self.BASELINE_BYTES), pick(self.OPTIMIZED_BYTES)
            for col in ("n_max_u_lt_1", "n_max_v95_mean"):
                out.append(int(opt[col]) / int(base[col]))
        return sorted(out)

    def test_the_four_ratios_are_what_the_board_claims(self):
        got = [round(r, 2) for r in self._ratios()]
        assert got == [1.94, 2.42, 3.22, 3.23], (
            f"the four capacity ratios moved: {got}. Update CLAUDE.md and the abstract together "
            f"— the board has been wrong about these before."
        )

    def test_abstract_quotes_the_true_range(self):
        """The abstract must bracket the real spread, not a rounded-up version of it."""
        tex = (REPO / "paper" / "main.tex").read_text()
        i, j = tex.index(r"\begin{abstract}"), tex.index(r"\end{abstract}")
        quoted = re.findall(r"\$?(\d\.\d)\\times\$?", tex[i:j])
        assert len(quoted) >= 2, f"abstract no longer quotes a ratio range: {quoted}"
        lo_q, hi_q = float(quoted[0]), float(quoted[1])
        rs = self._ratios()
        lo_t, hi_t = math.floor(rs[0] * 10) / 10, math.floor(rs[-1] * 10) / 10
        assert (lo_q, hi_q) == (lo_t, hi_t), (
            f"abstract quotes {lo_q}x--{hi_q}x but the artifact gives {rs[0]:.2f}--{rs[-1]:.2f} "
            f"(truncated {lo_t}--{hi_t}). ⚠️ Never round the upper end UP: it overstates the result."
        )


class TestLoraExternalTable:
    """⚠️ `tab:lora-external` was still built on the PURGED 3-seed run.

    Found 2026-08-07. The AUTHBC column read 0.0 / 13.4 / 59.0 / 74.7 %, which matches
    `lora_capacity_3seed_SUPERSEDED.csv` to three decimals; the current 30-seed-backed artifact
    gives 8.3 / 12.9 / 43.0 / 62.5 %. Six 3-seed artifacts were purged weeks earlier and this table
    was not re-derived with them, so the single defect class CLAUDE.md calls "the pattern of the
    whole audit" -- small samples against a threshold -- was still printed in the paper.

    Two consequences rode on it. `N_max` was quoted as 5 where the 30-seed data gives 3 (0.9508 at
    N=3, 0.8981 at N=4), and the row annotated "we are more optimistic" at N=5 restated finding
    **F18**, which the project had already RETRACTED -- while a paragraph 100 lines earlier said
    the opposite in bold. The paper contradicted itself on a retracted claim.

    The Bor column was correct throughout, which is what made this hard to see: half the table
    agreed with its source.
    """

    CSV = REPO / "results" / "raw" / "lora_external_check.csv"

    def _artifact(self) -> dict[int, tuple[float, float]]:
        out = {}
        for r in csv.DictReader(ln for ln in self.CSV.read_text().splitlines()
                                if not ln.startswith("#")):
            if r["authbc_ns3_loss_pct"]:
                out[int(r["n_devices"])] = (float(r["authbc_ns3_loss_pct"]),
                                            float(r["bor2017_loss_pct"]))
        return out

    def _paper_rows(self) -> dict[int, tuple[float, float]]:
        tex = (REPO / "paper" / "main.tex").read_text()
        i = tex.index(r"\label{tab:lora-external}")
        block = tex[i:tex.index(r"\end{tabular}", i)]
        out = {}
        for m in re.finditer(r"^(\d+)\s*&\s*\$([\d.]+)\\%\$\s*&\s*\$([\d.]+)\\%\$",
                             block, re.M):
            out[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
        return out

    def test_every_cell_matches_the_current_artifact(self):
        art, paper = self._artifact(), self._paper_rows()
        assert paper, "could not parse tab:lora-external"
        bad = []
        for n, (pa, pb) in paper.items():
            aa, ab = art[n]
            if abs(pa - aa) > 0.05 or abs(pb - ab) > 0.05:
                bad.append(f"N={n}: paper ({pa}, {pb}) vs artifact ({aa:.1f}, {ab:.1f})")
        assert not bad, ("tab:lora-external disagrees with lora_external_check.csv:\n"
                         + "\n".join(bad))

    def test_no_row_revives_the_retracted_optimism_claim(self):
        """⚠️ F18 is retracted. Above the crossover we are the MORE PESSIMISTIC model."""
        art = self._artifact()
        tex = (REPO / "paper" / "main.tex").read_text()
        i = tex.index(r"\label{tab:lora-external}")
        block = tex[i:tex.index(r"\end{tabular}", i)]
        for line in block.splitlines():
            m = re.match(r"^(\d+)\s*&", line)
            if m and "more optimistic" in line:
                n = int(m.group(1))
                ours, theirs = art[n]
                assert ours < theirs, (
                    f"row N={n} claims we are more optimistic, but the artifact has us at "
                    f"{ours}% loss against their {theirs}% — this is retracted finding F18."
                )

    def test_n_max_is_the_30_seed_value_not_the_3_seed_one(self):
        tex = (REPO / "paper" / "main.tex").read_text()
        i = tex.index(r"\label{tab:lora-external}")
        block = tex[i:tex.index(r"\end{tabular}", i)]
        m = re.search(r"&\s*\\textbf\{(\d+)\}\s*&\s*\\textbf\{(\d+)\}", block)
        assert m, "tab:lora-external no longer states both N_max values"
        ours, theirs = int(m.group(1)), int(m.group(2))
        assert (ours, theirs) == (3, 4), (
            f"N_max reads ({ours}, {theirs}). The canonical run is lora_capacity.csv (30 seeds, "
            f"jittered): 0.95981 at N=3 passes, 0.9167 at N=5 fails, so ours=3. Bor's closed form "
            f"gives 4 (4.418% at N=4, 5.065% at N=5). ⚠️ ours=5 is the purged 3-seed value. "
            f"⚠️ Do NOT cite lora_capacity_30seed.csv here — despite its name it is the "
            f"NO-JITTER CONTROL, not the canonical run."
        )

    def test_lowrate_table_arithmetic_is_self_consistent(self):
        """`tab:lowrate` inherited N_max=5 and reported aggregate 0.82 rec/s and a 2500x gap.

        With the correct N_max=3 the aggregate is 0.495 rec/s and the gap is ~4200x. The row is
        pure arithmetic over the two preceding columns, so it can simply be recomputed.
        """
        tex = (REPO / "paper" / "main.tex").read_text()
        i = tex.index(r"\label{tab:lowrate}")
        block = tex[i:tex.index(r"\end{tabular}", i)]
        lora = re.search(r"LoRa[^&]*&\s*([\d.]+) rec/s\s*&\s*(\d+)\s*&\s*([\d.]+) rec/s", block)
        wifi = re.search(r"802\.11a[^&]*&\s*(\d+) rec/s\s*&\s*(\d+)\s*&\s*(\d+) rec/s", block)
        assert lora and wifi, "could not parse tab:lowrate"
        per, nmax, agg = float(lora.group(1)), int(lora.group(2)), float(lora.group(3))
        assert nmax == 3, f"tab:lowrate says N_max={nmax}; the 30-seed run gives 3"
        assert abs(per * nmax - agg) < 0.01, f"{per} x {nmax} = {per * nmax:.3f}, table says {agg}"
        w_per, w_nmax, w_agg = int(wifi.group(1)), int(wifi.group(2)), int(wifi.group(3))
        assert w_per * w_nmax == w_agg, f"802.11a row: {w_per}x{w_nmax} != {w_agg}"
        ratios = re.search(r"ratio & \$(\d+)\\times\$ & \$(\d+)\\times\$ & "
                           r"\$\\mathbf\{\\approx\}\\mathbf\{(\d+)\}", block)
        assert ratios, "could not parse the ratio row"
        assert abs(int(ratios.group(1)) - w_per / per) < 1.0
        assert abs(int(ratios.group(2)) - w_nmax / nmax) < 1.0
        assert abs(int(ratios.group(3)) - w_agg / agg) < 100.0


class TestRemainingTables:
    """Close the gap: after three tables were found stale, guard the four that were not checked.

    tab:e1, tab:e5, tab:decomp and tab:t6 were audited by hand on 2026-08-07 and all four were
    CORRECT. These tests exist so they stay that way — the three that went stale did so silently,
    and a table nobody re-derives is a table nobody can trust.
    """

    def _tabular(self, label: str) -> str:
        tex = (REPO / "paper" / "main.tex").read_text()
        i = tex.index("\\label{" + label + "}")
        s = tex.index(r"\begin{tabular}", i)
        return tex[s:tex.index(r"\end{tabular}", s)]

    def _rows(self, path: str) -> list[dict[str, str]]:
        p = REPO / "results" / "raw" / path
        return list(csv.DictReader(ln for ln in p.read_text().splitlines()
                                   if not ln.startswith("#")))

    def test_e1_encoding_sizes(self):
        art = {r["encoding"]: r for r in self._rows("e1_dominance.csv")}
        block = self._tabular("tab:e1")
        seen = 0
        for name, key in (("JSON", "json"), ("CBOR", "cbor"),
                          ("MessagePack", "msgpack"), ("delta", "delta")):
            pat = (name + r"[^&]*&\s*\\?t?e?x?t?b?f?\{?([\d.]+)\}?\s*&\s*"
                   r"\\?t?e?x?t?b?f?\{?([\d.]+)\\%")
            m = re.search(pat, block)
            assert m, f"could not parse the {name} row of tab:e1"
            assert abs(float(m.group(1)) - float(art[key]["mean_bytes"])) < 0.05, name
            assert abs(float(m.group(2)) - float(art[key]["phi_pct"])) < 0.06, name
            seen += 1
        assert seen == 4

    def test_e5_headline_row_matches_the_optimizer(self):
        opt = next(r for r in self._rows("e5_codesign.csv") if r["role"] == "optimized")
        block = self._tabular("tab:e5")
        m = re.search(r"\\textbf\{optimized\}.*?\\textbf\{([\d.]+)\}\s*&\s*\\textbf\{([\d.]+)\}",
                      block, re.S)
        assert m, "could not parse the optimized row of tab:e5"
        assert abs(float(m.group(1)) - float(opt["auth_overhead_bytes"])) < 0.01
        assert abs(float(m.group(2)) - float(opt["bytes_per_rec"])) < 0.01
        assert opt["scheme"] == "ed25519" and opt["placement"] == "B" and opt["batch"] == "4", (
            "⚠️ the artifact no longer selects delta/Ed25519/self-batch b=4; the paper's prose "
            "asserts that selection in several places"
        )

    def test_decomp_shares_sum_and_derive_from_e5(self):
        """The two shares are a partition of one measured saving, so they must reconstruct it."""
        rows = {r["role"]: r for r in self._rows("e5_codesign.csv")}
        base, opt = rows["A+CBOR"], rows["optimized"]
        total = float(base["bytes_per_rec"]) - float(opt["bytes_per_rec"])
        auth = float(base["auth_overhead_bytes"]) - float(opt["auth_overhead_bytes"])
        payload = float(base["s"]) - float(opt["s"])
        assert abs((auth + payload) - total) < 0.01, (
            f"auth {auth} + payload {payload} != total {total}: "
            f"the decomposition is not a partition"
        )
        block = self._tabular("tab:decomp")
        printed = [float(x) for x in re.findall(r"([\d.]+)\\%\s*\\\\", block)]
        assert printed, "could not parse tab:decomp"
        for want in (round(100 * auth / total, 1), round(100 * payload / total, 1)):
            assert any(abs(want - p) < 0.1 for p in printed), (
                f"tab:decomp does not print the {want}% share derived from e5_codesign.csv"
            )

    def test_t6_tiers_are_arithmetic_on_the_measured_header(self):
        """⚠️ tab:t6 is the exclusion bound — it must track H_f=44 B, not the old assumed 40 B."""
        block = self._tabular("tab:t6")
        cap = (REPO / "paper" / "main.tex").read_text()
        i = cap.index(r"\label{tab:t6}")
        head = cap[cap.rindex(r"\caption{", 0, i):i]
        hf = int(re.search(r"H_f\{=\}(\d+)", head).group(1))
        ga = int(re.search(r"\\ba\{=\}(\d+)", head).group(1))
        smin = int(re.search(r"s_\{\\min\}\{=\}(\d+)", head).group(1))
        assert (hf, ga, smin) == (44, 64, 13), (
            f"tab:t6 caption constants changed: {hf},{ga},{smin}")
        for m in re.finditer(r"^[\d, ]+&\s*(\d+)\s*&\s*\$?(-?\d+)\$?\s*&\s*(\w+)", block, re.M):
            mtu, smax, verdict = int(m.group(1)), int(m.group(2)), m.group(3)
            assert smax == mtu - hf - ga, (
                f"MTU {mtu}: s_max should be {mtu - hf - ga}, table says {smax}")
            assert (verdict == "feasible") == (smax >= smin), (
                f"MTU {mtu}: s_max={smax} vs s_min={smin} contradicts verdict '{verdict}'"
            )


class TestDerivedConstants:
    """⚠️ Constants DERIVED from H_f lagged behind the measured H_f for weeks.

    Grepping for "40" found nothing, because these numbers never print H_f — they print a
    function of it. Found 2026-08-07:

        T2a boundary (M-H_f-g_a)/(b+1)   paper 232.7   H_f=40 -> 232.67   H_f=44 -> 232.00
        low-rate A = M/(M-H_f-g_a)       paper 1.88    H_f=40 -> 1.881    H_f=44 -> 1.947
        802.11  A at MTU 1500            paper 1.0745  H_f=40 -> 1.0744   H_f=44 -> 1.0776
        b_max at MTU 1500, delta         paper 31      H_f=40 -> 31       H_f=44 -> 30
        A realised at MTU 256            paper 1.68    H_f=40 -> 1.684    H_f=44 -> 1.730

    The models were CORRECT throughout — e2_batching.csv already carried 1.7297 and b_max=30.
    Only the prose lagged, which is the hardest case to see: the artifacts agree with each other
    and disagree only with the sentence describing them.
    """

    H_F, G_A = 44, 64   # measured wire-format header; Ed25519/ECDSA signature

    def _tex(self) -> str:
        return (REPO / "paper" / "main.tex").read_text()

    def test_t2a_boundary_uses_the_measured_header(self):
        b = int(20 * 0.250)                       # Lambda=20 rec/s, D_max=250 ms
        want = (1500 - self.H_F - self.G_A) / (b + 1)
        m = re.search(r"this is \$([\d.]+)\$\\,B on 802\.11", self._tex())
        assert m, "the T2a boundary sentence changed shape"
        assert abs(float(m.group(1)) - want) < 0.05, (
            f"T2a boundary reads {m.group(1)} B; with the measured "
            f"H_f={self.H_F} it is {want:.1f} B"
        )

    def test_low_rate_amplification(self):
        want = 222 / (222 - self.H_F - self.G_A)
        m = re.search(r"\$A\{=\}([\d.]+)\$ \\emph\{is\} operative", self._tex())
        assert m, "the low-rate amplification sentence changed shape"
        assert abs(float(m.group(1)) - want) < 0.01, (
            f"low-rate A reads {m.group(1)}; M=222 with H_f={self.H_F} gives {want:.2f}"
        )

    def test_e2_paragraph_matches_the_batching_artifact(self):
        rows = [r for r in csv.DictReader(
                    ln for ln in (REPO / "results" / "raw" / "e2_batching.csv")
                    .read_text().splitlines() if not ln.startswith("#"))
                if r["encoding"] == "delta" and r["placement"] == "B" and r["is_bmax"] == "1"]
        by_mtu = {int(r["mtu"]): r for r in rows}
        tex = self._tex()
        m = re.search(r"delta reaches \$b_\{\\max\}=(\d+)\$ with \$A_\{@b\}=A=([\d.]+)\$", tex)
        assert m, "the E2 sentence changed shape"
        assert int(m.group(1)) == int(by_mtu[1500]["b_max"]), (
            f"paper says b_max={m.group(1)}, e2_batching.csv says {by_mtu[1500]['b_max']}"
        )
        assert abs(float(m.group(2)) - float(by_mtu[1500]["A_formula"])) < 0.0005, (
            f"paper says A={m.group(2)}, artifact says {by_mtu[1500]['A_formula']}"
        )
        m256 = re.search(r"\$M\{=\}256\$ is MTU-limited \(\$A\{=\}([\d.]+)\$ realised\)", tex)
        assert m256, "the MTU-256 clause changed shape"
        assert abs(float(m256.group(1)) - float(by_mtu[256]["A_formula"])) < 0.005

    def test_reproducibility_claim_matches_the_gate(self):
        """⚠️ The paper claimed 20 re-derived artifacts; the gate re-derives 16.

        This is a headline contribution, so an inflated count is the worst place for one.
        """
        gate = (REPO / "tests" / "integration" / "test_frozen_reproducibility.py").read_text()
        actual = len(set(re.findall(r'"([\w.]+\.csv)"\s*:', gate)))
        claimed = {int(x) for x in re.findall(
            r"(?:all|\\emph\{)?(\d+)\}?\s+model-derived artifacts", self._tex())}
        assert claimed, "the paper no longer states how many artifacts the gate re-derives"
        assert claimed == {actual}, (
            f"paper claims {claimed} model-derived artifacts; the gate re-derives {actual}"
        )


class TestReviewerTargets:
    """Assumptions a reviewer will attack first, pinned to the code that sets them.

    Added in pass 5, after a reviewer-simulation read found three load-bearing claims with no
    stated justification. Two were genuine gaps; all three are now argued in the text, so these
    tests keep the text and the constants together.
    """

    def _tex(self) -> str:
        return (REPO / "paper" / "main.tex").read_text()

    def test_s_min_is_the_delta_record_minus_the_chain_link(self):
        """⚠️ The whole DR3 exclusion rests on s_min, which the paper never justified.

        s_min = 13 B is the 45 B delta record less the 32 B prev_hash, once chaining moves to
        once-per-frame. If either input moves, "misses by 6 B" moves with it.
        """
        gen = (REPO / "analysis" / "figures_envelope_lora.py").read_text()
        s_min = float(re.search(r"S_MIN_LORA\s*=\s*([\d.]+)", gen).group(1))
        rows = {r["encoding"]: r for r in csv.DictReader(
            ln for ln in (REPO / "results" / "raw" / "e1_dominance.csv").read_text().splitlines()
            if not ln.startswith("#"))}
        delta = float(rows["delta"]["mean_bytes"])
        assert abs(s_min - (delta - 32)) < 0.01, (
            f"s_min={s_min} is no longer (delta record {delta:.2f} B - 32 B chain link); "
            f"the paper justifies it as exactly that"
        )
        tex = self._tex()
        assert "32}\\,B chain link" in tex or "$32$\\,B chain link" in tex, (
            "the paper stopped justifying s_min; a reviewer will ask where 13 B comes from"
        )
        m = re.search(r"DR3 fails on the encoding, and by (\w+) bytes", tex)
        assert m, "the DR3 clause changed shape"
        gap = {"six": 6}[m.group(1)]
        assert (115 - 44 - 64) + gap == s_min, (
            f"DR3 s_max={115 - 44 - 64} plus a {gap} B miss should equal s_min={s_min}"
        )

    def test_p_sensitivity_is_reported_and_matches_the_sweep(self):
        """The paper fixes p=0.05; the sweep answering "why?" existed but went unreported."""
        rows = list(csv.DictReader(
            ln for ln in (REPO / "results" / "raw" / "sensitivity_p.csv").read_text().splitlines()
            if not ln.startswith("#")))
        feas = [r for r in rows if r["feasible"] == "1"]
        infeas = [r for r in rows if r["feasible"] == "0"]
        assert feas and infeas, "sensitivity_p.csv no longer brackets the cliff"
        assert len({r["bytes_per_rec"] for r in feas}) == 1, (
            "the optimum is no longer invariant across the feasible p range; the paper says it is"
        )
        n_feas = {r["n_feasible"] for r in feas}
        assert n_feas == {"44"}, f"feasible-set size changed to {n_feas}; the paper says 44"
        first_bad = min(float(r["p_loss"]) for r in infeas)
        assert abs(first_bad - 0.051) < 1e-9, f"the cliff moved to p={first_bad}"
        tex = self._tex()
        assert "Sensitivity to $p$" in tex, "the p-sensitivity paragraph was removed"
        assert "$p{=}0.051$ the feasible set is \\textbf{empty}" in tex

    def test_hardware_section_states_what_it_cannot_validate(self):
        """⚠️ One transmitter means zero contention. Claiming otherwise would overreach."""
        tex = self._tex()
        assert "zero contention" in tex and "does \\emph{not} validate" in tex, (
            "the two-node hardware caveat no longer says it cannot validate the contention models"
        )


class TestDirectionCSurvey:
    """The survey claim changed on new evidence (2026-08-07) and must track the artifact.

    Klimiashvili et al. 2020 entered the corpus under the pre-registered criteria and is the first
    REPORTS verdict — it states "the average of 50 independent runs". The paper had said none of
    four studies reported replication; it now says four of five, and reports a count rather than a
    percentage because n=5 cannot support one.

    ⚠️ A counter-example to one's own hypothesis is the single easiest thing to quietly drop. This
    test makes dropping it fail.
    """

    CSV = REPO / "results" / "raw" / "direction_c_survey.csv"

    def _verdicts(self) -> dict[str, str]:
        return {r["paper"]: r["verdict"] for r in csv.DictReader(
            ln for ln in self.CSV.read_text().splitlines() if not ln.startswith("#"))}

    def test_the_counter_example_is_in_the_corpus_and_counted(self):
        v = self._verdicts()
        assert "klimiashvili2020_lora_vs_wifi_adhoc_ns3" in v, (
            "the REPORTS counter-example was removed from the corpus"
        )
        assert v["klimiashvili2020_lora_vs_wifi_adhoc_ns3"] == "REPORTS"
        counted = [x for x in v.values() if x in {"REPORTS", "NONE"}]
        assert len(counted) == 14, f"corpus size changed to {len(counted)}"

    def test_paper_states_the_survey_as_the_artifact_has_it(self):
        v = self._verdicts()
        counted = [x for x in v.values() if x in {"REPORTS", "NONE"}]
        n_none = sum(1 for x in counted if x == "NONE")
        tex = (REPO / "paper" / "main.tex").read_text()
        assert "\\emph{fourteen} ns-3 LoRa simulation studies" in tex, (
            f"the paper no longer says the corpus holds {len(counted)} studies"
        )
        assert n_none == 12 and "\\textbf{twelve} state no seed count" in tex, (
            f"artifact has {n_none} NONE; the paper's wording disagrees"
        )
        assert "\\textbf{Two do}" in tex, (
            "the paper stopped disclosing the counter-examples to its own hypothesis"
        )
        assert "achieved $n$ is $14$" in tex, (
            "the paper stopped reporting the achieved n against the protocol's target of 56"
        )

    def test_reports_share_still_sits_below_the_preregistered_threshold(self):
        """If REPORTS ever reaches 25 %, H1 is unsupported and the paper must say so."""
        v = self._verdicts()
        counted = [x for x in v.values() if x in {"REPORTS", "NONE"}]
        share = sum(1 for x in counted if x == "REPORTS") / len(counted)
        assert share < 0.25, (
            f"REPORTS is now {share:.0%}, at or above the pre-registered 25 % falsification "
            f"threshold. H1 is NOT supported — the paper's claim must be withdrawn, not softened."
        )


class TestDR6Derivation:
    """DR6 is derived, not simulated, and the paper must keep saying so.

    Mohamed asked for a DR6 run (2026-08-07). It is not possible in this module: the sensitivity
    vectors are indexed by SF alone with no bandwidth dimension, so SF7-at-250kHz would return
    DR6's doubled bit rate with DR5's noise floor -- a clean, repeatable, optimistic number.
    The capacity claim rests instead on a closed form whose airtime term cancels, validated
    against the measured DR5 run.
    """

    DUTY = 0.009864   # measured duty cycle after jitter (EU868 requires < 1%)

    def test_closed_form_reproduces_the_measured_dr5_run(self):
        """If this drifts, the DR6 claim loses the evidence it rests on."""
        meas = {int(r["n_devices"]): float(r["delivered_frac"]) for r in csv.DictReader(
            ln for ln in (REPO / "results" / "raw" / "lora_capacity.csv").read_text().splitlines()
            if not ln.startswith("#"))}
        worst = 0.0
        for n, m in meas.items():
            if n < 2 or n > 10:
                continue
            worst = max(worst, abs(math.exp(-2 * (n - 1) * self.DUTY) - m))
        assert worst < 0.01, (
            f"the rate-independent closed form now deviates from DR5 by {worst:.4f} "
            f"(was <0.009); the DR6 derivation cited it as validated"
        )

    def test_closed_form_gives_the_same_n_max_as_the_simulation(self):
        n_max = max(n for n in range(1, 40) if math.exp(-2 * (n - 1) * self.DUTY) >= 0.95)
        assert n_max == 3, f"closed form now gives N_max={n_max}; the simulation gives 3"

    def test_paper_labels_dr6_as_derived_not_measured(self):
        tex = (REPO / "paper" / "main.tex").read_text()
        assert "We derive this rather than simulate it" in tex, (
            "the paper stopped disclosing that DR6 is derived rather than simulated"
        )
        assert "indexed by \\emph{spreading factor alone}" in tex, (
            "the paper stopped stating WHY DR6 cannot be simulated here"
        )

    def test_the_scenario_guard_states_the_true_reason(self):
        """The guard used to claim DR6 is not LoRa modulation. It is; FSK starts at DR7."""
        cc = (REPO / "ns3" / "ns-3.48" / "scratch" / "authbc-lora-capacity.cc")
        if not cc.exists():
            pytest.skip("NS-3 tree not present")
        src = cc.read_text()
        assert "LoRa modulation only" not in src, (
            "the false justification came back: DR6 IS LoRa modulation (SF7/250kHz)"
        )
        assert "indexed by SF only" in src
