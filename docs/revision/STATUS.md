# Revision status — one row per item of `docs/AUTHBC Revision Plan.md`

*Updated 2026-10-20. Branch `p11-reviewer-revision`. Registrations are `predictions/<ID>.md`,
tagged `prereg-<ID>` at the commit that registered them; outcomes are appended to the same file
below a line. Rules: `docs/revision/EXECUTION_PLAN.md`. Long jobs run through
`scripts/capped.sh` (memory-capped systemd units) since WSL ran out of memory on 2026-10-20.*

| ID | State | Registration | What is known |
|---|---|---|---|
| A1 | stage 1 running (5 seeds, places the grids) | `prereg-A1`; d_ref measured: **215 m** | stage 2 grids to be committed before stage 2 |
| A2 | model map done; age part **done**; ns-3 validation running (restarted after the crash) | `prereg-A2` | map: b* and ratios over 56 cells (6 infeasible); age: all registered statements held; one lost frame, not two, breaks the deadline |
| A3 | part 1 **done**; part 2 (ns-3 traces) waits for A1 stage 2 | `prereg-A3` | tolerable loss held (0.0423 at b = 4, 0.0482 at b = 2); the plan's margin rule fails in 5 of 192 bursty cells through the interval; F86 (bootstrap undercoverage) |
| A4 | scenario built (`ns3/authbc-adaptive.cc`), smoke-tested; registration being written | — | prior art: ETSI DCC / LIMERIC adapt rate from the busy ratio; A4 adapts the batch and keeps the record rate |
| A5 | running | `prereg-A5` | the plan's drift arithmetic is off by two (144 ms/h, not 72): disputed beforehand |
| A6 | registered model: lemma 1 **verified**; the sanity lemma and `no_replay` exhaust a 1 GB heap; remaining lemmas running | `prereg-A6` | restructured clock (persistent ticks + "latest tick" restriction) verifies the sanity lemma in 19 steps — a change after registration, to be reported as such |
| A7 | not started (code next; Pi off — H4) | — | |
| A8 | not started (Rust toolchain; Pi off — H4) | — | |
| A9 | not started (PX4 SITL, heavy CPU) | — | |
| A10 | not started (needs a trace option in the published scenario, after A2 frees the binary) | — | |
| A11 | not started | — | ns-3.48 has no OCB MAC: 802.11p PHY under the ad-hoc MAC (stated substitution) |
| A12 | registered; ns-3 runs queued | `prereg-A12` | model: the (N−1)/N correction leaves a positive residual up to +0.006 at 5–8 nodes |
| A13 | not started (depends on A7, A8) | — | |
| A14 | not started | — | |
| A15 | registered; ns-3 running; timing waits for a quiet host | `prereg-A15` | the no-fit models put the Falcon ratio at 3.5 (as Ed25519), not the plan's 3.9 |
| A16 | built and tested; one-hour mission running | `prereg-A16` | kept storage 43.25 B/record (0.97 GB/h for 124 neighbours); decoded records 134 B |
| A17 | **done** | `prereg-A17` | held; the CAM deadline is not in its standard |
| B1–B5 | not executable here (purchases, flights) | — | open item H3 |

## The crash of 2026-10-20 01:02

WSL ran out of memory: two Tamarin proofs (5.7 GB, growing), the test gate (4.2 GB), ten ns-3
runs (3.4 GB) and the editor (2.4 GB) against 14 GB + 4 GB swap; the kernel's OOM killer then
took WSL's own init processes (`journalctl -b -1`: "init.scope: Failed with result
'oom-kill'"). Lost: ~2.5 h of A2 runs (the driver checkpointed in submission order), the A5
run, both Tamarin runs, and everything under `/tmp`. Fixed: memory-capped units, completion-
order checkpoints, logs and the clean gate under `~/.cache`.
