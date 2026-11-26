
import json
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm.report_generator import generate_report


st.set_page_config(
    page_title="Automated Reports | Netflix Intelligence",
    page_icon="📊",
    layout="wide"
)


st.markdown("""
<style>
.stApp {
    background: #090D18;
    color: #F4F6FC;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

[data-testid="stSidebar"] {
    background: #101727;
    border-right: 1px solid #263249;
}

.hero {
    background: linear-gradient(120deg, #171F34, #251629);
    border: 1px solid #34334B;
    border-radius: 20px;
    padding: 30px 32px;
    margin-bottom: 25px;
}

.hero-tag {
    color: #F04B58;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
}

.hero-title {
    color: #FFFFFF;
    font-size: 34px;
    font-weight: 800;
    margin-top: 10px;
    margin-bottom: 8px;
}

.hero-subtitle {
    color: #AAB5CA;
    font-size: 15px;
}

.section-title {
    color: #F4F6FC;
    font-size: 21px;
    font-weight: 750;
    margin-top: 25px;
    margin-bottom: 14px;
}

.panel {
    background: #141D2F;
    border: 1px solid #29364D;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 18px;
}

.panel-label {
    color: #9AA9C2;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.panel-value {
    color: #FFFFFF;
    font-size: 25px;
    font-weight: 800;
    margin-top: 8px;
}

.panel-description {
    color: #9AA9C2;
    font-size: 13px;
    margin-top: 5px;
}

div[data-testid="stMetric"] {
    background: #141D2F;
    border: 1px solid #29364D;
    padding: 18px;
    border-radius: 14px;
}

div[data-testid="stMetricLabel"] {
    color: #AAB5CA;
}

div[data-testid="stMetricValue"] {
    color: #FFFFFF;
}

.stButton > button {
    background: #E50914;
    color: white;
    border: none;
    border-radius: 9px;
    padding: 10px 20px;
    font-weight: 700;
    min-height: 43px;
}

.stButton > button:hover {
    background: #B80710;
    color: white;
    border: none;
}

.stDownloadButton > button {
    background: #202D43;
    color: #FFFFFF;
    border: 1px solid #40516D;
    border-radius: 9px;
    min-height: 42px;
}

.stDownloadButton > button:hover {
    background: #2D3D57;
    color: white;
    border-color: #E50914;
}

div[data-baseweb="select"] > div {
    background: #141D2F;
    border-color: #34425B;
}

.stTextInput input {
    background: #141D2F;
    color: white;
}

div[data-testid="stExpander"] {
    background: #141D2F;
    border: 1px solid #29364D;
    border-radius: 12px;
}

hr {
    border-color: #29364D;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero">
    <div class="hero-tag">NETFLIX CUSTOMER INTELLIGENCE</div>
    <div class="hero-title">Automated Reports</div>
    <div class="hero-subtitle">
        Generate business reports, review AI-powered insights and
        download structured reporting data.
    </div>
</div>
""", unsafe_allow_html=True)


def json_safe(value):
    return json.dumps(value, indent=4, ensure_ascii=False, default=str)


def render_report_data(data, depth=0):
    if isinstance(data, dict):
        if not data:
            st.info("No report data available.")
            return

        for key, value in data.items():
            heading = str(key).replace("_", " ").title()

            if isinstance(value, (dict, list)):
                with st.expander(heading, expanded=(depth == 0)):
                    render_report_data(value, depth + 1)
            else:
                st.markdown(
                    f"**{heading}:** {value if value is not None else 'N/A'}"
                )

    elif isinstance(data, list):
        if not data:
            st.info("No records available in this section.")
            return

        if all(isinstance(item, dict) for item in data):
            st.dataframe(
                pd.DataFrame(data),
                use_container_width=True,
                hide_index=True
            )
        else:
            for item in data:
                st.write(item)

    else:
        st.write(data)


st.markdown('<div class="section-title">Report Configuration</div>',
            unsafe_allow_html=True)

left, right = st.columns([2, 1])

with left:
    period = st.selectbox(
        "Select reporting period",
        options=["weekly", "monthly", "quarterly"],
        format_func=lambda value: value.title()
    )

with right:
    st.markdown(
        '<div class="panel">'
        '<div class="panel-label">Report type</div>'
        f'<div class="panel-value">{period.title()}</div>'
        '<div class="panel-description">Business intelligence report</div>'
        '</div>',
        unsafe_allow_html=True
    )


if "generated_report" not in st.session_state:
    st.session_state["generated_report"] = None

if "generated_report_period" not in st.session_state:
    st.session_state["generated_report_period"] = None


generate_col, reset_col = st.columns([1, 5])

with generate_col:
    generate_clicked = st.button(
        "Generate Report",
        use_container_width=True
    )

with reset_col:
    reset_clicked = st.button(
        "Clear Current Report",
        use_container_width=True
    )


if reset_clicked:
    st.session_state["generated_report"] = None
    st.session_state["generated_report_period"] = None
    st.rerun()


if generate_clicked:
    try:
        with st.spinner(
            f"Generating your {period} report and AI interpretation..."
        ):
            result = generate_report(period)

        if not isinstance(result, dict):
            raise ValueError("The report generator returned an unexpected result.")

        if result.get("execution_status") != "SUCCESS":
            raise RuntimeError(
                result.get("error", "Report generation was unsuccessful.")
            )

        st.session_state["generated_report"] = result
        st.session_state["generated_report_period"] = period

        st.success("Report generated successfully.")

    except Exception as error:
        st.error(f"Report generation failed: {error}")


result = st.session_state["generated_report"]
result_period = st.session_state["generated_report_period"]


if result:
    st.divider()

    st.markdown(
        '<div class="section-title">Report Overview</div>',
        unsafe_allow_html=True
    )

    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")

    overview1, overview2, overview3 = st.columns(3)

    with overview1:
        st.metric("Report Period", result_period.title())

    with overview2:
        st.metric("Generation Status", "Successful")

    with overview3:
        st.metric("Generated On", generated_at)

    report_data = result.get("report_data", {})
    ai_interpretation = result.get("ai_interpretation", "")

    st.markdown(
        '<div class="section-title">Business Report Data</div>',
        unsafe_allow_html=True
    )

    with st.container(border=True):
        render_report_data(report_data)

    st.markdown(
        '<div class="section-title">AI Business Interpretation</div>',
        unsafe_allow_html=True
    )

    with st.container(border=True):
        if ai_interpretation:
            st.markdown(ai_interpretation)
        else:
            st.info("No AI interpretation was returned.")

    st.markdown(
        '<div class="section-title">Export Report</div>',
        unsafe_allow_html=True
    )

    report_document = {
        "report_period": result_period,
        "generated_at": generated_at,
        "execution_status": result.get("execution_status"),
        "report_data": report_data,
        "ai_interpretation": ai_interpretation
    }

    download_col1, download_col2 = st.columns(2)

    with download_col1:
        st.download_button(
            label="Download JSON Report",
            data=json_safe(report_document),
            file_name=f"netflix_{result_period}_report.json",
            mime="application/json",
            use_container_width=True
        )

    with download_col2:
        text_report = (
            f"NETFLIX CUSTOMER INTELLIGENCE\n"
            f"{result_period.upper()} REPORT\n"
            f"Generated: {generated_at}\n\n"
            f"REPORT DATA\n"
            f"{json_safe(report_data)}\n\n"
            f"AI BUSINESS INTERPRETATION\n"
            f"{ai_interpretation}\n"
        )

        st.download_button(
            label="Download Text Report",
            data=text_report,
            file_name=f"netflix_{result_period}_report.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    st.markdown("""
    <div class="panel">
        <div class="panel-label">Ready to generate</div>
        <div class="panel-value">Your next business report starts here.</div>
        <div class="panel-description">
            Select a reporting period and click Generate Report.
            Your database metrics and AI interpretation will appear here.
        </div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("""
<hr>
<div style="text-align:center; color:#71809A; font-size:12px; padding:12px;">
    Netflix Customer Intelligence Copilot · Automated Reporting
</div>
""", unsafe_allow_html=True)
