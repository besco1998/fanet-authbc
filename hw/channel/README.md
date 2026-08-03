# Hardware 802.11 channel validation — attempted 2026-08-04, **not yet working**

**Goal.** Every capacity claim in the paper is simulation. Two Pis exist; this measures real
broadcast delivery on an 802.11 ad-hoc link so the channel model has a hardware anchor.

## Status: BLOCKED on IBSS link formation. Two attempts, no data.

| attempt | change | result |
|---|---|---|
| 1 | `nmcli` ad-hoc, default security | `Error: 802.1X supplicant took too long to authenticate` — NM attempted 802.1X on an open cell. Link never formed, RX received **0** frames |
| 2 | added `802-11-wireless-security.key-mgmt none` | Still no IP on `wlan0`, `peers: 0`. Link never formed |

The chip is capable — `iw list` reports **IBSS** among supported modes on both Pis. `hw/SETUP.md:246`
already warned: *"brcmfmac IBSS can be finicky"*. That warning is now evidence, not folklore.

## ⚠️ Safety design — this part worked, and matters more than the result

SSH arrives over `wlan0` and **neither Pi has an ethernet cable** (`eth0 carrier=0`), so switching to
ad-hoc severs the only control path. Recovery had to be automatic:

1. **A systemd deadman armed *before* the switch**, restoring the AP profile after 600 s.
2. **The deadman mechanism was tested before being relied on** — the first test *failed*, because
   systemd's `PrivateTmp` isolates `/tmp`. Writing to `/home/pi` works. ⚠️ **Never use `/tmp` in a
   deadman.**
3. The session script self-reverts and **only disarms the deadman after confirming the LAN address
   is back**.

Both Pis recovered cleanly on both failed attempts. pi-b took ~20 s longer once, and returned on its
own. No physical intervention was needed at any point.

## What to try next

1. **Raw `iw` with NetworkManager set to unmanaged** for `wlan0` — NM may be fighting the mode
   change. `nmcli dev set wlan0 managed no`, then the `hw/SETUP.md:239-243` sequence verbatim.
2. **Check `wpa_supplicant` interference** — it is active on both and may re-associate to the AP.
3. **Fall back to infrastructure mode** and accept the AP in the path — ⚠️ this invalidates the
   *broadcast* MAC comparison (an AP relays and rate-limits broadcast), so it would measure a
   different thing and must not be reported as validating Ma & Chen.
4. **Plug in ethernet.** With `eth0` carrying SSH, `wlan0` becomes free to reconfigure and the whole
   class of lockout risk disappears. **This is the cheapest real fix and worth doing first.**

## Files
`bcast_tx.py` / `bcast_rx.py` — sequence-numbered UDP broadcast sender and counter, so loss and
duplication are distinguishable. `run_adhoc_session.sh` — the self-contained, self-reverting session.
