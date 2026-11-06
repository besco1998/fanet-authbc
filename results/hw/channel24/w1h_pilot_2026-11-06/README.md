# W1h pilot, 2026-11-06 morning. Disclosed, not scored

Purpose: prove the launch chain for W1h before registering it. The plan (`plan_pilot.txt`) is the
first 12 windows of the draft W1h plan: R1–R4, G31 ×4, then four quiet windows Q1–Q4. The draft
read the gate through Blue 2 during the quiet windows.

**`attempt0_blue2_not_back/`, 08:45**
* The Pis were rebooted and took the kit at the repo's hashes.
* Blue 2, rebooted at 08:46, never returned to the LAN: its radio scanned without finding the
  router (F129).
* Nothing was launched. Mohamed power-cycled it at about 09:00.

**`attempt/`, 09:06–09:17**
* The Pis were rebooted, and all four boards ran the 12 windows and reverted. Node 4 joined the
  Pis' cell at `FIXED CCK_1M`; pi-B was held at 8.00 dBm, then returned to auto.
* **The mid-session fetch failed:** no board can be reached during a session, since node 4's kit
  takes Blue 2's own radio off the air (`gate.log`; F129). The forced abort reached no board
  either. The plan simply ran to its end.
* **Found after collection (`session/`, gate run on the files):**
  * **The Pis broadcast faster than 1 Mb/s.** Each sent 600.0 frames/s of 145 B, with nothing late
    or dropped, and their rate checks read 1 666 µs, the sender's own period.
  * The diagnostics then showed this is the first ad-hoc session after a boot: 6 Mb/s
    (`../diag_rate_2026-11-06/`, F129).
  * So its gate readings (spread 2.64×; the Pis' loss about 1.2 % at G31) say nothing about W1g's
    setup at 1 Mb/s.

**What changed in W1h as a result** (Mohamed: "Revised W1h"):
* the gate is read after each attempt;
* the quiet windows are dropped;
* the Pis are not rebooted before attempts, and after any Pi boot one ad-hoc session runs first.
