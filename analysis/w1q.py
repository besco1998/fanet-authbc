#!/usr/bin/env python3
"""W1q — session 1 of the 2026-11-20 session plans: capture against power difference, the Pi 3 as
receiver (predictions/W1q.md; approved by Mohamed 2026-11-21, docs/DECISIONS.md).

pi-A and pi-B send, saturated; the Pi 3 receives. pi-A's power steps down; pi-B's is fixed.

**What q is here.** The share of a sender's collided frames that **the Pi 3** still receives
(Mohamed, 2026-11-21: it is the Pi 3 receiver's q, not a swarm's; F138's factor is not applied).

**How it is identified, without a channel model.** In a saturated pair each board is the other's
only sender, and a board that is transmitting cannot receive. So sender j's loss at its partner,
less the partner's link loss for j, is the share of j's frames that overlapped the partner's:
j's collision rate p_j in that very window. At the Pi 3, by (G22), L_j3 = p_j(1 − q_j) + ℓ_j3, so

    q_j = 1 − (L_j3 − ℓ_j3) / (L_j,partner − ℓ_j,partner).

ℓ comes from the step's single-sender windows at 50 frames/s. A sender's frames on air are its
receivers' widest span of sequence numbers (as `contention_hw.saturated`, with the span taken over
all its receivers so that every receiver's loss is counted against the same frames).

**The power difference** at the Pi 3 is ΔRSSI = RSSI_A − RSSI_B from the step's single-sender
windows: the firmware's per-peer reading if the kit check accepted it, else the zero-address
reading in each single-sender window (the registered fallback).

**ns-3's rule, the prediction** (U-CAP, U-CAP2; `authbc.models.capture`): DCF collisions start
within the 4 µs preamble window, where the stronger frame is kept if its SINR is at least 4 dB.
At 802.11b 1 Mb/s it then decodes. So q_strong = 1 at |ΔRSSI| ≥ 4 dB, 0 below, and q_weak = 0.
**Scored per step:** q_weak ≤ 0.10; q_strong ≥ 0.90 where |ΔRSSI| ≥ 5 dB; q_strong ≤ 0.10 where
|ΔRSSI| ≤ 3 dB; between 3 and 5 dB, reported. **Real chips are not ns-3:** a gradual curve, or
capture of a later, stronger frame, is a finding, not a failure of the method.

    python analysis/w1q.py --plan   -> experiments/channel24/plan_w1q.txt
    python analysis/w1q.py --score results/hw/channel24/<session>
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_three as w1d  # noqa: E402

PLAN = w1d.PLANS / "plan_w1q.txt"
PI_A, PI_B, PI_3 = 1, 2, 3
P0_MBM = 1500          # 15 dBm, fixed: "auto" reads back 31.00 dBm, the driver's cap, not a power
STEPS_DB = (0, 3, 6, 10, 15)
ALONE_FPS, SAT_FPS = 50, 600
CAPTURE_WINDOWS = 3
STEP_TOLERANCE_DB = 1.5
Q_WEAK_MAX, Q_STRONG_MIN, Q_STRONG_MAX_BELOW = 0.10, 0.90, 0.10
SIR_ABOVE_DB, SIR_BELOW_DB = 5.0, 3.0


def plan() -> list[str]:
    """Rate checks; then per step: each sender alone, three saturated pair windows; rate checks."""
    pay = w1d.PAYLOAD_UDP
    lines = ["# nodes: 1,2,3", "# W1q: pi-A stepped down from 15 dBm, pi-B fixed at 15 dBm,"
             " the Pi 3 receives (analysis/w1q.py)"]
    checks = [f"R{n} {w1d.RATE_CHECK_FPS} {pay} {n} 25" for n in w1d.BOARDS]
    lines += checks
    for i, d in enumerate(STEPS_DB):
        p = f"{PI_A}:{P0_MBM - 100 * d}" + (f",{PI_B}:{P0_MBM}" if i == 0 else "")
        lines += [f"A{d} {ALONE_FPS} {pay} {PI_A} 25 {p}", f"B{d} {ALONE_FPS} {pay} {PI_B} 25"]
        lines += [f"C{d} {SAT_FPS} {pay} {PI_A},{PI_B} 25"] * CAPTURE_WINDOWS
    return lines + checks


def on_air(rx: dict[int, dict[str, Any]], sender: int) -> int:
    """Frames the sender put on air: the widest span of its sequence numbers at any receiver."""
    spans = [g["max_seq"] - g["min_seq"] + 1 for r, d in rx.items() if r != sender
             for g in [d["by_source"].get(f"10.0.0.{sender}")] if g]
    return max(spans)


def losses(rx: dict[int, dict[str, Any]], sender: int, sent: int | None = None
           ) -> dict[int, float]:
    """Sender's loss at each receiver: against `sent` (a single-sender window, where the
    sender's own count holds) or against its frames on air (a saturated window)."""
    n = sent if sent is not None else on_air(rx, sender)
    return {r: 1 - d["by_source"].get(f"10.0.0.{sender}", {}).get("received_unique", 0) / n
            for r, d in rx.items() if r != sender}


def q_of(l_rx: float, ell_rx: float, l_partner: float, ell_partner: float) -> float:
    """q at the receiver from the window's own collision rate (the partner's excess loss)."""
    p = l_partner - ell_partner
    if p <= 0:
        raise ValueError("no collisions at the partner: q is not identified")
    return 1 - (l_rx - ell_rx) / p


def score_step(sir_db: float, q_strong: float, q_weak: float) -> dict[str, Any]:
    """ns-3's rule against one step's measured q, as registered."""
    weak_ok = q_weak <= Q_WEAK_MAX
    if abs(sir_db) >= SIR_ABOVE_DB:
        strong_ok: bool | str = q_strong >= Q_STRONG_MIN
    elif abs(sir_db) <= SIR_BELOW_DB:
        strong_ok = q_strong <= Q_STRONG_MAX_BELOW
    else:
        strong_ok = "reported (3–5 dB)"
    return {"sir_db": sir_db, "q_strong": q_strong, "q_weak": q_weak, "q_weak_held": weak_ok,
            "q_strong_held": strong_ok}


def step_valid(rssi_a_db: float, rssi_a0_db: float, step_db: float) -> bool:
    """pi-A's signal at the Pi 3 must fall by the step within ±1.5 dB, or the step is void."""
    return abs((rssi_a0_db - rssi_a_db) - step_db) <= STEP_TOLERANCE_DB


def optional_plan(step_db: int) -> list[str]:
    """Time permitting (Mohamed, 2026-11-21): the chosen step again with pi-B as receiver; pi-A at
    that step's power and the Pi 3 at 15 dBm send."""
    pay = w1d.PAYLOAD_UDP
    return (["# nodes: 1,2,3", f"# W1q, the optional step: {step_db} dB, pi-B receives"]
            + [f"X1 {ALONE_FPS} {pay} {PI_A} 25 {PI_A}:{P0_MBM - 100 * step_db},{PI_3}:{P0_MBM}",
               f"X3 {ALONE_FPS} {pay} {PI_3} 25"]
            + [f"XP {SAT_FPS} {pay} {PI_A},{PI_3} 25"] * CAPTURE_WINDOWS)


def optional_step(steps: list[dict[str, Any]]) -> int | None:
    """The registered choice: the valid step whose |ΔRSSI| at the Pi 3 is nearest 4 dB."""
    valid = [s for s in steps if s["valid"]]
    return min(valid, key=lambda s: abs(abs(s["sir_db"]) - 4.0))["step_db"] if valid else None


def _median(v: list[float]) -> float:
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _rssi_at(readings: list[dict[str, Any]], peer: int, per_mac: bool) -> float:
    vals = [r["peers"][peer] if per_mac else r["any"] for r in readings]
    good = [v for v in vals if v is not None]
    if not good:
        raise ValueError("no RSSI reading in the window")
    return _median(good)


def _step(files: dict[str, Any], tags: dict[str, list[str]], power_ok: dict, d: int | str,
          rx: int, s1: int, s2: int, rssi_rx: list[dict[str, Any]], per_mac: bool,
          prefix: tuple[str, str, str]) -> dict[str, Any]:
    """One step at receiver rx with senders s1 (stepped) and s2: link losses from the
    single-sender windows, q of each sender from its pair windows, ΔRSSI from the readings."""
    alone1, alone2, pair = (tags[f"{prefix[0]}{d}"][0], tags[f"{prefix[1]}{d}"][0],
                            tags[f"{prefix[2]}{d}"])
    ell1 = losses(files[alone1]["rx"], s1, files[alone1]["tx"][s1]["sent"])
    ell2 = losses(files[alone2]["rx"], s2, files[alone2]["tx"][s2]["sent"])
    r1 = _rssi_at([x for x in rssi_rx if x["tag"] == alone1], s1, per_mac)
    r2 = _rssi_at([x for x in rssi_rx if x["tag"] == alone2], s2, per_mac)
    q1, q2, p1, p2 = [], [], [], []
    for tag in pair:
        if not power_ok[tag]:
            continue
        lo1, lo2 = losses(files[tag]["rx"], s1), losses(files[tag]["rx"], s2)
        q1.append(q_of(lo1[rx], ell1[rx], lo1[s2], ell1[s2]))
        q2.append(q_of(lo2[rx], ell2[rx], lo2[s1], ell2[s1]))
        p1.append(lo1[s2] - ell1[s2])
        p2.append(lo2[s1] - ell2[s1])
    return {"rssi_1": r1, "rssi_2": r2, "sir_db": r1 - r2, "q_1": q1, "q_2": q2, "p_1": p1,
            "p_2": p2}


def score(session: Path) -> list[dict[str, Any]]:
    """W1q as registered: validity, the kit check on step 0, q per step against ns-3's rule."""
    import dsss_three
    import hw_session as hs
    import w1p
    windows = dsss_three.window_rows(session)
    files = dsss_three._files(session)
    power_ok = {w["window"]: w["power_ok"] for w in windows}
    tags: dict[str, list[str]] = {}
    for w in sorted(windows, key=lambda x: int(x["window"].split("_")[0])):
        tags.setdefault(w["label"], []).append(w["window"])
    out: list[dict[str, Any]] = [{"what": "frame burst off on every board", "item": "",
                                  "measured": "", "predicted": "0 before and after",
                                  "held": hs.frameburst_off(session)}]
    for w in windows:
        if w["label"] in ("R1", "R2", "R3"):
            c = w["cycle_us"] * 1e-6
            out.append({"what": "rate check", "item": w["window"], "measured": w["cycle_us"],
                        "predicted": "1900-2600 us",
                        "held": dsss_three.RATE_BAND_S[0] <= c <= dsss_three.RATE_BAND_S[1]})
    rssi3 = hs.rssi(session, PI_3)
    kit = {PI_A: [x for x in rssi3 if x["tag"] == tags["A0"][0]],
           PI_B: [x for x in rssi3 if x["tag"] == tags["B0"][0]]}
    readable = all(x["any"] is not None and all(v is not None for v in x["peers"].values())
                   for rs in kit.values() for x in rs)
    verdict = w1p.per_mac_accepted(kit) if readable else "rejected (a read failed)"
    per_mac = verdict == "accepted"
    out.append({"what": "kit check at the Pi 3 (step 0)", "item": "", "measured": verdict,
                "predicted": "accepted, or the fallback", "held": "reported"})
    steps = []
    r0 = None
    for d in STEPS_DB:
        s = _step(files, tags, power_ok, d, PI_3, PI_A, PI_B, rssi3, per_mac, ("A", "B", "C"))
        r0 = s["rssi_1"] if d == 0 else r0
        assert r0 is not None
        valid = step_valid(s["rssi_1"], r0, d)
        steps.append({"step_db": d, "valid": valid, "sir_db": s["sir_db"]})
        q_a, q_b = sum(s["q_1"]) / len(s["q_1"]), sum(s["q_2"]) / len(s["q_2"])
        strong, weak = (q_a, q_b) if s["sir_db"] >= 0 else (q_b, q_a)
        sc = score_step(s["sir_db"], strong, weak)
        out.append({"what": "step", "item": f"{d} dB (pi-A {P0_MBM // 100 - d} dBm)",
                    "measured": f"ΔRSSI {s['sir_db']:+.1f} dB; q_A {q_a:.3f} "
                                f"({min(s['q_1']):.3f}-{max(s['q_1']):.3f}), q_B {q_b:.3f} "
                                f"({min(s['q_2']):.3f}-{max(s['q_2']):.3f}); p_A "
                                f"{sum(s['p_1']) / len(s['p_1']):.4f}, p_B "
                                f"{sum(s['p_2']) / len(s['p_2']):.4f}; q_A + q_B {q_a + q_b:.3f}",
                    "predicted": "q_weak 0; q_strong 1 at |ΔRSSI| >= 4 dB, else 0",
                    "held": (f"void (pi-A fell {r0 - s['rssi_1']:.1f} dB, not {d} ± 1.5)"
                             if not valid else
                             f"weak {sc['q_weak_held']}, strong {sc['q_strong_held']}")})
    choice = optional_step(steps)
    out.append({"what": "the optional step, by the rule", "item": "", "measured": choice,
                "predicted": "the valid step nearest 4 dB", "held": "reported"})
    if "X1" in tags:
        rssi2 = hs.rssi(session, PI_B)
        s = _step(files, {"A": tags["X1"], "B": tags["X3"], "C": tags["XP"]}, power_ok, "",
                  PI_B, PI_A, PI_3, rssi2, False, ("A", "B", "C"))
        q_a, q_c = sum(s["q_1"]) / len(s["q_1"]), sum(s["q_2"]) / len(s["q_2"])
        strong, weak = (q_a, q_c) if s["sir_db"] >= 0 else (q_c, q_a)
        sc = score_step(s["sir_db"], strong, weak)
        out.append({"what": "optional step, pi-B receives", "item": f"{choice} dB",
                    "measured": f"ΔRSSI {s['sir_db']:+.1f} dB; q_A {q_a:.3f}, q_Pi3 {q_c:.3f}",
                    "predicted": "as above",
                    "held": f"weak {sc['q_weak_held']}, strong {sc['q_strong_held']}"})
    return out


def main() -> None:
    if "--score" in sys.argv:
        import csv
        import io

        from authbc.bench import provenance
        session = Path(sys.argv[sys.argv.index("--score") + 1])
        rows = score(session)
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": f"w1q_{session.name}"}.items():
            buf.write(f"# {k}={v}\n")
        wr = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
        (REPO / "results" / "raw" / f"w1q_{session.name}.csv").write_text(buf.getvalue())
        print(buf.getvalue())
        return
    if "--plan" in sys.argv:
        lines = plan()
        PLAN.write_text("\n".join(lines) + "\n")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
