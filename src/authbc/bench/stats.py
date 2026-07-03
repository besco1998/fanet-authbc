"""Bootstrap statistics for microbenchmarks (docs/02 §8).

Report **median + bootstrap 95% CI** (10 000 resamples). The bootstrap RNG is seeded so a
result is reproducible (a CI that changes across identical seeds would be a bug, Law 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

import numpy as np

DEFAULT_RESAMPLES = 10_000


@dataclass(frozen=True)
class Summary:
    median: float
    ci_lo: float
    ci_hi: float
    n: int

    def as_row(self) -> dict[str, float | int]:
        return {"median": self.median, "ci_lo": self.ci_lo, "ci_hi": self.ci_hi, "n": self.n}


def bootstrap_ci(
    samples: list[float],
    *,
    resamples: int = DEFAULT_RESAMPLES,
    ci: float = 0.95,
    seed: int = 0,
    statistic=np.median,
) -> tuple[float, float]:
    """Percentile bootstrap CI of ``statistic`` over ``samples`` (seeded → reproducible)."""
    if len(samples) < 2:
        raise ValueError("need >= 2 samples for a bootstrap CI")
    rng = np.random.default_rng(seed)
    arr = np.asarray(samples, dtype=float)
    idx = rng.integers(0, len(arr), size=(resamples, len(arr)))
    stats = statistic(arr[idx], axis=1)
    lo = float(np.percentile(stats, 100 * (1 - ci) / 2))
    hi = float(np.percentile(stats, 100 * (1 + ci) / 2))
    return lo, hi


def summarize(
    samples: list[float], *, seed: int = 0, resamples: int = DEFAULT_RESAMPLES
) -> Summary:
    lo, hi = bootstrap_ci(samples, resamples=resamples, seed=seed)
    return Summary(median=float(median(samples)), ci_lo=lo, ci_hi=hi, n=len(samples))
