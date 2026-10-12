"""Which smell types hurt most, in which game, and which requirements fail?

Every number is a within-requirement contrast: the same requirement when it appears
smelly vs. when it appears clean in the authors' random configurations (majority vote of
five runs, as in the paper).
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
import seaborn as sns

from smellrep import cache
from smellrep.data import load_requirements
from smellrep.paths import GAMES, GPT, LLAMA, SMELL_CATEGORY, out_dir
from smellrep.report import Report
from smellrep.stats import cluster_bootstrap_diff

warnings.filterwarnings("ignore")
SHORT = {GPT: "GPT-4o", LLAMA: "Llama-3.1-70B"}


def per_requirement(req: pd.DataFrame) -> pd.DataFrame:
    d = req[req.smell_type.notna()]
    g = d.groupby(["model", "game", "requirement_id", "req_key", "smell_type", "smell_category", "smelly"])
    agg = g.agg(acc=("correct", "mean"), acc_intent=("correct_intent", "mean"),
                f1=("f1_strict", "mean"), said_yes=("implemented_pred", "mean"),
                n=("correct", "size")).reset_index()
    wide = agg.pivot_table(index=["model", "game", "requirement_id", "req_key", "smell_type", "smell_category"],
                           columns="smelly", values=["acc", "acc_intent", "f1", "said_yes", "n"])
    wide.columns = [f"{a}_{'smelly' if b else 'clean'}" for a, b in wide.columns]
    wide = wide.reset_index()
    for m in ["acc", "acc_intent", "f1"]:
        wide[f"delta_{m}"] = wide[f"{m}_smelly"] - wide[f"{m}_clean"]
    return wide


def main():
    out = out_dir("H_breakdown")
    figs = out_dir("H_breakdown", "figures")
    rep = Report("Breakdown by smell type, game, and requirement")
    req, _ = cache.authors()
    gt_flip = req.drop_duplicates("req_key").set_index("req_key")
    flipped = set(gt_flip.index[(gt_flip.smelly_traceable.notna())
                                & (gt_flip.smelly_traceable != gt_flip.implemented_actual)])

    rep.p(
        "Delta = (score when the requirement is smelly) - (score of the same requirement when "
        "clean), averaged over the random configurations. Accuracy is the implemented yes/no "
        "decision scored like the paper; *intent* scores against the clean requirement's ground "
        "truth; F1 is line-level F1 with empty predictions counted as 0. 95% CIs bootstrap "
        "whole requirements. Requirements whose smelly version flips the ground truth to "
        f"*not traceable* ({len(flipped)}) are marked with *."
    )

    # ---------- by smell type ----------
    rep.h("1. By smell type")
    rows = []
    for model, d in req[req.smell_type.notna()].groupby("model"):
        for st, ds in d.groupby("smell_type"):
            r = {"model": SHORT[model], "smell_type": st, "category": SMELL_CATEGORY[st],
                 "n_reqs": ds.req_key.nunique(),
                 "n_label_flips": len(set(ds.req_key) & flipped)}
            for metric, name in [("correct", "acc"), ("correct_intent", "acc_intent"), ("f1_strict", "f1")]:
                dd = ds.dropna(subset=[metric]).assign(smelly=lambda x: x.smelly.astype(int))
                est, lo, hi = cluster_bootstrap_diff(dd, "req_key", metric, "smelly", 0, 1, n=1000)
                r[f"delta_{name}"], r[f"{name}_lo"], r[f"{name}_hi"] = est, lo, hi
            rows.append(r)
    by_type = pd.DataFrame(rows).sort_values(["model", "delta_acc"])
    by_type.to_csv(out / "by_smell_type.csv", index=False)
    rep.table(by_type)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    order = by_type[by_type.model == "GPT-4o"].sort_values("delta_acc").smell_type.tolist()
    for ax, metric, title in [(axes[0], "acc", "yes/no accuracy"), (axes[1], "f1", "line F1")]:
        for i, (model, d) in enumerate(by_type.groupby("model")):
            d = d.set_index("smell_type").loc[order]
            y = np.arange(len(order)) + (i - 0.5) * 0.3
            ax.errorbar(d[f"delta_{metric}"], y, xerr=[d[f"delta_{metric}"] - d[f"{metric}_lo"],
                        d[f"{metric}_hi"] - d[f"delta_{metric}"]], fmt="o", capsize=2, label=model)
        ax.axvline(0, color="grey", ls="--")
        ax.set_yticks(np.arange(len(order)), order, fontsize=8)
        ax.set_title(f"change in {title} when smelly")
        ax.legend(fontsize=8)
    plt.tight_layout()
    p = figs / "by_smell_type.png"
    plt.savefig(p, dpi=150)
    plt.close()
    rep.image(p, out, "by type")

    # ---------- by category, corrected ----------
    rep.h("2. By category (corrected RQ3: only configurations where the requirement is smelly)")
    rows = []
    for model, d in req[req.smell_category.notna()].groupby("model"):
        for cat, dc in d.groupby("smell_category"):
            for subset, dd in [("all", dc), ("without label flips", dc[~dc.req_key.isin(flipped)])]:
                rows.append({"model": SHORT[model], "category": cat, "subset": subset,
                             "acc_smelly": dd[dd.smelly].correct.mean(),
                             "acc_clean": dd[~dd.smelly].correct.mean(),
                             "f1_smelly": dd[dd.smelly].f1_strict.mean(),
                             "f1_clean": dd[~dd.smelly].f1_strict.mean()})
    by_cat = pd.DataFrame(rows)
    by_cat["delta_acc"] = by_cat.acc_smelly - by_cat.acc_clean
    by_cat["delta_f1"] = by_cat.f1_smelly - by_cat.f1_clean
    by_cat.to_csv(out / "by_category.csv", index=False)
    rep.table(by_cat)

    # ---------- by game x type ----------
    rep.h("3. Smell type x game (change in accuracy, GPT-4o | Llama-3.1-70B)")
    pr = per_requirement(req)
    pr.to_csv(out / "per_requirement.csv", index=False)
    heat = pr.groupby(["model", "smell_type", "game"]).delta_acc.mean().reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, (model, d) in zip(axes, heat.groupby("model")):
        piv = d.pivot(index="smell_type", columns="game", values="delta_acc").reindex(columns=GAMES)
        sns.heatmap(piv, annot=True, fmt=".2f", cmap="RdBu", center=0, vmin=-1, vmax=1, ax=ax, cbar=False)
        ax.set_title(SHORT[model])
    plt.tight_layout()
    p = figs / "type_by_game.png"
    plt.savefig(p, dpi=150)
    plt.close()
    rep.image(p, out, "type x game")

    # ---------- worst requirements ----------
    rep.h("4. Requirements that fail most when smelly")
    texts = pd.concat([load_requirements(g) for g in GAMES])
    texts["req_key"] = texts.game + "#" + texts.id.astype(str)
    worst = (pr.groupby(["req_key", "game", "requirement_id", "smell_type"])
             [["delta_acc", "delta_f1", "said_yes_smelly"]].mean().reset_index()
             .sort_values("delta_acc").head(15))
    worst = worst.merge(texts[["req_key", "clean", "smelly"]], on="req_key")
    worst["flip"] = worst.req_key.isin(flipped).map({True: "*", False: ""})
    worst.to_csv(out / "worst_requirements.csv", index=False)
    rep.p("Mean over both models. `said_yes_smelly` = how often the model still answered "
          "*implemented* for the smelly version.")
    for r in worst.itertuples():
        rep.p(f"- **{r.req_key}{r.flip}** ({r.smell_type}) delta acc {r.delta_acc:+.2f}, delta F1 "
              f"{r.delta_f1:+.2f}, said yes {r.said_yes_smelly:.0%}  \n"
              f"  clean: _{r.clean}_  \n  smelly: _{r.smelly}_")

    # ---------- per game ----------
    rep.h("5. Per game")
    per_game = pr.groupby(["model", "game"])[["delta_acc", "delta_acc_intent", "delta_f1"]].mean().reset_index()
    per_game["model"] = per_game.model.map(SHORT)
    per_game.to_csv(out / "per_game.csv", index=False)
    rep.table(per_game)

    rep.save(out / "README.md")
    print(by_type.to_string())
    print(by_cat.to_string())
    print(worst[["req_key", "smell_type", "delta_acc", "delta_f1", "said_yes_smelly", "flip"]].to_string())
    print(per_game.to_string())


if __name__ == "__main__":
    main()
