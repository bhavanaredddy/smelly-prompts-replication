import numpy as np
import pandas as pd


def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def cluster_bootstrap_diff(
    df: pd.DataFrame, cluster: str, value: str, group: str, a, b, n: int = 2000, seed: int = 0
):
    """Mean(value | group == b) - mean(value | group == a), resampling whole clusters.

    Returns (estimate, ci_low, ci_high)."""
    rng = np.random.default_rng(seed)
    clusters = df[cluster].unique()
    by = {c: g for c, g in df.groupby(cluster)}

    def diff(d):
        return d.loc[d[group] == b, value].mean() - d.loc[d[group] == a, value].mean()

    est = diff(df)
    boots = []
    for _ in range(n):
        pick = rng.choice(clusters, size=len(clusters), replace=True)
        boots.append(diff(pd.concat([by[c] for c in pick])))
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return est, lo, hi
