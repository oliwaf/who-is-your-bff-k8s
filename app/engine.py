import json
import re
from functools import partial
from pathlib import Path
from typing import Any, BinaryIO


_fix_mojibake_escapes = partial(
    re.compile(rb"\\u00([\da-f]{2})").sub,
    lambda match: bytes.fromhex(match.group(1).decode()),
)


class MessengerJsonError(ValueError):
    """Raised when a Messenger JSON export cannot be loaded safely."""


def repair_messenger_encoding(raw_data: bytes) -> bytes:
    return _fix_mojibake_escapes(raw_data)


def fix_mojibake(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


def _read_bytes(source: str | Path | bytes | BinaryIO) -> bytes:
    if isinstance(source, bytes):
        return source

    if isinstance(source, (str, Path)):
        with Path(source).open("rb") as file:
            return file.read()

    if hasattr(source, "read"):
        data = source.read()
        if isinstance(data, str):
            return data.encode("utf-8")
        return data

    raise MessengerJsonError("Unsupported input. Provide a path, bytes, or binary file.")


def validate_messenger_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise MessengerJsonError("Messenger export must be a JSON object.")

    messages = data.get("messages", [])
    if not isinstance(messages, list):
        raise MessengerJsonError("Messenger export has an invalid 'messages' field.")

    participants = data.get("participants", [])
    if participants is not None and not isinstance(participants, list):
        raise MessengerJsonError("Messenger export has an invalid 'participants' field.")

    return data


def normalize_messenger_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)

    thread_name = normalized.get("threadName")
    if "title" not in normalized and isinstance(thread_name, str):
        normalized["title"] = thread_name

    participants = normalized.get("participants", [])
    if isinstance(participants, list):
        normalized_participants: list[dict[str, str]] = []
        for participant in participants:
            if isinstance(participant, str) and participant.strip():
                normalized_participants.append({"name": participant})
            elif isinstance(participant, dict):
                name = participant.get("name")
                if isinstance(name, str) and name.strip():
                    normalized_participants.append({"name": name})

        normalized["participants"] = normalized_participants

    messages = normalized.get("messages", [])
    if isinstance(messages, list):
        normalized_messages: list[dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, dict):
                continue

            normalized_message = dict(message)

            sender_name = normalized_message.get("senderName")
            if (
                "sender_name" not in normalized_message
                and isinstance(sender_name, str)
            ):
                normalized_message["sender_name"] = sender_name

            text = normalized_message.get("text")
            if "content" not in normalized_message and isinstance(text, str):
                normalized_message["content"] = text

            timestamp = normalized_message.get("timestamp")
            if (
                "timestamp_ms" not in normalized_message
                and isinstance(timestamp, (int, float))
            ):
                normalized_message["timestamp_ms"] = timestamp

            normalized_messages.append(normalized_message)

        normalized["messages"] = normalized_messages

    return normalized


def load_messenger_json(source: str | Path | bytes | BinaryIO) -> dict[str, Any]:
    raw_data = _read_bytes(source)
    repaired_data = repair_messenger_encoding(raw_data)

    try:
        decoded_text = repaired_data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise MessengerJsonError("Could not decode this file as UTF-8 JSON.") from error

    try:
        data = json.loads(decoded_text, strict=False)
    except json.JSONDecodeError as error:
        raise MessengerJsonError("This file is not valid JSON.") from error

    return normalize_messenger_data(validate_messenger_data(data))


def discover_messenger_json_files(folder: str | Path) -> list[Path]:
    base_path = Path(folder).expanduser()

    if not base_path.exists():
        raise MessengerJsonError("This folder does not exist.")

    if not base_path.is_dir():
        raise MessengerJsonError("Provide a folder path, not a file path.")

    return sorted(
        path
        for path in base_path.rglob("*.json")
        if path.is_file()
    )
