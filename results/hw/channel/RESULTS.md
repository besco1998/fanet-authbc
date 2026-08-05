# Hardware 802.11 broadcast channel measurement — results

*Measured 2026-08-05 on the two-Pi rig (`authbc-pi4a` → `authbc-pi4b`), ad-hoc IBSS, one
transmitter. Raw artifacts: `adhoc_sweep_5ghz.csv`, `adhoc_sweep_2g4.csv`, and the per-node session
logs in `5g_pi-{a,b}/` and `2g4_pi-{a,b}/`.*

**This closes the longest-standing gap in the project: every 802.11 capacity claim was simulation.
Two of them now have a hardware anchor.**

---

## Law-6 record: what was predicted BEFORE the run

Stated in advance, before the 5 GHz sweep was launched:

> at 6 Mb/s a 1400 B frame occupies ≈1.99 ms including DIFS/preamble/mean-backoff, so capacity
> ≈ **500 fps**; Phase A at 100 fps ≈ 20 % utilisation should give **≥99 % delivery, 0 duplicates**;
> the Phase B knee should fall between **400 and 600 fps**, with `tx_dropped` ≈0 below it.

| quantity | predicted | measured | error |
|---|---|---|---|
| airtime per 1400 B broadcast frame | 1.99 ms | **1.995 ms** | **0.36 %** |
| broadcast capacity | ≈500 fps (503) | **501.19 fps** | **0.36 %** |
| delivery at the 100 fps operating point | ≥99 % | **99.977 %** | held |
| duplicates | exactly 0 | **0** | held |
| `tx_dropped` below the knee | ≈0 | **0** | held |
| knee location | 400–600 fps | **~501 fps** | held |

Every prediction held. The airtime figure is the load-bearing one: it is an **independent hardware
confirmation of the 802.11a timing model** that the Bianchi and Ma & Chen capacity numbers rest on.

---

## 1. Link loss at the operating point — 5 GHz, 802.11a

Eight repeats, 100 fps × 1400 B (1.12 Mb/s ≈ 21 % utilisation), 22 s each.

| | |
|---|---|
| pooled | **17 596 / 17 600 delivered = 99.9773 %** |
| loss `p` | **2.273 × 10⁻⁴** (0.0227 %) |
| per-window | mean 99.977 %, min 99.954 %, max 100.000 %, **σ = 0.024 pp** |
| duplicates | **0** across all windows |
| local `tx_dropped` | **0** across all windows |

**The loss is on air, not in the stack — and that is measured, not assumed.** In each window that
lost a frame, the receiver's NIC counter and the application count agree exactly (e.g. window 01:
2200 transmitted, `rx_frames_nic` 2199, `received_unique` 2199). So the frame was lost between the
radios, not dropped in a socket buffer. This separation is the whole reason the interface counters
were added.

### What this does and does not license

**Does:** give `p` a hardware floor. `docs/OPEN_ITEMS.md` B4 justified the `p = 0.05` grid by
mechanism (broadcast has no ACK, so the receiver sees the raw channel error rate) and argued the
grid is 20–100× more pessimistic than TS 22.125's 99.9 %. Measured, benign-case loss is
**2.3 × 10⁻⁴**, i.e. the grid is conservative by **≈220×** here. B4's reasoning is corroborated.

**Does not:** justify lowering `p`. This is a two-node, ~1–2 m, line-of-sight, stationary,
interference-free measurement — the **best case by construction**. It bounds the optimistic end of
the grid and nothing else.

⚠️ **It also cannot validate Ma & Chen.** That model describes *N contending stations*; this rig has
one transmitter and therefore zero contention. Claiming otherwise would be exactly the category
error this project's audit has spent its time correcting. The contention model remains
simulation-only.

---

## 2. The saturation knee — and why the 2.4 GHz run had to be discarded

| offered | achieved | on air | delivered |
|---|---|---|---|
| 50 fps | 50.00 | 0.56 Mb/s | 100.000 % |
| 100 fps | 100.00 | 1.12 Mb/s | 100.000 % |
| 200 fps | 200.00 | 2.24 Mb/s | 99.917 % |
| 300 fps | 300.00 | 3.36 Mb/s | 99.861 % |
| 400 fps | 400.00 | 4.48 Mb/s | 99.875 % |
| 600 fps | **501.19** | 5.61 Mb/s | 99.127 % |
| 900 fps | **501.07** | 5.61 Mb/s | 98.538 % |

The interface tracks the offered rate exactly up to 400 fps and then pins at **≈501 fps / 5.61 Mb/s**
regardless of demand. That ceiling is the 6 Mb/s basic rate plus per-frame overhead.

### ⚠️ The 2.4 GHz run measured saturation and was nearly reported as channel loss

The first sweep ran on 2.4 GHz channel 1 and produced a tidy-looking **97.45 % delivery** with
σ = 0.196 pp over eight windows. It is in `adhoc_sweep_2g4.csv` and it is **not a channel-loss
measurement**:

* every offered rate from **100 to 1600 fps** produced the same ~85 fps / 0.96 Mb/s on air;
* 1400 B at the 802.11b **1 Mb/s basic rate** is 11.2 ms → ~85 fps. Broadcast always uses the lowest
  basic rate, and on 2.4 GHz that rate is 1 Mb/s;
* so the 100 fps "operating point" was actually **≈118 % of capacity**. The 97.45 % was
  over-subscription.

Two things caught it, both of which were in place *before* the run rather than invented afterwards:
the pre-stated prediction (which named 1 Mb/s explicitly as the risk if `mcast_rate` could not be
pinned), and the offered-load sweep. A single 100 fps run would have produced a plausible,
publishable, **wrong** number — the failure mode CLAUDE.md's status board warns about.

Moving to 5 GHz is not a workaround: 802.11a has no sub-6 Mb/s rate, so its basic rate is 6 Mb/s,
which is exactly what the NS-3 model assumes. **5 GHz is the band that makes hardware and simulation
comparable.**

---

## 3. Rig facts established along the way

| finding | evidence |
|---|---|
| `nmcli` cannot bring up an open IBSS cell here | attempt 1 (no security) → *"802.1X supplicant took too long to authenticate"*; attempt 2 (`key-mgmt none`) → *"Secrets were required"*, because in NM **`key-mgmt none` means static WEP**, not open. Raw `iw` with `nmcli dev set wlan0 managed no` works |
| brcmfmac rejects the `HT20` argument to `ibss join` | single-node probe: `2412 fixed-freq` rc=0, `2412 HT20 fixed-freq` **-22**, `5180 fixed-freq` rc=0, `5180 HT20 fixed-freq` **-22**, `5200 fixed-freq` rc=0. The band was never the limitation |
| brcmfmac rejects `iw set mcast_rate` | *"Operation not supported (-95)"*. The broadcast PHY rate cannot be pinned, so the band choice is the only control over it |
| brcmfmac ignores a requested fixed BSSID on 2.4 GHz | asked for `02:12:34:56:78:9a`; the nodes self-generated **different** BSSIDs and still exchanged traffic. On 5 GHz they merged correctly onto `52:d2:79:6c:1a:4d` |
| `peers: 0` does **not** mean the link failed | the 2.4 GHz run reported `peers: 0` and an empty `station dump` while delivering 4988/5000 frames. FullMAC drivers do not expose IBSS peers via nl80211 — an earlier diagnosis that read `peers: 0` as link failure was wrong |
| `net.core.rmem_max` is 208 KB by default | caps `SO_RCVBUF`; raised to 16 MB at runtime (not persisted) so receiver-side drops could be excluded at the top of the sweep |

## 4. Safety design — it was exercised, and it held

SSH arrives over `wlan0` and **`eth0` has no carrier on either Pi**, so every session severed its own
control path. Recovery was automatic on all five sessions (two failed 2.4 GHz attempts, one 2.4 GHz
sweep, one failed 5 GHz probe, one 5 GHz sweep):

1. a **600–800 s systemd deadman** running a full idempotent revert, and
2. a **900–1100 s reboot timer** as the guaranteed path — NetworkManager is enabled at boot and
   `preconfigured` has `autoconnect=yes`, both verified before first use.

⚠️ The deadman mechanism was **tested before being relied on**, and the first test *failed*: systemd's
`PrivateTmp` isolates `/tmp`, so a marker written there is invisible. Writing to `/home/pi` works.
**Never use `/tmp` in a deadman.**

No session ever required physical intervention, and neither reboot timer ever fired.
