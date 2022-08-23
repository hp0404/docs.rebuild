import os
import re
import pytz
import datetime
import typing
from pathlib import Path

import pandas as pd

# multi-select values / corresponding tags in the source file
TAGS = {
    "у мене щось не працює (технічна проблема)": "bugs",
    "я не знаю як внести дані (змістовна проблема)": "questions",
    "я хочу запропонувати як покращити систему": "suggestions",
    "date": "date",
}
JSON = typing.Dict[str, typing.Any]
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs" / "source"
INDEX = SOURCE / "index.md"

DATE = datetime.datetime.now(pytz.timezone("Europe/Kyiv"))


def read_questions() -> JSON:
    df = pd.read_csv(os.environ["URL"])
    transformed_data = {}
    sections = df["Я заповнюю форму, тому що"].unique().tolist()
    for section in sections:
        data = df.loc[
            df["Відповідь (текст)"].notnull()
            & df["Я заповнюю форму, тому що"].eq(section)
        ]
        records = data.to_dict(orient="records")
        transformed_data[section] = records
    return transformed_data


def format_question(item: JSON) -> str:
    return "> *{question}*\n\n{answer}\n".format(
        question=item["Опишіть, будь ласка, суть пропозиції/звернення"],
        answer=item["Відповідь (текст)"],
    )


def update_docs(
    original_tag: str, readme_content: str, questions: str, inline: bool
) -> str:
    tag = TAGS[original_tag]
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
        "date", readme_contents, DATE.strftime("%d.%m.%Y %H:%M:%S"), inline=True
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
