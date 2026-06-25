import math
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.engine import (
    MessengerJsonError,
    discover_messenger_json_files,
    load_messenger_json,
)
from app.participants import get_message_count_by_sender, get_participants
from app.stats import (
    get_conversation_label,
    get_conversation_stats,
    get_conversation_summaries,
    get_message_count_by_day,
    get_message_count_by_hour,
    get_word_count_by_sender,
    group_conversation_parts,
    merge_messenger_data,
)
from app.text_analysis import get_most_common_words, get_word_frequencies

try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None


REPORT_SECTIONS = [
    "Overview",
    "Messages by sender",
    "Words by sender",
    "Activity by hour",
    "Activity by day",
    "Top words",
    "Word cloud",
]


def build_word_cloud_figure(word_frequencies: dict[str, int]):
    if not word_frequencies:
        return None

    if WordCloud is not None:
        word_cloud = WordCloud(
            width=1400,
            height=720,
            max_words=140,
            background_color="white",
            colormap="viridis",
            prefer_horizontal=0.88,
            relative_scaling=0.45,
            collocations=False,
            random_state=42,
            min_font_size=9,
            contour_width=1,
            contour_color="#e5e7eb",
            margin=4,
        ).generate_from_frequencies(word_frequencies)

        fig, ax = plt.subplots(figsize=(12, 6.2))
        ax.imshow(word_cloud, interpolation="bilinear")
        ax.set_axis_off()
        fig.tight_layout(pad=0)
        return fig

    top_words = sorted(
        word_frequencies.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:80]

    max_count = top_words[0][1]
    colors = [
        "#0f766e",
        "#2563eb",
        "#7c3aed",
        "#db2777",
        "#ea580c",
        "#65a30d",
        "#0891b2",
        "#475569",
    ]
    rng = random.Random(42)

    fig, ax = plt.subplots(figsize=(12, 6.2))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("#fbfbf8")
    fig.patch.set_facecolor("#fbfbf8")
    placed_boxes: list[tuple[float, float, float, float]] = []

    def has_collision(box: tuple[float, float, float, float]) -> bool:
        left, bottom, right, top = box
        if left < 0.02 or bottom < 0.04 or right > 0.98 or top > 0.96:
            return True

        return any(
            left < other_right
            and right > other_left
            and bottom < other_top
            and top > other_bottom
            for other_left, other_bottom, other_right, other_top in placed_boxes
        )

    for index, (word, count) in enumerate(top_words):
        weight = count / max_count
        size = 10 + 54 * (weight**0.62)
        rotation = 0 if rng.random() > 0.12 else 90

        word_width = 0.62 * len(word) * size / (12 * 72)
        word_height = 1.35 * size / (6.2 * 72)
        if rotation:
            word_width, word_height = word_height, word_width

        x = 0.5
        y = 0.52
        for step in range(420):
            angle = step * 0.42 + index * 0.19
            radius = 0.0045 * step
            candidate_x = 0.5 + math.cos(angle) * radius * 0.86
            candidate_y = 0.52 + math.sin(angle) * radius * 0.48
            candidate_box = (
                candidate_x - word_width / 2,
                candidate_y - word_height / 2,
                candidate_x + word_width / 2,
                candidate_y + word_height / 2,
            )
            if not has_collision(candidate_box):
                x = candidate_x
                y = candidate_y
                placed_boxes.append(candidate_box)
                break
        else:
            continue

        ax.text(
            x,
            y,
            word,
            fontsize=size,
            color=rng.choice(colors),
            ha="center",
            va="center",
            rotation=rotation,
            fontweight="bold" if weight > 0.72 else "semibold",
            alpha=0.96,
        )

    fig.tight_layout(pad=0)
    return fig


def build_bar_figure(
    values: dict[str, int | float],
    title: str,
    ylabel: str,
):
    if not values:
        return None

    sorted_values = sorted(values.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_values]
    counts = [item[1] for item in sorted_values]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, counts, color="#2563eb")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=25)
    ax.bar_label(bars, labels=[format_chart_value(count) for count in counts])
    fig.tight_layout()
    return fig


def format_chart_value(value: int | float) -> str:
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.2f}"
    return str(int(value))


def top_items(values: dict[str, int | float], limit: int = 10) -> dict[str, int | float]:
    return dict(
        sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit]
    )


def top_nested_items(
    values: dict[str, dict[Any, int | float]],
    limit: int = 10,
) -> dict[str, dict[Any, int | float]]:
    top_senders = sorted(
        values.items(),
        key=lambda item: sum(item[1].values()),
        reverse=True,
    )[:limit]
    return dict(top_senders)


def build_hourly_activity_figure(hourly_counts: dict[str, dict[int, int | float]]):
    if not hourly_counts:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    hours = list(range(24))

    for sender, counts in hourly_counts.items():
        ax.plot(hours, [counts.get(hour, 0) for hour in hours], marker="o", label=sender)

    ax.set_title("Messages by hour")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Messages")
    ax.set_xticks(hours)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def build_daily_activity_figure(daily_counts: dict[str, dict[str, int | float]]):
    if not daily_counts:
        return None

    day_keys = sorted(
        {
            day
            for sender_counts in daily_counts.values()
            for day in sender_counts.keys()
        }
    )
    if not day_keys:
        return None

    days = [datetime.fromisoformat(day) for day in day_keys]
    fig, ax = plt.subplots(figsize=(10, 5))

    for sender, counts in daily_counts.items():
        ax.plot(days, [counts.get(day, 0) for day in day_keys], linewidth=1.8, label=sender)

    ax.set_title("Messages by day")
    ax.set_xlabel("Day")
    ax.set_ylabel("Messages")
    ax.xaxis.set_major_locator(
        mdates.AutoDateLocator(minticks=5, maxticks=10)
    )
    ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(ax.xaxis.get_major_locator())
    )
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    ax.legend(loc="best")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


def load_conversations(
    sources: list[tuple[str, Any]],
) -> list[tuple[str, dict]]:
    conversations: list[tuple[str, dict]] = []

    for source_name, source in sources:
        try:
            data = load_messenger_json(source)
        except MessengerJsonError as error:
            st.error(f"{source_name}: {error}")
            continue
        except OSError:
            st.error(f"{source_name}: Could not read this file.")
            continue

        label = get_conversation_label(data, fallback=source_name)
        conversations.append((label, data))

    return group_conversation_parts(conversations)


def count_source_files(conversations: list[tuple[str, dict]]) -> int:
    return sum(data.get("source_files_count", 1) for _, data in conversations)


def discover_json_files_from_folders(folder_inputs: list[str]) -> list[Path]:
    json_files: list[Path] = []
    seen_files: set[Path] = set()

    for folder_input in folder_inputs:
        try:
            discovered_files = discover_messenger_json_files(folder_input)
        except MessengerJsonError as error:
            st.error(f"{folder_input}: {error}")
            continue

        for path in discovered_files:
            resolved_path = path.resolve()
            if resolved_path not in seen_files:
                json_files.append(path)
                seen_files.add(resolved_path)

    return json_files


def get_shared_sender_for_average(
    conversations: list[tuple[str, dict]],
) -> str | None:
    conversation_counts: Counter[str] = Counter()
    message_totals: Counter[str] = Counter()

    for _, conversation in conversations:
        messages_by_sender = get_message_count_by_sender(conversation)
        for sender, count in messages_by_sender.items():
            if sender == "Unknown":
                continue
            conversation_counts[sender] += 1
            message_totals[sender] += count

    if not conversation_counts:
        return None

    sender, count = max(
        conversation_counts.items(),
        key=lambda item: (item[1], message_totals[item[0]]),
    )
    if count <= 1:
        return None

    return sender


def average_shared_sender_values(
    values: dict[str, int | float],
    sender: str | None,
    conversations_count: int,
) -> dict[str, int | float]:
    if sender is None or sender not in values or conversations_count <= 1:
        return values

    averaged_values = dict(values)
    value = averaged_values.pop(sender)
    averaged_values[f"{sender} (top 10 avg/conversation)"] = round(
        value / conversations_count,
        2,
    )
    return averaged_values


def average_shared_sender_nested_values(
    values: dict[str, dict[Any, int | float]],
    sender: str | None,
    conversations_count: int,
) -> dict[str, dict[Any, int | float]]:
    if sender is None or sender not in values or conversations_count <= 1:
        return values

    averaged_values = dict(values)
    sender_values = averaged_values.pop(sender)
    averaged_values[f"{sender} (top 10 avg/conversation)"] = {
        key: round(value / conversations_count, 2)
        for key, value in sender_values.items()
    }
    return averaged_values


def render_section_buttons(scope_key: str) -> str | None:
    if st.session_state.get("report_scope_key") != scope_key:
        st.session_state["report_scope_key"] = scope_key
        st.session_state["report_section"] = None

    button_columns = st.columns(3)
    for index, section in enumerate(REPORT_SECTIONS):
        column = button_columns[index % len(button_columns)]
        if column.button(section, use_container_width=True, key=f"{scope_key}-{index}"):
            st.session_state["report_section"] = section

    selected_section = st.session_state.get("report_section")
    if selected_section is None:
        st.info("Choose what you want to generate.")

    return selected_section


def render_dashboard(
    data: dict,
    all_conversations: list[tuple[str, dict]],
    is_all_view: bool,
    section: str,
) -> None:
    participants = get_participants(data)
    messages_by_sender = get_message_count_by_sender(data)
    words_by_sender = get_word_count_by_sender(data)
    hourly_counts = get_message_count_by_hour(data)
    daily_counts = get_message_count_by_day(data)
    word_frequencies = get_word_frequencies(data, min_length=2)
    conversation_stats = get_conversation_stats(data)
    shared_sender = (
        get_shared_sender_for_average(all_conversations)
        if is_all_view and len(all_conversations) > 1
        else None
    )
    conversations_count = len(all_conversations)

    if section == "Overview":
        st.caption(
            "Stats are calculated for the selected scope. In All conversations, "
            "sender charts show the shared sender as an average per conversation."
        )
        if is_all_view and len(all_conversations) > 1:
            st.subheader("Conversations overview")
            summaries = sorted(
                get_conversation_summaries(all_conversations),
                key=lambda summary: summary["total_messages"],
                reverse=True,
            )[:10]
            st.caption("Showing top 10 conversations.")
            st.table(summaries)

            messages_by_conversation = top_items(
                {
                    summary["conversation"]: summary["total_messages"]
                    for summary in summaries
                }
            )
            overview_chart = build_bar_figure(
                messages_by_conversation,
                title="Top 10 conversations by messages",
                ylabel="Messages",
            )
            if overview_chart:
                st.pyplot(overview_chart)

        st.subheader("Participants")
        if participants:
            st.write(participants)
        else:
            st.info("No participants found in this export.")

        st.subheader("Basic stats")
        metric_columns = st.columns(4)
        metric_columns[0].metric("Messages", conversation_stats["total_messages"])
        metric_columns[1].metric("Text messages", conversation_stats["text_messages"])
        metric_columns[2].metric("Words", conversation_stats["total_words"])
        metric_columns[3].metric(
            "Avg words / msg",
            conversation_stats["average_words_per_message"],
        )
        st.json(
            {
                "total_messages": conversation_stats["total_messages"],
                "text_messages": conversation_stats["text_messages"],
                "media_or_non_text_messages": conversation_stats[
                    "media_or_non_text_messages"
                ],
                "total_words": conversation_stats["total_words"],
                "average_words_per_message": conversation_stats[
                    "average_words_per_message"
                ],
                "average_words_per_text_message": conversation_stats[
                    "average_words_per_text_message"
                ],
                "participants_count": conversation_stats["participants_count"],
                "first_message_date": conversation_stats["first_message_date"],
                "last_message_date": conversation_stats["last_message_date"],
            }
        )
        return

    if section == "Messages by sender":
        st.subheader("Messages by sender")
        messages_by_sender = average_shared_sender_values(
            messages_by_sender,
            shared_sender,
            conversations_count,
        )
        limited_messages_by_sender = top_items(messages_by_sender)
        if limited_messages_by_sender:
            st.caption(
                "Top 10 senders. In All conversations, the shared sender is "
                "shown as avg/conversation."
            )
            st.table(limited_messages_by_sender.items())
            messages_chart = build_bar_figure(
                limited_messages_by_sender,
                title="Top 10 senders by messages (shared sender avg/conversation)",
                ylabel="Messages",
            )
            if messages_chart:
                st.pyplot(messages_chart)
        else:
            st.info("No messages found in this export.")
        return

    if section == "Words by sender":
        st.subheader("Words by sender")
        words_by_sender = average_shared_sender_values(
            words_by_sender,
            shared_sender,
            conversations_count,
        )
        limited_words_by_sender = top_items(words_by_sender)
        if limited_words_by_sender:
            st.caption(
                "Top 10 senders. In All conversations, the shared sender is "
                "shown as avg/conversation."
            )
            st.table(limited_words_by_sender.items())
            words_chart = build_bar_figure(
                limited_words_by_sender,
                title="Top 10 senders by words (shared sender avg/conversation)",
                ylabel="Words",
            )
            if words_chart:
                st.pyplot(words_chart)
        else:
            st.info("No text messages found for word counts.")
        return

    if section == "Activity by hour":
        st.subheader("Activity by hour")
        hourly_counts = average_shared_sender_nested_values(
            hourly_counts,
            shared_sender,
            conversations_count,
        )
        hourly_figure = build_hourly_activity_figure(top_nested_items(hourly_counts))
        if hourly_figure:
            st.caption(
                "Top 10 senders by timestamped messages. In All conversations, "
                "the shared sender is shown as avg/conversation."
            )
            st.pyplot(hourly_figure)
        else:
            st.info("No timestamped messages found for hourly activity.")
        return

    if section == "Activity by day":
        st.subheader("Activity by day")
        daily_counts = average_shared_sender_nested_values(
            daily_counts,
            shared_sender,
            conversations_count,
        )
        daily_figure = build_daily_activity_figure(top_nested_items(daily_counts))
        if daily_figure:
            st.caption(
                "Top 10 senders by timestamped messages. In All conversations, "
                "the shared sender is shown as avg/conversation."
            )
            st.pyplot(daily_figure)
        else:
            st.info("No timestamped messages found for daily activity.")
        return

    if section == "Top words":
        st.subheader("Top words")
        common_words = get_most_common_words(data, limit=15)
        if common_words:
            st.table(common_words)
        else:
            st.info("No text messages found to analyze.")
        return

    if section == "Word cloud":
        st.subheader("Word cloud")
        word_cloud_figure = build_word_cloud_figure(word_frequencies)
        if word_cloud_figure:
            st.pyplot(word_cloud_figure)
        else:
            st.info("No words found to show in a word cloud.")
        return

st.set_page_config(
    page_title="Who is your BFF?",
    page_icon="💬",
)

st.title("Who is your BFF? 💬")
st.write(
    "Upload Messenger JSON files or scan a local export folder to inspect all "
    "conversations or focus on a selected person."
)

source_mode = st.radio(
    "Data source",
    ["Upload JSON files", "Scan local folder"],
    horizontal=True,
)

conversations: list[tuple[str, dict]] = []

if source_mode == "Upload JSON files":
    uploaded_files = st.file_uploader(
        "Choose Messenger JSON files",
        type=["json"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        conversations = load_conversations(
            [(uploaded_file.name, uploaded_file) for uploaded_file in uploaded_files]
        )
else:
    folders_input = st.text_area(
        "Folder paths",
        placeholder=(
            r"C:\Users\you\Downloads\facebook-export-1\messages\inbox"
            "\n"
            r"C:\Users\you\Downloads\facebook-export-2\messages\inbox"
        ),
        height=96,
    )
    st.caption(
        "Add one folder path per line. You can point to conversation folders or "
        "parent folders containing many users and groups."
    )

    folder_inputs = [
        line.strip().strip('"')
        for line in folders_input.splitlines()
        if line.strip()
    ]

    if folder_inputs:
        json_files = discover_json_files_from_folders(folder_inputs)
        if json_files:
            folder_paths = [
                Path(folder_input).expanduser()
                for folder_input in folder_inputs
            ]
            st.success(
                f"Found {len(json_files)} JSON file(s) across "
                f"{len(folder_inputs)} folder path(s)."
            )

            def get_source_label(path: Path) -> str:
                for folder_path in folder_paths:
                    if path.is_relative_to(folder_path):
                        return str(path.relative_to(folder_path))
                return path.name

            conversations = load_conversations(
                [
                    (get_source_label(path), path)
                    for path in json_files
                ]
            )
        else:
            st.info("No JSON files found in these folders.")

if conversations:
    if not conversations:
        st.stop()

    source_files_count = count_source_files(conversations)
    st.caption(
        f"Loaded {source_files_count} JSON file(s), grouped into "
        f"{len(conversations)} conversation(s)."
    )

    options = ["All conversations", *[label for label, _ in conversations]]
    selected_label = st.selectbox("Choose analysis scope", options)
    section = render_section_buttons(selected_label)

    if section:
        if selected_label == "All conversations":
            selected_data = merge_messenger_data([data for _, data in conversations])
            render_dashboard(
                selected_data,
                all_conversations=conversations,
                is_all_view=True,
                section=section,
            )
        else:
            selected_data = dict(conversations)[selected_label]
            render_dashboard(
                selected_data,
                all_conversations=conversations,
                is_all_view=False,
                section=section,
            )
