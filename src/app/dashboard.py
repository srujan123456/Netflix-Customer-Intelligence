
from pathlib import Path

import streamlit as st


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
PAGES_DIR = APP_DIR / "pages"


# --------------------------------------------------
# STREAMLIT CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Netflix Customer Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

PAGES = [
    {
        "title": "Executive Dashboard",
        "filename": "01_Executive_Dashboard.py",
        "icon": "📊",
        "section": "Overview"
    },
    {
        "title": "Customer Analytics",
        "filename": "02_Customer_Analytics.py",
        "icon": "👥",
        "section": "Analytics"
    },
    {
        "title": "Churn Prediction",
        "filename": "03_Churn_Prediction.py",
        "icon": "📉",
        "section": "Analytics"
    },
    {
        "title": "Customer Segmentation",
        "filename": "04_Customer_Segmentation.py",
        "icon": "🎯",
        "section": "Analytics"
    },
    {
        "title": "AI Analytics Copilot",
        "filename": "05_AI_Analytics_Copilot.py",
        "icon": "🤖",
        "section": "AI Intelligence"
    },
    {
        "title": "Support Intelligence",
        "filename": "06_Support_Intelligence.py",
        "icon": "💬",
        "section": "AI Intelligence"
    },
    {
        "title": "Automated Reports",
        "filename": "07_Automated_Reports.py",
        "icon": "📄",
        "section": "AI Intelligence"
    }
]


# --------------------------------------------------
# CHECK PAGE FILES
# --------------------------------------------------

missing_pages = []

for page in PAGES:
    page_path = PAGES_DIR / page["filename"]

    if not page_path.is_file():
        missing_pages.append(page["filename"])


if missing_pages:
    st.error("Some application pages are missing.")

    for filename in missing_pages:
        st.write(f"- {filename}")

    st.info(
        "Ensure that all seven Python page files "
        "are available inside src/app/pages."
    )

    st.stop()


# --------------------------------------------------
# CREATE NAVIGATION
# --------------------------------------------------

navigation = {}

for page in PAGES:

    section = page["section"]

    if section not in navigation:
        navigation[section] = []

    navigation[section].append(
        st.Page(
            str(PAGES_DIR / page["filename"]),
            title=page["title"],
            icon=page["icon"],
            default=(
                page["filename"]
                == "01_Executive_Dashboard.py"
            )
        )
    )


# --------------------------------------------------
# RUN SELECTED PAGE
# --------------------------------------------------

selected_page = st.navigation(
    navigation,
    position="sidebar"
)

selected_page.run()
