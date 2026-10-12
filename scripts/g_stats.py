"""Improved statistics on the authors' 6,100 runs (and the friend's 550 as a replication).

The paper regresses configuration-level accuracy on the share of smelly requirements with a
linear mixed model that has only 5 game groups and did not converge for most outcomes.
Here the unit of analysis is the requirement inside a configuration (after the same
majority vote), which allows a within-requirement comparison: the *same* requirement
presented smelly vs. clean.

Models
  M1  linear probability model, requirement fixed effects, SE clustered by requirement
      correct ~ smelly + pct_other_smelly + C(req_key)
  M2  logistic regression, game fixed effects, SE clustered by requirement -> odds ratios
  M3  conditional (fixed-effects) logit grouped by requirement
  M4  configuration-level binomial GLM (the paper's question, properly bounded)
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from smellrep import cache
from smellrep.paths import GPT, LLAMA, out_dir
from smellrep.report import Report

warnings.filterwarnings("ignore")

SHORT = {GPT: "GPT-4o", LLAMA: "Llama-3.1-70B", "friend": "GPT-4o (friend)"}


def lpm_fe(d: pd.DataFrame, y: str, terms=("smelly", "pct_other_smelly")):
    d = d.dropna(subset=[y]).copy()
    d[y] = d[y].astype(float)
    d["smelly"] = d["smelly"].astype(float)
    f = f"{y} ~ " + " + ".join(terms) + " + C(req_key)"
    fit = smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": d["req_key"].astype("category").cat.codes})
    rows = []
    for t in terms:
        lo, hi = fit.conf_int().loc[t]
        rows.append({"term": t, "estimate": fit.params[t], "ci_low": lo, "ci_high": hi,
                     "p": fit.pvalues[t], "n": int(fit.nobs), "clusters": d.req_key.nunique()})
    return rows


def _prep_binary(d: pd.DataFrame, y: str) -> pd.DataFrame:
    d = d.dropna(subset=[y]).copy()
    d[y] = d[y].astype(int)
    d["smelly"] = d["smelly"].astype(int)
    d["pct_other_smelly_10"] = d["pct_other_smelly"] / 10
    return d


def _or_rows(fit, terms):
    rows = []
    for t in terms:
        lo, hi = fit.conf_int().loc[t]
        rows.append({"term": t, "odds_ratio": np.exp(fit.params[t]), "or_ci_low": np.exp(lo),
                     "or_ci_high": np.exp(hi), "p": fit.pvalues[t]})
    return rows


def logit_cluster(d: pd.DataFrame, y: str):
    """Pooled logistic regression with game fixed effects, SE clustered by requirement."""
    d = _prep_binary(d, y)
    fit = smf.glm(f"{y} ~ smelly + pct_other_smelly_10 + C(game)", d,
                  family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": d["req_key"].astype("category").cat.codes})
    return _or_rows(fit, ["smelly", "pct_other_smelly_10"])


def conditional_logit(d: pd.DataFrame, y: str):
    """Within-requirement logistic model. Requirements that are always (or never) correct carry
    no information and drop out automatically."""
    from statsmodels.discrete.conditional_models import ConditionalLogit

    d = _prep_binary(d, y)
    keep = d.groupby("req_key")[y].transform("nunique") > 1
    d = d[keep]
    exog = d[["smelly", "pct_other_smelly_10"]].astype(float)
    fit = ConditionalLogit(d[y].values, exog, groups=d["req_key"].values).fit(disp=0)
    rows = _or_rows(fit, ["smelly", "pct_other_smelly_10"])
    for r in rows:
        r["informative_reqs"] = d.req_key.nunique()
    return rows


def config_glm(exp: pd.DataFrame):
    rows = []
    for model, d in exp.groupby("model"):
        d = d.copy()
        d["pct10"] = d["percentage_smelly"] / 10
        fit = smf.glm("n_correct + I(n - n_correct) ~ pct10 + C(game)", d,
                      family=sm.families.Binomial()).fit()
        lo, hi = fit.conf_int().loc["pct10"]
        rows.append({"model": SHORT.get(model, model), "OR_per_10pct": np.exp(fit.params["pct10"]),
                     "ci_low": np.exp(lo), "ci_high": np.exp(hi), "p": fit.pvalues["pct10"],
                     "pearson_chi2_per_df": fit.pearson_chi2 / fit.df_resid})
    return pd.DataFrame(rows)


def main():
    out = out_dir("G_statistics")
    rep = Report("Improved statistics: is the smell effect real, and how large is it?")
    a_req, a_exp = cache.authors()
    f_req, f_exp = cache.friend()
    f_req = f_req.assign(model="friend")
    f_exp = f_exp.assign(model="friend")
    req = pd.concat([a_req, f_req], ignore_index=True)
    exp = pd.concat([a_exp, f_exp], ignore_index=True)

    # ---------- context: trivial baseline ----------
    rep.h("0. Context: how hard is the yes/no decision?")
    base = req.groupby("model").agg(
        model_accuracy=("correct", "mean"),
        always_yes_accuracy=("expected", "mean"),
        share_smelly=("smelly", "mean"),
    ).reset_index()
    base["model"] = base["model"].map(SHORT)
    rep.p("`always_yes_accuracy` is the accuracy of a dummy that answers *implemented* for "
          "every requirement. The binary task is lopsided, so small accuracy changes matter.")
    rep.table(base)

    # ---------- M1 + M2 + M3 ----------
    rep.h("1. Within-requirement effect of a smell on the yes/no decision")
    rows = []
    for model, d in req.groupby("model"):
        for y, label in [("correct", "vs. dataset label"), ("correct_intent", "vs. original intent")]:
            for r in lpm_fe(d, y):
                rows.append({"model": SHORT[model], "outcome": label, **r})
    m1 = pd.DataFrame(rows)
    m1.to_csv(out / "m1_lpm_fixed_effects.csv", index=False)
    rep.p(
        "**M1** linear probability model with one fixed effect per requirement, so `smelly` is "
        "estimated only from the same requirement appearing smelly in some configurations and "
        "clean in others. Estimates are percentage-point changes in the probability of a correct "
        "decision; `pct_other_smelly` is per 1 point of the *other* requirements being smelly "
        "(spill-over). *vs. dataset label* uses the authors' scoring (for smelly requirements the "
        "correct answer is `smelly_traceable`); *vs. original intent* scores against whether the "
        "clean requirement is implemented."
    )
    rep.table(m1, ".4f")

    rows = []
    for model, d in req.groupby("model"):
        for y, label in [("correct", "vs. dataset label"), ("correct_intent", "vs. original intent")]:
            for r in logit_cluster(d, y):
                rows.append({"model": SHORT[model], "outcome": label, "method": "M2 logit, clustered SE", **r})
            for r in conditional_logit(d, y):
                rows.append({"model": SHORT[model], "outcome": label, "method": "M3 conditional logit", **r})
    m23 = pd.DataFrame(rows)
    m23.to_csv(out / "m2_m3_odds_ratios.csv", index=False)
    rep.p("**M2/M3** odds ratios for a correct decision. `pct_other_smelly_10` is per 10 points "
          "of the other requirements being smelly. M3 compares each requirement only with itself "
          "and uses only requirements whose correctness varies; its standard errors treat the "
          "configurations of one requirement as independent, so its p-values are optimistic. "
          "M1 (clustered) is the primary test.")
    rep.table(m23, ".3f")

    # ---------- label flips ----------
    rep.h("2. Where does the drop come from? Smells that change the correct answer")
    sm_ = req[req.smelly].copy()
    sm_["label_flipped"] = sm_["smelly_traceable"] != sm_["implemented_actual"]
    flip = sm_.groupby(["model", "label_flipped"]).agg(
        n=("correct", "size"), accuracy=("correct", "mean"),
        said_implemented=("implemented_pred", "mean")).reset_index()
    flip["model"] = flip["model"].map(SHORT)
    flip.to_csv(out / "label_flips.csv", index=False)
    n_flip = int(req[req.smelly].drop_duplicates("req_key").pipe(
        lambda x: (x.smelly_traceable != x.implemented_actual).sum()))
    rep.p(
        f"In {n_flip} requirements the smelly rewrite makes the requirement *untraceable* "
        "(e.g., a contradiction), so the authors' ground truth flips from yes to no. "
        "`said_implemented` is how often the model still answered yes."
    )
    rep.table(flip)
    rows = []
    for model, d in req.groupby("model"):
        keys_flip = set(sm_.loc[sm_.label_flipped, "req_key"])
        d2 = d[~d.req_key.isin(keys_flip)]
        for r in lpm_fe(d2, "correct"):
            rows.append({"model": SHORT[model], "subset": "requirements whose label does not flip", **r})
    noflip = pd.DataFrame(rows)
    noflip.to_csv(out / "m1_without_label_flips.csv", index=False)
    rep.p("M1 re-estimated without the label-flipping requirements:")
    rep.table(noflip, ".4f")

    # ---------- LOC ----------
    rep.h("3. Effect on the traced lines (F1)")
    rows = []
    for model, d in req.groupby("model"):
        for y, label in [("f1", "notebook F1 (drops empty predictions)"),
                         ("f1_strict", "strict F1 (empty prediction = 0)")]:
            for r in lpm_fe(d, y):
                rows.append({"model": SHORT[model], "outcome": label, **r})
    loc = pd.DataFrame(rows)
    loc.to_csv(out / "m1_loc_f1.csv", index=False)
    rep.p("Same M1 design with line-level F1 as outcome (F1 points, 0-1 scale).")
    rep.table(loc, ".4f")

    # ---------- configuration level ----------
    rep.h("4. The paper's configuration-level question with a bounded model")
    m4 = config_glm(exp)
    m4.to_csv(out / "m4_config_binomial.csv", index=False)
    rep.p("**M4** binomial GLM of correct decisions per configuration with game fixed effects. "
          "Odds ratio per 10 points more smelly requirements. The dispersion is far below 1 "
          "because the same requirements recur in every configuration, so the binomial SEs "
          "are kept rather than shrunk; M1-M3 are the more trustworthy tests.")
    rep.table(m4, ".4f")

    # ---------- figure ----------
    fig, ax = plt.subplots(figsize=(7, 3.5))
    d = m1[m1.term == "smelly"].reset_index(drop=True)
    labels = d["model"] + " | " + d["outcome"]
    y = np.arange(len(d))
    ax.errorbar(d.estimate * 100, y, xerr=[(d.estimate - d.ci_low) * 100, (d.ci_high - d.estimate) * 100],
                fmt="o", capsize=3)
    ax.axvline(0, color="grey", ls="--")
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_xlabel("change in P(correct) when smelly (pp, 95% CI)")
    plt.tight_layout()
    p = out / "forest_smelly_effect.png"
    plt.savefig(p, dpi=150)
    plt.close()
    rep.image(p, out, "forest plot")

    rep.save(out / "README.md")
    for t in (base, m1, m23, flip, noflip, loc, m4):
        print(t.to_string(), "\n")


if __name__ == "__main__":
    main()
