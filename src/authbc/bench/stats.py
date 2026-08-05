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


@dataclass(frozen=True)
class ThresholdCI:
    """A capacity threshold crossing reported as an interval rather than a point."""

    point: int
    ci_lo: int
    ci_hi: int
    resamples: int
    #: fraction of bootstrap replicates that returned each candidate value
    distribution: dict[int, float]

    @property
    def is_knife_edge(self) -> bool:
        """True when the interval spans more than one candidate — i.e. quoting a bare number lies.

        ⚠️ The criterion is the CI being non-degenerate, **not** the point estimate losing a
        majority vote. A first version used "point holds < 50 % of replicates" and it passed a
        56/44 split as settled, which is plainly a knife edge. What matters scientifically is
        whether the data distinguish the candidates at the stated confidence; a bare majority
        does not.
        """
        return self.ci_lo != self.ci_hi


def threshold_crossing_ci(
    per_n: dict[int, list[float]],
    *,
    threshold: float,
    resamples: int = DEFAULT_RESAMPLES,
    ci: float = 0.95,
    seed: int = 0,
) -> ThresholdCI:
    """Bootstrap CI for "largest N whose mean still meets ``threshold``" (docs/02 §6b).

    **Why this exists.** ``N_max`` is a threshold crossing on a noisy curve, and the project has
    already had four headline numbers move because a small-sample mean was compared against a
    threshold and reported as a point. A mean gets a CI almost automatically; a *crossing* does
    not, because the quantity is discrete and non-linear in the sample. Resampling the seeds and
    recomputing the whole crossing each time is the honest way to attach uncertainty to it.

    The crossing rule matches the driver exactly (F26/A4): the largest N such that N **and every
    smaller N** pass. Taking the last passing N would over-report the moment the curve is
    non-monotone, and it is noisy enough to be.

    ``per_n`` maps node count → that N's per-seed delivered fractions. Every N must carry the same
    number of seeds, since an interval built from uneven samples would not mean anything.
    """
    if not per_n:
        raise ValueError("need at least one N")
    sizes = {len(v) for v in per_n.values()}
    if len(sizes) != 1:
        raise ValueError(f"every N must have the same seed count, got {sorted(sizes)}")
    n_seeds = sizes.pop()
    if n_seeds < 2:
        raise ValueError("need >= 2 seeds per N for a bootstrap CI")

    ns = sorted(per_n)
    rng = np.random.default_rng(seed)
    # Resample each N independently: seeds are independent runs, so a replicate should redraw
    # them per N rather than reusing one index vector across the sweep.
    passes = np.empty((resamples, len(ns)), dtype=bool)
    for j, n in enumerate(ns):
        arr = np.asarray(per_n[n], dtype=float)
        idx = rng.integers(0, n_seeds, size=(resamples, n_seeds))
        passes[:, j] = arr[idx].mean(axis=1) >= threshold

    # Consecutive-pass prefix length -> index of the last N that passed with no earlier failure.
    prefix = np.cumprod(passes, axis=1).sum(axis=1)  # 0 means even the smallest N failed
    values = np.where(prefix > 0, np.take(np.asarray(ns), np.clip(prefix - 1, 0, len(ns) - 1)), 0)

    counts = {int(v): float(c) / resamples for v, c in zip(*np.unique(values, return_counts=True),
                                                           strict=True)}
    return ThresholdCI(
        point=int(np.median(values)),
        ci_lo=int(np.percentile(values, 100 * (1 - ci) / 2)),
        ci_hi=int(np.percentile(values, 100 * (1 + ci) / 2)),
        resamples=resamples,
        distribution=counts,
    )
