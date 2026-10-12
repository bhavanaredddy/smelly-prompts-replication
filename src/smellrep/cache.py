from pathlib import Path

import pandas as pd

from smellrep.data import load_runs
from smellrep.metrics import evaluate
from smellrep.paths import AUTHORS_RUNS, FRIEND_RUNS, GENERATED


def evaluated(runs_path: Path, name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Majority-voted, ground-truth-scored frames for a runs file, cached as pickles."""
    GENERATED.mkdir(exist_ok=True)
    req_p = GENERATED / f"{name}_req.pkl"
    exp_p = GENERATED / f"{name}_exp.pkl"
    if req_p.exists() and exp_p.exists() and req_p.stat().st_mtime > runs_path.stat().st_mtime:
        return pd.read_pickle(req_p), pd.read_pickle(exp_p)
    req, exp = evaluate(load_runs(runs_path))
    req.to_pickle(req_p)
    exp.to_pickle(exp_p)
    return req, exp


def authors():
    return evaluated(AUTHORS_RUNS, "authors")


def friend():
    return evaluated(FRIEND_RUNS, "friend")
