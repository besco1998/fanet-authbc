# docs/audits

Per-phase audit files: `p<N>.md`. Written at every module and phase end
(`docs/prompts/T_TEMPLATES.md §Audit`, Law 5): a findings table
`[severity | evidence(cmd/output) | root cause | fix]`, then the fixes are implemented and
the relevant tests re-run. Law 6 results-validation lives here too (`§Validate-Results`).
