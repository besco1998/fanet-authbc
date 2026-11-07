# A1, stage 2 — the grids, committed before any stage-2 run (2026-10-20)

Stage 1 (`results/raw/ns3_spatial_stage1_runs.csv`, 430 runs, seeds 1–5) is exploratory and
is not reported as a capacity. By the rule registered in `predictions/A1.md`, each stage-2 grid
is round(x₁(1 + 0.04k)), k = −2…2, x₁ the stage-1 interpolated crossing; S3 at 5 and 15 m/s
runs the speed-0 grid; `fixed` runs the published grids. Plan: `experiments/spatial/plan_stage2.txt`.

| scenario | base x₁ → grid | inline4 x₁ → grid | design x₁ → grid |
|---|---|---|---|
| s1-r100 | 38.8 → 36 37 39 40 42 | 82.8 → 76 79 83 86 89 | 136.0 → 125 131 136 141 147 |
| s1-r300 | 30.3 → 28 29 30 31 33 | 62.8 → 58 60 63 65 68 | 111.8 → 103 107 112 116 121 |
| s1-r600 | 31.7 → 29 30 32 33 34 | 61.7 → 57 59 62 64 67 | 108.5 → 100 104 109 113 117 |
| s1-r1000 | 65.1 → 60 63 65 68 70 | 117.1 → 108 112 117 122 126 | 216.6 → 199 208 217 225 234 |
| s2 | 33.7 → 31 32 34 35 36 | 69.9 → 64 67 70 73 75 | 122.2 → 112 117 122 127 132 |
| s3-v0, -v5, -v15 | 39.5 → 36 38 40 41 43 | 83.6 → 77 80 84 87 90 | 136.7 → 126 131 137 142 148 |
| fixed | published: 32–38 | published: 71–83 step 2 | published: 115–133 step 3 |

**The binary.** `ns3/authbc-spatial.cc` gained a `--traceLinks` option for A3, part 2 (absent
by default). Rebuilt, it reproduced three stage-1 runs bit for bit (s1-r300/base/40/1,
s3-v0/design/40/2, s2/inline4/60/3, every summary value).

**Disclosure.** What stage 1 showed is above; it was read before this file. In particular the
design's stage-1 crossing at R = 1000 m comes with about 8 neighbours, below the [10, 40] of my
registered A1-2 — that prediction stands as registered and is scored on stage 2.
