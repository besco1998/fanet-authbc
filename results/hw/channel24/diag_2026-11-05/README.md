# Diagnostics after W1d's S0 (2026-11-05) — disclosed, outside the registration

Run after S0 stopped the campaign (`predictions/W1d.md`, outcome; F121). Nothing here is scored.

* `pi3/` — the Pi 3 alone in the ad-hoc cell on channel 11, 600 frames/s of 145 B offered.
  * `diag_pi3.sh`: one 15 s run with `vmstat` and `top`. CPU or radio?
  * `diag2_pi3.sh`: four 15 s runs — power save as found / off / off with Bluetooth blocked / as
    found. Does either set the rate?
  * `diag3_pi3.sh`: after nine idle minutes, eight 10 s runs back to back with the SoC
    temperature. Does the rate decay with sending?
  * Each run's `*.json` is `bcast_tx.py`'s output; `diag2.log` and `diag3.log` hold one line per run.
* `blue1/`, `blue2/` — the Blues' monitor interfaces.
  * `sniffer.log` and `sniff_*.pcap` (empty): `hw/channel/run_sniffer.sh` through S0, channel 11.
  * `montest.sh` / `.log` (Blue 1): `wlan0` itself as a monitor, channel 1, 10 s.
  * `montest2.sh` / `.log` (Blue 1): a monitor interface beside a connected `wlan0`, channel 1,
    10 s.
