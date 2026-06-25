from datetime import datetime, timezone
from typing import Any

from app.participants import UNKNOWN_SENDER, get_message_count_by_sender, get_participants
from app.text_analysis import extract_words


def _format_timestamp(timestamp_ms: Any) -> str | None:
    if not isinstance(timestamp_ms, (int, float)):
        return None

    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()


def get_conversation_stats(data: dict[str, Any]) -> dict[str, Any]:
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    text_messages = 0
    total_words = 0
    timestamps: list[int | float] = []

    for message in messages:
        if not isinstance(message, dict):
            continue

        content = message.get("content")
        if isinstance(content, str) and content.strip():
            text_messages += 1
            total_words += len(extract_words(content, min_length=2))

        timestamp_ms = message.get("timestamp_ms")
        if isinstance(timestamp_ms, (int, float)):
            timestamps.append(timestamp_ms)

    first_timestamp = min(timestamps) if timestamps else None
    last_timestamp = max(timestamps) if timestamps else None

    return {
        "total_messages": len(messages),
        "text_messages": text_messages,
        "media_or_non_text_messages": len(messages) - text_messages,
        "total_words": total_words,
        "average_words_per_message": round(total_words / len(messages), 2)
        if messages
        else 0,
        "average_words_per_text_message": round(total_words / text_messages, 2)
        if text_messages
        else 0,
        "participants_count": len(get_participants(data)),
        "first_message_date": _format_timestamp(first_timestamp),
        "last_message_date": _format_timestamp(last_timestamp),
        "messages_by_sender": get_message_count_by_sender(data),
    }


def get_conversation_label(data: dict[str, Any], fallback: str = "Conversation") -> str:
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        return title

    participants = get_participants(data)
    if participants:
        return ", ".join(participants)

    return fallback


def get_conversation_group_label(label: str) -> str:
    stripped_label = label.strip()
    if not stripped_label:
        return "Conversation"

    if "_" in stripped_label:
        base_label, suffix = stripped_label.rsplit("_", 1)
        if suffix.isdigit() and base_label.strip():
            return base_label.strip()

    return stripped_label


def merge_messenger_data(conversations: list[dict[str, Any]]) -> dict[str, Any]:
    merged_messages: list[dict[str, Any]] = []
    participant_names: list[str] = []
    seen_participants: set[str] = set()

    for conversation in conversations:
        messages = conversation.get("messages", [])
        if isinstance(messages, list):
            merged_messages.extend(
                message for message in messages if isinstance(message, dict)
            )

        for participant in get_participants(conversation):
            if participant not in seen_participants:
                participant_names.append(participant)
                seen_participants.add(participant)

    return {
        "participants": [{"name": name} for name in participant_names],
        "messages": merged_messages,
        "title": "All uploaded conversations",
    }


def group_conversation_parts(
    conversations: list[tuple[str, dict[str, Any]]],
) -> list[tuple[str, dict[str, Any]]]:
    grouped_conversations: dict[str, list[dict[str, Any]]] = {}
    label_order: list[str] = []

    for label, conversation in conversations:
        group_label = get_conversation_group_label(label)
        if group_label not in grouped_conversations:
            grouped_conversations[group_label] = []
            label_order.append(group_label)
        grouped_conversations[group_label].append(conversation)

    grouped_results: list[tuple[str, dict[str, Any]]] = []
    for label in label_order:
        parts = grouped_conversations[label]
        if len(parts) == 1:
            grouped_data = dict(parts[0])
            grouped_data["title"] = label
        else:
            grouped_data = merge_messenger_data(parts)
            grouped_data["title"] = label
            grouped_data["source_files_count"] = len(parts)

        grouped_results.append((label, grouped_data))

    return grouped_results


def get_conversation_summaries(
    conversations: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for label, conversation in conversations:
        stats = get_conversation_stats(conversation)
        words_by_sender = get_word_count_by_sender(conversation)
        top_sender = None
        top_sender_messages = 0

        if stats["messages_by_sender"]:
            top_sender, top_sender_messages = max(
                stats["messages_by_sender"].items(),
                key=lambda item: item[1],
            )

        summaries.append(
            {
                "conversation": label,
                "participants_count": stats["participants_count"],
                "total_messages": stats["total_messages"],
                "text_messages": stats["text_messages"],
                "words": sum(words_by_sender.values()),
                "top_sender": top_sender,
                "top_sender_messages": top_sender_messages,
                "first_message_date": stats["first_message_date"],
                "last_message_date": stats["last_message_date"],
            }
        )

    return summaries


def get_word_count_by_sender(
    data: dict[str, Any],
    min_length: int = 2,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for message in data.get("messages", []):
        if not isinstance(message, dict):
            continue

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue

        sender = message.get("sender_name")
        if not isinstance(sender, str) or not sender.strip():
            sender = UNKNOWN_SENDER

        counts[sender] = counts.get(sender, 0) + len(
            extract_words(content, min_length=min_length)
        )

    return counts


def get_message_count_by_hour(data: dict[str, Any]) -> dict[str, dict[int, int]]:
    counts: dict[str, dict[int, int]] = {}

    for message in data.get("messages", []):
        if not isinstance(message, dict):
            continue

        timestamp_ms = message.get("timestamp_ms")
        if not isinstance(timestamp_ms, (int, float)):
            continue

        sender = message.get("sender_name")
        if not isinstance(sender, str) or not sender.strip():
            sender = UNKNOWN_SENDER

        hour = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).hour
        counts.setdefault(sender, {hour: 0 for hour in range(24)})
        counts[sender][hour] += 1

    return counts


def get_message_count_by_day(data: dict[str, Any]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}

    for message in data.get("messages", []):
        if not isinstance(message, dict):
            continue

        timestamp_ms = message.get("timestamp_ms")
        if not isinstance(timestamp_ms, (int, float)):
            continue

        sender = message.get("sender_name")
        if not isinstance(sender, str) or not sender.strip():
            sender = UNKNOWN_SENDER

        day = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date()
        day_key = day.isoformat()
        counts.setdefault(sender, {})
        counts[sender][day_key] = counts[sender].get(day_key, 0) + 1

    return counts
