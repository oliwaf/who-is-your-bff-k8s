from app.engine import get_most_common_words


def test_get_most_common_words_counts_words():
    data = {
        "messages": [
            {"content": "Ala ma kota"},
            {"content": "Ala ma psa"},
            {"content": "Kot ma Ale"},
        ]
    }

    result = get_most_common_words(data)

    assert result[0] == ("ma", 3)
    assert ("ala", 2) in result