
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database.query_executor import get_db_connection

st.set_page_config(
    page_title="Netflix Intelligence | Customer Analytics",
    page_icon="🎬",
    layout="wide"
)

BG = "#0B1120"
CARD = "#111D31"
TEXT = "#FFFFFF"
MUTED = "#91A8C5"
RED = "#E50914"
BORDER = "#263851"

st.markdown("""
<style>
.stApp {
    background: #0B1120;
    color: #FFFFFF;
}

header[data-testid="stHeader"] {
    background: #0B1120;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1600px;
}

h1, h2, h3 {
    color: #FFFFFF !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #17263E, #111D31);
    border: 1px solid #293B56;
    border-radius: 14px;
    padding: 18px;
    min-height: 125px;
}

[data-testid="stMetricLabel"] {
    color: #91A8C5 !important;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-weight: 750;
}

.section-card {
    background: #111D31;
    border: 1px solid #263851;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 15px;
}

.dashboard-header {
    background: linear-gradient(110deg, #15243B, #101B2D);
    border-left: 6px solid #E50914;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 24px;
}

.netflix-title {
    font-size: 34px;
    font-weight: 850;
    letter-spacing: 1px;
}

.netflix-red {
    color: #E50914;
}

.dashboard-subtitle {
    color: #91A8C5;
    font-size: 13px;
    margin-top: 8px;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner="Loading customer analytics from PostgreSQL...")
def load_data():
    connection = get_db_connection()

    try:
        customers = pd.read_sql_query(
            "SELECT * FROM customers",
            connection
        )

        subscriptions = pd.read_sql_query(
            "SELECT * FROM subscriptions",
            connection
        )

        viewing = pd.read_sql_query(
            "SELECT * FROM viewing_activity",
            connection
        )

        plans = pd.read_sql_query(
            "SELECT * FROM subscription_plans",
            connection
        )

        return customers, subscriptions, viewing, plans

    finally:
        connection.close()


def style_chart(fig, height=350):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=CARD,
        font=dict(
            color=MUTED,
            family="Arial"
        ),
        margin=dict(
            l=15,
            r=15,
            t=45,
            b=15
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)"
        )
    )

    fig.update_xaxes(gridcolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER)

    return fig


def has_columns(frame, columns):
    return all(column in frame.columns for column in columns)


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.markdown("""
<div class="dashboard-header">
    <div class="netflix-title">
        <span class="netflix-red">NETFLIX</span> INTELLIGENCE
    </div>

    <div class="dashboard-subtitle">
        CUSTOMER ANALYTICS |
        DEMOGRAPHICS · ENGAGEMENT · SUBSCRIPTIONS
    </div>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# LOAD DATABASE DATA
# --------------------------------------------------

try:
    customers, subscriptions, viewing, plans = load_data()

except Exception as error:
    st.error(f"Unable to load Customer Analytics data: {error}")

    st.info(
        "This page reads the existing local PostgreSQL database "
        "through database.query_executor.get_db_connection(). "
        "Check that PostgreSQL is running and that the four "
        "project tables are populated."
    )

    st.stop()


if customers.empty:
    st.warning(
        "The customers table is empty. "
        "No customer analytics can be displayed yet."
    )
    st.stop()


# --------------------------------------------------
# DATA TYPE CONVERSIONS
# --------------------------------------------------

if "age" in customers.columns:
    customers["age"] = pd.to_numeric(
        customers["age"],
        errors="coerce"
    )

if "watch_duration_minutes" in viewing.columns:
    viewing["watch_duration_minutes"] = pd.to_numeric(
        viewing["watch_duration_minutes"],
        errors="coerce"
    )

if "completion_percentage" in viewing.columns:
    viewing["completion_percentage"] = pd.to_numeric(
        viewing["completion_percentage"],
        errors="coerce"
    )


# --------------------------------------------------
# KPI CALCULATIONS
# --------------------------------------------------

total_customers = (
    customers["customer_id"].nunique()
    if "customer_id" in customers.columns
    else len(customers)
)

subscription_customers = (
    subscriptions["customer_id"].nunique()
    if has_columns(subscriptions, ["customer_id"])
    else 0
)

active_customers = 0

if has_columns(
    subscriptions,
    ["customer_id", "subscription_status"]
):
    active_status = (
        subscriptions["subscription_status"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    active_customers = subscriptions.loc[
        active_status.eq("active"),
        "customer_id"
    ].nunique()


viewing_customers = (
    viewing["customer_id"].nunique()
    if "customer_id" in viewing.columns
    else 0
)

total_sessions = len(viewing)

total_watch_hours = (
    viewing["watch_duration_minutes"].sum() / 60
    if "watch_duration_minutes" in viewing.columns
    else 0
)

avg_completion = (
    viewing["completion_percentage"].mean()
    if "completion_percentage" in viewing.columns
    else None
)


# --------------------------------------------------
# KPI DISPLAY
# --------------------------------------------------

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Total Customers",
    f"{total_customers:,}"
)

m2.metric(
    "Active Subscribers",
    f"{active_customers:,}"
)

m3.metric(
    "Viewing Sessions",
    f"{total_sessions:,}"
)

m4.metric(
    "Watch Time",
    f"{total_watch_hours:,.0f} hrs"
)


st.markdown("---")


# --------------------------------------------------
# CUSTOMER EXPLORER
# --------------------------------------------------

st.subheader("Customer Explorer")

filter_cols = st.columns(3)

filtered = customers.copy()


if "country" in filtered.columns:

    countries = sorted(
        filtered["country"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_countries = filter_cols[0].multiselect(
        "Country",
        countries,
        placeholder="All countries"
    )

    if selected_countries:
        filtered = filtered[
            filtered["country"].astype(str).isin(
                selected_countries
            )
        ]


if "gender" in filtered.columns:

    genders = sorted(
        filtered["gender"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_genders = filter_cols[1].multiselect(
        "Gender",
        genders,
        placeholder="All genders"
    )

    if selected_genders:
        filtered = filtered[
            filtered["gender"].astype(str).isin(
                selected_genders
            )
        ]


if "acquisition_channel" in filtered.columns:

    channels = sorted(
        filtered["acquisition_channel"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_channels = filter_cols[2].multiselect(
        "Acquisition Channel",
        channels,
        placeholder="All channels"
    )

    if selected_channels:
        filtered = filtered[
            filtered["acquisition_channel"].astype(str).isin(
                selected_channels
            )
        ]


st.caption(
    f"Showing {len(filtered):,} of {len(customers):,} customer records"
)


# --------------------------------------------------
# CUSTOMER DEMOGRAPHICS
# --------------------------------------------------

st.subheader("Customer Demographics")

left, right = st.columns(2)


# AGE DISTRIBUTION

with left:

    if (
        "age" in filtered.columns
        and filtered["age"].notna().any()
    ):

        age_data = filtered.dropna(
            subset=["age"]
        ).copy()

        age_data["Age Group"] = pd.cut(
            age_data["age"],
            bins=[0, 17, 24, 34, 44, 54, 120],
            labels=[
                "Under 18",
                "18–24",
                "25–34",
                "35–44",
                "45–54",
                "55+"
            ],
            include_lowest=True
        )

        age_counts = (
            age_data["Age Group"]
            .value_counts()
            .sort_index()
            .reset_index()
        )

        age_counts.columns = [
            "Age Group",
            "Customers"
        ]

        fig = px.bar(
            age_counts,
            x="Age Group",
            y="Customers",
            title="Customer Age Distribution",
            color_discrete_sequence=[RED],
            text="Customers"
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info(
            "Age data is not available in the customers table."
        )


# GENDER DISTRIBUTION

with right:

    if (
        "gender" in filtered.columns
        and filtered["gender"].notna().any()
    ):

        gender_counts = (
            filtered["gender"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Gender")
            .reset_index(name="Customers")
        )

        fig = px.pie(
            gender_counts,
            names="Gender",
            values="Customers",
            title="Customer Distribution by Gender",
            hole=0.55
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info(
            "Gender data is not available in the customers table."
        )


# --------------------------------------------------
# COUNTRY DISTRIBUTION AND ACQUISITION CHANNELS
# --------------------------------------------------

left, right = st.columns(2)


# TOP 10 COUNTRIES

with left:

    if "country" in filtered.columns:

        country_counts = (
            filtered["country"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .head(10)
            .rename_axis("Country")
            .reset_index(name="Customers")
        )

        fig = px.bar(
            country_counts.sort_values("Customers"),
            x="Customers",
            y="Country",
            orientation="h",
            title="Top 10 Countries by Customer Count",
            color_discrete_sequence=[RED]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("Country data is not available.")


# ACQUISITION CHANNELS

with right:

    if "acquisition_channel" in filtered.columns:

        channel_counts = (
            filtered["acquisition_channel"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Channel")
            .reset_index(name="Customers")
        )

        fig = px.bar(
            channel_counts,
            x="Channel",
            y="Customers",
            title="Customer Acquisition Channels",
            color_discrete_sequence=["#4F8EF7"]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info(
            "Acquisition-channel data is not available."
        )


# --------------------------------------------------
# WORLD CUSTOMER DISTRIBUTION MAP
# --------------------------------------------------

st.markdown("---")

st.subheader("World Customer Distribution")

if "country" in filtered.columns:

    map_data = filtered.dropna(
        subset=["country"]
    ).copy()

    map_data["country"] = (
        map_data["country"]
        .astype(str)
        .str.strip()
    )

    map_data = map_data[
        map_data["country"] != ""
    ]

    map_data = (
        map_data.groupby("country")
        .size()
        .reset_index(name="Customers")
    )

    if not map_data.empty:

        fig = px.choropleth(
            map_data,
            locations="country",
            locationmode="country names",
            color="Customers",
            hover_name="country",
            hover_data={
                "Customers": True,
                "country": False
            },
            color_continuous_scale=[
                "#17263E",
                "#7B1420",
                "#E50914"
            ],
            title="Customer Distribution Across Countries"
        )

        fig.update_geos(
            showframe=False,
            showcoastlines=True,
            coastlinecolor=BORDER,
            showland=True,
            landcolor="#17263E",
            showocean=True,
            oceancolor="#0B1120",
            bgcolor="rgba(0,0,0,0)"
        )

        fig.update_layout(
            template="plotly_dark",
            height=550,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                color=MUTED,
                family="Arial"
            ),
            margin=dict(
                l=0,
                r=0,
                t=55,
                b=0
            ),
            coloraxis_colorbar=dict(
                title="Customers"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.caption(
            "The map uses customer country values from the "
            "currently selected Customer Explorer filters."
        )

    else:
        st.info(
            "No valid country values are available to display on the map."
        )

else:
    st.info(
        "The customers table does not contain a country column."
    )


# --------------------------------------------------
# VIEWING ENGAGEMENT
# --------------------------------------------------

st.markdown("---")

st.subheader("Viewing Engagement")


if has_columns(
    viewing,
    ["customer_id", "watch_duration_minutes"]
):

    engagement = viewing.groupby(
        "customer_id",
        as_index=False
    ).agg(
        Total_Watch_Minutes=(
            "watch_duration_minutes",
            "sum"
        ),
        Viewing_Sessions=(
            "customer_id",
            "size"
        )
    )

    engagement["Watch_Hours"] = (
        engagement["Total_Watch_Minutes"] / 60
    )

    a, b = st.columns(2)


    # WATCH HOURS DISTRIBUTION

    with a:

        fig = px.histogram(
            engagement,
            x="Watch_Hours",
            nbins=30,
            title="Distribution of Customer Watch Hours",
            color_discrete_sequence=[RED]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )


    # TOP VIEWERS

    with b:

        top_viewers = engagement.nlargest(
            10,
            "Watch_Hours"
        ).copy()

        fig = px.bar(
            top_viewers.sort_values("Watch_Hours"),
            x="Watch_Hours",
            y="customer_id",
            orientation="h",
            title="Top 10 Customers by Watch Time",
            color_discrete_sequence=["#4F8EF7"]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )


    # CONTENT COMPLETION

    if "completion_percentage" in viewing.columns:

        completion = (
            viewing["completion_percentage"]
            .dropna()
        )

        if not completion.empty:

            st.metric(
                "Average Content Completion",
                f"{completion.mean():.1f}%"
            )

else:

    st.info(
        "Viewing engagement requires customer_id and "
        "watch_duration_minutes in viewing_activity."
    )


# --------------------------------------------------
# SUBSCRIPTION BEHAVIOUR
# --------------------------------------------------

st.markdown("---")

st.subheader("Subscription Behaviour")

sub_left, sub_right = st.columns(2)


# SUBSCRIPTION STATUS

with sub_left:

    if "subscription_status" in subscriptions.columns:

        status_counts = (
            subscriptions["subscription_status"]
            .fillna("Unknown")
            .astype(str)
            .str.title()
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Subscriptions")
        )

        fig = px.pie(
            status_counts,
            names="Status",
            values="Subscriptions",
            title="Subscription Status Mix",
            hole=0.5
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info(
            "Subscription status is not available."
        )


# CUSTOMERS BY SUBSCRIPTION PLAN

with sub_right:

    if has_columns(
        subscriptions,
        ["plan_id", "customer_id"]
    ):

        if has_columns(
            plans,
            ["plan_id", "plan_name"]
        ):

            plan_data = subscriptions.merge(
                plans[
                    ["plan_id", "plan_name"]
                ].drop_duplicates("plan_id"),
                on="plan_id",
                how="left"
            )

        else:
            plan_data = subscriptions.copy()

        plan_label = (
            "plan_name"
            if "plan_name" in plan_data.columns
            else "plan_id"
        )

        plan_counts = (
            plan_data.groupby(plan_label)["customer_id"]
            .nunique()
            .sort_values(ascending=False)
            .reset_index(name="Customers")
        )

        fig = px.bar(
            plan_counts,
            x=plan_label,
            y="Customers",
            title="Customers by Subscription Plan",
            color_discrete_sequence=[RED]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info(
            "Plan information is not available."
        )


# SUBSCRIPTION START TREND

if has_columns(
    subscriptions,
    ["subscription_start_date"]
):

    starts = pd.to_datetime(
        subscriptions["subscription_start_date"],
        errors="coerce"
    ).dropna()

    if not starts.empty:

        monthly_starts = (
            starts.dt.to_period("M")
            .astype(str)
            .value_counts()
            .sort_index()
        )

        trend = (
            monthly_starts
            .rename_axis("Month")
            .reset_index(name="Subscriptions Started")
        )

        fig = px.line(
            trend,
            x="Month",
            y="Subscriptions Started",
            title="Subscription Starts Over Time",
            markers=True
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )


# --------------------------------------------------
# CUSTOMER SEGMENTATION OVERVIEW
# --------------------------------------------------

st.markdown("---")

st.subheader("Customer Segmentation Overview")


if "customer_segment" in filtered.columns:

    segment_counts = (
        filtered["customer_segment"]
        .fillna("Unassigned")
        .astype(str)
        .value_counts()
        .rename_axis("Segment")
        .reset_index(name="Customers")
    )

    seg_left, seg_right = st.columns([1, 1])


    # SEGMENT DISTRIBUTION

    with seg_left:

        fig = px.pie(
            segment_counts,
            names="Segment",
            values="Customers",
            title="Customer Segment Distribution",
            hole=0.55
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )


    # SEGMENT TABLE

    with seg_right:

        st.dataframe(
            segment_counts,
            use_container_width=True,
            hide_index=True
        )

else:

    st.info(
        "The customers table does not contain customer_segment. "
        "Use the Customer Segmentation page for the trained "
        "clustering output."
    )


# --------------------------------------------------
# CUSTOMER RECORDS
# --------------------------------------------------

st.markdown("---")

st.subheader("Customer Records")

display_columns = [
    column
    for column in [
        "customer_id",
        "age",
        "gender",
        "country",
        "city",
        "acquisition_channel",
        "customer_segment",
        "preferred_language"
    ]
    if column in filtered.columns
]


if display_columns:

    st.dataframe(
        filtered[display_columns].head(500),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Displaying up to 500 filtered customer records."
    )

else:

    st.info(
        "No supported customer attributes were found "
        "for the customer table."
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.caption(
    "Data source: local PostgreSQL project database. "
    "Refresh the page after updating source data."
)
