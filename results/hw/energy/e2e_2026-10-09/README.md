# Energy runs of 2026-10-09 — the second board, the second sensor

*Finding F79. What was expected of each run is in `hw/BENCH_SESSION.md`, committed in
`a38994f` before the first of them. This file is the record of how they were made.*

| | |
|---|---|
| board under test | `authbc-pi4b`, Raspberry Pi 4 B rev 1.4, Debian 12, Python 3.12.13, governor `performance` — the software of July |
| meter | INA219, 0.1 Ω shunt, **channel 2**; Arduino logger v2, 50 samples a second; sync wire on the board's GPIO17 |
| rig check | passed at 05:12 UTC (`../rig/rigcheck-20261009T051248Z.json`), 2½ minutes before the first run; no wire touched after it |
| a run | `hw/validate_energy_e2e.py`: idle for 60 s, then the pipeline back to back for 60 s, with the sync line high in both; five times (ten for the JSON row) |
| reduction | `hw/ina219_capture.py --reduce manifest_<run>.json samples_<run>.csv --channel 2` |
| table | `analysis/energy_runs.py` → `results/raw/energy_runs.csv` |

| run | command line after the script's name |
|---|---|
| `control_cbor` | `--batch 1 --encoding cbor --record-bytes 107 --t-enc-ns 50407 --p-cpu-w 0.749 --seconds 60 --reps 5` |
| `lean_b4` | `--format lean --batch 4 --t-frame-ns 868098.3 --p-cpu-w 0.749 --seconds 60 --reps 5` |
| `lean_b1` | `--format lean --batch 1 --t-frame-ns 379280.8 --p-cpu-w 0.749 --seconds 60 --reps 5` |
| `ajson_r10` | `--batch 1 --encoding json --record-bytes 191 --t-enc-ns 51370 --p-cpu-w 0.749 --seconds 60 --reps 10` |

Per run: `samples_*.csv` the meter's capture; `manifest_*.json` what the board wrote;
`run_*.log` what it printed, with the value it expected stated before the first window;
`energy_*.csv` and `-summary.csv` the reduction; `state_before_*`/`state_after_*` the board's
flags, temperature and under-voltage count around the run.

## Three things a reader should know

* ⚠️ **Repetition 2 of the control reads high (120.7 µJ against 114.8–117.0) because of the
  person running it.** While it was being metered the board was logged in to several times to
  see how far the run had got; each login costs it processor time on another core. From the
  second run on, nothing was asked of the board until a run's expected end. The repetition is
  kept: no rule written beforehand removes it, and the median does not move with it.
* **The manifests name the driver of the sync pin as `gpiod`. It was the kernel's sysfs
  interface**; the script wrote `gpiod` whenever any driver worked. Corrected in the script
  after these runs; the files are left as the runs wrote them.
* **The board ran the scripts of the repository's working tree at the time**, which is commit
  `a38994f` for the three files that matter (`energy_loop.py`, `validate_energy_e2e.py`,
  `rig_selftest.py`; checked by hash before the first run), on a checkout of `1239c66` for
  everything else. The pipelines themselves (`src/`) did not change between the two.

No reference load was at hand: these figures carry the sensor's gain, unchecked, as July's do.
