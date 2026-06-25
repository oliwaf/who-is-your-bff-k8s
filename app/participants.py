from collections import Counter
from typing import Any


UNKNOWN_SENDER = "Unknown"


def get_participants(data: dict[str, Any]) -> list[str]:
    participants = data.get("participants", [])
    if not isinstance(participants, list):
        return []

    names: list[str] = []
    for participant in participants:
        if isinstance(participant, str) and participant.strip():
            names.append(participant)
            continue

        if not isinstance(participant, dict):
            continue

        name = participant.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name)

    return names


def get_message_count_by_sender(data: dict[str, Any]) -> dict[str, int]:
    counter: Counter[str] = Counter()

    for message in data.get("messages", []):
        if not isinstance(message, dict):
            continue

        sender = message.get("sender_name")
        if not isinstance(sender, str) or not sender.strip():
            sender = UNKNOWN_SENDER

        counter[sender] += 1

    return dict(counter)
