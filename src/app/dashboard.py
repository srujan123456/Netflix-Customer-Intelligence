
from pathlib import Path

import streamlit as st


CURRENT_DIR = Path(__file__).resolve().parent
PAGES_DIR = CURRENT_DIR / "pages"


st.set_page_config(
    page_title="Netflix Customer Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


PAGE_CONFIG = [
    {
        "title": "Executive Dashboard",
        "file": "01_Executive_Dashboard.py",
        "icon": "📊",
        "section": "Overview"
    },
    {
        "title": "Customer Analytics",
        "file": "02_Customer_Analytics.py",
        "icon": "👥",
        "section": "Analytics"
    },
    {
        "title": "Churn Prediction",
        "file": "03_Churn_Prediction.py",
        "icon": "📉",
        "section": "Analytics"
    },
    {
        "title": "Customer Segmentation",
        "file": "04_Customer_Segmentation.py",
        "icon": "🎯",
        "section": "Analytics"
    },
    {
        "title": "AI Analytics Copilot",
        "file": "05_AI_Analytics_Copilot.py",
        "icon": "🤖",
        "section": "AI Intelligence"
    },
    {
        "title": "Support Intelligence",
        "file": "06_Support_Intelligence.py",
        "icon": "💬",
        "section": "AI Intelligence"
    },
    {
        "title": "Automated Reports",
        "file": "07_Automated_Reports.py",
        "icon": "📄",
        "section": "AI Intelligence"
    }
]


missing_pages = [
    page["file"]
    for page in PAGE_CONFIG
    if not (PAGES_DIR / page["file"]).is_file()
]

if missing_pages:
    st.error("The following page files could not be found:")
    for filename in missing_pages:
        st.write(f"- {filename}")
    st.info(
        "Check that all seven page files are saved inside "
        "the src/app/pages folder."
    )
    st.stop()


navigation_groups = {}

for page in PAGE_CONFIG:
    navigation_groups.setdefault(page["section"], []).append(
        st.Page(
            str(PAGES_DIR / page["file"]),
            title=page["title"],
            icon=page["icon"],
            default=page["file"] == "01_Executive_Dashboard.py"
        )
    )


selected_page = st.navigation(
    navigation_groups,
    position="sidebar"
)

selected_page.run()
