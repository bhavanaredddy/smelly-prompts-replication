"""Rule-based requirements smell detector (word lists and regular expressions).

Semantic smells (logical inconsistencies, numerical discrepancies) cannot be found with
word lists; only a few numeric consistency heuristics are attempted for them.
"""

import re

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}

LEXICONS = {
    "subjective_language": [
        "fun", "easy", "easily", "user friendly", "user-friendly", "simple", "simply", "nice",
        "good", "great", "reasonable", "reasonably", "appropriate", "adequate", "fast",
        "quickly", "quick", "smooth", "smoothly", "enjoyable", "interesting", "intuitive",
        "convenient", "efficient", "beautiful", "pleasant", "exciting", "challenging",
        "suitable", "sufficient", "properly", "cool", "awesome", "attractive", "fair",
        "satisfying", "engaging", "nicely", "comfortable", "decent",
    ],
    "weak_verbs": ["can", "could", "may", "might", "would"],
    "optional_parts": [
        "possibly", "eventually", "if possible", "if needed", "if necessary", "optionally",
        "optional", "as needed", "where appropriate", "and/or", "potentially", "perhaps",
        "maybe", "if desired", "if wanted", "as required",
    ],
    "negative": [
        "not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot",
        "without", "unable",
    ],
    "ambiguities": [
        "some", "several", "certain", "various", "something", "somehow", "somewhere",
        "etc", "a few", "a number of", "a lot", "many", "different", "specific",
        "predetermined", "accordingly", "relevant", "similar", "usual", "normal",
        "some kind", "anything", "particular", "a while",
    ],
}

IRREGULAR_PARTICIPLES = (
    "put|shown|given|made|held|set|placed|dealt|drawn|thrown|known|seen|done|kept|left|"
    "lost|won|hit|shot|split|spent|told|sent|built|chosen|taken|broken|hidden|written"
)
PASSIVE = re.compile(
    rf"\b(am|is|are|was|were|be|been|being|get|gets|got|getting)\s+(\w+ly\s+)?"
    rf"(\w+ed|{IRREGULAR_PARTICIPLES})\b",
    re.I,
)
VAGUE_PRONOUN = re.compile(
    r"(^|[.;:,]\s*|\b(and|then|when|if|until|so)\s+)(it|they|them|this|that|these|those|he|she)\b"
    r"|\b(it|them|its)\b",
    re.I,
)


def _has_term(text: str, term: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text, re.I) is not None


def _number(tok: str):
    tok = tok.lower()
    if tok.isdigit():
        return int(tok)
    return WORD_NUMBERS.get(tok)


def numeric_issues(text: str) -> bool:
    """Internal numeric contradictions, e.g. "10 cards, from 1 to 12" or "four suits (a, b, c, d, e)"."""
    for m in re.finditer(r"\b(\w+)\s+\w+[^.]*?\bfrom\s+(\d+)\s+to\s+(\d+)", text, re.I):
        n, a, b = _number(m.group(1)), int(m.group(2)), int(m.group(3))
        if n and b >= a and b - a + 1 != n:
            return True
    for m in re.finditer(r"\b(\w+)\s+\w+\s*\(([^)]*)\)", text):
        n = _number(m.group(1))
        items = [x for x in re.split(r",|\band\b", m.group(2)) if x.strip()]
        if n and len(items) > 1 and len(items) != n:
            return True
    return False


def cross_requirement_numbers(texts: dict[int, str]) -> set[int]:
    """Flags requirements that give a different number for the same noun than another one."""
    seen: dict[str, dict[int, set[int]]] = {}
    for rid, t in texts.items():
        for m in re.finditer(r"\b(\d+|" + "|".join(WORD_NUMBERS) + r")\s+([a-z]+)", t, re.I):
            n, noun = _number(m.group(1)), m.group(2).lower().rstrip("s")
            if n is None or noun in ("point", "time", "second", "pixel"):
                continue
            seen.setdefault(noun, {}).setdefault(n, set()).add(rid)
    flagged = set()
    for noun, by_n in seen.items():
        if len(by_n) > 1:
            minority = min(by_n.values(), key=len)
            flagged |= minority
    return flagged


def detect(text: str) -> set[str]:
    found = set()
    for smell, terms in LEXICONS.items():
        if any(_has_term(text, t) for t in terms):
            found.add(smell)
    if "n't" in text.lower():
        found.add("negative")
    if PASSIVE.search(text):
        found.add("passive_voice")
    if VAGUE_PRONOUN.search(text):
        found.add("vague_pronouns")
    if numeric_issues(text):
        found.add("numerical_discrepancies")
    return found


def detect_list(texts: dict[int, str]) -> dict[int, set[str]]:
    out = {rid: detect(t) for rid, t in texts.items()}
    for rid in cross_requirement_numbers(texts):
        out[rid].add("numerical_discrepancies")
    return out
