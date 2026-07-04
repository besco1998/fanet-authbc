#!/usr/bin/env bash
# sim_ns3.sh — build the authbc-sat scenario and run a 2-node both-modes smoke (docs/06 §2).
# Invoked by `make sim-ns3`. The full N-matrix (P6b) is a separate driver.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
NS3="$REPO/ns3/ns-allinone-3.41/ns-3.41"
PY="${PY:-$REPO/.venv/bin/python}"

if [ ! -x "$NS3/ns3" ]; then
  echo "ERROR: NS-3 3.41 not built at $NS3 — see ns3/README.md (download + ./ns3 build)."; exit 1
fi

cp "$REPO/ns3/authbc-sat.cc" "$NS3/scratch/authbc-sat.cc"
( cd "$NS3" && ./ns3 build authbc-sat >/dev/null 2>&1 || ./ns3 build >/dev/null )

OUT="$(mktemp -d)"
for mode in unicast broadcast; do
  ( cd "$NS3" && ./ns3 run "authbc-sat --mode=$mode --nNodes=2 --simTime=5 --seed=1 --outPrefix=$OUT/$mode" ) >/dev/null 2>&1
done

"$PY" "$REPO/ns3/parse_ns3.py" --stats "$OUT/unicast.stats" "$OUT/broadcast.stats" \
  --out "$REPO/results/raw/ns3_smoke.csv"
echo "=== ns3_smoke.csv ==="
cat "$REPO/results/raw/ns3_smoke.csv"
rm -rf "$OUT"
