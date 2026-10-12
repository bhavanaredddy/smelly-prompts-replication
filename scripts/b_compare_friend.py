"""Step B: check the friend's 550 new GPT-4o runs against the authors' original runs."""

import hashlib
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf

from smellrep import cache
from smellrep.data import load_runs
from smellrep.paths import ARTIFACT, AUTHORS_RUNS, FRIEND, FRIEND_RUNS, GAMES, GPT, out_dir
from smellrep.report import Report
from smellrep.stats import cohen_kappa

warnings.filterwarnings("ignore")

# Printed in the friend's Evaluation.ipynb (cells 24, 27, 48).
FRIEND_NB_RQ1 = {
    "arkanoid": (1.0, 0.749369, 0.800433, 0.731896),
    "dice_game": (0.96, 0.726357, 0.905902, 0.766912),
    "pong": (0.90, 0.549655, 0.829507, 0.609830),
    "scopa": (1.0, 0.705591, 0.842125, 0.739316),
    "snake": (0.928571, 0.556640, 0.748939, 0.587189),
}
FRIEND_NB_RQ3 = {"semantic": 0.829545, "syntactic": 0.977273, "lexical": 0.890152}

SAME_FILES = [
    ("results_all.json", "results_all.json"),
    ("ground_truth.csv", "ground_truth.csv"),
    ("prompts/system_prompt_guidelines.txt", "system_prompt_guidelines.txt"),
    ("prompts/user_prompt.txt", "user_prompt.txt"),
] + [
    (f"games/{i}_{g}/{g}_{kind}", f"{g}_{kind}")
    for i, g in enumerate(GAMES, 1)
    for kind in ("code.java", "requirements.csv", "requirements_smelly.csv")
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def jaccard(a, b):
    a, b = set(a), set(b)
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def main():
    out = out_dir("B_friend_check")
    rep = Report("Step B: friend's 550 GPT-4o runs vs. the authors' original runs")

    # ---- 1. inputs identical? ----
    rep.h("1. Are the friend's inputs identical to the Figshare artifact?")
    rows = [{"file": f, "identical": sha(FRIEND / f) == sha(ARTIFACT / a)} for f, a in SAME_FILES]
    integ = pd.DataFrame(rows)
    integ.to_csv(out / "input_integrity.csv", index=False)
    rep.p(f"{integ.identical.sum()} of {len(integ)} files byte-identical "
          "(code, requirements, prompts, ground truth, and the authors' results file).")
    if not integ.identical.all():
        rep.table(integ[~integ.identical])

    # ---- 2. the friend's own notebook numbers reproduce? ----
    a_req, a_exp = cache.authors()
    f_req, f_exp = cache.friend()
    a_req, a_exp = a_req[a_req.model == GPT], a_exp[a_exp.model == GPT]
    rep.h("2. Does our pipeline reproduce the numbers printed in the friend's notebook?")
    rows = []
    for game, vals in FRIEND_NB_RQ1.items():
        b = f_exp[(f_exp.game == game) & (f_exp.experiment == "no_smells_01")].iloc[0]
        ours = (b.accuracy, b.precision, b.recall, b.f1)
        rows.append({"game": game, **{f"ours_{k}": v for k, v in zip(["acc", "p", "r", "f1"], ours)},
                     "max_abs_diff": max(abs(x - y) for x, y in zip(ours, vals))})
    chk = pd.DataFrame(rows)
    rep.table(chk)
    cats = {c: f_req[f_req.smell_category == c]["correct"].mean() for c in FRIEND_NB_RQ3}
    rep.p("RQ3 category accuracy (notebook definition): " + ", ".join(
        f"{c} ours {v:.4f} / notebook {FRIEND_NB_RQ3[c]:.4f}" for c, v in cats.items()))

    # ---- 3. baselines side by side ----
    rep.h("3. No-smell and all-smell baselines: authors vs. friend (GPT-4o, majority of 5 runs)")
    cols = ["accuracy", "precision", "recall", "f1"]
    base = []
    for exp_name in ["no_smells_01", "all_smells_01"]:
        for game in GAMES:
            a = a_exp[(a_exp.game == game) & (a_exp.experiment == exp_name)].iloc[0]
            f = f_exp[(f_exp.game == game) & (f_exp.experiment == exp_name)].iloc[0]
            row = {"config": exp_name, "game": game}
            for c in cols:
                row[f"authors_{c}"] = a[c]
                row[f"friend_{c}"] = f[c]
            base.append(row)
    base = pd.DataFrame(base)
    means = base.groupby("config").mean(numeric_only=True).reset_index().assign(game="MEAN")
    base = pd.concat([base, means], ignore_index=True)
    base.to_csv(out / "baselines.csv", index=False)
    rep.table(base)

    # ---- 4. matched configurations ----
    rep.h("4. Agreement on identical prompts")
    a_sets = a_req.groupby(["game", "experiment"]).apply(
        lambda g: tuple(sorted(g.loc[g.smelly, "requirement_id"])), include_groups=False)
    f_sets = f_req.groupby(["game", "experiment"]).apply(
        lambda g: tuple(sorted(g.loc[g.smelly, "requirement_id"])), include_groups=False)
    pairs = []
    for (game, f_e), s in f_sets.items():
        matches = [a_e for (g2, a_e), s2 in a_sets.items() if g2 == game and s2 == s]
        if matches:
            pairs.append((game, f_e, matches[0]))
    rows = []
    for game, f_e, a_e in pairs:
        fa = f_req[(f_req.game == game) & (f_req.experiment == f_e)].set_index("requirement_id")
        aa = a_req[(a_req.game == game) & (a_req.experiment == a_e)].set_index("requirement_id")
        idx = fa.index.intersection(aa.index)
        for rid in idx:
            rows.append({
                "game": game, "friend_config": f_e, "authors_config": a_e, "requirement_id": rid,
                "authors_impl": aa.loc[rid, "implemented_pred"], "friend_impl": fa.loc[rid, "implemented_pred"],
                "lines_jaccard": jaccard(aa.loc[rid, "loc_predicted"], fa.loc[rid, "loc_predicted"]),
            })
    agree = pd.DataFrame(rows)
    agree.to_csv(out / "matched_agreement.csv", index=False)
    same = (agree.authors_impl == agree.friend_impl).mean()
    kappa = cohen_kappa(agree.authors_impl, agree.friend_impl)
    rep.p(
        f"{len(pairs)} configurations have exactly the same smelly set in both datasets "
        f"(the 10 baselines plus {len(pairs) - 10} random configurations that happen to coincide), "
        f"giving {len(agree)} requirement-level comparisons.\n\n"
        f"- Same implemented yes/no decision: **{same:.1%}** (Cohen's kappa {kappa:.2f})\n"
        f"- Mean Jaccard overlap of the majority-vote traced lines: **{agree.lines_jaccard.mean():.2f}** "
        f"(median {agree.lines_jaccard.median():.2f})"
    )

    # ---- 5. run-to-run stability at temperature 0 ----
    rep.h("5. Stability of the five repeats (temperature 0)")
    stab = pd.DataFrame([
        {"dataset": "authors GPT-4o", "unanimous_implemented": a_req.unanimous.mean()},
        {"dataset": "friend GPT-4o", "unanimous_implemented": f_req.unanimous.mean()},
    ])
    a_runs = load_runs(AUTHORS_RUNS)
    a_runs = a_runs[a_runs.model == GPT]
    f_runs = load_runs(FRIEND_RUNS)
    for df, name in [(a_runs, "authors GPT-4o"), (f_runs, "friend GPT-4o")]:
        g = df.groupby(["game", "experiment", "requirement_id"])["loc_predicted"].apply(
            lambda s: len({tuple(x) for x in s}) == 1)
        stab.loc[stab.dataset == name, "identical_lines_all_runs"] = g.mean()
    rep.p("Share of (configuration, requirement) pairs where all five runs gave the same answer:")
    rep.table(stab)

    # ---- 6. does the friend's data show the same smell effect? ----
    rep.h("6. Same trend? Accuracy vs. share of smelly requirements")
    a_exp = a_exp.assign(dataset="authors")
    f_exp = f_exp.assign(dataset="friend")
    both = pd.concat([a_exp, f_exp], ignore_index=True)
    rows = []
    for name, d in [("authors", a_exp), ("friend", f_exp)]:
        for y in ["accuracy", "f1"]:
            fit = smf.ols(f"{y} ~ percentage_smelly + C(game)", d).fit(cov_type="HC3")
            rows.append({"dataset": name, "outcome": y, "n_configs": len(d),
                         "slope_per_10pct": fit.params["percentage_smelly"] * 10,
                         "ci_low": fit.conf_int().loc["percentage_smelly", 0] * 10,
                         "ci_high": fit.conf_int().loc["percentage_smelly", 1] * 10,
                         "p": fit.pvalues["percentage_smelly"]})
    for y in ["accuracy", "f1"]:
        fit = smf.ols(f"{y} ~ percentage_smelly * dataset + C(game)", both).fit(cov_type="HC3")
        term = "percentage_smelly:dataset[T.friend]"
        rows.append({"dataset": "difference (friend - authors)", "outcome": y,
                     "n_configs": len(both), "slope_per_10pct": fit.params[term] * 10,
                     "ci_low": fit.conf_int().loc[term, 0] * 10,
                     "ci_high": fit.conf_int().loc[term, 1] * 10, "p": fit.pvalues[term]})
    trend = pd.DataFrame(rows)
    trend.to_csv(out / "trend_comparison.csv", index=False)
    rep.p("OLS with game fixed effects and HC3 robust standard errors; slope = change in the "
          "outcome per 10 percentage points more smelly requirements.")
    rep.table(trend, ".4f")

    sns.set(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, y in zip(axes, ["accuracy", "f1"]):
        sns.regplot(data=a_exp, x="percentage_smelly", y=y, ax=ax, scatter_kws={"s": 8, "alpha": .3},
                    label=f"authors (n={len(a_exp)})", x_jitter=1)
        sns.regplot(data=f_exp, x="percentage_smelly", y=y, ax=ax, scatter_kws={"s": 14, "alpha": .6},
                    label=f"friend (n={len(f_exp)})", x_jitter=1)
        ax.set_xlabel("smelly requirements (%)")
        ax.set_title(f"GPT-4o {y} per configuration")
        ax.legend()
    plt.tight_layout()
    fig_path = out / "trend_authors_vs_friend.png"
    plt.savefig(fig_path, dpi=150)
    plt.close()
    rep.image(fig_path, out, "trend")

    rep.save(out / "README.md")
    print(integ.identical.value_counts().to_string())
    print(chk.to_string())
    print(cats)
    print(base.to_string())
    print("pairs", len(pairs), "agree", same, "kappa", kappa, "jacc", agree.lines_jaccard.mean())
    print(stab.to_string())
    print(trend.to_string())


if __name__ == "__main__":
    main()
