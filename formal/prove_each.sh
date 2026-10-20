#!/usr/bin/env bash
# Prove the lemmas of formal/authbc.spthy one at a time, each with a heap cap and a time limit,
# so that one lemma whose proof search does not end cannot exhaust the machine (the 2026-10-20
# OOM). Usage: formal/prove_each.sh [-D=TIME] ; output: one block per lemma on stdout.
set -u
cd "$(dirname "$0")"
define="${1:-}"
heap="${TAMARIN_HEAP:-1g}"
limit="${TAMARIN_SECONDS:-600}"
lemmas=$(grep -E '^lemma ' authbc.spthy | sed -E 's/^lemma ([A-Za-z0-9_]+).*/\1/')
for lemma in $lemmas; do
    if [[ -z "$define" ]] && grep -q "^lemma $lemma" <(sed -n '/^#ifdef TIME/,/^#endif/p' authbc.spthy); then
        continue                                  # a lemma that exists only with TIME
    fi
    start=$(date +%s)
    out=$(timeout "$limit" tamarin-prover $define --derivcheck-timeout=0 --prove="$lemma" \
          authbc.spthy +RTS -M"$heap" -RTS 2>&1)
    code=$?
    verdict=$(printf '%s\n' "$out" | grep -E "^  $lemma " | head -1)
    echo "$lemma | exit $code | $(( $(date +%s) - start )) s | ${verdict:-no verdict}"
done
