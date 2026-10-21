# Revision status — one row per item of `docs/AUTHBC Revision Plan.md`

*Updated 2026-10-20, 08:30. Branch `p11-reviewer-revision`. Registrations are
`predictions/<ID>.md`, tagged `prereg-<ID>` at the commit that registered them; outcomes are
appended to the same file below a line. Rules: `docs/revision/EXECUTION_PLAN.md`. Long jobs run
as memory-capped systemd user units (`scripts/capped.sh`; `systemctl --user list-units
'authbc-*'`), logs in `~/.cache/authbc-logs/`.*

| ID | State | What is known |
|---|---|---|
| A1 | ✔ stage 2 (4 230 runs) | ratio 3.46–3.58 in every layout, equal power to a 1 km disc (hidden share up to 0.11); capacity in neighbours falls (8.7 at R = 1 km), in nodes it rises (218). My A1-2 bracket [10, 40] missed. ⚠️ S3's 5 and 15 m/s are identical runs: group speed untestable in this scenario (F88, H8) |
| A1-motion | ✔ (900 runs) | every node moving on its own at 0/5/15 m/s: ΔV ≤ 0.0005, ratio 3.57–3.63; motion changes the runs (0/300 identical) but not the neighbour count. F103 (closes H8) |
| A2 | ✔ map, age part, ns-3 validation (3 150 runs) | one lost frame breaks the deadline; the map holds in ns-3 at 15 roles within 1.05 % of the model; ratio 6.63 at (100 /s, 100 ms) (F90, F100) |
| A3 | ✔ part 1 and part 2 (60 traced runs, 3 000 links) | tolerable loss held; the margin rule fails in 5 of 192 bursty cells (interval; F86). Traces: ns-3 collision loss is independent frame to frame (burst 1.06), so V follows Eq. (3) for independent loss, not the Gilbert form (F98); plan (3) missed in 1 of 4 by 0.0002 |
| A4 | ✔ (120 runs) | the controller saves 9–41 ms of peak age but runs at the target's edge: V ≈ 0.955, a quarter of windows < 0.95 on the ramp, fails at 76 nodes (fixed b = 4: 127; oracle: 125). Plan (2), (3) failed; (1), (4)–(6) held. H9 |
| A4b | ✔ (60 runs) | the shortfall was mostly margin: margin 0.02 holds 93 % of windows, fails at 116 (A4: 75 %, 76), saves 20 ms vs fixed b = 4; growth term alone 85 %, 108. Neither within 5 % of fixed b = 4. Mobile cannot discriminate (identical series). F102 |
| A5 | ✔ | the window closes the delay-line attack; the plan's "2 hours" failed as predicted (75 min) |
| A6 | ✔ — registered model: 3 of 9 settled (19 predicted verdicts, 4 came true). **After registration**, two encodings changed (counters keyed by a fresh session id; a receiver start rule) and helpers added: lemmas 1–3 and gap detection verified in `formal/authbc_counters.spthy` (all 15, one run); continuity in the registered model; lemma 5 attack-then-fix in `formal/authbc_time.spthy`. One model with everything (`formal/authbc_full.spthy`) did not settle | the plan's statement held across three models, two made after registration |
| A7 | registered `prereg-A7`; code + tests ✔; timing waits for pi-B (H4) | the tag costs 3 % of capacity (not 2 %) |
| A8 | registered `prereg-A8`; Rust codec ✔; **byte-identical to Python on 10 000 frames**; timing and energy wait for pi-B (H4, G22) | |
| A9 | registered `prereg-A9` (size code reproduces the encoder on 9 fields, tested); flights need a quiet host (H7) | SIH flies all three airframes; fixed-wing needed two parameters (stated) |
| A10 | ✔ (1 860 runs) | Table 5 reproduced (all N_max in their intervals); against 100 ms only MAVLink 2 (42.1), Wong–Lam (29.1) and TESLA with d = 2, I ≤ 20 ms (39.6–39.8) cross; G-R, every EMSS and TESLA-batch4 never do. F99 |
| A11 | ✔ 802.11 (2 520 runs); NR sidelink not run (H6) | ratio 3.39–3.80 on six PHYs/rates, rising with rate (not the plan's 1.7–4.3); the model within 1.5 % down to 178 µs frames, 4–4.6 % optimistic at the fastest rates (F104) |
| A12 | ✔ (330 runs) | delivery follows the total frame rate: every plan statement held, the model within 0.0011 up to 350 frames/s per node; eight radios can stand for 124 nodes in ns-3 |
| A13 | not started — depends on A8's timing on pi-B | |
| A14 | not started — the plan's lowest priority ("keep for a follow-up paper") | |
| A15 | capacity ✔; timing waits for a quiet host / pi-B | Falcon fits; the design with it serves 43.5 nodes; the ratio is 3.5, as with Ed25519 (the plan's "larger" failed) |
| A16 | ✔ | both faults caught, no false finding; 6.4 min of a core per flight hour; 0.96 GB/h for 124 neighbours |
| A17 | ✔ | the CAM deadline is not in its standard |
| B1–B5 | not executable here — purchases, flights (H3) | |

## The crash of 2026-10-20 01:02

WSL ran out of memory: two Tamarin proofs (5.7 GB, growing), the test gate (4.2 GB), ten ns-3
runs (3.4 GB) and the editor (2.4 GB) against 14 GB + 4 GB swap; the kernel's OOM killer then
took WSL's own init processes (`journalctl -b -1`: "init.scope: Failed with result
'oom-kill'"). Lost: ~2.5 h of A2 runs (the driver checkpointed in submission order), the A5
run, both Tamarin runs, and everything under `/tmp`. Fixed: memory-capped units, completion-
order checkpoints, logs and the clean gate under `~/.cache`.
