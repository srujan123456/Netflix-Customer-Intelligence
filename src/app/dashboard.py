
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
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background: #080B12;
    color: #F8FAFC;
    font-family: 'Inter', sans-serif;
}

.block-container {
    max-width: 1500px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #101622;
    border-right: 1px solid #293449;
}

[data-testid="stSidebar"] * {
    color: #E8EDF5;
}

.hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(115deg, #170D16, #35111D 48%, #70131F);
    border: 1px solid #71303B;
    border-radius: 22px;
    padding: 38px 40px;
    margin-bottom: 25px;
    box-shadow: 0 12px 35px rgba(0,0,0,0.25);
}

.hero-label {
    color: #FF9AA2;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 3px;
    margin-bottom: 14px;
}

.hero-title {
    color: #FFFFFF;
    font-size: 36px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 12px;
}

.hero-description {
    color: #E7D4D8;
    font-size: 15px;
    line-height: 1.8;
    max-width: 780px;
}

.hero-tag {
    display: inline-block;
    margin-top: 18px;
    background: rgba(229,9,20,0.18);
    border: 1px solid rgba(255,130,140,0.35);
    color: #FFD9DC;
    padding: 8px 14px;
    border-radius: 30px;
    font-size: 11px;
    font-weight: 700;
}

.section-title {
    color: #FFFFFF;
    font-size: 21px;
    font-weight: 750;
    margin-bottom: 5px;
}

.section-description {
    color: #94A3B8;
    font-size: 13px;
    margin-bottom: 18px;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #192231, #111824);
    border: 1px solid #303E54;
    border-radius: 15px;
    padding: 18px;
}

[data-testid="stMetricLabel"] {
    color: #AAB6C8;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF;
    font-weight: 750;
}

.mode-panel {
    background: linear-gradient(145deg, #192231, #111824);
    border: 1px solid #303E54;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
}

div[role="radiogroup"] {
    gap: 12px;
}

div[role="radiogroup"] label {
    background: #192231;
    border: 1px solid #35445C;
    border-radius: 10px;
    padding: 10px 16px;
}

div[role="radiogroup"] label:has(input:checked) {
    border-color: #E50914;
    background: #35111D;
}

.stButton button {
    border-radius: 9px;
    border: 1px solid #71303B;
    font-weight: 600;
}

.stButton button[kind="primary"] {
    background: #E50914;
    color: white;
    border: none;
}

.stButton button:hover {
    border-color: #E50914;
    color: white;
}

div[data-testid="stChatMessage"] {
    background: #141C29;
    border: 1px solid #293449;
    border-radius: 15px;
    padding: 17px;
    margin-bottom: 12px;
}

div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: #171C29;
}

/* AI Copilot conversation input visibility */
[data-testid="stChatInput"] {
    border: 1px solid #71303B !important;
    border-radius: 13px !important;
    background: #FFFFFF !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #E50914 !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] textarea:focus,
[data-testid="stChatInputTextArea"],
[data-testid="stChatInputTextArea"]:focus {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    caret-color: #000000 !important;
    background-color: #FFFFFF !important;
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
    color: #E50914 !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #303E54;
    border-radius: 10px;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

hr {
    border-color: #293449;
}

footer {
    visibility: hidden;
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
    <div class="hero-label">NETFLIX CUSTOMER INTELLIGENCE PLATFORM</div>
    <div class="hero-title">🤖 AI Analytics Copilot</div>
    <div class="hero-description">
        Your intelligent business analysis assistant.
        Explore customer intelligence, query business data,
        understand customer feedback and uncover actionable insights.
    </div>
    <div class="hero-tag">
        TEXT-TO-SQL &nbsp; · &nbsp; RETRIEVAL AUGMENTED GENERATION
    </div>
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

st.markdown("---")

left, right = st.columns([3, 1])

with left:
    st.markdown(
        '<div class="section-title">Choose Analysis Mode</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="section-description">Select the intelligence engine for your question.</div>',
        unsafe_allow_html=True
    )

    analysis_mode = st.radio(
        "Analysis mode",
        ["Text-to-SQL", "RAG - Support & Feedback"],
        horizontal=True,
        label_visibility="collapsed"
    )

with right:
    st.write("")
    st.write("")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.copilot_messages = []
        st.rerun()


if analysis_mode == "Text-to-SQL":
    st.info(
        "📊 **Database Intelligence:** Ask questions about customers, "
        "subscriptions, revenue, churn and business performance. "
        "The system generates and executes SQL queries."
    )
else:
    st.info(
        "💬 **Support Intelligence:** Ask questions about customer "
        "complaints, support tickets and feedback. The system retrieves "
        "relevant records using RAG."
    )


st.markdown("---")

st.markdown(
    '<div class="section-title">Conversation Workspace</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="section-description">Ask a business question and review the generated insights below.</div>',
    unsafe_allow_html=True
)


if not st.session_state.copilot_messages:
    st.markdown("""
    <div style="
        background:linear-gradient(145deg,#192231,#111824);
        border:1px solid #303E54;
        border-radius:16px;
        padding:28px;
        text-align:center;
        margin:18px 0;
    ">
        <div style="font-size:36px;">🤖</div>
        <div style="font-size:19px;font-weight:750;color:#FFFFFF;margin:12px 0;">
            Welcome to AI Analytics Copilot
        </div>
        <div style="font-size:13px;color:#AAB6C8;line-height:1.8;">
            Start a conversation by asking a question about your business data
            or customer feedback.
        </div>
    </div>
    """, unsafe_allow_html=True)


for message in st.session_state.copilot_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            if message.get("status"):
                st.caption(f"Execution status: {message['status']}")

            if message.get("results"):
                st.markdown("#### 📊 Query Results")

                results = message["results"]

                if isinstance(results, list) and results:
                    if all(isinstance(item, dict) for item in results):
                        st.dataframe(
                            pd.DataFrame(results),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.write(results)
                else:
                    st.write(results)

            if message.get("sources"):
                with st.expander("📚 View Retrieved Sources"):
                    st.write(message["sources"])

            if message.get("elapsed") is not None:
                st.caption(
                    f"⏱️ Response time: {message['elapsed']:.2f} seconds"
                )


question = st.chat_input("Ask your business question here...")

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

        st.session_state.copilot_messages.append(assistant_message)

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
