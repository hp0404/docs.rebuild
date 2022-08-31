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
    "я хочу запропонувати як покращити систему": "suggestions",
    "до якого типу віднести об'єкт": "classification",
    "немає доступу до об'єкту": "access",
    "фотобанк": "photos",
    "параметри об'єкта": "parameters",
    "відновлення об'єкту": "restoration",
    "доступ до Системи": "system",
    "геодані, адреса об'єкта": "geolocation",
    "date": "date",
}
SUGGESTIONS = [
    "я хочу запропонувати як покращити систему",
    "у мене щось не працює (технічна проблема)",
]
IGNORE_TAG = "я не знаю як внести дані (змістовна проблема)"

JSON = typing.Dict[str, typing.Any]
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs" / "source"
INDEX = SOURCE / "index.md"

DATE = datetime.datetime.now(pytz.timezone("Europe/Kyiv"))


def read_questions() -> JSON:
    df = pd.read_csv(os.environ["URL"])
    df["Позначка часу"] = pd.to_datetime(df["Позначка часу"])
    df = df.loc[df["Позначка часу"].notnull()].sort_values("Позначка часу").copy()
    df["type"] = df["тип питання 'змістовна проблема'"].combine_first(
        df["Я заповнюю форму, тому що"]
    )
    sections = df["type"].unique().tolist()
    if IGNORE_TAG in sections:
        sections.remove(IGNORE_TAG)

    transformed_data = {}
    for section in sections:
        if section in SUGGESTIONS:
            data = df.loc[df["Статус"].eq("в процесі") & df["type"].eq(section)]
            data["Відповідь (текст)"] = data["Відповідь (текст)"].fillna(
                "Найближчим часом буде реалізовано"
            )
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
