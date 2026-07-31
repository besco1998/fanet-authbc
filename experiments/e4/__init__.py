"""E4 lives in a *script*, not the bench package, and deliberately so.

`run_e4.py` is imported by the frozen-reproduction gate via an explicit file-path loader rather
than as a package module, because it predates the `authbc.bench.experiments` runner registry and
reads its crypto timings from the hardware CSV directly. This file exists only so the directory is
importable; see `experiments/e4/run_e4.py` for the experiment itself.
"""
