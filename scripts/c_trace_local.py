"""Step C: fresh tracing runs with a free local model through Ollama.

Conditions per game:
  clean         all requirements in their clean form (the authors' no_smells)
  smelly        every smell-able requirement in its smelly form (the authors' all_smells)
  fixed_blind   the smelly set after the LLM fixer decided itself what to fix (scripts/e_fixer.py)
  fixed_rewrite the smelly set after the fixer rewrote every requirement as a "shall" statement
  fixed_oracle  the smelly set after the fixer rewrote only the known smelly requirements

Output follows the format of artifact/results_all.json so the same evaluation code applies.

Example:
  python scripts/c_trace_local.py --games dice_game --conditions clean smelly --runs 1
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from smellrep import llm
from smellrep.data import _to_bool, load_code, load_requirements, parse_lines
from smellrep.paths import GAMES, GENERATED
from smellrep.prompts import tracing_messages

CONDITIONS = ["clean", "smelly", "fixed_blind", "fixed_rewrite", "fixed_oracle"]
DEFAULT_CONDITIONS = ["clean", "smelly", "fixed_rewrite", "fixed_oracle"]


def model_tag(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "_", model)


def requirement_set(game: str, condition: str, model: str) -> tuple[list[tuple[int, str]], list[int]]:
    reqs = load_requirements(game)
    smelly_ids = reqs.loc[reqs["smelly"].notna(), "id"].astype(int).tolist()
    if condition == "clean":
        return list(zip(reqs["id"].astype(int), reqs["clean"])), []
    if condition == "smelly":
        texts = reqs["smelly"].fillna(reqs["clean"])
        return list(zip(reqs["id"].astype(int), texts)), smelly_ids
    mode = condition.removeprefix("fixed_")
    path = GENERATED / "fixed" / model_tag(model) / mode / f"{game}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run scripts/e_fixer.py --mode {mode} first")
    fixed = pd.read_csv(path)
    return list(zip(fixed["id"].astype(int), fixed["fixed"])), smelly_ids


def parse_tracing(text: str, ids: list[int]) -> tuple[list[dict], dict]:
    info = {"parse_error": False, "missing": 0, "extra": 0}
    try:
        items = llm.find_list(llm.parse_json(text), ("requirements", "tracing", "traces"))
    except ValueError:
        items, info["parse_error"] = [], True
    by_id = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        m = re.search(r"\d+", str(it.get("requirement_id", it.get("id", ""))))
        if not m:
            continue
        rid = int(m.group())
        if rid not in ids:
            info["extra"] += 1
            continue
        impl = _to_bool(it.get("implemented", False))
        lines = parse_lines(it.get("lines_of_code", it.get("lines", [])))
        by_id[rid] = {
            "requirement_id": rid,
            "implemented": bool(impl) if impl == impl else False,
            "lines_of_code": lines,
        }
    out = []
    for rid in ids:
        if rid not in by_id:
            info["missing"] += 1
            out.append({"requirement_id": rid, "implemented": False, "lines_of_code": []})
        else:
            out.append(by_id[rid])
    return out, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--games", nargs="+", default=GAMES)
    ap.add_argument("--conditions", nargs="+", default=DEFAULT_CONDITIONS, choices=CONDITIONS)
    ap.add_argument("--runs", type=int, default=1, help="repetitions per condition (seed varies)")
    ap.add_argument("--num-ctx", type=int, default=8192)
    args = ap.parse_args()

    out_dir = GENERATED / "local_runs" / model_tag(args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "runs.jsonl"
    done = set()
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["id"])

    for condition in args.conditions:
        for game in args.games:
            reqs, smelly_ids = requirement_set(game, condition, args.model)
            ids = [rid for rid, _ in reqs]
            messages = tracing_messages(load_code(game), reqs)
            for run in range(1, args.runs + 1):
                run_id = f"{game}/{condition}_01/local/{run:02d}"
                if run_id in done:
                    continue
                content, stats = llm.chat(
                    messages, model=args.model, seed=run, num_ctx=args.num_ctx
                )
                traces, info = parse_tracing(content, ids)
                if info["parse_error"] or info["missing"] == len(ids):
                    # Greedy decoding would repeat the same failure, so the retry samples.
                    content, stats = llm.chat(
                        messages, model=args.model, seed=100 + run, num_ctx=args.num_ctx,
                        temperature=0.4,
                    )
                    traces, info = parse_tracing(content, ids)
                    info["retried"] = True
                record = {
                    "id": run_id, "game": game, "experiment": f"{condition}_01",
                    "timestamp": "local", "run": run, "model": args.model,
                    "smelly_requirements": smelly_ids, "requirements": traces,
                    "stats": stats, "parse": info, "raw": content,
                }
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
                print(f"{run_id}: {stats['seconds']}s, prompt={stats['prompt_tokens']} "
                      f"out={stats['output_tokens']} parse={info}", flush=True)

    records = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    slim = [{k: v for k, v in r.items() if k not in ("raw", "stats", "parse")} for r in records]
    (out_dir / "results_all.json").write_text(json.dumps(slim), encoding="utf-8")
    print(f"{len(slim)} runs -> {out_dir / 'results_all.json'}")


if __name__ == "__main__":
    main()
