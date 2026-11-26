
import time
import uuid

import pandas as pd
import streamlit as st

from database.query_executor import ask_database


st.set_page_config(
    page_title="Netflix | AI Analytics Copilot",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)


st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #101827 0%, #172235 55%, #101827 100%);
    color: #F8FAFC;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1150px;
    padding-top: 2.5rem;
    padding-bottom: 5rem;
}

.hero {
    padding: 28px 30px;
    border: 1px solid #334155;
    border-radius: 18px;
    background: linear-gradient(120deg, #202D42, #172235);
    margin-bottom: 28px;
}

.hero h1 {
    color: #F8FAFC;
    font-size: 36px;
    font-weight: 750;
    margin-bottom: 8px;
}

.hero p {
    color: #CBD5E1;
    font-size: 16px;
    margin-bottom: 0;
}

.section-title {
    color: #F8FAFC;
    font-size: 21px;
    font-weight: 650;
    margin-top: 24px;
    margin-bottom: 12px;
}

.feature-card {
    background: #202D42;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 18px;
    min-height: 115px;
}

.feature-card h3 {
    color: #F8FAFC;
    font-size: 17px;
    margin-bottom: 8px;
}

.feature-card p {
    color: #CBD5E1;
    font-size: 14px;
    margin-bottom: 0;
}

div[data-testid="stChatMessage"] {
    background: #202D42;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 14px;
}

div[data-testid="stChatMessage"] p {
    color: #F8FAFC !important;
}

[data-testid="stTextInput"] input {
    background: #FFFFFF !important;
    color: #111827 !important;
    border: 2px solid #64748B !important;
    border-radius: 12px !important;
}

[data-testid="stTextInput"] input::placeholder {
    color: #64748B !important;
}

.stFormSubmitButton button {
    background: #E50914;
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
}

.stFormSubmitButton button:hover {
    background: #B20710;
    color: white;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 12px;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

.footer {
    text-align: center;
    color: #94A3B8;
    font-size: 13px;
    padding-top: 30px;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero">
    <h1>🎬 Netflix AI Analytics Copilot</h1>
    <p>
        Explore customer behavior, subscriptions, viewing activity,
        payments and business performance using natural language.
    </p>
</div>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="section-title">What can I help you analyze?</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>👥 Customer Insights</h3>
        <p>Explore customer counts, demographics and segments.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Business Performance</h3>
        <p>Investigate subscriptions, payments and customer churn.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🎥 Viewing Analytics</h3>
        <p>Understand viewing activity and content engagement.</p>
    </div>
    """, unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = []

if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False


chat_col, clear_col = st.columns([5, 1])

with chat_col:
    st.markdown(
        '<div class="section-title">💬 AI Analytics Copilot</div>',
        unsafe_allow_html=True
    )

with clear_col:
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.confirm_clear = True

if st.session_state.confirm_clear:
    st.warning("Are you sure you want to clear the entire conversation?")

    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button("Yes, clear chat", key="confirm_clear_chat"):
            st.session_state.messages = []
            st.session_state.confirm_clear = False
            st.rerun()

    with cancel_col:
        if st.button("Cancel", key="cancel_clear_chat"):
            st.session_state.confirm_clear = False
            st.rerun()


st.caption(
    "Ask a business question. The Copilot will analyze your database "
    "and return the results."
)


with st.form("question_form", clear_on_submit=True):
    question = st.text_input(
        "Ask your Netflix business question",
        placeholder="Example: How many customers are there?"
    )

    submitted = st.form_submit_button("Submit question")


if submitted and question.strip():

    turn_id = uuid.uuid4().hex

    st.session_state.messages.append({
        "role": "user",
        "content": question.strip(),
        "turn_id": turn_id
    })

    with st.spinner("Analyzing your Netflix data..."):

        start_time = time.perf_counter()

        try:
            response = ask_database(question.strip())

            if not isinstance(response, dict):
                raise ValueError(
                    "The AI service returned an unexpected response."
                )

            status = response.get("execution_status", "FAILED")

            if status == "SUCCESS":

                results = response.get(
                    "results",
                    response.get("rows", [])
                )

                answer = response.get(
                    "answer",
                    "The analysis completed, but an explanation could not be generated."
                )

                elapsed = time.perf_counter() - start_time

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "results": results,
                    "elapsed": elapsed,
                    "turn_id": turn_id
                })

            else:
                error_message = response.get(
                    "error",
                    "The database query could not be completed."
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        "I couldn't complete that analysis. "
                        "Please try rephrasing your question."
                    ),
                    "error": error_message,
                    "results": None,
                    "turn_id": turn_id
                })

        except Exception:
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    "I couldn't process that question. Please try again."
                ),
                "results": None,
                "turn_id": turn_id
            })


delete_turn_id = None

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        if message["role"] == "user":
            st.markdown(message["content"])

            if message.get("turn_id"):
                if st.button(
                    "🗑️ Delete this exchange",
                    key=f"delete_{message['turn_id']}"
                ):
                    delete_turn_id = message["turn_id"]

        else:
            st.markdown(message["content"])

            if message.get("results") is not None:

                if message["results"]:
                    st.dataframe(
                        pd.DataFrame(message["results"]),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No records found.")

                if message.get("elapsed") is not None:
                    st.caption(
                        f"Completed in {message['elapsed']:.1f} seconds."
                    )

            if message.get("error"):
                st.error(message["error"])


if delete_turn_id:
    st.session_state.messages = [
        message
        for message in st.session_state.messages
        if message.get("turn_id") != delete_turn_id
    ]
    st.rerun()


st.markdown("""
<div class="footer">
    Netflix Customer Intelligence & AI Analytics Copilot
</div>
""", unsafe_allow_html=True)
