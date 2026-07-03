# docs/status

Per-lane status & handoff files: `lane<N>.md` (one file per lane — never shared, so
parallel lanes never collide; docs/07 §3, docs/06 §8).

Each session appends a **§Handoff** block (format in `docs/prompts/T_TEMPLATES.md §Handoff`)
so any fresh session resumes in <1 minute via **§Resume**.
