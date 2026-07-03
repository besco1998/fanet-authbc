# T_TEMPLATES — Reusable Prompt Blocks
Paste these as needed inside any phase/session. Kept separate so phase prompts stay lean.

## §Audit  (run at every module and phase end; use the strongest model)
```
Adversarially audit <scope> against the specs it implements (cite docs/NN §M per item).
SCIENTIFIC ATTACK: exact formula/notation conformance; units; edge cases; statistical
compliance (docs/02 §8: seeds, ≥30 reps, bootstrap CI, >10% gap investigated); any path
where a reported number could be silently wrong; baseline fairness.
ENGINEERING ATTACK: determinism (same seed ⇒ same bytes), seed independence across
configs, error/exception paths, resource leaks, dead-code-elimination in benches, CI
honesty (does it truly run these tests?).
OUTPUT: append to docs/audits/p<N>.md a findings table [severity | evidence(cmd/output) |
root cause | fix]. Then IMPLEMENT the fixes and re-run the relevant tests. List anything
that should become a ⚠️ decision.
```

## §Validate-Results  (MANDATORY before committing ANY number, table, or figure)
```
Before you record/commit this result, prove it is trustworthy — a plausible-looking wrong
number is worse than a crash. Run this checklist and write the answers into the phase's
audit file (docs/audits/p<N>.md, "Results validation" subsection):
1. EXPECTATION: state, IN ADVANCE, the value/shape/sign/order-of-magnitude you expect and
   WHY (cite the theorem/anchor/hand-calc). Then compare to what you got.
2. SANITY GATES (any breach ⇒ STOP + investigate, do NOT record): value within the
   expected order of magnitude; monotonic where theory says monotonic; verify-time > sign-
   time never for the same scheme unless justified; throughput ≤ PHY bound; probabilities
   in [0,1]; CI width not ~0 and not absurdly wide; a metric that must equal a hand-
   computed value does.
3. CROSS-CHECK: reproduce ONE data point by an independent path (hand calc, a second
   method, or a tiny script) and show it matches.
4. AMBIGUITY RULE: if the result is surprising, borderline, self-contradictory, or you are
   unsure whether it is a real finding or a bug — do NOT average it away and do NOT assume
   it's fine. Reproduce it minimally, form hypotheses, and either (a) explain it with
   evidence as a genuine finding, or (b) treat it as a bug (§Debug). If still ambiguous
   after honest effort, raise it to Mohamed (§Decision-Request) — never bury it.
5. DETERMINISM: a result that changes across identical seeds is a bug, not noise — STOP.
6. PROVENANCE: seeds, config hash, env header present in the CSV; figure caption states
   them. If any is missing the result does not count.
Only after all six pass may you commit the number/table/figure.
```

## §Debug  (any failure — Law 3)
```
FAILURE: <paste exact command + full output>.
Per CLAUDE.md Law 3: (1) reproduce minimally (write the smallest repro). (2) form ≤3
hypotheses, each with the evidence for/against. (3) identify the ROOT cause (not a
symptom). (4) fix the root cause. (5) add a regression test that fails before / passes
after. (6) run the full suite. (7) write docs/failures/YYYYMMDD-<slug>.md using docs/06
§7 template. Do NOT proceed, skip, comment out, mock, or widen tolerance. If the fix
touches a FROZEN artifact (wire vectors, frozen configs) or a ⚠️ item: STOP and ask
Mohamed.
```

## §Resume  (start of any session continuing prior work)
```
Resuming AUTHBC. Read (in order): CLAUDE.md; docs/status/lane<N>.md (latest handoff);
the current phase prompt docs/prompts/<file>; and ONLY the docs sections that prompt's
CONTEXT BUDGET names. Then: run `git log --oneline -5` and `make test` to confirm the
green baseline; restate where the last session stopped, the open ⚠️ items, and the next
3 concrete steps; continue the phase. If make test is NOT green, that is your first task
(Law 3) before anything else.
```

## §Handoff  (write at end of every session/phase into docs/status/lane<N>.md)
```
## Handoff <date> — phase <P?> (<serial|lane N>)
- Green baseline: commit <hash>, tag <p?-done or none>, `make test` = PASS
- Done this session: <bullets>
- Frozen this session: <vectors/configs, if any> (D6)
- Open ⚠️ decisions awaiting Mohamed: <list or none>
- Next 3 steps: <ordered>
- Gotchas for next session: <env quirks, partial work, TODOs>
```

## §Decision-Request  (when hitting a ⚠️ item)
```
⚠️ DECISION NEEDED (<D#>). Context: <1–2 lines>. Options: A) … B) … (+trade-offs).
My recommendation: <X> because <reason>. Impact if deferred: <blocks/none>. I will not
proceed on this item until you answer; meanwhile I <continue other unblocked work / am
blocked>.
```

## §Sync-Merge  (integrator at a SYNC point — parallel mode)
```
SYNC-<k> merge. On main: for each ready lane branch: `git merge --ff-only lane<N>` (if
non-ff, rebase the lane first and re-run its `make all`). Then on main: `make all` must be
green; update CLAUDE.md status board; tag `sync-<k>`; push. Re-plan the next phase set per
docs/07 §2 and confirm ownership boundaries still hold.
```
