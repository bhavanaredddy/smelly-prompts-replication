"""Metrics, implemented the same way as the authors' Evaluation.ipynb unless noted."""

from collections import Counter

import numpy as np
import pandas as pd

from smellrep.data import load_ground_truth

KEYS = ["model", "game", "experiment", "requirement_id"]


def majority_vote(runs: pd.DataFrame) -> pd.DataFrame:
    """Collapses repeated runs per (model, game, experiment, requirement).

    `implemented_pred` takes the mode; a line is kept if it is predicted in more than
    half of the runs (the notebook's `count > 2` for five runs).
    """
    def vote(g: pd.DataFrame) -> pd.Series:
        n = len(g)
        counts = Counter(line for lines in g["loc_predicted"] for line in lines)
        lines = sorted(l for l, c in counts.items() if c > n / 2)
        return pd.Series(
            {
                "implemented_pred": bool(g["implemented_pred"].dropna().mode().iloc[0])
                if g["implemented_pred"].notna().any()
                else False,
                "loc_predicted": lines,
                "smelly": bool(g["smelly"].mode().iloc[0]),
                "n_runs": n,
                "unanimous": g["implemented_pred"].nunique(dropna=False) == 1,
            }
        )

    voted = runs.groupby(KEYS, sort=False).apply(vote, include_groups=False).reset_index()
    return voted


def attach_ground_truth(voted: pd.DataFrame, gt: pd.DataFrame | None = None) -> pd.DataFrame:
    gt = load_ground_truth() if gt is None else gt
    df = voted.merge(
        gt[
            [
                "game",
                "requirement_id",
                "req_key",
                "smell_type",
                "smell_category",
                "implemented",
                "smelly_traceable",
                "loc_actual",
            ]
        ].rename(columns={"implemented": "implemented_actual"}),
        on=["game", "requirement_id"],
        how="inner",
    )
    df["expected"] = np.where(
        df["smelly"], df["smelly_traceable"].fillna(False), df["implemented_actual"]
    ).astype(bool)
    df["correct"] = df["implemented_pred"] == df["expected"]
    df["correct_intent"] = df["implemented_pred"] == df["implemented_actual"]
    pct = df.groupby(["model", "game", "experiment"])["smelly"].transform("mean") * 100
    df["percentage_smelly"] = pct
    n_reqs = df.groupby(["model", "game", "experiment"])["smelly"].transform("size")
    n_smelly = df.groupby(["model", "game", "experiment"])["smelly"].transform("sum")
    df["pct_other_smelly"] = (n_smelly - df["smelly"].astype(int)) / (n_reqs - 1) * 100
    prf = df.apply(_prf_notebook, axis=1, result_type="expand")
    df[["precision", "recall", "f1"]] = prf
    strict = df.apply(_prf_strict, axis=1, result_type="expand")
    df[["precision_strict", "recall_strict", "f1_strict"]] = strict
    return df


def _prf(pred: list[int], actual: list[int]):
    tp = len(set(pred) & set(actual))
    if len(pred) == 0:
        p = 1.0 if len(actual) == 0 else 0.0
    else:
        p = tp / len(pred)
    if len(actual) == 0:
        r = 1.0 if len(pred) == 0 else 0.0
    else:
        r = tp / len(actual)
    f = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    return p, r, f


def _prf_notebook(row):
    """The notebook drops rows whose voted predicted or actual line list is empty."""
    if not row["loc_predicted"] or not row["loc_actual"]:
        return np.nan, np.nan, np.nan
    return _prf(row["loc_predicted"], row["loc_actual"])


def _prf_strict(row):
    """Scores every requirement that should be traced; an empty prediction counts as 0."""
    if not row["expected"] or not row["loc_actual"]:
        return np.nan, np.nan, np.nan
    return _prf(row["loc_predicted"], row["loc_actual"])


def per_experiment(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["model", "game", "experiment"])
    out = g.agg(
        accuracy=("correct", "mean"),
        accuracy_intent=("correct_intent", "mean"),
        precision=("precision", "mean"),
        recall=("recall", "mean"),
        f1=("f1", "mean"),
        f1_strict=("f1_strict", "mean"),
        percentage_smelly=("percentage_smelly", "mean"),
        n_correct=("correct", "sum"),
        n=("correct", "size"),
    ).reset_index()
    return out


def evaluate(runs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (requirement-level frame, experiment-level frame)."""
    req = attach_ground_truth(majority_vote(runs))
    return req, per_experiment(req)
