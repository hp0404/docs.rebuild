import os
import re
import json
import pytz
import datetime
import typing
from pathlib import Path

import pandas as pd

JSON = typing.Dict[str, typing.Any]
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs" / "source"
INDEX = SOURCE / "index.md"

NOW = datetime.datetime.now(pytz.timezone("Europe/Kyiv"))


class Config(typing.NamedTuple):
    TAGS: typing.Dict[str, str]
    SUGGESTIONS: typing.List[str]
    IGNORE_TAGS: typing.List[str]

    @classmethod
    def from_json(cls, filepath: Path, *, encoding: str = "utf-8") -> "Config":
        with filepath.open("r", encoding=encoding) as f:
            data = json.load(f)
        return Config(
            TAGS=data["question_types"],
            SUGGESTIONS=data["suggestions"],
            IGNORE_TAGS=data["ignore_tag"],
        )


config = Config.from_json(ROOT / "config.json")


def read_questions() -> JSON:
    df = pd.read_csv(os.environ["URL"])
    df["Позначка часу"] = pd.to_datetime(df["Позначка часу"])
    df = (
        df.loc[df["Позначка часу"].notnull()]
        .sort_values("Позначка часу", ascending=False)
        .copy()
    )
    df["type"] = df["тип питання 'змістовна проблема'"].combine_first(
        df["Я заповнюю форму, тому що"]
    )
    sections = df["type"].unique().tolist()
    for tag in config.IGNORE_TAGS:
        if tag in sections:
            sections.remove(tag)

    transformed_data = {}
    for section in sections:
        if section in config.SUGGESTIONS:
            data = df.loc[df["Статус"].eq("в процесі") & df["type"].eq(section)].copy()
            data["Відповідь (текст)"] = data["Відповідь (текст)"].fillna("На розгляді")
        else:
            data = df.loc[
                df["Відповідь (текст)"].notnull()
                & df["Статус"].eq("виконано")
                & df["type"].eq(section)
            ]
        records = data.to_dict(orient="records")
        transformed_data[section] = records
    return transformed_data


def format_question(item: JSON) -> str:
    return "> *{question}*\n\n{answer}\n".format(
        question=item["Опишіть, будь ласка, суть пропозиції/звернення"]
        .replace("\n", " ")
        .replace("*", "")
        .strip(),
        answer=item["Відповідь (текст)"],
    )


def update_docs(
    original_tag: str, readme_content: str, questions: str, inline: bool
) -> str:
    tag = config.TAGS[original_tag]
    pattern = re.compile(
        rf"<!-- {tag} starts -->.*<!-- {tag} ends -->",
        re.DOTALL,
    )
    if not inline:
        questions = f"\n{questions}\n"
    chunk = rf"<!-- {tag} starts -->{questions}<!-- {tag} ends -->"
    return pattern.sub(chunk, readme_content)


def main() -> int:
    data = read_questions()
    readme_contents = INDEX.read_text(encoding="utf-8")
    rewritten_readme = update_docs(
        "date", readme_contents, NOW.strftime("%d.%m.%Y %H:%M:%S"), inline=True
    )
    for section, questions in data.items():
        formatted_questions = "\n---\n".join(
            format_question(question) for question in questions
        )
        rewritten_readme = update_docs(
            section, rewritten_readme, formatted_questions, inline=False
        )
        with INDEX.open("w", encoding="utf-8") as output:
            output.write(rewritten_readme)
    return 0


if __name__ == "__main__":
    main()
