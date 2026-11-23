# Mohamed's decisions of 2026-11-21, carried out: UF2, UG25H, U5 and four hardware sessions

*Branch `p13-sending-pattern`, 2026-11-21 to 2026-11-23. It follows
`2026-11-21_sending_pattern_and_capture.md`; the decisions are in `docs/DECISIONS.md`, 2026-11-21
to 2026-11-23. Each result's full outcome is in its registration, below its outcome line. **Final**
(2026-11-23): Mohamed's answers to its open questions, the last session W1s and U3's closure are
included.*

## Every registered claim, held or failed

| registration | what was claimed | outcome | side of the misses |
|---|---|---|---|
| `prereg-UF2` (a) | (G23) with the half-duplex factor (G22a) and (G25), ±5 %, 8 new configurations, occupancy ≤ 0.78 | **8 of 8 held** (−0.12 … −0.86 %) | all conservative |
| `prereg-UF2` (b), statistic 2 | (G24a), the expected worst sender per 20 s window, ±5 % | **8 of 8 held** (−1.30 … −4.79 %) | all conservative |
| `prereg-UF2` (b), statistic 1 | (G24) per sender, pooled over 30 seeds on a fixed placement, ±5 % | **8 of 8 held** (−0.15 … −1.41 %) | all conservative |
| `prereg-UG25H` | (G25) at 802.11b, occupancy 0.82–0.87, no capture: quantify, no tolerance | **optimistic by +1.16 … +2.41 %**; F140's band (+3.6 … +5.5 %) held at none of 4 | optimistic |
| `prereg-W1p` | the saturated pi-A + pi-B pair: a family is consistent if inside the 95 % interval for loss and rate | **neither family consistent** | — |
| `prereg-W1q` | ns-3's 4 dB capture rule, per valid power step, weak and strong | **5 of 6 held**; the 3 dB step's strong prediction failed | — |
| `prereg-W1r` | W1e's windows with frame burst off, scored with W1p's family | **valid; reported, not scored** (W1p chose none) | — |
| `prereg-W1s` A | W1q's capture curve (steps with every single-sender loss ≤ 1 %) on unseen steps, the halfway reading alone | **2 of 3 scored steps held: the curve is not used** | the one failure: q_A below the band |
| `prereg-W1s` B | the windows re-derived from 2026-11-22's cycles, the saturated pair at 345 B, W1p's rule | **neither family consistent:** the window is not identifiable without a frame sniffer | between them in loss, just below both in rate |
| `prereg-W1s` C | the Pi 3's extra time per frame: fixed (d ≥ ⅔c) or backoff (d ≤ ⅓c) | **unresolved** (d/c = 0.60): an unexplained property of the BCM43430 | — |

## UF2 — F (a) and (b), on placements and seeds never used

* **All 24 claims held, and every one is conservative.** The half-duplex factor is supported where
  it matters (802.11a, N ≈ 11–15: errors −0.41 … −0.74 % with it, +0.12 … +1.42 % without). At
  802.11b it moves the root by 0.2–0.4 %, so this is not a test that the factor is needed.
* **(G24a)'s errors are the largest** (−4.35 % and −4.79 % at 802.11b with Rayleigh fading), on
  the side its two stated assumptions predict.
* **The z_N closed form lies nearer ns-3 than the exact (G24a).** That is two approximations
  offsetting, not evidence that the senders are independent.

## UG25H — F (c), the limit past occupancy 0.78

* **(G25)'s range at 802.11b now reads:** checked to occupancy 0.78 (−1.9 … +0.3 %); from 0.82 to
  0.87 without capture, optimistic by 1.2–2.4 %.
* **F140's 3.6–5.5 % did not recur here.** It stays recorded for its own regime (N ≈ 10, loss
  6.4–7.9 %), which these cells do not include; its cause is not established.

## F (d) and U5

* **(d):** the model is stated as limited to one collision domain, every station hearing every
  other, in `capture.py`, the reports and DECISIONS, with F141 and the outlier as the evidence.
* **U5's note** is in ch. 10, worded as Mohamed approved, with one narrowing on insertion
  (DECISIONS, "The U5 note's wording").
* **U5's N ≥ 20 drift is closed.** A clean-tree rebuild equals the main build in all 480 runs. The
  fifth-decimal difference from July's files remains; the C library's two upgrades are the
  untested candidate.

## The three hardware sessions, 2026-11-22, in the approved order 3, 1, 2

| session | layout | validity | result |
|---|---|---|---|
| **W1p** (session 3): the saturated pair, jitter, gap distributions | side by side, W1e's | held | **Neither family consistent.** The pair lost 0.1029 (0.0979–0.1079) at 262.7 frames/s, against 0.413 / 331 (σ 20/DIFS 50) and 0.169 / 288 (σ 9/DIFS 28). W is not identified within the two; σ 9 µs is nearer by loss, reported, not adopted |
| **W1q** (session 1): capture against power difference, the Pi 3 receiving | 1 m triangle | held | **5 of 6 held.** At a measured 1.5 dB the Pi 3 kept the stronger frame 93.7 % of the time, where the 4 dB rule keeps none. Steps 6, 10 and 15 were void by the RSSI reading |
| **W1r** (session 2): W1e's 12 points, frame burst off | side by side, **20 cm** (a deviation Mohamed chose before the run) | held; 48 of 48 windows usable | **Reported against both families:** σ 20 inside the 95 % interval at 2 of 12 points, σ 9 at 1 of 12; the hardware lies between them |

* **The per-peer RSSI kit check was rejected at all three boards,** so W1q and W1r used the
  registered fallback, the zero-address reading in single-sender windows.
* **Before W1p, W1q and W1r a preflight said GO.** Before W1q, after the power cut, the first
  said RETRY (F129's fresh-boot fast rate) and the second GO, as `analysis/pis_preflight.py` now
  decides.

## W1s, 2026-11-23 — the last board session of the phase, and U3 closed

* **Valid:** all 42 windows on every board in the 1 m triangle; no chip stop; frame burst 0; every
  power read back exactly. The independent recompute matched every value.
* **A, the capture curve: not used.** 2 of the 3 scored steps held.
  * Δ came out −4 to −7 dB at every step. W1q measured +7 at equal power in the same 1 m legs, and
    here it was −5. So only the mirrored curve was tested.
  * The failure: q_A was −0.106 at pi-A 10 dBm.
  * The 18 dBm step read back exactly but was not scored: pi-A's link alone lost 1.09 %.
  * **The thesis states W1q's scored result alone** (5 of 6).
* **B, the window: not identifiable without a frame sniffer.**
  * The pair lost 0.1019 (0.0873–0.1166) at 145.6 (144.2–147.0) frames/s.
  * σ 20 predicted 0.1227 / 149.5, and σ 9 0.0686 / 145.9; neither is consistent.
  * The loss lies between them; the rate lies 0.3 frames/s below σ 9's, so it is not bracketed by
    the registered definition.
* **C, the Pi 3's timing: an unexplained property of the BCM43430** (d = 158 µs, c = 265 µs,
  d/c = 0.60).
* **U3 is closed,** as Mohamed decided, whatever the outcome. No further hardware session runs in
  this phase.

## The failures, and what each one means

* **W1p, neither family consistent.** Both families were fitted to W1f's cycle, which was
  measured with frame burst on. With it off, today's Pi 4 cycles are 4.7 % and 7.8 % longer (seen
  after scoring). A W re-derived from them would need a fresh registered check.
* **W1q, the 3 dB step's strong prediction.** Capture on this receiver is gradual, not ns-3's
  4 dB step. The registration counted a gradual curve as a finding.
* **W1q's three void steps come from the reading, not the radios** (seen after scoring). The
  fallback averages a reading taken after each window, when the sender has stopped. At pi-A's low
  powers that reading is 5–6 dB too loud. The halfway readings alone give falls of 0, 4, 7, 10
  and 13 dB against 0, 3, 6, 10 and 15. By Mohamed's rule, that corrected reading is used only
  after a fresh registered check on unseen points.
* **W1r, the Pi 3's pairs** (seen after scoring). AC and BC lose 1.01–1.63× what AB loses; ns-3
  gives 0.20–0.52×, because the Pi 3's window is inferred from its longer one-sender cycle. Both
  directions of every pair lose about equally. Hypothesis, untested: the Pi 3's extra time per
  frame is not spent in a wider random backoff.
* **W1s, why the last session could not settle the curve or the window** (seen after scoring):
  * the triangle's radio geometry differed from W1q's (pi-A −59 against −41 dBm at the Pi 3), and
    the one halfway reading per window barely followed the set power;
  * 37–46 % of the Pi 4s' gaps sit at DIFS with no backoff. No board fits "DIFS + a uniform
    backoff", the model behind both the cycle-to-W step and part C's statistic.
  * A hypothesis, untested: frames that reach an idle medium are sent at once, so a one-sender
    cycle measures the sending pattern as well as W.
* **pi-B's chip locked in the revert after W1p.** A soft reboot did not clear it; a power cut did.
  The cause is not established. The revert now logs each step and keeps the kernel log
  (DECISIONS, 2026-11-22).

## Mohamed's answers (2026-11-23), and what stays open

1. **The capture curve:** a fresh check, W1s part A. It was run; the curve is not used.
2. **The window:** re-derived once, one test, W1s part B. Neither family; the window is not
   identifiable without a frame sniffer.
3. **The Pi 3's timing:** a test in the same session, W1s part C. Unresolved; it is an unexplained
   property of the BCM43430.
4. **U3:** closed after W1s.
5. **The thesis and paper (U8):** the thesis gets all five results, negative ones and limits
   included. The paper gets (G25) and capture as validated, the one-collision-domain scope and the
   hardware capture finding, with the window and the Pi 3's timing as one-line limitations.
   * **Placement approved:** a new chapter, "A closed-form model of the channel", between ch. 8 and
     ch. 9.
   * **Open:** the drafting, on `main` only, after this branch is merged. Mohamed approves the text.
6. **Merges:** `p12-unified-model` is in `main` (fast-forward, `2713629e`). This branch follows once
   this report is final and CI is green.

## Handoff 2026-11-23 — Mohamed's decisions of 2026-11-21 to 2026-11-23 (serial), final

* **Green baseline:** branch `p13-sending-pattern` at the commit that adds W1s's outcome and this
  final report.
  * Before the push, the fast suite passes in a clean worktree, with ruff clean.
  * Registration tags `prereg-UF2`, `UG25H`, `W1p`, `W1q`, `W1r`, `W1s`, all held in
    `NOT_YET_IN_THE_THESIS`. No phase tag.
* **Done:**
  * UF2, 24 of 24; UG25H quantified; (c) and (d) stated; U5's note and drift closed;
  * the kit (K1–K5, `chip_check.sh`), `--positionsFile` (gate 9/9) and `pis_preflight.py`;
  * W1p, W1q (with its optional step), W1r and W1s, each scored or reported, with an independent
    recompute;
  * **U3 closed;** `p12-unified-model` merged into `main`.
* **Frozen this session:** nothing.
* **Open, awaiting Mohamed:** U8's text, once drafted.
* **Next three steps:**
  1. CI green on this branch, then fast-forward `main` to it;
  2. on `main`, draft the new thesis chapter and the ch. 9 hardware sections (U8), and give
     Mohamed the text;
  3. then the paper, per his item 5.
* **Gotchas:**
  * the fast suite needs a 6G cap (a bootstrap fixture peaks at 3.5 GB);
  * a locked Pi chip needs a 10 s power cut, and the first preflight after one says RETRY;
  * don't ssh to the boards during a session;
  * "the same layout" by tape is not the same radio geometry (W1s against W1q). Record the boards'
    orientation, not only the distances;
  * Mohamed's uncommitted `Makefile`, `docs/README.md` and untracked files stay untouched. His two
    untracked test files add 3 tests in the main tree only.
