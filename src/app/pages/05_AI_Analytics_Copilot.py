
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(PROJECT_ROOT / ".env")

from database.query_executor import ask_database
from llm.rag_system import ask_support_question

st.set_page_config(
    page_title="AI Analytics Copilot | Netflix Intelligence",
    page_icon="🎬",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #101010;
    color: #ffffff;
}

[data-testid="stSidebar"] {
    background: #171717;
}

.hero {
    background: linear-gradient(110deg, #8b0000, #c1121f);
    padding: 28px;
    border-radius: 14px;
    margin-bottom: 24px;
}

.hero h1 {
    color: #ffffff;
    font-size: 32px;
    margin-bottom: 8px;
}

.hero p {
    color: #f2f2f2;
    font-size: 15px;
    margin-bottom: 0;
}

[data-testid="stMetric"] {
    background: #1c1c1c;
    border: 1px solid #333333;
    padding: 15px;
    border-radius: 10px;
}

.stButton button {
    border-radius: 8px;
}

div[data-testid="stChatMessage"] {
    background: #191919;
    border-radius: 12px;
    padding: 12px;
}

/* Conversation input styling */
[data-testid="stChatInput"] {
    background-color: #ffffff !important;
    border: 1px solid #c1121f !important;
    border-radius: 12px !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] textarea:focus,
[data-testid="stChatInputTextArea"],
[data-testid="stChatInputTextArea"]:focus {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    caret-color: #000000 !important;
    background-color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
    font-size: 16px !important;
}

[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputTextArea"]::placeholder {
    color: #555555 !important;
    -webkit-text-fill-color: #555555 !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] button {
    color: #c1121f !important;
}

.stRadio label {
    color: #ffffff !important;
}

[data-testid="stAlert"] {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

if "copilot_messages" not in st.session_state:
    st.session_state.copilot_messages = []

if "copilot_question_count" not in st.session_state:
    st.session_state.copilot_question_count = 0

if "copilot_response_times" not in st.session_state:
    st.session_state.copilot_response_times = []

st.markdown("""
<div class="hero">
    <h1>🎬 AI Analytics Copilot</h1>
    <p>Ask questions about customer intelligence, business performance,
    customer feedback and support tickets.</p>
</div>
""", unsafe_allow_html=True)

total_questions = st.session_state.copilot_question_count
response_times = st.session_state.copilot_response_times

average_time = (
    sum(response_times) / len(response_times)
    if response_times else 0
)

col1, col2, col3 = st.columns(3)

col1.metric("Questions Asked", total_questions)
col2.metric("Analysis Modes", 2)
col3.metric("Average Response Time", f"{average_time:.2f} sec")

st.divider()

left, right = st.columns([3, 1])

with left:
    st.subheader("Choose Analysis Mode")

    analysis_mode = st.radio(
        "Select how the Copilot should answer",
        ["Text-to-SQL", "RAG - Support & Feedback"],
        horizontal=True,
        label_visibility="collapsed"
    )

with right:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.copilot_messages = []
        st.rerun()

if analysis_mode == "Text-to-SQL":
    st.info(
        "Ask questions about customer data. "
        "The system generates and executes SQL queries."
    )
else:
    st.info(
        "Ask questions about customer support tickets and feedback. "
        "The system retrieves relevant information using RAG."
    )

st.divider()

st.subheader("Conversation")

for message in st.session_state.copilot_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            if message.get("status"):
                st.caption(f"Execution status: {message['status']}")

            if message.get("results"):
                st.markdown("**Query Results**")
                results = message["results"]

                if isinstance(results, list) and results:
                    if all(isinstance(item, dict) for item in results):
                        st.dataframe(
                            pd.DataFrame(results),
                            use_container_width=True
                        )
                    else:
                        st.write(results)
                else:
                    st.write(results)

            if message.get("sources"):
                with st.expander("View Retrieved Sources"):
                    st.write(message["sources"])

            if message.get("elapsed") is not None:
                st.caption(
                    f"Response time: {message['elapsed']:.2f} seconds"
                )

question = st.chat_input("Ask your question here...")

if question and question.strip():
    question = question.strip()

    st.session_state.copilot_messages.append({
        "role": "user",
        "content": question
    })

    start_time = time.perf_counter()

    try:
        with st.spinner("🤖 Analyzing your question and generating insights..."):
            if analysis_mode == "Text-to-SQL":
                response = ask_database(question)
            else:
                response = ask_support_question(
                    question,
                    top_k=5
                )

        elapsed = time.perf_counter() - start_time

        if not isinstance(response, dict):
            raise TypeError(
                "The Copilot backend returned an unexpected response format."
            )

        answer = response.get("answer") or "No answer was returned."

        status = response.get("execution_status")

        if analysis_mode == "Text-to-SQL":
            results = response.get("results", [])
            sources = None
        else:
            results = None
            sources = response.get("source_references", [])

        assistant_message = {
            "role": "assistant",
            "content": str(answer),
            "status": status,
            "results": results,
            "sources": sources,
            "elapsed": elapsed
        }

        st.session_state.copilot_messages.append(
            assistant_message
        )

        st.session_state.copilot_question_count += 1
        st.session_state.copilot_response_times.append(elapsed)

    except Exception as error:
        elapsed = time.perf_counter() - start_time

        st.session_state.copilot_messages.append({
            "role": "assistant",
            "content": (
                "I couldn't process that question. "
                "Please check the backend error in the terminal."
            ),
            "status": "Error",
            "elapsed": elapsed
        })

        st.error(f"Copilot error: {error}")

    st.rerun()
