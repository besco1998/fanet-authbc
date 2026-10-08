#!/usr/bin/env bash
# Build and run the Ed25519 batch-verification timing (docs/OPEN_ITEMS.md G19).
#
#   hw/ed25519_batch/build.sh            fetch the pinned library, build, run, write the CSV
#
# The library is ed25519-donna (public domain), fetched at a pinned commit into a git-ignored
# directory; nothing of it is kept in this repository. Output:
#   results/hw/ed25519_batch.<host>.csv
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PIN=8757bd4cd209cb032853ece0ce413f122eef212c
SRC="$HERE/.donna"
REPS="${REPS:-300}"

if [ ! -f "$SRC/ed25519.c" ]; then
  git clone -q https://github.com/floodyberry/ed25519-donna "$SRC"
fi
git -C "$SRC" checkout -q "$PIN"
[ "$(git -C "$SRC" rev-parse HEAD)" = "$PIN" ] || { echo "FAIL: library is not at the pinned commit" >&2; exit 1; }

# SHA-512: OpenSSL's if its headers are installed, else the library's own reference code.
if echo '#include <openssl/sha.h>' | "${CC:-gcc}" -E - >/dev/null 2>&1; then
  HASH_FLAGS=""; HASH_LIBS="-lcrypto"; HASH="openssl"
else
  HASH_FLAGS="-DED25519_REFHASH"; HASH_LIBS=""; HASH="reference (slow) sha-512"
fi
# The batch coefficients' randomness comes from bench_batch.c (/dev/urandom).
: > "$SRC/ed25519-randombytes-custom.h"
"${CC:-gcc}" -O3 -o "$HERE/bench_batch" "$HERE/bench_batch.c" "$SRC/ed25519.c" -I"$SRC" \
  -DED25519_CUSTOMRANDOM $HASH_FLAGS $HASH_LIBS

HOST="$(hostname -s)"
OUT="$REPO/results/hw/ed25519_batch.$HOST.csv"
if [ -r /proc/device-tree/model ]; then MODEL="$(tr -d '\0' </proc/device-tree/model)"; else MODEL=unknown; fi
GOV="$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo NA)"
{
  echo "# run=ed25519_batch"
  echo "# device_model=$MODEL"
  echo "# device_host=$HOST"
  echo "# device_governor=$GOV"
  echo "# machine=$(uname -m)"
  echo "# compiler=$("${CC:-gcc}" --version | head -1)"
  echo "# library=ed25519-donna@$PIN"
  echo "# sha512=$HASH"
  echo "# message_bytes=200 signatures=64 repetitions=$REPS"
  echo "# run_utc=$(date -u +%Y%m%dT%H%M%SZ)"
  "$HERE/bench_batch" "$REPS"
} > "$OUT"
echo "wrote $OUT"
grep -v '^#' "$OUT"
