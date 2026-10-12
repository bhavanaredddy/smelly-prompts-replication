import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

GAME_ORDER = ["dice game", "arkanoid", "snake", "scopa", "pong"]


def line_by_game(df, y, title, path, ylim=(0.4, 1.05)):
    """Same layout as the authors' RQ2 line plots."""
    d = df.copy()
    d["game"] = d["game"].replace({"dice_game": "dice game"})
    d = d.sort_values("percentage_smelly")
    sns.set(style="whitegrid")
    plt.figure(figsize=(6, 4))
    sns.lineplot(
        x="percentage_smelly", y=y, hue="game", style="game", hue_order=GAME_ORDER,
        style_order=GAME_ORDER, data=d, markers=True, dashes=False, linewidth=1.5,
    )
    plt.xticks(range(0, 81, 10), [f"{i} %" for i in range(0, 81, 10)], fontsize=8)
    plt.ylim(*ylim)
    plt.xlabel("Smelly Requirements Percentage")
    plt.ylabel(f"Mean {y}")
    plt.title(title, fontsize=10)
    plt.legend(title="Game", fontsize=8, loc="lower left")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def save(fig_path):
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
