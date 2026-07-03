# docs/failures

Failure Reports: `YYYYMMDD-<slug>.md`, one per failure, using the `docs/06 §7` template
(WHAT / CONTEXT / REPRO / HYPOTHESES / ROOT CAUSE / FIX / REGRESSION GUARD / VERIFICATION).

Law 3 — **never bypass a failure.** A failing test / install / KAT / determinism check
stops the phase until root-caused, fixed, and guarded by a regression test.
