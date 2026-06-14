import tempfile
from pathlib import Path

import streamlit as st

from engine import get_most_common_words, load_messenger_json


st.set_page_config(
    page_title="Who is your BFF?",
    page_icon="💬",
)

st.title("Who is your BFF? 💬")
st.write("Upload Messenger JSON file and analyze most common words.")

uploaded_file = st.file_uploader(
    "Choose Messenger JSON file",
    type=["json"],
)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        temp_path = Path(temp_file.name)

    try:
        data = load_messenger_json(str(temp_path))
        common_words = get_most_common_words(data)

        st.subheader("Participants")
        st.write(data.get("participants", []))

        st.subheader("Most common words")
        st.table(common_words)

    except Exception as error:
        st.error("Could not analyze this file.")
        st.exception(error)