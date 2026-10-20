# Revision status — one row per item of `docs/AUTHBC Revision Plan.md`

*Updated 2026-10-20, 07:40. Branch `p11-reviewer-revision`. Registrations are
`predictions/<ID>.md`, tagged `prereg-<ID>` at the commit that registered them; outcomes are
appended to the same file below a line. Rules: `docs/revision/EXECUTION_PLAN.md`. Long jobs run
as memory-capped systemd user units (`scripts/capped.sh`; `systemctl --user list-units
'authbc-*'`), logs in `~/.cache/authbc-logs/`.*

| ID | State | What is known |
|---|---|---|
| A1 | stage 1 done (430 runs); **stage 2 running** (4 230 runs, `prereg-A1-stage2`) | d_ref = 215 m. Stage 1: ratio ≈ 3.3–3.7 everywhere; at R = 1 000 m the design crosses with ≈ 8 neighbours |
| A2 | map ✔, age part ✔ (all held); **ns-3 validation frozen** behind stage 2, resumes automatically | one lost frame, not two, breaks the deadline |
| A3 | part 1 ✔; part 2 (traces) after A1 stage 2 | tolerable loss held; the margin rule fails in 5 of 192 bursty cells (interval); F86 |
| A4 | registered `prereg-A4`; **running** (120 runs, 10 seeds) | controller held V ≥ 0.951 on a development ramp after one definitional fix (disclosed) |
| A5 | ✔ | the window closes the delay-line attack; the plan's "2 hours" failed as predicted (75 min) |
| A6 | registered model: 3 of 9 lemmas verified, 6 not settled (1 GB heap). **After registration:** lemma 5 in a small timed model — attack trace found without the window, gone with it, bounded-delay freshness proven; lemmas 1–4 in a clock-free model, **running** | the change of model is reported as one |
| A7 | registered `prereg-A7`; code + tests ✔; timing waits for pi-B (H4) | the tag costs 3 % of capacity (not 2 %) |
| A8 | registered `prereg-A8`; Rust codec ✔; **byte-identical to Python on 10 000 frames**; timing and energy wait for pi-B (H4, G22) | |
| A9 | registered draft (`predictions/A9.md`, not committed); flights need a quiet host (H7) | SIH flies all three airframes; fixed-wing needed two parameters (stated) |
| A10 | registered `prereg-A10`; schemes ✔ (tests); **queued** after A12 | |
| A11 | registered `prereg-A11`; **queued** after A10; NR sidelink not run (H6) | the no-fit model puts the ratio at 3.4–3.8 on every PHY, not 1.7–4.3 |
| A12 | registered `prereg-A12`; **running** | |
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
