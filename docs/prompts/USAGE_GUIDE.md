# PROMPTS — USAGE GUIDE
How to run this project with Claude Code so the agent owns everything and you only make
decisions. Read once fully; then you'll mostly just paste prompt files.

## 0. One-time prerequisites (the ONLY manual setup — ⚠️ D0, ~10 minutes)
1. WSL2 Ubuntu 24.04 working; VSCode with the WSL extension.
2. Unzip this package to `~/authbc_package/` **inside WSL** (Linux filesystem).
3. `sudo apt install -y git gh` (if missing) → `gh auth login` (browser flow, once)
   → `git config --global user.name "..."` and `user.email "..."`.
4. Install/launch Claude Code per the official docs:
   https://docs.claude.com/en/docs/claude-code/overview
That's it. From here the agent creates the repo, the structure, and everything else.

## 1. The session model (how prompts map to Claude Code sessions)
- **One phase = one session** (default). Fresh session (or `/clear`) → paste the phase
  prompt file's entire contents → agent plans → you approve → it executes to the phase
  tag. This keeps context small, which keeps the agent sharp and cheap.
- **Autonomous chaining:** the Master Kickoff authorizes the agent to proceed to the
  next phase prompt (they live in the repo at `docs/prompts/`) after each green tag
  WITHOUT waiting for you — it stops only at ⚠️ decisions and failures. If a session
  grows long, the agent writes a handoff (T_TEMPLATES §Resume) so the next session
  continues seamlessly; you just open a new session and paste the Resume template.
- **Plan mode habit:** always start a phase in plan mode; approve the plan; then let it
  run. (Feature details/keybindings: see the official docs above.)


## 1b. What's new in v3 (why the prompts look self-sufficient)
- **Copy-paste self-contained:** each phase prompt inlines the exact numbers, formulas,
  APIs, and expected values it needs, so you can paste it cold and the agent rarely has to
  open other files (it still may, when a prompt says so). Less context hunting = fewer
  mistakes and lower cost.
- **Results-checking is now a LAW (Law 6):** every phase makes the agent state the expected
  value/shape IN ADVANCE, compare, run sanity gates, cross-check a point independently, and
  treat anything surprising/ambiguous as either an explained finding or a bug — never
  silently accepted. The mechanics live in T_TEMPLATES.md §Validate-Results.

## 2. Exact kickoff sequence (day 1)
1. Open VSCode → WSL → open folder `~/projects` (create it). Start Claude Code.
2. Paste **`00_MASTER_KICKOFF.md`** (whole file). The agent confirms it will fetch the
   package from `~/authbc_package/`, states the laws back, lists risks.
3. Paste **`P0_BOOTSTRAP.md`**. The agent creates the repo (local + GitHub via `gh`),
   copies docs+prompts+CLAUDE.md into it, scaffolds everything, proves a clean clone
   works, and stops at **⚠️ D7** asking you: serial or parallel?
4. Answer D7 (recommended: `2-lane` per docs/07 §5). The agent then either continues
   into P1 (serial) or prints the lane-setup checklist (parallel).

## 3. Running parallel lanes (if you chose 2-lane at D7)
- The agent's `scripts/lane.sh 2` creates the second worktree. Open
  `../fanet-authbc-lane2` in a **second VSCode window**, start a **second Claude Code
  session** there, paste `docs/prompts/P5_MODELS_OPTIMIZER.md`.
- Your main window's session runs Lane 1 (P1→P4). At each SYNC point (docs/07 §2) the
  Lane-1 session acts as integrator: merges, runs `make all`, tags, pushes.
- Never run two Claude Code sessions in the SAME directory (doc 06 §8).

## 4. Model selection (efficiency + quality)
Use the **strongest available model** for: the Master Kickoff, every phase's planning
step, every T_AUDIT run, and NS-3 debugging. Use a **fast model** for routine execution
once a plan is approved. Switch models per the official docs above (current model names
and the switch command are documented there — don't rely on memory).

## 5. What YOU do vs what the agent does
| You (only) | The agent (everything else) |
|---|---|
| D0 auth once · answer ⚠️ D1–D7 · approve phase plans · read audit files at tags · buy hardware (D5) · read Failure Reports when it stops | create repo & structure · write all code/tests/experiments · run everything · debug to root cause · write audits & handoffs · commit/push/tag · chain phases |

## 6. Efficiency rules already baked into the prompts (so you know why they look strict)
- **Context budget blocks:** each prompt names the exact files/sections to read and
  forbids reading anything else (prevents context bloat and drift).
- **Mechanical acceptance:** every criterion is a runnable command (`make test`, a diff,
  a tag) — no "looks done".
- **One module = one commit** (code+tests together); targeted tests while developing,
  full suite only at checkpoints.
- **Handoffs by default:** each phase ends by updating `docs/status/lane<N>.md`, so any
  fresh session resumes in <1 minute with T_TEMPLATES §Resume.

## 7. Monitoring from anywhere
`git log --oneline`, the tags (`p0-done`…), GitHub Actions status, `docs/status/`,
`docs/audits/`, `docs/failures/`. If the repo is green and tagged, it's real — the rules
make it impossible for the agent to fake progress silently.

## 8. If something goes wrong
The agent stops and produces a Failure Report (doc 06 §7) — read it, answer any question
it asks, and say "proceed". If a session was interrupted mid-phase: new session → paste
T_TEMPLATES §Resume → it reads the status file and continues. Never let it (or yourself)
"temporarily" skip a red test — that rule is the project's immune system.
