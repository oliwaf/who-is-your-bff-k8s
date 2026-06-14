import json
import re
from collections import Counter
from functools import partial
from pathlib import Path
from typing import Any


fix_mojibake_escapes = partial(
    re.compile(rb"\\u00([\da-f]{2})").sub,
    lambda match: bytes.fromhex(match.group(1).decode()),
)


def load_messenger_json(file_path: str) -> dict:
    path = Path(file_path)

    with path.open("rb") as file:
        raw_data = file.read()

    repaired_data = fix_mojibake_escapes(raw_data)
    decoded_text = repaired_data.decode("utf-8")
    data = json.loads(decoded_text, strict=False)

    return data


def get_most_common_words(data: dict[str, Any]) -> list:
    counter = Counter()

    for message in data.get("messages", []):
        content = message.get("content")

        if content:
            words = re.findall(r"\w+", content.lower())
            counter.update(words)

    return counter.most_common(10)


if __name__ == "__main__":
    data = load_messenger_json("tests/fixtures/message_11.json")

    print("Uczestnicy rozmowy:")
    print(data["participants"])

    print("Najczęstsze słowa:")
    common_words = get_most_common_words(data)
    print(common_words)