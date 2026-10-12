"""Smell fixer: a free local LLM rewrites smelly requirements into clear ones.

The fixer never sees the code, so it cannot tailor requirements to the implementation.

  --mode blind    the fixer gets the whole smelly list and decides itself what to rewrite
  --mode rewrite  the fixer must rewrite every requirement into a precise "shall" statement
                  (no hint which ones are smelly)
  --mode oracle   the fixer is told which requirements are smelly and with which smell type
                  (an upper bound for a perfect detector)

Writes generated/fixed/<model>/<mode>/<game>.csv with columns id, input, fixed, changed.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from smellrep import llm
from smellrep.data import load_requirements
from smellrep.paths import GAMES, GENERATED
from smellrep.prompts import SMELL_DEFINITIONS

SYSTEM = f"""You are an expert requirements engineer. You improve the quality of natural-language
software requirements by removing requirements smells. The smell types are:

{SMELL_DEFINITIONS}

Rules:
- Keep the intended meaning. Do not add new features or remove existing ones.
- Name the actor explicitly (e.g., "the program", "the player") instead of passive voice.
- Replace vague pronouns with the noun they refer to.
- Replace weak verbs and optional wording with "shall" statements.
- Replace subjective or vague words with precise wording. If another requirement in the
  list states the precise value, use it. Never invent numbers that appear nowhere in the list.
- Resolve contradictions and inconsistent numbers in favor of the reading that is consistent
  with the other requirements and with common knowledge about the game.
{{unchanged_rule}}
- Output JSON: {{"requirements": [{{"id": <int>, "text": "<rewritten requirement>"}}, ...]}}
  with exactly one entry per input requirement, in the same order."""

UNCHANGED_RULE = {
    "blind": "- Leave requirements that have no smell unchanged.",
    "oracle": "- Leave requirements that have no smell unchanged.",
    "rewrite": "- Rewrite every requirement as one precise, testable statement using \"shall\", "
               "even if it already looks fine.",
}

TASK = {
    "blind": "Rewrite every requirement that contains a smell; copy the others unchanged.",
    "rewrite": "Rewrite every requirement into a precise, unambiguous, testable \"shall\" statement.",
    "oracle": "Rewrite only the requirements marked with [SMELL: ...] to remove that smell; copy "
              "the others unchanged (without the marker).",
}


def user_prompt(game: str, reqs: pd.DataFrame, mode: str) -> str:
    lines = []
    for _, r in reqs.iterrows():
        line = f"{r.id}. {r.input}"
        if mode == "oracle" and isinstance(r.smell_type, str):
            line += f"   [SMELL: {r.smell_type}]"
        lines.append(line)
    task = TASK[mode]
    name = game.replace("_", " ")
    return f"Requirements of a {name} computer game:\n\n" + "\n".join(lines) + f"\n\n{task}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--mode", choices=["blind", "rewrite", "oracle"], default="rewrite")
    ap.add_argument("--games", nargs="+", default=GAMES)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    tag = re.sub(r"[^A-Za-z0-9.]+", "_", args.model)
    out = GENERATED / "fixed" / tag / args.mode
    out.mkdir(parents=True, exist_ok=True)

    for game in args.games:
        path = out / f"{game}.csv"
        if path.exists() and not args.force:
            print(f"skip {path}")
            continue
        reqs = load_requirements(game)
        reqs["input"] = reqs["smelly"].fillna(reqs["clean"])
        messages = [
            {"role": "system", "content": SYSTEM.replace("{unchanged_rule}", UNCHANGED_RULE[args.mode])},
            {"role": "user", "content": user_prompt(game, reqs, args.mode)},
        ]
        content, stats = llm.chat(messages, model=args.model)
        try:
            items = llm.find_list(llm.parse_json(content), ("requirements",))
        except ValueError:
            items = []
        rewritten = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            m = re.search(r"\d+", str(it.get("id", it.get("requirement_id", ""))))
            text = it.get("text") or it.get("requirement") or it.get("description")
            if m and isinstance(text, str) and text.strip():
                rewritten[int(m.group())] = re.sub(r"\s*\[SMELL:[^\]]*\]", "", text).strip()
        fixed = []
        for _, r in reqs.iterrows():
            new = rewritten.get(int(r.id), r.input)
            if args.mode == "oracle" and not isinstance(r.smell_type, str):
                new = r.input
            fixed.append(new)
        reqs["fixed"] = fixed
        reqs["changed"] = reqs["fixed"] != reqs["input"]
        reqs[["id", "input", "fixed", "changed", "clean", "smell_type", "smell_category"]].to_csv(
            path, index=False
        )
        (out / f"{game}_raw.json").write_text(
            json.dumps({"stats": stats, "raw": content}, indent=2), encoding="utf-8"
        )
        print(f"{game}: {stats['seconds']}s, parsed {len(rewritten)}/{len(reqs)}, "
              f"changed {int(reqs['changed'].sum())}", flush=True)


if __name__ == "__main__":
    main()
