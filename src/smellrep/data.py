"""Loading of the artifact's games, requirements, ground truth and LLM runs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from smellrep.paths import ARTIFACT, GROUND_TRUTH


def _to_bool(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip().lower()
    if s in ("true", "yes", "1", "y"):
        return True
    if s in ("false", "no", "0", "n", ""):
        return False
    return np.nan


def parse_lines(value) -> list[int]:
    """Accepts lists of ints, numeric strings, and strings such as "3, 5-9"."""
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    if isinstance(value, (int, np.integer)):
        return [int(value)]
    if isinstance(value, list):
        out = []
        for v in value:
            out.extend(parse_lines(v))
        return sorted(set(out))
    lines = []
    for part in str(value).replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                a, b = int(a.strip()), int(b.strip())
            except ValueError:
                continue
            if 0 < b - a < 1000:
                lines.extend(range(a, b + 1))
        else:
            try:
                lines.append(int(float(part)))
            except ValueError:
                continue
    return sorted(set(lines))


def load_ground_truth(path: Path = GROUND_TRUTH) -> pd.DataFrame:
    gt = pd.read_csv(path)
    gt["implemented"] = gt["implemented"].map({"yes": True, "no": False})
    gt["smelly_traceable"] = gt["smelly_traceable"].map({"yes": True, "no": False})
    gt["loc_actual"] = gt["lines"].apply(parse_lines)
    gt["req_key"] = gt["game"] + "#" + gt["requirement_id"].astype(str)
    return gt


def load_requirements(game: str) -> pd.DataFrame:
    """One row per requirement with clean and (if available) smelly text."""
    clean = pd.read_csv(ARTIFACT / f"{game}_requirements.csv", encoding="utf-8")
    smelly = pd.read_csv(ARTIFACT / f"{game}_requirements_smelly.csv", encoding="utf-8")
    clean = clean.rename(columns={"description": "clean"})[["id", "clean"]]
    smelly = smelly.rename(
        columns={"description": "smelly", "smell": "smell_type", "smell_type": "smell_category"}
    )[["id", "smelly", "smell_type", "smell_category"]]
    df = clean.merge(smelly, on="id", how="left")
    df.insert(0, "game", game)
    return df


def load_code(game: str) -> str:
    return (ARTIFACT / f"{game}_code.java").read_text(encoding="utf-8")


def load_runs(path: Path) -> pd.DataFrame:
    """Flattens a results_all.json-style file into one row per (run, requirement)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return runs_to_long(data)


def runs_to_long(data: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in data:
        smelly = set(entry.get("smelly_requirements", []))
        for r in entry["requirements"]:
            rid = int(r["requirement_id"])
            rows.append(
                {
                    "id": entry["id"],
                    "game": entry["game"],
                    "experiment": entry["experiment"],
                    "run": int(entry["run"]),
                    "model": entry["model"],
                    "requirement_id": rid,
                    "implemented_pred": _to_bool(r["implemented"]),
                    "loc_predicted": parse_lines(r.get("lines_of_code", [])),
                    "smelly": rid in smelly,
                }
            )
    return pd.DataFrame(rows)
