"""Smell detector baseline: rule-based word lists vs. a free local LLM.

Gold labels come from the dataset: in the clean list every requirement is non-smelly; in
the smelly list a requirement is smelly (with its labelled type) if it has a smelly version.

  python scripts/d_detector.py --run-llm    # query Ollama (10 calls), then evaluate
  python scripts/d_detector.py              # evaluate rule-based (+ cached LLM answers)
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from smellrep import llm, rules
from smellrep.data import load_requirements
from smellrep.paths import GAMES, GENERATED, SMELL_CATEGORY, SMELL_TYPES, out_dir
from smellrep.prompts import SMELL_DEFINITIONS
from smellrep.report import Report

SYSTEM = f"""You are an expert requirements engineer who reviews requirements for smells.
Smell types:

{SMELL_DEFINITIONS}

For each requirement decide whether it contains at least one of these smells. Consider the
whole list, because inconsistencies span several requirements. Output JSON:
{{"requirements": [{{"id": <int>, "smelly": true|false, "smell_types": ["<type>", ...]}}, ...]}}
Use only the type names listed above. Give one entry per requirement."""


def gold_rows() -> pd.DataFrame:
    rows = []
    for game in GAMES:
        reqs = load_requirements(game)
        for _, r in reqs.iterrows():
            rows.append({"game": game, "version": "clean", "id": int(r.id), "text": r.clean,
                         "gold_smelly": False, "gold_type": None})
            has = isinstance(r.smelly, str)
            rows.append({"game": game, "version": "smelly", "id": int(r.id),
                         "text": r.smelly if has else r.clean, "gold_smelly": has,
                         "gold_type": r.smell_type if has else None})
    return pd.DataFrame(rows)


def run_llm(gold: pd.DataFrame, model: str, cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    for (game, version), g in gold.groupby(["game", "version"]):
        path = cache / f"{game}_{version}.json"
        if path.exists():
            continue
        listing = "\n".join(f"{r.id}. {r.text}" for r in g.itertuples())
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Requirements of a {game.replace('_', ' ')} game:\n\n{listing}"},
        ]
        content, stats = llm.chat(messages, model=model)
        path.write_text(json.dumps({"stats": stats, "raw": content}, indent=2), encoding="utf-8")
        print(f"detector {game}/{version}: {stats['seconds']}s", flush=True)


def llm_predictions(gold: pd.DataFrame, cache: Path) -> pd.DataFrame | None:
    preds = []
    for (game, version), g in gold.groupby(["game", "version"]):
        path = cache / f"{game}_{version}.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))["raw"]
        try:
            items = llm.find_list(llm.parse_json(raw), ("requirements",))
        except ValueError:
            items = []
        by_id = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            m = re.search(r"\d+", str(it.get("id", it.get("requirement_id", ""))))
            if not m:
                continue
            types = it.get("smell_types") or []
            if isinstance(types, str):
                types = [types]
            types = {t.strip().lower().replace(" ", "_") for t in types if isinstance(t, str)}
            types = {t for t in types if t in SMELL_TYPES}
            smelly = it.get("smelly")
            smelly = (str(smelly).lower() in ("true", "yes", "1")) or bool(types)
            by_id[int(m.group())] = (smelly, types)
        for r in g.itertuples():
            s, t = by_id.get(r.id, (False, set()))
            preds.append({"game": game, "version": version, "id": r.id, "pred_smelly": s, "pred_types": t})
    return pd.DataFrame(preds)


def rule_predictions(gold: pd.DataFrame) -> pd.DataFrame:
    preds = []
    for (game, version), g in gold.groupby(["game", "version"]):
        found = rules.detect_list(dict(zip(g["id"], g["text"])))
        for rid, types in found.items():
            preds.append({"game": game, "version": version, "id": rid,
                          "pred_smelly": bool(types), "pred_types": types})
    return pd.DataFrame(preds)


def score(gold: pd.DataFrame, pred: pd.DataFrame, name: str) -> tuple[dict, pd.DataFrame]:
    df = gold.merge(pred, on=["game", "version", "id"])
    tp = (df.gold_smelly & df.pred_smelly).sum()
    fp = (~df.gold_smelly & df.pred_smelly).sum()
    fn = (df.gold_smelly & ~df.pred_smelly).sum()
    tn = (~df.gold_smelly & ~df.pred_smelly).sum()
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    sm = df[df.gold_smelly]
    type_hit = sm.apply(lambda x: x.gold_type in x.pred_types, axis=1)
    cat_hit = sm.apply(
        lambda x: SMELL_CATEGORY[x.gold_type] in {SMELL_CATEGORY[t] for t in x.pred_types}, axis=1
    )
    summary = {
        "detector": name, "precision": p, "recall": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        "accuracy": (tp + tn) / len(df), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "type_hit_rate": type_hit.mean(), "category_hit_rate": cat_hit.mean(),
        "mean_types_flagged": df.pred_types.apply(len).mean(),
    }
    sm = sm.assign(type_hit=type_hit.values, detected=sm.pred_smelly.values)
    per_type = sm.groupby("gold_type").agg(n=("id", "size"), recall=("detected", "mean"),
                                           type_hit_rate=("type_hit", "mean")).reset_index()
    per_type.insert(0, "detector", name)
    return summary, per_type


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--run-llm", action="store_true")
    args = ap.parse_args()

    gold = gold_rows()
    cache = GENERATED / "detector" / re.sub(r"[^A-Za-z0-9.]+", "_", args.model)
    if args.run_llm:
        run_llm(gold, args.model, cache)

    detectors = {"rule_based": rule_predictions(gold)}
    for model_cache in sorted((GENERATED / "detector").glob("*")):
        lp = llm_predictions(gold, model_cache)
        if lp is not None:
            detectors[f"llm ({model_cache.name})"] = lp

    summaries, per_types = [], []
    for name, pred in detectors.items():
        s, pt = score(gold, pred, name)
        summaries.append(s)
        per_types.append(pt)
    summary = pd.DataFrame(summaries)
    per_type = pd.concat(per_types)

    out = out_dir("D_detector")
    summary.to_csv(out / "summary.csv", index=False)
    per_type.to_csv(out / "per_type.csv", index=False)
    detail = gold.merge(detectors["rule_based"], on=["game", "version", "id"])
    detail["pred_types"] = detail["pred_types"].apply(lambda s: ",".join(sorted(s)))
    detail.to_csv(out / "rule_based_predictions.csv", index=False)

    rep = Report("Smell detector baseline")
    rep.p(
        f"{int(gold.gold_smelly.sum())} smelly and {int((~gold.gold_smelly).sum())} non-smelly "
        "requirement texts (clean versions of all requirements plus the smelly list per game). "
        "*Type hit rate*: share of smelly requirements whose labelled smell type is among the "
        "flagged types. Rule-based word lists are in `src/smellrep/rules.py`."
    )
    rep.table(summary)
    rep.h("Recall and type hit rate per labelled smell type")
    pivot = per_type.pivot_table(index=["gold_type"], columns="detector",
                                 values=["recall", "type_hit_rate"]).round(2)
    pivot.columns = [f"{a} | {b}" for a, b in pivot.columns]
    rep.table(pivot.reset_index())
    rep.save(out / "README.md")
    print(summary.to_string())
    print(per_type.to_string())


if __name__ == "__main__":
    main()
