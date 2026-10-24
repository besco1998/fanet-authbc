# Revision status — one row per item of `docs/AUTHBC Revision Plan.md`

*Updated 2026-10-22. Branch `p11-reviewer-revision`. Registrations are
`predictions/<ID>.md`, tagged `prereg-<ID>` at the commit that registered them; outcomes are
appended to the same file below a line. Rules: `docs/revision/EXECUTION_PLAN.md`. Long jobs run
as memory-capped systemd user units (`scripts/capped.sh`; `systemctl --user list-units
'authbc-*'`), logs in `~/.cache/authbc-logs/`.*

| ID | State | What is known |
|---|---|---|
| A1 | ✔ stage 2 (4 230 runs) | ratio 3.46–3.58 in every layout, equal power to a 1 km disc (hidden share up to 0.11); capacity in neighbours falls (8.7 at R = 1 km), in nodes it rises (218). My A1-2 bracket [10, 40] missed. ⚠️ S3's 5 and 15 m/s are identical runs: group speed untestable in this scenario (F88, H8) |
| A1-motion | ✔ (900 runs) | every node moving on its own at 0/5/15 m/s: ΔV ≤ 0.0005, ratio 3.57–3.63; motion changes the runs (0/300 identical) but not the neighbour count. F103 (closes H8) |
| A2 | ✔ map, age part, ns-3 validation (3 150 runs) | one lost frame breaks the deadline; the map holds in ns-3 at 15 roles within 1.05 % of the model; ratio 6.63 at (100 /s, 100 ms) (F90, F100) |
| A3 | ✔ part 1 and part 2 (60 traced runs, 3 000 links) | tolerable loss held; the margin rule fails in 5 of 192 cells, all bursty, by its interval (F86; one is the design, b = 4, at ε = 0.1, p = 0.08, Gilbert-8; under bit errors, outside the 192, the design misses by its interval at the same point). Traces: ns-3 collision loss is independent frame to frame (burst 1.06), so V follows Eq. (3) for independent loss, not the Gilbert form (F98); plan (3) missed in 1 of 4 by 0.0002 |
| A4 | ✔ (120 runs) | the controller saves 9–41 ms of peak age but runs at the target's edge: V ≈ 0.955, a quarter of windows < 0.95 on the ramp, fails at 76 nodes (fixed b = 4: 127; oracle: 125). Plan (2), (3) failed; (1), (4)–(6) held. H9 |
| A4b | ✔ (60 runs) | the shortfall was mostly margin: margin 0.02 holds 93 % of windows, fails at 116 (A4: 75 %, 76), saves 20 ms vs fixed b = 4; growth term alone 85 %, 108. Neither within 5 % of fixed b = 4. Mobile cannot discriminate (identical series). F102 |
| A5 | ✔ | the window closes the delay-line attack; the plan's "2 hours" failed as predicted (75 min) |
| A6 | ✔ — registered model: 3 of 9 settled (19 predicted verdicts, 4 came true). **After registration**, two encodings changed (counters keyed by a fresh session id; a receiver start rule) and helpers added: lemmas 1–3 and gap detection verified in `formal/authbc_counters.spthy` (all 15, one run); continuity in the registered model; lemma 5 attack-then-fix in `formal/authbc_time.spthy`. One model with everything (`formal/authbc_full.spthy`) did not settle | the plan's statement held across three models, two made after registration |
| A7 | ✔ timing + flood on pi-B (2026-10-22) | the 8 B group tag stops an outsider (refused at 22.5 µs; V = 0.984 at 3 000 forged/s with 41 senders); a forged frame costs 1.08 ms, not 1.4 (928/s per core, not 700); cheap checks and the cap do nothing against an insider spreading forgeries (V < 0.95 from ~125/s); the tag costs 3.1 % of capacity. F109. Reboot during the first flood (a jostled power supply): re-run whole, disclosed |
| A8 | ✔ timing and energy on pi-B (2026-10-22) | compiled receive 0.277 ms vs Python 1.409 (×5.1); 289 nodes per core, 643 with batches of 64 (F108). Energy (rig check passed; calibration waived by Mohamed): the compiled lean sender spends 17.1 µJ/record (b = 4) and 60.7 (b = 1) against the first format's 58.4 and 118.0: the anomaly is the interpreter's; my ranges missed low (power 0.65 W, not 0.75). F112 |
| A9 | ✔ (30 SIH flights) + **A9-fast ✔** (the 20 fixed-wing/VTOL missions re-flown at their drawn 15–25 m/s, 2026-10-22) | delta = one byte per field on every airframe; at the registered speeds fixed wings cost +0.2 B (9.22 vs 9.00); 25 fields: saving 63.3 %, ratio 3.04. The plan's ~60 B keyframe and 10–13 B fixed-wing delta missed at every speed. A9's airplane flights had a ground-level first leg (TECS reference from sea level): no effect. F105, F107, F111 | the gain is set by the frame count: 2× until a 159–282 B delta |
| A10 | ✔ (1 860 runs) | Table 5 reproduced (all N_max in their intervals); against 100 ms only MAVLink 2 (42.1), Wong–Lam (29.1) and TESLA with d = 2, I ≤ 20 ms (39.6–39.8) cross; G-R, every EMSS and TESLA-batch4 never do. F99 |
| A11 | ✔ 802.11 (2 520 runs); NR sidelink: **future work** (Mohamed, 2026-10-24) | ratio 3.39–3.80 on six PHYs/rates, rising with rate (not the plan's 1.7–4.3); the model within 1.5 % except at the fastest rate of each channel width, 2.9–4.6 % optimistic there (F104, corrected 2026-10-24) |
| A12 | ✔ (330 runs) | delivery follows the total frame rate: every plan statement held, the model within 0.0011 up to 350 frames/s per node; eight radios can stand for 124 nodes in ns-3. Not in the paper: it only prepared B2 |
| A13 | ✔ (pi-B, 2026-10-22) | lazy verification: tier 1 10.2 µs, tier 2 117.2 µs per frame → 628 nodes per core; evidence ≤ 171 ms (my 170 ms bound missed by 1 ms). F108 |
| A14 | not done — **not stated** in the paper or the letter, not even as future work, until the purchases (Mohamed, 2026-10-24) | |
| A15 | ✔ capacity and timing (host + pi-B, 2026-10-22) | Falcon fits; the design with it serves 43.5 nodes; the ratio is 3.5, as with Ed25519 (the plan's "larger" failed). Falcon-512 on pi-B: sign 638 µs, verify 88 µs (3× faster than Ed25519's 259). F110 |
| A16 | ✔ | both faults caught, no false finding; 6.4 min of a core per flight hour; 0.96 GB/h for 124 neighbours |
| A17 | ✔ | the CAM deadline is not in its standard |
| B1–B5 | not executable here — purchases, flights (H3); **not stated** in the paper or the letter until the purchases (Mohamed, 2026-10-24) | |

## The crash of 2026-10-20 01:02

WSL ran out of memory: two Tamarin proofs (5.7 GB, growing), the test gate (4.2 GB), ten ns-3
runs (3.4 GB) and the editor (2.4 GB) against 14 GB + 4 GB swap; the kernel's OOM killer then
took WSL's own init processes (`journalctl -b -1`: "init.scope: Failed with result
'oom-kill'"). Lost: ~2.5 h of A2 runs (the driver checkpointed in submission order), the A5
run, both Tamarin runs, and everything under `/tmp`. Fixed: memory-capped units, completion-
order checkpoints, logs and the clean gate under `~/.cache`.
