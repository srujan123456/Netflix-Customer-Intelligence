
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database.query_executor import get_db_connection
from llm.rag_system import ask_support_question


st.set_page_config(
    page_title="Support Intelligence | Netflix",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)


COLORS = {
    "background": "#090B10",
    "surface": "#121722",
    "surface_alt": "#192131",
    "border": "#293449",
    "red": "#E50914",
    "text": "#F5F7FA",
    "muted": "#9BA8BA",
    "green": "#22C55E",
    "yellow": "#F5B942",
    "orange": "#F97316"
}


st.markdown("""
<style>
.stApp {
    background: #090B10;
    color: #F5F7FA;
}

[data-testid="stSidebar"] {
    background: #10141E;
    border-right: 1px solid #293449;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

/* Main heading */

.hero {
    background: linear-gradient(115deg, #29080D 0%, #651018 55%, #B20D19 100%);
    border: 1px solid #81202A;
    border-radius: 18px;
    padding: 32px;
    margin-bottom: 25px;
}

.eyebrow {
    color: #FF9299;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.hero-title {
    color: #FFFFFF !important;
    font-size: 34px;
    font-weight: 800;
    margin: 8px 0;
}

.hero-description {
    color: #F2D5D8 !important;
    font-size: 14px;
    margin: 0;
}

/* Section headings */

.section-title {
    font-size: 21px;
    font-weight: 750;
    color: #F5F7FA !important;
    margin: 10px 0 16px 0;
}

/* KPI cards */

.kpi-card {
    background: linear-gradient(145deg, #192131, #111722);
    border: 1px solid #293449;
    border-radius: 15px;
    padding: 20px;
    min-height: 125px;
}

.kpi-label {
    color: #9BA8BA !important;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.7px;
}

.kpi-value {
    color: #FFFFFF !important;
    font-size: 29px;
    font-weight: 800;
    margin-top: 10px;
}

.kpi-caption {
    color: #AAB4C5 !important;
    font-size: 11px;
    margin-top: 4px;
}

/* Panels */

.panel {
    background: #121722;
    border: 1px solid #293449;
    border-radius: 15px;
    padding: 20px;
}

/* AI section */

.ai-panel {
    background: linear-gradient(145deg, #191E2B, #111722);
    border: 1px solid #3A3445;
    border-radius: 17px;
    padding: 24px;
}

.ai-label {
    color: #FF7A83 !important;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
}

.ai-panel h2 {
    color: #FFFFFF !important;
}

.ai-panel p {
    color: #C2CCDA !important;
}

/* AI response containers */

div[data-testid="stChatMessage"] {
    background-color: #192131 !important;
    border: 1px solid #36445B !important;
    border-radius: 13px !important;
    padding: 16px !important;
    color: #F5F7FA !important;
}

div[data-testid="stChatMessage"] * {
    color: #F5F7FA !important;
}

div[data-testid="stChatMessage"] p,
div[data-testid="stChatMessage"] li,
div[data-testid="stChatMessage"] h1,
div[data-testid="stChatMessage"] h2,
div[data-testid="stChatMessage"] h3,
div[data-testid="stChatMessage"] h4,
div[data-testid="stChatMessage"] strong,
div[data-testid="stChatMessage"] span,
div[data-testid="stChatMessage"] div {
    color: #F5F7FA !important;
}

div[data-testid="stChatMessage"] a {
    color: #FF737D !important;
}

div[data-testid="stChatMessage"] code {
    color: #FFFFFF !important;
    background-color: #252F40 !important;
}

/* Input fields */

div[data-testid="stTextInput"] input {
    background: #101722 !important;
    color: #FFFFFF !important;
    border: 1px solid #36445B !important;
    border-radius: 10px !important;
}

div[data-testid="stTextInput"] input::placeholder {
    color: #8290A5 !important;
}

/* Buttons */

.stButton button {
    border-radius: 9px;
    min-height: 42px;
    font-weight: 650;
}

/* Metrics */

div[data-testid="stMetric"] {
    background: #192131;
    border: 1px solid #293449;
    border-radius: 12px;
    padding: 15px;
}

div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: #F5F7FA !important;
}

/* Dataframes */

div[data-testid="stDataFrame"] {
    border: 1px solid #293449;
    border-radius: 10px;
    overflow: hidden;
}

/* General text */

.stApp p,
.stApp label,
.stApp li {
    color: #DCE3ED;
}

.stApp h1,
.stApp h2,
.stApp h3 {
    color: #F5F7FA;
}

hr {
    border-color: #293449;
}
</style>
""", unsafe_allow_html=True)


def fetch_dataframe(query):
    connection = get_db_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(query)

        rows = cursor.fetchall()
        columns = [item[0] for item in cursor.description]

        return pd.DataFrame(rows, columns=columns)

    finally:
        connection.close()


@st.cache_data(ttl=300)
def load_support_metrics():
    return fetch_dataframe("""
        SELECT
            COUNT(*) AS total_tickets,
            COUNT(*) FILTER (
                WHERE LOWER(priority) = 'high'
            ) AS high_priority_tickets
        FROM support_tickets
    """)


@st.cache_data(ttl=300)
def load_feedback_metrics():
    return fetch_dataframe("""
        SELECT
            COUNT(*) AS total_feedback,
            ROUND(AVG(rating)::numeric, 2) AS average_rating
        FROM customer_feedback
    """)


@st.cache_data(ttl=300)
def load_sentiment_distribution():
    return fetch_dataframe("""
        SELECT
            sentiment_label,
            COUNT(*) AS feedback_count
        FROM customer_feedback
        WHERE sentiment_label IS NOT NULL
        GROUP BY sentiment_label
        ORDER BY feedback_count DESC
    """)


@st.cache_data(ttl=300)
def load_support_trends():
    return fetch_dataframe("""
        SELECT
            DATE_TRUNC('month', ticket_date)::date AS month,
            COUNT(*) AS ticket_count
        FROM support_tickets
        WHERE ticket_date IS NOT NULL
        GROUP BY DATE_TRUNC('month', ticket_date)
        ORDER BY month
    """)


@st.cache_data(ttl=300)
def load_feedback_trends():
    return fetch_dataframe("""
        SELECT
            DATE_TRUNC('month', feedback_date)::date AS month,
            COUNT(*) AS feedback_count
        FROM customer_feedback
        WHERE feedback_date IS NOT NULL
        GROUP BY DATE_TRUNC('month', feedback_date)
        ORDER BY month
    """)


def format_number(value):
    return f"{int(value):,}"


def render_kpi(label, value, caption, accent=None):
    value_color = accent or COLORS["text"]

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{value_color}">
                {value}
            </div>
            <div class="kpi-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def style_chart(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial",
            color="#DCE3ED"
        ),
        margin=dict(l=15, r=15, t=55, b=15),
        legend=dict(
            bgcolor="rgba(0,0,0,0)"
        )
    )

    return fig


st.markdown("""
<div class="hero">
    <div class="eyebrow">NETFLIX CUSTOMER INTELLIGENCE</div>
    <div class="hero-title">Support Intelligence</div>
    <p class="hero-description">
        Understand customer complaints, feedback and sentiment.
        Discover actionable insights using AI-powered retrieval.
    </p>
</div>
""", unsafe_allow_html=True)


if "support_ai_response" not in st.session_state:
    st.session_state.support_ai_response = None

if "support_ai_question" not in st.session_state:
    st.session_state.support_ai_question = ""


try:
    support_metrics = load_support_metrics()
    feedback_metrics = load_feedback_metrics()
    sentiment_data = load_sentiment_distribution()
    support_trends = load_support_trends()
    feedback_trends = load_feedback_trends()

    total_tickets = support_metrics.iloc[0]["total_tickets"]
    high_priority = support_metrics.iloc[0]["high_priority_tickets"]
    total_feedback = feedback_metrics.iloc[0]["total_feedback"]

    average_rating = feedback_metrics.iloc[0]["average_rating"]

    average_rating = (
        float(average_rating)
        if pd.notna(average_rating)
        else 0
    )

except Exception as error:
    st.error(f"Unable to load support analytics: {error}")
    st.stop()


st.markdown(
    '<div class="section-title">Customer Experience Overview</div>',
    unsafe_allow_html=True
)

kpi_columns = st.columns(4)

with kpi_columns[0]:
    render_kpi(
        "TOTAL SUPPORT TICKETS",
        format_number(total_tickets),
        "Recorded support requests"
    )

with kpi_columns[1]:
    render_kpi(
        "HIGH PRIORITY",
        format_number(high_priority),
        "High-priority support requests",
        "#FF747C"
    )

with kpi_columns[2]:
    render_kpi(
        "CUSTOMER FEEDBACK",
        format_number(total_feedback),
        "Total feedback records"
    )

with kpi_columns[3]:
    render_kpi(
        "AVERAGE RATING",
        f"{average_rating:.2f}/5",
        "Average customer rating",
        "#F5B942"
    )


st.divider()


st.markdown(
    '<div class="section-title">Customer Sentiment Intelligence</div>',
    unsafe_allow_html=True
)

sentiment_col, sentiment_details_col = st.columns([1.7, 1])

with sentiment_col:
    if not sentiment_data.empty:
        sentiment_chart = px.pie(
            sentiment_data,
            names="sentiment_label",
            values="feedback_count",
            hole=0.68,
            color="sentiment_label",
            color_discrete_map={
                "Positive": "#22C55E",
                "Neutral": "#F5B942",
                "Negative": "#EF4444"
            }
        )

        sentiment_chart.update_traces(
            textposition="outside",
            textinfo="percent+label",
            marker=dict(
                line=dict(
                    color="#121722",
                    width=3
                )
            )
        )

        sentiment_chart.update_layout(
            showlegend=False,
            title="Feedback Sentiment Distribution"
        )

        st.plotly_chart(
            style_chart(sentiment_chart),
            use_container_width=True
        )

    else:
        st.info("No sentiment records are available.")


with sentiment_details_col:
    st.markdown(
        '<div class="panel"><b>Sentiment Breakdown</b></div>',
        unsafe_allow_html=True
    )

    if not sentiment_data.empty:
        st.dataframe(
            sentiment_data,
            use_container_width=True,
            hide_index=True
        )

        total_sentiment = sentiment_data["feedback_count"].sum()

        if total_sentiment:
            for _, row in sentiment_data.iterrows():
                percentage = (
                    row["feedback_count"] / total_sentiment
                ) * 100

                st.markdown(
                    f"**{row['sentiment_label']}** · {percentage:.1f}%"
                )

                st.progress(float(percentage / 100))

    else:
        st.caption("Sentiment data is not available.")


st.divider()


st.markdown(
    '<div class="section-title">Support & Feedback Trends</div>',
    unsafe_allow_html=True
)

trend_left, trend_right = st.columns(2)

with trend_left:
    if not support_trends.empty:
        fig = px.area(
            support_trends,
            x="month",
            y="ticket_count",
            markers=True,
            title="Monthly Support Ticket Volume"
        )

        fig.update_traces(
            line_color="#E50914",
            fillcolor="rgba(229,9,20,0.18)"
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("No support trend data is available.")


with trend_right:
    if not feedback_trends.empty:
        fig = px.line(
            feedback_trends,
            x="month",
            y="feedback_count",
            markers=True,
            title="Monthly Customer Feedback"
        )

        fig.update_traces(
            line_color="#F5B942",
            line_width=3,
            marker_size=7
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("No feedback trend data is available.")


st.divider()


st.markdown("""
<div class="ai-panel">
    <div class="ai-label">AI-POWERED CUSTOMER INTELLIGENCE</div>
    <h2 style="color:#FFFFFF; margin-top:8px;">
        Ask your customer data
    </h2>
    <p style="color:#C2CCDA;">
        Search support tickets and customer feedback using natural language.
        Get evidence-based answers from your RAG system.
    </p>
</div>
""", unsafe_allow_html=True)


question = st.text_input(
    "Ask a support intelligence question",
    placeholder="Example: What are the most common customer complaints?",
    key="support_question_input"
)

search_col, clear_col = st.columns([1, 5])

with search_col:
    search_clicked = st.button(
        "Analyze with AI",
        type="primary",
        use_container_width=True
    )

with clear_col:
    clear_clicked = st.button(
        "Clear Results",
        use_container_width=True
    )


if clear_clicked:
    st.session_state.support_ai_response = None
    st.session_state.support_ai_question = ""
    st.rerun()


if search_clicked:
    if not question.strip():
        st.warning("Please enter a question before searching.")

    else:
        with st.spinner(
            "Retrieving records and generating AI insights..."
        ):
            try:
                response = ask_support_question(
                    question.strip(),
                    top_k=8
                )

                st.session_state.support_ai_response = response
                st.session_state.support_ai_question = question.strip()

            except Exception as error:
                st.error(f"AI analysis failed: {error}")


if st.session_state.support_ai_response:
    response = st.session_state.support_ai_response

    st.markdown(
        '<div class="section-title">AI Analysis Results</div>',
        unsafe_allow_html=True
    )

    with st.chat_message("user"):
        st.markdown(
            st.session_state.support_ai_question,
            unsafe_allow_html=False
        )

    with st.chat_message("assistant"):
        st.markdown(
            response.get("answer", "No answer returned."),
            unsafe_allow_html=False
        )

    result_col1, result_col2 = st.columns(2)

    with result_col1:
        st.metric(
            "Records Retrieved",
            response.get("records_retrieved", 0)
        )

    with result_col2:
        st.metric(
            "Execution Status",
            response.get("execution_status", "Unknown")
        )

    references = response.get("source_references", [])

    if references:
        with st.expander("View Supporting Source References"):
            st.dataframe(
                pd.DataFrame(references),
                use_container_width=True,
                hide_index=True
            )


st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#9BA8BA;
        font-size:12px;
    ">
        NETFLIX CUSTOMER INTELLIGENCE · SUPPORT INTELLIGENCE
    </div>
    """,
    unsafe_allow_html=True
)
