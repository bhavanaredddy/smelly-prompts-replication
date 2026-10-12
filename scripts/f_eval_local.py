"""Evaluates the local-model runs (Step C) and the smell fixer.

Two ways to score a smelly or fixed requirement:
  dataset label   the authors' scoring (smelly requirements use `smelly_traceable`)
  original intent the clean requirement's ground truth; this is what a fixer should recover
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from smellrep import cache, llm, rules
from smellrep.data import load_requirements, runs_to_long
from smellrep.metrics import _prf, evaluate
from smellrep.paths import GAMES, GENERATED, GPT, LLAMA, out_dir
from smellrep.report import Report
from smellrep.stats import cluster_bootstrap_diff

COND_ORDER = ["clean", "smelly", "fixed_blind", "fixed_rewrite", "fixed_oracle"]


def f1_intent(row):
    if not row["implemented_actual"] or not row["loc_actual"]:
        return np.nan
    return _prf(row["loc_predicted"], row["loc_actual"])[2]


def summarize(req: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, cond), d in req.groupby(["model", "condition"]):
        s = d[d.smellable]
        rows.append({
            "model": model, "condition": cond,
            "acc_all": d.correct.mean(),
            "acc_smellable_label": s.correct.mean(),
            "acc_smellable_intent": s.correct_intent.mean(),
            "f1_smellable_intent": s.f1_intent.mean(),
            "said_yes": d.implemented_pred.mean(),
            "n_smellable": len(s),
        })
    out = pd.DataFrame(rows)
    out["condition"] = pd.Categorical(out["condition"], COND_ORDER, ordered=True)
    return out.sort_values(["model", "condition"])


def prepare(req: pd.DataFrame, smellable_keys: set) -> pd.DataFrame:
    req = req.copy()
    req["condition"] = req["experiment"].str.replace(r"_\d+$", "", regex=True).replace(
        {"no_smells": "clean", "all_smells": "smelly"})
    req["smellable"] = req["req_key"].isin(smellable_keys)
    req["f1_intent"] = req.apply(f1_intent, axis=1)
    return req


STOP = set("""a an the and or of to in on for is are be shall must will should can could may might
it its his her their they he she this that these those if when then than with by as at from
each every all any system program game player players""".split())


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1}


def overlap(a: str, b: str) -> float:
    wa, wb = content_words(a), content_words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 1.0


def fixer_quality(model_tag: str) -> pd.DataFrame:
    rows = []
    for mode_dir in sorted((GENERATED / "fixed" / model_tag).glob("*")):
        for game in GAMES:
            p = mode_dir / f"{game}.csv"
            if not p.exists():
                continue
            d = pd.read_csv(p)
            clean_by_id = dict(zip(d.id, d.clean))
            fixed_flags = rules.detect_list(dict(zip(d.id, d.fixed)))
            input_flags = rules.detect_list(dict(zip(d.id, d.input)))
            for r in d.itertuples():
                if not isinstance(r.smell_type, str):
                    continue
                sims = {cid: overlap(r.fixed, c) for cid, c in clean_by_id.items()}
                rows.append({
                    "mode": mode_dir.name, "game": game, "id": r.id, "smell_type": r.smell_type,
                    "smell_category": r.smell_category, "changed": r.changed,
                    "sim_input_to_clean": overlap(r.input, r.clean),
                    "sim_fixed_to_clean": sims[r.id],
                    "drifted": max(sims.values()) > sims[r.id] + 0.05,
                    "rule_flags_before": len(input_flags[r.id]),
                    "rule_flags_after": len(fixed_flags[r.id]),
                    "own_smell_flag_removed": r.smell_type in input_flags[r.id] and r.smell_type not in fixed_flags[r.id],
                })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    args = ap.parse_args()
    tag = re.sub(r"[^A-Za-z0-9.]+", "_", args.model)
    runs_path = GENERATED / "local_runs" / tag / "runs.jsonl"
    records = [json.loads(l) for l in runs_path.read_text(encoding="utf-8").splitlines()]

    smellable = set()
    for g in GAMES:
        r = load_requirements(g)
        smellable |= {f"{g}#{i}" for i in r.loc[r.smelly.notna(), "id"]}

    local_req, _ = evaluate(runs_to_long(records))
    local_req = prepare(local_req, smellable)
    a_req, _ = cache.authors()
    a_req = prepare(a_req[a_req.experiment.isin(["no_smells_01", "all_smells_01"])], smellable)
    all_req = pd.concat([local_req, a_req], ignore_index=True)
    summary = summarize(all_req)

    out = out_dir("C_local_and_fixer")
    summary.to_csv(out / "conditions_summary.csv", index=False)
    local_req.drop(columns=["loc_predicted", "loc_actual"]).to_csv(out / "local_requirement_level.csv", index=False)

    rep = Report(f"Step C + smell fixer: fresh tracing runs with {args.model} (free, local)")
    n_runs = len(records)
    secs = sum(r["stats"]["seconds"] for r in records)
    parse_issues = sum(1 for r in records if r["parse"]["parse_error"] or r["parse"]["missing"])
    rep.p(
        f"{n_runs} tracing runs on CPU ({secs / 60:.0f} min total, temperature 0, so one run per "
        f"condition is deterministic). Runs with parse problems or missing requirements: {parse_issues}. "
        "The prompt is byte-for-byte the authors' prompt. Rows for GPT-4o and Llama-3.1-70B come "
        "from the authors' saved no-smell / all-smell runs, for reference.\n\n"
        "*smellable* = the 72 requirements that have a smelly variant. "
        "`acc_smellable_intent` and `f1_smellable_intent` score against the clean requirement's "
        "ground truth, i.e. whether the original intent was still traced correctly."
    )
    rep.table(summary)

    rep.h("Did the fixer recover the loss? (local model, smellable requirements)")
    rows = []
    loc = local_req[local_req.smellable]
    for metric in ["correct_intent", "f1_intent", "correct"]:
        by = loc.groupby("condition")[metric].mean()
        if "clean" not in by or "smelly" not in by:
            continue
        gap = by["clean"] - by["smelly"]
        for cond in [c for c in COND_ORDER if c.startswith("fixed") and c in by]:
            d = loc[loc.condition.isin(["smelly", cond])].dropna(subset=[metric])
            est, lo, hi = cluster_bootstrap_diff(d, "req_key", metric, "condition", "smelly", cond)
            rows.append({
                "metric": metric, "fixer": cond, "clean": by["clean"], "smelly": by["smelly"],
                "fixed": by[cond], "fixed_minus_smelly": est, "ci_low": lo, "ci_high": hi,
                "share_of_gap_recovered": (by[cond] - by["smelly"]) / gap if abs(gap) > 1e-9 else np.nan,
            })
    recovery = pd.DataFrame(rows)
    recovery.to_csv(out / "fixer_recovery.csv", index=False)
    rep.p("95% CIs from a bootstrap over requirements. `share_of_gap_recovered` = "
          "(fixed - smelly) / (clean - smelly); it is unstable when the clean-smelly gap is tiny.")
    rep.table(recovery)

    rep.h("Fixer text quality (smelly requirements only)")
    fq = fixer_quality(tag)
    if not fq.empty:
        fq.to_csv(out / "fixer_text_quality.csv", index=False)
        agg = fq.groupby("mode").agg(
            n=("id", "size"), changed=("changed", "mean"),
            sim_input_to_clean=("sim_input_to_clean", "mean"),
            sim_fixed_to_clean=("sim_fixed_to_clean", "mean"),
            drifted=("drifted", "mean"),
            rule_flags_before=("rule_flags_before", "mean"),
            rule_flags_after=("rule_flags_after", "mean"),
            own_smell_flag_removed=("own_smell_flag_removed", "mean"),
        ).reset_index()
        rep.p("`sim_*` = content-word overlap (Jaccard, stop words removed) with the authors' "
              "clean version. `drifted` = the rewrite overlaps clearly more with a *different* "
              "requirement's clean text (the fixer mixed requirements up). Rule flags come from "
              "the rule-based detector.")
        rep.table(agg)
        by_cat = fq.groupby(["mode", "smell_category"]).agg(
            changed=("changed", "mean"), sim_gain=("sim_fixed_to_clean", "mean")).reset_index()
        rep.table(by_cat)

    rep.h("Per smell category (local model, smellable requirements)")
    cat = loc.groupby(["smell_category", "condition"]).agg(
        acc_intent=("correct_intent", "mean"), f1_intent=("f1_intent", "mean"), n=("req_key", "size")
    ).reset_index()
    cat.to_csv(out / "local_by_category.csv", index=False)
    rep.table(cat)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, metric, title in [(axes[0], "acc_smellable_intent", "yes/no accuracy (intent)"),
                              (axes[1], "f1_smellable_intent", "line F1 (intent)")]:
        piv = summary.pivot(index="condition", columns="model", values=metric)
        piv.plot.bar(ax=ax, rot=20)
        ax.set_title(title)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7)
    plt.tight_layout()
    p = out / "conditions.png"
    plt.savefig(p, dpi=150)
    plt.close()
    rep.image(p, out, "conditions")

    rep.save(out / "README.md")
    print(summary.to_string())
    print(recovery.to_string())
    if not fq.empty:
        print(agg.to_string())


if __name__ == "__main__":
    main()
