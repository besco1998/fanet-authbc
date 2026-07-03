#!/usr/bin/env bash
# scripts/lane.sh — create a parallel-execution git worktree for a lane (docs/07 §3–4).
#
# Usage: scripts/lane.sh <N>        N ∈ {2,3,4}
#   lane 2 -> P5_MODELS_OPTIMIZER   lane 3 -> P6_NS3_VALIDATION   lane 4 -> P7_HARDWARE
#
# Lane 1 is the MAIN working tree (integrator) and is never created here.
# Refuses to clobber an existing worktree directory or reuse an existing branch.
set -euo pipefail

usage() {
  echo "usage: scripts/lane.sh <N>   (N = 2 | 3 | 4)"
  echo "  lane 2 -> P5_MODELS_OPTIMIZER   lane 3 -> P6_NS3_VALIDATION   lane 4 -> P7_HARDWARE"
}

[ $# -eq 1 ] || { usage; exit 2; }
N="$1"
case "$N" in
  2) PROMPT="docs/prompts/P5_MODELS_OPTIMIZER.md" ;;
  3) PROMPT="docs/prompts/P6_NS3_VALIDATION.md" ;;
  4) PROMPT="docs/prompts/P7_HARDWARE.md" ;;
  1) echo "ERROR: lane 1 is the main working tree (integrator); not created by lane.sh."; exit 2 ;;
  *) echo "ERROR: lane must be 2, 3, or 4 (got '$N')."; usage; exit 2 ;;
esac

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "ERROR: run this from inside the fanet-authbc git repo."; exit 1; }
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

DIR="../fanet-authbc-lane${N}"
BRANCH="lane${N}"

# refuse to clobber an existing directory or branch
if [ -e "$DIR" ]; then
  echo "ERROR: refusing to clobber existing path: $DIR"; exit 1
fi
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "ERROR: branch '${BRANCH}' already exists; delete it or choose another lane."; exit 1
fi

git worktree add "$DIR" -b "$BRANCH"
ABS="$(cd "$DIR" && pwd)"

cat <<EOF

✅ Lane ${N} worktree ready.
   path:   ${ABS}
   branch: ${BRANCH}

Checklist (docs/07 §4, USAGE_GUIDE §3):
  1. Open the folder in a SEPARATE VSCode window:  code ${ABS}
  2. Start a NEW Claude Code session there — one session per worktree, never two per dir.
  3. Run 'make setup' once in that tree (the venv is per-worktree).
  4. Paste the phase prompt:  ${PROMPT}
  5. Edit ONLY this lane's owned paths (docs/07 §3). Shared files (Makefile, pyproject,
     CLAUDE.md, docs/) are P0-frozen — coordinate any change at a SYNC point.
  6. Merges to main happen only at SYNC points; the Lane-1 session is the integrator.
EOF
