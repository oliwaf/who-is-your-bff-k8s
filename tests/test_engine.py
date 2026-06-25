import json

import pytest

from app.engine import (
    MessengerJsonError,
    discover_messenger_json_files,
    fix_mojibake,
    load_messenger_json,
    repair_messenger_encoding,
)
from app.participants import get_message_count_by_sender, get_participants
from app.stats import (
    get_conversation_label,
    get_conversation_group_label,
    get_conversation_stats,
    get_conversation_summaries,
    get_message_count_by_day,
    get_message_count_by_hour,
    get_word_count_by_sender,
    group_conversation_parts,
    merge_messenger_data,
)
from app.text_analysis import get_most_common_words, get_word_frequencies


def test_load_messenger_json_loads_fixture_and_repairs_polish_characters():
    data = load_messenger_json("tests/fixtures/message_11.json")

    assert data["participants"][0]["name"] == "Maciek Łapa"
    assert data["messages"][1]["content"].startswith("Też tak myślę")


def test_load_messenger_json_accepts_bytes():
    payload = json.dumps({"messages": [{"content": "Cześć"}]}).encode("utf-8")

    data = load_messenger_json(payload)

    assert data["messages"][0]["content"] == "Cześć"


def test_load_messenger_json_normalizes_new_messenger_export_shape():
    payload = json.dumps(
        {
            "participants": ["Fabian Oliwa", "Wojciech Choroniewski"],
            "threadName": "Wojciech Choroniewski_26",
            "messages": [
                {
                    "senderName": "Fabian Oliwa",
                    "text": "Siemka",
                    "timestamp": 1_708_259_114_138,
                    "type": "text",
                },
                {
                    "senderName": "Wojciech Choroniewski",
                    "text": "Elko",
                    "timestamp": 1_708_260_302_150,
                    "type": "text",
                },
            ],
        }
    ).encode("utf-8")

    data = load_messenger_json(payload)

    assert data["title"] == "Wojciech Choroniewski_26"
    assert data["participants"] == [
        {"name": "Fabian Oliwa"},
        {"name": "Wojciech Choroniewski"},
    ]
    assert data["messages"][0]["sender_name"] == "Fabian Oliwa"
    assert data["messages"][0]["content"] == "Siemka"
    assert data["messages"][0]["timestamp_ms"] == 1_708_259_114_138


def test_repair_messenger_encoding_repairs_escaped_mojibake():
    raw_data = b'{"name": "Maciek \\u00c5\\u0081apa"}'

    repaired = repair_messenger_encoding(raw_data)
    data = json.loads(repaired.decode("utf-8"))

    assert data["name"] == "Maciek Łapa"


def test_fix_mojibake_repairs_already_decoded_text():
    assert fix_mojibake("TeÅ¼ tak myÅ\x9blÄ\x99") == "Też tak myślę"


def test_load_messenger_json_raises_friendly_error_for_invalid_json():
    with pytest.raises(MessengerJsonError, match="not valid JSON"):
        load_messenger_json(b"{not json")


def test_load_messenger_json_validates_basic_structure():
    with pytest.raises(MessengerJsonError, match="messages"):
        load_messenger_json(b'{"messages": {}}')


def test_discover_messenger_json_files_finds_json_files_recursively(tmp_path):
    inbox = tmp_path / "messages" / "inbox" / "ala_123"
    inbox.mkdir(parents=True)
    first_file = inbox / "message_1.json"
    second_file = inbox / "message_2.json"
    ignored_file = inbox / "photo.png"

    first_file.write_text('{"messages": []}', encoding="utf-8")
    second_file.write_text('{"messages": []}', encoding="utf-8")
    ignored_file.write_text("not json", encoding="utf-8")

    assert discover_messenger_json_files(tmp_path) == [first_file, second_file]


def test_discover_messenger_json_files_requires_existing_folder(tmp_path):
    with pytest.raises(MessengerJsonError, match="does not exist"):
        discover_messenger_json_files(tmp_path / "missing")

    file_path = tmp_path / "message_1.json"
    file_path.write_text('{"messages": []}', encoding="utf-8")

    with pytest.raises(MessengerJsonError, match="folder path"):
        discover_messenger_json_files(file_path)


def test_get_participants_handles_missing_participants_key():
    assert get_participants({"messages": []}) == []


def test_get_participants_extracts_names():
    data = {"participants": [{"name": "Ala"}, {"name": "Ola"}, {}]}

    assert get_participants(data) == ["Ala", "Ola"]


def test_get_participants_accepts_new_export_string_participants():
    data = {"participants": ["Ala", "Ola", ""]}

    assert get_participants(data) == ["Ala", "Ola"]


def test_get_message_count_by_sender_handles_missing_sender_name():
    data = {
        "messages": [
            {"sender_name": "Ala", "content": "Hej"},
            {"content": "Bez nadawcy"},
            {"sender_name": "", "content": "Pusty nadawca"},
        ]
    }

    assert get_message_count_by_sender(data) == {"Ala": 1, "Unknown": 2}


def test_get_most_common_words_ignores_missing_content_and_stopwords():
    data = {
        "messages": [
            {"content": "Kot lubi mleko, kot lubi sen."},
            {"sticker": {"uri": "sticker.png"}},
            {"content": "Sen i mleko!"},
        ]
    }

    result = get_most_common_words(data)

    assert result[0] == ("kot", 2)
    assert ("lubi", 2) in result
    assert ("mleko", 2) in result
    assert "i" not in dict(result)


def test_get_word_frequencies_excludes_single_character_words():
    data = {
        "messages": [
            {"content": "ja ty on kot kot a x y"},
            {"content": "ty kot"},
            {"sticker": {"uri": "sticker.png"}},
        ]
    }

    frequencies = get_word_frequencies(data, min_length=2)

    assert frequencies["kot"] == 3
    assert frequencies["ty"] == 2
    assert "a" not in frequencies
    assert "x" not in frequencies
    assert "y" not in frequencies


def test_get_conversation_stats_counts_messages_and_dates():
    data = {
        "participants": [{"name": "Ala"}, {"name": "Ola"}],
        "messages": [
            {
                "sender_name": "Ala",
                "timestamp_ms": 2000,
                "content": "Druga wiadomość",
            },
            {
                "sender_name": "Ola",
                "timestamp_ms": 1000,
                "sticker": {"uri": "sticker.png"},
            },
            {
                "timestamp_ms": 3000,
                "content": "Bez nadawcy",
            },
        ],
    }

    stats = get_conversation_stats(data)

    assert stats["total_messages"] == 3
    assert stats["text_messages"] == 2
    assert stats["media_or_non_text_messages"] == 1
    assert stats["total_words"] == 4
    assert stats["average_words_per_message"] == 1.33
    assert stats["average_words_per_text_message"] == 2
    assert stats["participants_count"] == 2
    assert stats["first_message_date"] == "1970-01-01"
    assert stats["last_message_date"] == "1970-01-01"
    assert stats["messages_by_sender"] == {"Ala": 1, "Ola": 1, "Unknown": 1}


def test_get_word_count_by_sender_counts_text_words_only():
    data = {
        "messages": [
            {"sender_name": "Ala", "content": "kot lubi mleko"},
            {"sender_name": "Ala", "sticker": {"uri": "sticker.png"}},
            {"sender_name": "Ola", "content": "sen i kot"},
            {"content": "bez nadawcy"},
        ]
    }

    assert get_word_count_by_sender(data) == {
        "Ala": 3,
        "Ola": 2,
        "Unknown": 2,
    }


def test_get_message_count_by_hour_groups_messages_by_sender_and_utc_hour():
    data = {
        "messages": [
            {"sender_name": "Ala", "timestamp_ms": 0},
            {"sender_name": "Ala", "timestamp_ms": 3_600_000},
            {"sender_name": "Ola", "timestamp_ms": 3_600_000},
            {"timestamp_ms": 7_200_000},
            {"sender_name": "No timestamp"},
        ]
    }

    counts = get_message_count_by_hour(data)

    assert counts["Ala"][0] == 1
    assert counts["Ala"][1] == 1
    assert counts["Ola"][1] == 1
    assert counts["Unknown"][2] == 1


def test_get_message_count_by_day_groups_messages_by_sender_and_utc_day():
    data = {
        "messages": [
            {"sender_name": "Ala", "timestamp_ms": 0},
            {"sender_name": "Ala", "timestamp_ms": 86_400_000},
            {"sender_name": "Ola", "timestamp_ms": 86_400_000},
            {"timestamp_ms": 172_800_000},
        ]
    }

    assert get_message_count_by_day(data) == {
        "Ala": {"1970-01-01": 1, "1970-01-02": 1},
        "Ola": {"1970-01-02": 1},
        "Unknown": {"1970-01-03": 1},
    }


def test_get_conversation_label_prefers_title_then_participants():
    assert get_conversation_label({"title": "Ala"}) == "Ala"
    assert get_conversation_label(
        {"participants": [{"name": "Ala"}, {"name": "Ola"}]}
    ) == "Ala, Ola"
    assert get_conversation_label({}, fallback="message_1.json") == "message_1.json"


def test_get_conversation_group_label_removes_numeric_export_suffix():
    assert get_conversation_group_label("Wojciech Choroniewski_26") == (
        "Wojciech Choroniewski"
    )
    assert get_conversation_group_label("Rodzina") == "Rodzina"


def test_merge_messenger_data_combines_messages_and_unique_participants():
    conversations = [
        {
            "participants": [{"name": "Ala"}, {"name": "Fabian"}],
            "messages": [{"sender_name": "Ala", "content": "hej"}],
        },
        {
            "participants": [{"name": "Ola"}, {"name": "Fabian"}],
            "messages": [{"sender_name": "Ola", "content": "siema"}],
        },
    ]

    merged = merge_messenger_data(conversations)

    assert merged["participants"] == [
        {"name": "Ala"},
        {"name": "Fabian"},
        {"name": "Ola"},
    ]
    assert merged["messages"] == [
        {"sender_name": "Ala", "content": "hej"},
        {"sender_name": "Ola", "content": "siema"},
    ]


def test_group_conversation_parts_merges_files_with_same_base_label():
    grouped = group_conversation_parts(
        [
            (
                "Wojciech Choroniewski_26",
                {
                    "participants": [
                        {"name": "Fabian Oliwa"},
                        {"name": "Wojciech Choroniewski"},
                    ],
                    "messages": [{"sender_name": "Fabian Oliwa", "content": "hej"}],
                },
            ),
            (
                "Wojciech Choroniewski_27",
                {
                    "participants": [
                        {"name": "Fabian Oliwa"},
                        {"name": "Wojciech Choroniewski"},
                    ],
                    "messages": [
                        {"sender_name": "Wojciech Choroniewski", "content": "elko"}
                    ],
                },
            ),
            (
                "Sebastian Łapa_71",
                {
                    "participants": [
                        {"name": "Fabian Oliwa"},
                        {"name": "Sebastian Łapa"},
                    ],
                    "messages": [{"sender_name": "Sebastian Łapa", "content": "yo"}],
                },
            ),
        ]
    )

    assert [label for label, _ in grouped] == [
        "Wojciech Choroniewski",
        "Sebastian Łapa",
    ]
    assert len(grouped[0][1]["messages"]) == 2
    assert grouped[0][1]["source_files_count"] == 2


def test_get_conversation_summaries_returns_one_row_per_conversation():
    conversations = [
        (
            "Ala",
            {
                "participants": [{"name": "Ala"}, {"name": "Fabian"}],
                "messages": [
                    {"sender_name": "Ala", "timestamp_ms": 0, "content": "hej kot"},
                    {"sender_name": "Fabian", "timestamp_ms": 1000},
                ],
            },
        ),
        (
            "Ola",
            {
                "participants": [{"name": "Ola"}, {"name": "Fabian"}],
                "messages": [
                    {"sender_name": "Ola", "timestamp_ms": 2000, "content": "dobry sen"}
                ],
            },
        ),
    ]

    summaries = get_conversation_summaries(conversations)

    assert summaries[0]["conversation"] == "Ala"
    assert summaries[0]["total_messages"] == 2
    assert summaries[0]["words"] == 2
    assert summaries[0]["top_sender"] == "Ala"
    assert summaries[1]["conversation"] == "Ola"
    assert summaries[1]["total_messages"] == 1
