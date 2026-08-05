# Hardware 802.11 channel validation — **WORKING** (2026-08-05)

**Goal.** Every 802.11 capacity claim in the paper was simulation. This measures real broadcast
delivery on an ad-hoc link between the two Pis, so the channel model has a hardware anchor.

## Status: measured. Results in `results/hw/channel/RESULTS.md`.

Headline: **99.977 % delivery** at the operating point (8 windows, σ = 0.024 pp, 0 duplicates,
loss `p` = 2.3 × 10⁻⁴), and a measured broadcast airtime of **1.995 ms/frame against 1.99 ms
predicted** — an independent hardware check on the 802.11a timing model.

⚠️ One transmitter ⇒ **zero contention**. This measures *link* loss and *airtime*. It **cannot**
validate Ma & Chen, which models N contending stations.

---

## How to run it

```bash
# from the repo root, with the Pis reachable on the LAN
START=$(( $(date +%s) + 45 ))
ssh pi@<pi-b> "cd /home/pi/authbc_channel && nohup setsid ./run_adhoc_sweep.sh rx $START 5180 full &"
ssh pi@<pi-a> "cd /home/pi/authbc_channel && nohup setsid ./run_adhoc_sweep.sh tx $START 5180 full &"
# ~7 minutes; both Pis leave the LAN and return by themselves
python3 analysis/reduce_channel_sweep.py --tx-dir results/hw/channel/5g_pi-a \
    --rx-dir results/hw/channel/5g_pi-b --out results/hw/channel/adhoc_sweep_5ghz.csv \
    --band "5GHz ch36 5180MHz (802.11a)"
```

`probe` instead of `full` runs a single short window — use it to check the link forms before
spending a seven-minute lockout window.

⚠️ **Pi addressing is not in git** (keys are gitignored, addresses are DHCP). At the time of writing:
pi-a = `authbc-pi4a` = 192.168.1.21, pi-b = `authbc-pi4b` = 192.168.1.20, keys at `hw/keys/pi-{a,b}/`.
There is no `~/.ssh/config`, so `ssh pi-a` will not resolve — use the IP.

## ⚠️ Use 5 GHz, not 2.4 GHz

802.11 sends broadcast at the **lowest basic rate**. On 2.4 GHz that is 802.11b's **1 Mb/s**, where a
1400 B frame occupies 11.2 ms — so ~85 fps saturates the medium and a 100 fps test already sits at
118 % of capacity. The first sweep did exactly that and produced a plausible-looking 97.45 % that was
**saturation, not channel loss**. On 5 GHz the lowest rate is 6 Mb/s, which is also what the NS-3
802.11a model assumes. `iw set mcast_rate` cannot fix this — brcmfmac returns *Operation not
supported (-95)* — so the band is the only control.

## Driver quirks, each verified by probe rather than inferred

| symptom | truth |
|---|---|
| `nmcli` ad-hoc fails with *802.1X supplicant took too long* | NM attempts 802.1X on an open cell |
| adding `key-mgmt none` then fails with *Secrets were required* | ⚠️ in NetworkManager **`key-mgmt none` means static WEP**, not "open". An earlier version of this file called `key-mgmt none` REQUIRED — that was wrong, and it is what broke attempt 2 |
| `ibss join ... HT20 ...` fails with `-22` | brcmfmac rejects the HT20 argument on **both** bands. Drop it |
| requested fixed BSSID ignored | on 2.4 GHz the nodes self-generated different BSSIDs and still talked; on 5 GHz they merged correctly onto one |
| `peers: 0`, empty `station dump` | FullMAC does not expose IBSS peers via nl80211. **Not** evidence of failure — verify with `ping` |

**The fix for every NM-related symptom is to take `wlan0` away from NetworkManager**
(`nmcli dev set wlan0 managed no` + `systemctl stop wpa_supplicant`) and drive it with raw `iw`.

## ⚠️ Safety — read before running

SSH arrives over `wlan0` and **`eth0` has no carrier on either Pi**, so going ad-hoc severs the only
control path. Every session therefore:

1. arms a **systemd deadman** (full idempotent revert) **before** touching the radio,
2. arms a **reboot timer** behind it — the guaranteed path, since NetworkManager is enabled at boot
   and `preconfigured` has `autoconnect=yes` (both verified before first use),
3. runs detached under `nohup setsid`, and
4. disarms both **only after confirming the LAN address is back**.

⚠️ **Never write a deadman marker to `/tmp`** — systemd's `PrivateTmp` isolates it. Not a guess: the
first deadman test failed exactly this way. Use `/home/pi`.

Five sessions have run, three of which failed to form a link. All recovered without physical
intervention and no reboot timer ever fired. **Plugging in ethernet would remove this entire class of
risk** and is still worth doing.

## Files
| | |
|---|---|
| `run_adhoc_sweep.sh` | the session: deadmen, join, N measurement windows on a shared clock, revert |
| `revert_adhoc.sh` | idempotent teardown; also what the deadman runs |
| `bcast_tx.py` / `bcast_rx.py` | sequence-numbered UDP broadcast sender / counter, so loss and duplication are distinguishable |
| `run_adhoc_session.sh` | the older single-window session, kept because `RESULTS.md` §2 cites its 2.4 GHz output |
| `../../analysis/reduce_channel_sweep.py` | pairs tx/rx windows → CSV with a provenance header |
