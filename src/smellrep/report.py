from pathlib import Path

import pandas as pd


def md_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return df.to_markdown(index=False, floatfmt=floatfmt)


class Report:
    """Accumulates markdown sections and writes them to a file."""

    def __init__(self, title: str):
        self.parts = [f"# {title}\n"]

    def h(self, text: str, level: int = 2):
        self.parts.append(f"\n{'#' * level} {text}\n")

    def p(self, text: str):
        self.parts.append(text.strip() + "\n")

    def table(self, df: pd.DataFrame, floatfmt: str = ".3f"):
        self.parts.append(md_table(df, floatfmt) + "\n")

    def code(self, text: str):
        self.parts.append("```\n" + text.rstrip() + "\n```\n")

    def image(self, path: Path, base: Path, alt: str = ""):
        self.parts.append(f"![{alt}]({path.relative_to(base).as_posix()})\n")

    def save(self, path: Path):
        path.write_text("\n".join(self.parts), encoding="utf-8")
        print(f"wrote {path}")
