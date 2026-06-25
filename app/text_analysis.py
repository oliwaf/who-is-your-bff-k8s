import re
import string
from collections import Counter
from typing import Any


STOPWORDS = {
    "a",
    "ale",
    "and",
    "bo",
    "by",
    "co",
    "do",
    "for",
    "i",
    "in",
    "is",
    "it",
    "ja",
    "jak",
    "ma",
    "mi",
    "na",
    "nie",
    "no",
    "of",
    "on",
    "or",
    "po",
    "sie",
    "się",
    "tak",
    "the",
    "to",
    "w",
    "we",
    "za",
    "ze",
    "że",
}


def normalize_text(text: str) -> str:
    normalized = text.lower()
    translator = str.maketrans({char: " " for char in string.punctuation})
    return normalized.translate(translator)


def extract_words(text: str, min_length: int = 3) -> list[str]:
    normalized = normalize_text(text)
    words = re.findall(r"\w+", normalized, flags=re.UNICODE)
    return [
        word
        for word in words
        if len(word) >= min_length and word not in STOPWORDS
    ]


def get_most_common_words(
    data: dict[str, Any],
    limit: int = 10,
    min_length: int = 3,
) -> list[tuple[str, int]]:
    return Counter(get_word_frequencies(data, min_length=min_length)).most_common(limit)


def get_word_frequencies(
    data: dict[str, Any],
    min_length: int = 2,
) -> dict[str, int]:
    counter: Counter[str] = Counter()

    for message in data.get("messages", []):
        if not isinstance(message, dict):
            continue

        content = message.get("content")
        if isinstance(content, str) and content.strip():
            counter.update(extract_words(content, min_length=min_length))

    return dict(counter)
