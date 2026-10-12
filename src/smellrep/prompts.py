"""Rebuilds the authors' tracing prompt exactly (see artifact/llm.py and requirement.py)."""

from smellrep.paths import ARTIFACT

SYSTEM_PROMPT = (ARTIFACT / "system_prompt_guidelines.txt").read_text(encoding="utf-8")
USER_TEMPLATE = (ARTIFACT / "user_prompt.txt").read_text(encoding="utf-8")


def code_numbered(code: str) -> str:
    return "\n".join(f"{i + 1}. {line}" for i, line in enumerate(code.splitlines()))


def requirements_list(reqs: list[tuple[int, str]]) -> str:
    return "\n".join(f"{rid}. {text}" for rid, text in sorted(reqs))


def tracing_messages(code: str, reqs: list[tuple[int, str]]) -> list[dict]:
    user = USER_TEMPLATE.replace("{{code}}", code_numbered(code)).replace(
        "{{requirements}}", requirements_list(reqs)
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


SMELL_DEFINITIONS = """\
- passive_voice (syntactic): passive voice makes it unclear who performs an action.
- negative (syntactic): negative modifiers or expressions (e.g., "not", "no", "never").
- vague_pronouns (syntactic): pronouns whose referent is unclear.
- logical_inconsistencies (semantic): two requirements about the same concept contradict each other.
- numerical_discrepancies (semantic): two requirements about the same concept give inconsistent or contradicting numbers.
- ambiguities (semantic): sentences or parts that are imprecise and can be understood differently by different readers.
- subjective_language (lexical): words without objective meaning (user friendly, easy, reasonable, fun) or personal opinions.
- optional_parts (lexical): optional wording such as possibly, eventually, if possible, if needed.
- weak_verbs (lexical): weak verbs such as can, could, may, might."""
