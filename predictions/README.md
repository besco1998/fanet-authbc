# Registrations — every prediction made before its experiment ran

*One folder for all of them since 2026-11-01. The eight older files lived in `docs/` and were moved
here unchanged (`git mv`, so `git log --follow` shows each file's first commit). **A registration is
never edited:** its commit date, set before the run, is the evidence. Outcomes are appended below a
line in the same file. Paths written inside the older files (for example `docs/NMAX_DIRECT_EXPECTATIONS.md`)
are kept as they were written; the files are now here.*

**How to read a row.** *Registered* is the commit that added the file, before any run. A-items and
S01 also carry a git tag, `prereg-<ID>`, at that commit. *Outcome* is a one-line summary; the
file's own outcome section and `thesis/appB_preregistrations.tex` give the full verdict, misses
included.

## Before the reviewer revision (2026-08 to 2026-10-09)

| File | What it predicted | Registered | Outcome |
|---|---|---|---|
| `DIRECTION_C_SURVEY_PROTOCOL.md` | a survey protocol for LoRa simulation papers (Direction C) | `eb3eda5`, 2026-08-07 | sweep log appended 2026-08-08: n = 14 achieved against a target of 56 |
| `DR6_EXPECTATIONS.md` | LoRa DR6: batch, duty interval, capacity | `ca8fd1c`, 2026-08-07 | batch and interval confirmed; capacity derived, **not simulated** (run aborted), and labelled so |
| `M4_EXPECTATIONS.md` | the crossing at a 174 B frame | `84adb92`, 2026-08-28 | crossing 2.367 inside 2.1–2.8, **confirmed**; the directional prediction was untestable, a flaw stated in the file |
| `NMAX_DIRECT_EXPECTATIONS.md` | the 802.11 capacity search and its follow-ups F1–F7 | `6f82599`, 2026-10-06 (follow-ups added later, each before its runs) | stage 1: the single-ceiling prediction **failed** (F50). F1 and F1b: the mean held, both spread predictions failed (`docs/LOGBOOK.md` 2026-10-06). F2: the airtime line, 7 of 7 within 3.4 %. F3: stream schemes. F4: sources agree. F5: contention model, 6 of 6. F6: batches 2/3/8, 6 of 6. F7: capture, 4 of 4 |
| `PX4_LOGS_EXPECTATIONS.md` | record sizes in twelve public PX4 flight logs | `e4e3cdf`, 2026-10-06 | key-record size **missed** by 0.02 B (F52); the 50 Hz delta untestable from 5 Hz logs |
| `CONTENTION_HW_EXPECTATIONS.md` | contention between two real radios | `456a4e7`, 2026-10-09 | held at two loads, **failed** at the third (F73) |
| `CONTENTION_HW_FRAMEBURST_EXPECTATIONS.md` | the effect of turning frame bursting off | `06f1bfa`, 2026-10-09 | **all four predictions failed** (F75) |
| `CONTENTION_HW_SATURATED_EXPECTATIONS.md` | two saturated radios against the standard's rule | `9a85afa`, 2026-10-09 | **held**: 12.4 % lost against 11.8 % (F76) |

## The reviewer revision, A1–A17 (`docs/revision/REVISION_PLAN.md`)

Full states: `docs/revision/STATUS.md`.

| File | Experiment | Registered | Outcome |
|---|---|---|---|
| `A1.md`, `A1-dref.md`, `A1-stage2.md` | a spread swarm with hidden stations | `d4bf273` / `b2b6ae6` / `c7f05c7`, 2026-10-19/20 | the ratio held at 3.46–3.58; the neighbour-count bracket 10–40 **missed** (8.7) |
| `A1-motion.md` | every node moving on its own | `13c406e`, 2026-10-21 | held: ΔV ≤ 0.0005, ratio 3.57–3.63 |
| `A2.md` | the design map and age under loss | `b2b6ae6`, 2026-10-19 | held, within 1.05 % of the model; the stated cause of the age tail was wrong |
| `A3.md` | the verifiability margin | `527ba59`, 2026-10-19 | the rule failed by its interval in 5 of 192 cells, all bursty |
| `A4.md` | a controller choosing the batch at run time | `1469c2b`, 2026-10-20 | **failed** (fails at 76 nodes, not within 5 % of fixed b = 4) |
| `A4b.md` | a second controller, margin 0.02 | `a36489a`, 2026-10-21 | failure points held; the window share **missed** (93 %) |
| `A5.md` | the timestamp acceptance window | `04658f3`, 2026-10-20 | held; the plan's "two hours" failed, as the finer prediction said (75 min) |
| `A6.md` | the protocol in Tamarin | `3b17a90`, 2026-10-20 | proven across three models; the registered model settled 3 of 9 lemmas, 15 of 19 predicted verdicts missed |
| `A7.md` | flooding and the group MAC | `6dc683f`, 2026-10-20 | outsiders stopped, insiders not; the registered rates **missed** |
| `A8.md` | the Rust receiver and sender | `3a9e85a`, 2026-10-20 | held (290 nodes per core by Eq. (4)); energy ranges missed low |
| `A9.md`, `A9-fast.md` | richer records, three airframes | `aa3b86d` / `89cfd6f`, 2026-10-20/22 | saving and ratio held; key-record and fixed-wing delta sizes **missed** |
| `A10.md` | stream schemes against the deadline | `b7e1ae3`, 2026-10-20 | held; three finer predictions missed |
| `A11.md` | other 802.11 PHYs | `b7e1ae3`, 2026-10-20 | the rise held; the registered span **failed** (3.39–3.80) |
| `A12.md` | few fast radios standing for many slow ones | `8a3d302`, 2026-10-20 | held (not in the paper: it only prepared a hardware test) |
| `A13.md` | deferred batch verification | `3b06582`, 2026-10-20 | held (629 nodes per core); the 170 ms bound missed by 1 ms |
| `A15.md` | Falcon-512 in the frame | `50e715b`, 2026-10-20 | capacities held; "a larger ratio" **failed** (3.5, as with Ed25519) |
| `A16.md` | the post-mission ledger audit | `baeb1d2`, 2026-10-20 | held: both planted faults found, no false finding |
| `A17.md` | ADS-B, Remote ID and V2X CAM | `fd128fd`, 2026-10-20 | held |

## The review of 2026-10-27

| File | Experiment | Registered | Outcome |
|---|---|---|---|
| `S01.md` | capacity at 97 % delivery | `3149f70`, 2026-10-27 | **held**: 27.6 and 97.3 nodes, both within ±3 % of the contention model; ratio 3.5 |

## Open items run later

| File | Experiment | Registered | Outcome |
|---|---|---|---|
| `G27.md` | which rule for a radio's own queued frames fits the one-sender spacing, two saturated senders and F73's 36 windows; found the frozen model's self-collision defect first (F114) | `5ec2eda`, 2026-11-03 (no tag; a stray tag pushed by mistake at `f06b55a` was deleted, see the file) | **no rule survives**: with frame burst on none passes the saturated screen; with it off the one that does misses F73 at 211 frames/s; 5 of 5 expectations held. F76's reading withdrawn (F115) |
| `W4a.md` | a record size no telemetry of the schema can exceed (schema and physical bounds, real frames), and AUTHBC's capacity and ratio there (main open item W4) | tag `prereg-W4a`, 2026-11-05 | **held, 5 of 5**: 2.75× at the schema's largest records against per-record at its smallest; break-even needs 223 B deltas (F117) |
| `W1a.md` | whether AUTHBC's capacity ratio survives the contention windows of real cards (W = 4, 8; ns-3) and the rules calibrated on our chip (model) (main open item W1) | tag `prereg-W1a`, 2026-11-05 | **held**: ns-3 ratio 3.48 (W = 4) and 3.52 (W = 8) against 3.53; crossings within 1 % of the model (F116) |
| `W1b.md` | the contention model at 802.11b, 1 Mb/s, against ns-3, and A12's equivalence at five stations (Phase 0 of the 2.4 GHz campaign; main open item W1) | tag `prereg-W1b`, 2026-11-05 | **held, 3 of 4 in full**: crossings within 0.7 % of the model, ratio 3.20; the equivalence holds up to the crossing; one split missed in overload (ns-3's 500 ms queue limit) (F119) |
| `W1c.md` | five radios at 2.4 GHz (two Pi 4, a Pi 3 B, two BeagleBone Blue): contention at N = 2–5 and the capacity ratio measured on hardware, at 802.11b 1 Mb/s (Phase 0 of the 2.4 GHz campaign) | tag `prereg-W1c`, 2026-11-05 | **not run; superseded by W1d**: the Blues have no ad-hoc mode (F120) |
| `W1d.md` | three ad-hoc radios at 2.4 GHz, channel 11 (pi-A, pi-B, Pi 3): rate check, background, contention for the three pairs and the trio against W1c's registered model rows | tag `prereg-W1d`, 2026-11-05 | **stopped at S0 by its rule**: the Pi 3 failed the rate check (4.9 ms against 1.9–2.6); background 0.09 % and both Pi 4 (1 946 µs, short of the standard) held; S1 not run (F121). Repeated with the Pi 3 moved beside the Pi 4s and one Blue unplugged, it ran at 2.5 ms: the cause was outside it, and F121's reading is withdrawn (F122) |
| `W1e.md` | three ad-hoc radios side by side at 2.4 GHz, channel 11 (pi-A, pi-B, Pi 3, 10–15 cm apart, Blues unplugged): W1d's contention windows unchanged, between one rate check per board before and one after; void unless all six are in the band | tag `prereg-W1e`, 2026-11-05 | **valid session; 11 of 12 contention points held** (A–B at 0.50 over by 0.0075 points, 1.44× against 1.40×); loss above the model at low load, below at high, in every group (F123) |
| `W1f.md` | four ad-hoc radios at 2.4 GHz, channel 11 (pi-A, pi-B, Pi 3 and the TP-Link on Blue 2 at `rate_ctl` 1 Mb/s): rate checks before and after, N = 4 contention at W1c's rows, and the capacity-equivalent points of both designs (four boards, f_b = (N_eq − 1)·f₀/3) — **the AUTHBC / per-record ratio on hardware**, model 3.304 (band 2.974–3.635); void on the bracket, the background, or node 4 not in the Pis' cell at 1 Mb/s | tag `prereg-W1f`, 2026-11-05 | **valid; contention 3/3; AUTHBC crossing 31.57 vs 29.50 (+7.0 %), held; per-record not determined, so the ratio is not measured** (< 3.32); loss depends on the sender: capture by the stronger one (F127) |
| `W1g.md` | four radios **balanced** (TP-Link at 90 cm, pi-B at 8 dBm; calibration `results/hw/channel24/w1g_cal_2026-11-06/`), the grid moved to bracket both crossings (A29–A32, P9–P9.75): the ratio on real radios with capture present; W1f's bands unchanged (ratio 2.974–3.635); void unless balanced (≤ 1.5× at A31) and pi-B at 8 dBm — a deviation from `PROTOCOL.md`, approved by Mohamed | tag `prereg-W1g`, 2026-11-06 | **VOID**: the balance failed (spread 5.08×; ⚠️ ~~the TP-Link's transmit strength changed between boots~~ corrected: cause undetermined; Blue 2 was later found displaced, when unknown) and the Pi 3's rate check after the session was 2 780 µs (band ≤ 2 600); neither curve crossed 0.95 inside the grid (F128) |
| `W1h.md` | **W1g's session, scored only on an attempt whose own gate windows show balanced senders**: R1–R4, four gate windows at W1g's A31 line, W1g's capacity block verbatim, R1–R4; the gate (spread ≤ 1.5×, rate checks before in band, node 4 joined) is read after each attempt, since no board can be reached during a session (F129); up to three attempts, the first GO is the session, scored by `w1g.score` unchanged against W1f's bands (ratio 2.974–3.635); the Pis are not rebooted (their first ad-hoc session after a boot runs at 6 Mb/s, F129) | tag `prereg-W1h`, 2026-11-06 | **VOID** on V5: the session's A31 spread 1.549× (rule ≤ 1.5×; its gate read 1.433×); all other conditions held. Reported, not scored: crossings 30.99 / 9.33, ratio 3.32 (model 3.30). Two deviations approved by Mohamed: Blue 2 at 120 cm, pi-A at 8 dBm (F130) |
| `W1i.md` | **an adaptive preflight tunes the Pis' powers to within 1.25×** (registered rule `next_powers`: too-strong Pis down one rung, held Pis up when the TP-Link is too strong or they are weakest; ladder auto/1000/800/600/400 mBm; at most 5 preflights; check 7: each sender alone ≥ 97 %), **then one long run at those powers, fixed** (`plan_w1h.txt`, W1h's gate); V5 still 1.5×, V6 for every held Pi; W1f's bands (ratio 2.974–3.635); W1h's void reading (3.32) disclosed | tag `prereg-W1i`, 2026-11-06 | pending |
