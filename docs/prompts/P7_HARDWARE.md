# P7 — RPi4 HARDWARE CAMPAIGN  (COPY-PASTE WHOLE FILE)  — LANE 4 (opportunistic; scripts anytime)
Needs P0 (P7a scripts); p1a-code-done + hardware + ⚠️ D5 meter (P7b) · ends: tags p7a-done,
p7-done · Eight Laws · PLAN MODE.

You OWN ONLY: hw/**, results/hw/**. Re-read the repo CLAUDE.md.

CONTEXT BUDGET — read exactly: docs/04 §1 (micro suite to rerun) and §4 (hardware campaign +
energy protocol) · docs/06 §1 (governor/thermal/clock) · docs/03 §3 (the bench harness reused).

OBJECTIVE: hardware ground truth on 4× Raspberry Pi 4 — real crypto/encoding timings and
energy — fed back into the E4/E5 model layers to produce the paper's headline hardware tables.

KEY FACTS INLINED:
- RPi4, Raspberry Pi OS Bookworm 64-bit, headless, governor = performance
  (`cpufreq-set -g performance`; verify with `cpufreq-info`). Record `lscpu`, temperature,
  governor into results/hw/meta/ for every run.
- Energy protocol (external USB meter; ⚠️ D5 selects it, e.g. UM25C ≈ $30, one needed): CALIBRATE
  against a known resistive load first (note the reading). Then per operation: measure idle
  baseline power 60 s → run the op in a tight loop 60 s → energy/op = (P_loop − P_idle)·t_loop
  /n_ops; ≥5 repetitions; report median + CI. THERMAL GUARD: log temperature throughout;
  discard/flag any run showing throttling (Bookworm logs it; also watch for freq capping).
- Timing harness is the SAME as P1 (perf_counter_ns, GC off, warmup, ≥10k iters, checksum,
  bootstrap CI) — reuse it; only the platform changes. Expect RPi4 to be ~5–15× slower than
  x86 for these ops; a much larger/smaller ratio ⇒ investigate (governor? throttling?).

P7a STEPS (prep — no hardware needed; can run right after P0 in spare time):
1. hw/provision.sh (committed): OS deps, governor=performance, headless config, clock-sync note.
   hw/run_micro.sh: reruns the P1 micro suite with device metadata in CSV headers.
   hw/energy_protocol.md: the exact procedure inlined above. Tag `p7a-done`; push.

P7b STEPS (hardware present; ⚠️ D5 meter approved):
2. Provision 4× RPi4; capture lscpu/temps/governor to results/hw/meta/.
3. Rerun micro suite → hardware timing tables; compute x86/RPi4 ratios.
4. Energy: calibrate meter, then the per-op protocol → energy/op tables per scheme + encoding.
5. 2-node real-802.11 ad-hoc broadcast run of the golden scenario with MEASURED loss (not
   injected) — qualitative validation; state small-N honesty explicitly.
6. Feed back: rerun the E4/E5 MODEL layers with RPi4-measured (t_*, P_c, P_r) → hardware-
   grounded tables.
7. RESULTS VALIDATION (Law 6, §Validate-Results): state expected ranges (RPi4 ~5–15× x86;
   verify≥sign per scheme; BLS-verify ≫ Ed25519-verify still holds on ARM; energy/op positive
   and ordered sensibly — BLS most expensive); confirm NO run used throttled data (check the
   thermal logs); meter calibration within tolerance; determinism of timing medians across
   repetitions. Any anomaly ⇒ reproduce/hypothesize/explain-or-debug; ambiguous ⇒ raise to
   Mohamed. Write into audits/p7.md.
8. AUDIT P7b (§Audit): thermal throttling in ANY recorded run? meter calibration valid?
   clock/ntp effects? governor actually applied? Fix → `make all` where applicable → tag
   `p7-done` → push → §Handoff.

ACCEPTANCE: provision+micro+energy scripts committed & run · hardware tables with device
metadata + thermal logs · meter calibration noted · model layers re-run with measured params ·
results-validation in audits/p7.md · tags pushed.
