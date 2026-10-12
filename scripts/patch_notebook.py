"""Makes the authors' Evaluation.ipynb run offline on the local artifact files.

Only the two cells that downloaded data from Google Drive are changed, plus one positional
Series lookup that current pandas no longer accepts. Optionally point it
at another results file (e.g. the friend's runs):
  python scripts/patch_notebook.py [--results path/to/results_all.json] [--out name.ipynb]
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../artifact/results_all.json")
    ap.add_argument("--out", default="Evaluation_local.ipynb")
    args = ap.parse_args()

    nb = json.loads((ROOT / "artifact" / "Evaluation.ipynb").read_text(encoding="utf-8"))
    replaced = 0
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        src = "".join(cell["source"])
        if "1ndohs_oWW4pFf6wUhkQmzHdRZ7iDsnqQ" in src:
            src = src.replace(
                "url = 'https://drive.google.com/uc?id=1ndohs_oWW4pFf6wUhkQmzHdRZ7iDsnqQ'\n\n"
                "response = requests.get(url)\ndata = json.loads(response.text)",
                f"with open({args.results!r}, encoding='utf-8') as f:\n    data = json.load(f)",
            )
            replaced += 1
        elif "1wJm__YhVkmJgv52vV6eYkvjf9y7DrgbN" in src:
            src = "ground_truth = pd.read_csv('../artifact/ground_truth.csv')\nground_truth"
            replaced += 1
        src = src.replace("[v[0] for v in random_effects.values()]",
                          "[v.iloc[0] for v in random_effects.values()]")
        cell["source"] = src
        cell["outputs"] = []
        cell["execution_count"] = None
    assert replaced == 2, f"expected to patch 2 cells, patched {replaced}"
    nb["cells"].insert(0, {
        "cell_type": "markdown", "metadata": {},
        "source": "**Local copy.** Identical to the authors' notebook except that results and "
                  "ground truth are read from the local artifact instead of Google Drive.",
    })
    nb.setdefault("metadata", {})["kernelspec"] = {
        "name": "smellrep", "display_name": "Python (smellrep)", "language": "python"}
    out = ROOT / "notebooks" / args.out
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
