from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifact"
FRIEND = ROOT / "friend" / "27153441"
RESULTS = ROOT / "results"
GENERATED = ROOT / "generated"

AUTHORS_RUNS = ARTIFACT / "results_all.json"
FRIEND_RUNS = FRIEND / "data" / "results" / "results_all.json"
GROUND_TRUTH = ARTIFACT / "ground_truth.csv"

GAMES = ["dice_game", "arkanoid", "snake", "scopa", "pong"]
GPT = "gpt-4o-2024-08-06"
LLAMA = "llama3.1:70b"

SMELL_TYPES = [
    "passive_voice",
    "negative",
    "vague_pronouns",
    "logical_inconsistencies",
    "numerical_discrepancies",
    "ambiguities",
    "subjective_language",
    "optional_parts",
    "weak_verbs",
]

SMELL_CATEGORY = {
    "passive_voice": "syntactic",
    "negative": "syntactic",
    "vague_pronouns": "syntactic",
    "logical_inconsistencies": "semantic",
    "numerical_discrepancies": "semantic",
    "ambiguities": "semantic",
    "subjective_language": "lexical",
    "optional_parts": "lexical",
    "weak_verbs": "lexical",
}


def out_dir(*parts: str) -> Path:
    p = RESULTS.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p
