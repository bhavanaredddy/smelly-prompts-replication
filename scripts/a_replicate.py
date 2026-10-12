"""Step A: reproduce the paper's RQ1-RQ3 numbers from the authors' 6,100 saved runs."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2

from smellrep import cache
from smellrep.paths import GAMES, GPT, LLAMA, RESULTS, out_dir
from smellrep.plots import line_by_game
from smellrep.report import Report

warnings.filterwarnings("ignore")

# Values printed in the saved outputs of the authors' Evaluation.ipynb.
NOTEBOOK_RQ1 = {
    (GPT, "dice_game"): (0.96, 0.712211, 0.833812, 0.731467),
    (GPT, "arkanoid"): (1.00, 0.682900, 0.796861, 0.688089),
    (GPT, "snake"): (0.928571, 0.609895, 0.748939, 0.629313),
    (GPT, "scopa"): (1.00, 0.738284, 0.836410, 0.741331),
    (GPT, "pong"): (0.90, 0.585452, 0.730017, 0.591990),
    (LLAMA, "dice_game"): (0.92, 0.682790, 0.726615, 0.654602),
    (LLAMA, "arkanoid"): (0.947368, 0.644872, 0.609499, 0.531839),
    (LLAMA, "snake"): (0.928571, 0.489180, 0.673618, 0.528021),
    (LLAMA, "scopa"): (1.00, 0.641816, 0.695267, 0.628522),
    (LLAMA, "pong"): (0.95, 0.654429, 0.709124, 0.642982),
}
NOTEBOOK_RQ3_ACC = {
    (GPT, "lexical"): 0.896516, (GPT, "syntactic"): 0.976639, (GPT, "semantic"): 0.833431,
    (LLAMA, "lexical"): 0.829235, (LLAMA, "syntactic"): 0.909836, (LLAMA, "semantic"): 0.861827,
}
NOTEBOOK_GLMM_ACC = {"Intercept": 0.953, "percentage_smelly": -0.001, "z": -7.001}


def notebook_glmm(df: pd.DataFrame, y: str):
    """The exact mixed model specification used in the notebook."""
    m = smf.mixedlm(
        f"{y} ~ percentage_smelly", df, groups=df["game"],
        re_formula="1 + percentage_smelly", vc_formula={"model": "0 + C(model)"},
    )
    fit = m.fit()
    ols = smf.ols(f"{y} ~ percentage_smelly", data=df).fit()
    lr = 2 * (fit.llf - ols.llf)
    return fit, lr, chi2.sf(lr, df=2)


def main():
    out = out_dir("A_replication")
    figs = out_dir("A_replication", "figures")
    rep = Report("Step A: Replication of the paper's analysis from the authors' saved runs")
    req, exp = cache.authors()
    rep.p(
        f"Input: `artifact/results_all.json` ({req['n_runs'].sum():.0f} requirement-run rows, "
        f"{len(exp)} model x game x configuration groups). Majority vote over 5 runs per "
        "configuration, as in the authors' notebook. The pipeline is in `src/smellrep/metrics.py`."
    )

    # ---------- RQ1 ----------
    rep.h("RQ1: tracing performance without smells")
    base = exp[exp["experiment"] == "no_smells_01"].copy()
    rows = []
    for (model, game), (acc, p, r, f) in NOTEBOOK_RQ1.items():
        b = base[(base.model == model) & (base.game == game)].iloc[0]
        rows.append({
            "model": model, "game": game,
            "accuracy": b.accuracy, "nb_accuracy": acc,
            "precision": b.precision, "nb_precision": p,
            "recall": b.recall, "nb_recall": r,
            "f1": b.f1, "nb_f1": f,
        })
    rq1 = pd.DataFrame(rows)
    num = [c for c in rq1.columns if c not in ("model", "game")]
    means = rq1.groupby("model")[num].mean().reset_index().assign(game="MEAN")
    rq1 = pd.concat([rq1, means], ignore_index=True)
    rq1["max_abs_diff"] = np.max(
        np.abs(rq1[["accuracy", "precision", "recall", "f1"]].values
               - rq1[["nb_accuracy", "nb_precision", "nb_recall", "nb_f1"]].values), axis=1)
    rq1.to_csv(out / "rq1_no_smells.csv", index=False)
    rep.p("Columns prefixed `nb_` are the values printed in the authors' notebook.")
    rep.table(rq1)
    rq1_ok = rq1["max_abs_diff"].max() < 1e-3
    rep.p(f"**Match with notebook (|diff| < 0.001): {rq1_ok}** "
          f"(largest difference {rq1['max_abs_diff'].max():.2e}).")

    # ---------- RQ2 ----------
    rep.h("RQ2: performance as the share of smelly requirements grows")
    exp.to_csv(out / "rq2_per_configuration.csv", index=False)
    for model, tag in [(GPT, "GPT"), (LLAMA, "Llama")]:
        for y in ["accuracy", "precision", "recall", "f1"]:
            p = figs / f"rq2_{y}_{tag}.png"
            line_by_game(exp[exp.model == model], y, f"{tag}: {y} vs. smelly share", p)
    rep.p("Line plots (same layout as the paper's Fig. 2):")
    for tag in ["GPT", "Llama"]:
        rep.image(figs / f"rq2_accuracy_{tag}.png", out, f"BTA {tag}")

    rep.h("Authors' mixed model, refitted", 3)
    glmm_rows = []
    for y in ["accuracy", "precision", "recall", "f1"]:
        fit, lr, p_lr = notebook_glmm(exp, y)
        glmm_rows.append({
            "outcome": y,
            "intercept": fit.params["Intercept"],
            "slope_per_pct": fit.params["percentage_smelly"],
            "z": fit.tvalues["percentage_smelly"],
            "p": fit.pvalues["percentage_smelly"],
            "converged": fit.converged,
            "LR_vs_OLS": lr,
        })
        (out / f"glmm_{y}.txt").write_text(str(fit.summary()), encoding="utf-8")
    glmm = pd.DataFrame(glmm_rows)
    glmm.to_csv(out / "rq2_glmm.csv", index=False)
    rep.table(glmm, ".4g")
    a = glmm.iloc[0]
    rep.p(
        f"Notebook reported for accuracy: intercept {NOTEBOOK_GLMM_ACC['Intercept']}, slope "
        f"{NOTEBOOK_GLMM_ACC['percentage_smelly']}, z = {NOTEBOOK_GLMM_ACC['z']}. "
        f"Refit: intercept {a.intercept:.3f}, slope {a.slope_per_pct:.5f}, z = {a.z:.3f}. "
        "A slope of about -0.001 per percentage point means roughly -0.08 accuracy "
        "going from 0 % to 80 % smelly requirements."
    )

    # ---------- RQ3 ----------
    rep.h("RQ3: performance per smell category")
    rows = []
    for model in [GPT, LLAMA]:
        for cat in ["lexical", "syntactic", "semantic"]:
            nb_rows = req[(req.model == model) & (req.smell_category == cat)]
            smelly_rows = nb_rows[nb_rows.smelly]
            clean_rows = nb_rows[~nb_rows.smelly]
            rows.append({
                "model": model, "category": cat,
                "nb_accuracy": NOTEBOOK_RQ3_ACC[(model, cat)],
                "accuracy_as_notebook": nb_rows["correct"].mean(),
                "accuracy_only_when_smelly": smelly_rows["correct"].mean(),
                "accuracy_same_reqs_when_clean": clean_rows["correct"].mean(),
                "f1_as_notebook": nb_rows["f1"].mean(),
                "f1_only_when_smelly": smelly_rows["f1"].mean(),
                "f1_same_reqs_when_clean": clean_rows["f1"].mean(),
                "n_smelly": len(smelly_rows), "n_clean": len(clean_rows),
            })
    rq3 = pd.DataFrame(rows)
    rq3.to_csv(out / "rq3_categories.csv", index=False)
    rep.table(rq3)
    rep.p(
        "**Issue found in the original notebook.** The RQ3 cell filters rows by "
        "`smell_category` but not by `smelly == True`, so each category's score mixes "
        "configurations where the requirement was presented in its smelly form with "
        "configurations where the same requirement was presented in its clean form. "
        "`accuracy_as_notebook` reproduces the published value; `accuracy_only_when_smelly` "
        "is what the paper describes. Separately, the LaTeX export cell prints GPT-4o's F1 "
        "in the Llama F1 column."
    )

    rep.save(out / "README.md")
    print(rq1[["model", "game", "max_abs_diff"]].to_string())
    print(glmm.to_string())
    print(rq3.to_string())


if __name__ == "__main__":
    main()
