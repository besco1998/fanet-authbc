#!/bin/bash
# Before each window: is this board's radio still in the cell? Mohamed, 2026-11-23: "if it locks up
# during the session, stop that board's windows and record it" (docs/DECISIONS.md). pi-B's chip
# locked once, in the revert after W1p (2026-11-22); a locked chip sends nothing and may drop out of
# the cell, so a board that ran on would only add windows with no frames of its own.
#
#   chip_check.sh <freq MHz> <frames the interface sent in the previous window, or - if not a sender>
#   -> exit 0, nothing printed: carry on;   exit 1, the reason on stdout: stop this board's windows
#
# IW overrides the iw binary (tests). Reads only; changes nothing on the board.
set -u
FREQ="$1"
SENT="${2:--}"
IW="${IW:-/usr/sbin/iw}"

info=$("$IW" dev wlan0 info 2>&1)
if ! grep -q "type IBSS" <<<"$info"; then
    echo "not in the ad-hoc cell: $(tr -s ' \t\n' ' ' <<<"$info")"
    exit 1
fi
if ! grep -q "(${FREQ} MHz)" <<<"$info"; then
    echo "not on ${FREQ} MHz: $(tr -s ' \t\n' ' ' <<<"$info")"
    exit 1
fi
if [ "$SENT" != "-" ] && [ "$SENT" -eq 0 ] 2>/dev/null; then
    echo "sent nothing in the previous window, though it was a sender"
    exit 1
fi
exit 0
