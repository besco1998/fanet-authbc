"""Does the anomalous slot explain the unicast small-frame bias? (item O4, findings F29/E21/E24)

**The open question this closes.** The unicast validation band is +1.29/−0.40 % at 1400 B, but at
72 B the deviation is a *systematic* −1.40…−2.60 % — confirmed real (SE ±0.06 %), not scatter.
`OPEN_ITEMS` E21 called the anomalous-slot effect a "plausible" cause and recorded it as an
**untested hypothesis**. These tests test it.

**The prediction, made from theory alone.** Bianchi omits the anomalous slot, so it under-counts the
cycle by one idle slot σ per success and over-predicts throughput by σ/(T_s + σ). That is a *worst
case* (one full slot every time), so it should **bound** the observed bias, and — the discriminating
part — it should scale with frame size as 1/T_s, collapsing from 3.3 % at 72 B to 0.44 % at 1400 B.

⚠️ This is a consistency check against a bounding argument, not a fit of the full Tinnirello model.
It establishes that the anomalous slot is of the right sign and magnitude to account for the bias,
which is a much weaker claim than "this is the whole effect" — and the tests are written to assert
only what is actually supported.
"""

from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

import pytest

from authbc.models import bianchi

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
NS = (5, 10, 20, 35, 50)
MATRICES = {72: "ns3_matrix_72B.csv", 288: "ns3_matrix_288B.csv", 1400: "ns3_matrix.csv"}


def _unicast_deviations(frame_bytes: int) -> list[float]:
    """(sim − model)/model in percent, per N, for the unicast arm at this frame size."""
    path = RAW / MATRICES[frame_bytes]
    rows = csv.DictReader([ln for ln in path.read_text().splitlines() if not ln.startswith("#")])
    grouped: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        if r["mode"] == "unicast":
            grouped[int(r["N"])].append(float(r["goodput_mbps"]))
    out = []
    for n in NS:
        if n not in grouped:
            continue
        model = bianchi.solve(n, frame_bytes).throughput_bps / 1e6
        out.append(100.0 * (st.mean(grouped[n]) - model) / model)
    return out


class TestThePredictionIsAnUpperBoundOnTheBias:
    @pytest.mark.parametrize("frame_bytes", sorted(MATRICES))
    def test_no_measured_deviation_is_more_negative_than_the_bound(self, frame_bytes):
        """If the bias exceeded the worst-case anomalous slot, something else would be going on."""
        predicted = bianchi.anomalous_slot_bias_pct(frame_bytes)
        worst = min(_unicast_deviations(frame_bytes))
        assert worst >= predicted - 0.05, (
            f"at {frame_bytes} B the measured bias {worst:+.2f} % exceeds the anomalous-slot "
            f"bound {predicted:+.2f} % — the effect cannot be the whole explanation"
        )


class TestTheDiscriminatingPrediction:
    """Sign and magnitude are easy to match by accident; the SCALING with frame size is not."""

    def test_the_bias_shrinks_as_the_frame_grows(self):
        worst = {L: min(_unicast_deviations(L)) for L in sorted(MATRICES)}
        assert worst[72] < worst[288] < worst[1400], (
            f"the bias must weaken as T_s grows; got {worst}"
        )

    def test_predicted_magnitude_falls_by_the_ratio_of_frame_durations(self):
        """sigma/T_s: 3.32 % at 72 B down to 0.44 % at 1400 B, a ~7.5x collapse."""
        p72 = bianchi.anomalous_slot_bias_pct(72)
        p1400 = bianchi.anomalous_slot_bias_pct(1400)
        assert p72 == pytest.approx(-3.32, abs=0.05)
        assert p1400 == pytest.approx(-0.44, abs=0.02)
        assert p72 / p1400 == pytest.approx(7.5, rel=0.1)

    def test_at_1400_bytes_the_bound_essentially_meets_the_measured_floor(self):
        """The strongest single point: predicted -0.44 % against a measured floor of -0.40 %.

        At large frames the anomalous slot is nearly the ONLY thing separating model from
        measurement on the pessimistic side, and the two agree to 0.04 points.
        """
        assert min(_unicast_deviations(1400)) == pytest.approx(
            bianchi.anomalous_slot_bias_pct(1400), abs=0.10)


class TestGuards:
    def test_rejects_nonpositive_payload(self):
        with pytest.raises(ValueError, match="must be positive"):
            bianchi.anomalous_slot_bias_pct(0)

    def test_broadcast_is_not_claimed_to_be_explained_by_this(self):
        """⚠️ Broadcast has no ACK and holds to +-0.21 % at 72 B — TIGHTER than at 1400 B.

        So the small-frame story is unicast-only, and the headline (which runs on broadcast) is
        untouched. Asserted so nobody generalises this explanation to the arm it does not apply to.
        """
        rows = csv.DictReader([ln for ln in (RAW / MATRICES[72]).read_text().splitlines()
                               if not ln.startswith("#")])
        grouped: dict[int, list[float]] = defaultdict(list)
        for r in rows:
            if r["mode"] == "broadcast":
                grouped[int(r["N"])].append(float(r["goodput_mbps"]))
        devs = []
        for n in NS:
            model = bianchi_broadcast_mbps(n, 72)
            devs.append(100.0 * (st.mean(grouped[n]) - model) / model)
        assert max(abs(d) for d in devs) < 1.0, f"broadcast at 72 B should stay tight, got {devs}"


def bianchi_broadcast_mbps(n: int, frame_bytes: int) -> float:
    from authbc.models import broadcast_dcf

    return broadcast_dcf.solve(
        n, frame_bytes, bianchi.t_broadcast(frame_bytes), w0=bianchi.W, slot_s=bianchi.SLOT
    ).throughput_bps / 1e6
