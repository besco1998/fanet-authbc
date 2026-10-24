#!/usr/bin/env bash
# Run a long job under a memory cap, so that it cannot take WSL down with it.
#
# WHY. On 2026-10-20 the VM ran out of memory (journal of that boot: "Out of memory: Killed
# process … python3.12", then "init.scope: Failed with result 'oom-kill'"): two Tamarin proofs
# (5.7 GB and growing), the frozen test gate (4.2 GB), ten ns-3 runs (3.4 GB) and the editor
# (2.4 GB) against 14 GB of RAM and 4 GB of swap. The kernel's killer then took WSL's own
# init processes, which is what a "crash" looks like from Windows. Nothing had a cap.
#
# WHAT. Every job runs as a systemd user service in `authbc.slice`. The slice holds all of
# them to SLICE_MAX (default 8G, plus 1G of swap), leaving ~6 GB for WSL, the editor and the
# system; each job also has its own cap. Past a cap the kernel kills inside that cgroup only.
# A service also survives a closed terminal or editor, which `nohup setsid` was used for.
#
#   scripts/capped.sh NAME MEMMAX LOGFILE -- COMMAND [ARGS...]
#   scripts/capped.sh a2-ns3 4G /tmp/a2.log -- .venv/bin/python ns3/run_nmax_direct.py …
#
# Watch:  systemctl --user status authbc-NAME     Stop: systemctl --user stop authbc-NAME
# Slice:  systemctl --user status authbc.slice    (memory in use against the cap)
set -euo pipefail
if [[ $# -lt 5 || "$4" != "--" ]]; then
    echo "usage: $0 NAME MEMMAX LOGFILE -- COMMAND [ARGS...]" >&2
    exit 2
fi
name="$1"; mem="$2"; log="$3"; shift 4
slice_max="${SLICE_MAX:-8G}"
systemctl --user set-property --runtime authbc.slice \
    MemoryMax="$slice_max" MemoryHigh="$slice_max" MemorySwapMax=1G
mkdir -p "$(dirname "$log")"
exec systemd-run --user --quiet --collect \
    --unit="authbc-$name" --slice=authbc.slice \
    -p MemoryMax="$mem" -p MemorySwapMax=512M \
    -p StandardOutput="append:$log" -p StandardError="append:$log" \
    --working-directory="$PWD" --setenv=PATH="$PATH" --setenv=HOME="$HOME" \
    -- "$@"
