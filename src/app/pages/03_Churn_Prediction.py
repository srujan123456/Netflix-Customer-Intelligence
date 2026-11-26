
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
    page_title="Netflix Intelligence | Churn Prediction",
    page_icon="🎬",
    layout="wide"
)


st.markdown("""
<style>
.stApp {
    background: #0B1120;
    color: #FFFFFF;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1600px;
}

h1, h2, h3, h4 {
    color: #FFFFFF !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #17263E, #111D31);
    border: 1px solid #293B56;
    border-radius: 14px;
    padding: 18px;
    min-height: 120px;
}

[data-testid="stMetricLabel"] {
    color: #91A8C5 !important;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-weight: 750;
}

.dashboard-header {
    background: linear-gradient(110deg, #15243B, #101B2D);
    border-left: 6px solid #E50914;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 25px;
}

.netflix-title {
    font-size: 32px;
    font-weight: 850;
    letter-spacing: 1px;
}

.netflix-red {
    color: #E50914;
}

.subtitle {
    color: #91A8C5;
    font-size: 13px;
    margin-top: 8px;
    letter-spacing: 1px;
}

.info-card {
    background: #111D31;
    border: 1px solid #263851;
    border-radius: 12px;
    padding: 20px;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #263851;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_database_data():

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

        return customers, subscriptions, viewing

    finally:
        connection.close()


def style_chart(fig, height=350):

    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111D31",
        font=dict(
            color="#91A8C5",
            family="Arial"
        ),
        margin=dict(
            l=15,
            r=15,
            t=50,
            b=15
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)"
        )
    )

    fig.update_xaxes(gridcolor="#263851")
    fig.update_yaxes(gridcolor="#263851")

    return fig


def find_status_column(data):

    possible_columns = [
        "subscription_status",
        "status",
        "customer_status",
        "churn_status"
    ]

    for column in possible_columns:
        if column in data.columns:
            return column

    return None


def calculate_churn_status(data, status_column):

    if status_column is None:
        return None

    values = (
        data[status_column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    churn_values = [
        "churned",
        "cancelled",
        "canceled",
        "inactive",
        "terminated"
    ]

    return values.isin(churn_values)


def format_percentage(value):

    if pd.isna(value):
        return "—"

    return f"{value:.1f}%"


st.markdown("""
<div class="dashboard-header">
    <div class="netflix-title">
        <span class="netflix-red">NETFLIX</span> INTELLIGENCE
    </div>
    <div class="subtitle">
        CHURN PREDICTION | CUSTOMER RETENTION & RISK ANALYSIS
    </div>
</div>
""", unsafe_allow_html=True)


st.title("Customer Churn Prediction")

st.write(
    "Understand customer cancellations, subscription behaviour, "
    "and viewing engagement to support retention decisions."
)


if st.button("Refresh Analytics"):

    load_database_data.clear()
    st.rerun()


try:

    customers, subscriptions, viewing = load_database_data()

except Exception as error:

    st.error(f"Database connection or data loading failed: {error}")

    st.info(
        "Check that PostgreSQL is running, the local database is accessible, "
        "and the customers, subscriptions, and viewing_activity tables exist."
    )

    st.stop()


if customers.empty:

    st.warning("The customers table contains no records.")
    st.stop()


if subscriptions.empty:

    st.warning("The subscriptions table contains no records.")
    st.stop()


# --------------------------------------------------
# PREPARE DATA
# --------------------------------------------------

if "customer_id" not in customers.columns:

    st.error("The customers table does not contain customer_id.")

    st.stop()


if "customer_id" not in subscriptions.columns:

    st.error("The subscriptions table does not contain customer_id.")

    st.stop()


total_customers = customers["customer_id"].nunique()

total_subscribers = subscriptions["customer_id"].nunique()

status_column = find_status_column(subscriptions)

if status_column:

    subscriptions["_churned"] = calculate_churn_status(
        subscriptions,
        status_column
    )

    customer_status = (
        subscriptions
        .groupby("customer_id")["_churned"]
        .any()
    )

    churned_customers = int(customer_status.sum())

    retained_customers = int(
        (~customer_status).sum()
    )

    churn_rate = (
        churned_customers / len(customer_status) * 100
        if len(customer_status) else 0
    )

    retention_rate = (
        retained_customers / len(customer_status) * 100
        if len(customer_status) else 0
    )

else:

    churned_customers = None
    retained_customers = None
    churn_rate = None
    retention_rate = None


# --------------------------------------------------
# KPI OVERVIEW
# --------------------------------------------------

st.subheader("Churn Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Customers",
    f"{total_customers:,}"
)

col2.metric(
    "Total Subscribers",
    f"{total_subscribers:,}"
)

col3.metric(
    "Churned Customers",
    f"{churned_customers:,}"
    if churned_customers is not None else "—"
)

col4.metric(
    "Churn Rate",
    format_percentage(churn_rate)
)


st.markdown("---")


# --------------------------------------------------
# CHURN AND RETENTION DISTRIBUTION
# --------------------------------------------------

st.subheader("Churn & Retention Distribution")

if status_column:

    status_data = (
        subscriptions[status_column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
        .value_counts()
        .rename_axis("Subscription Status")
        .reset_index(name="Subscriptions")
    )

    left, right = st.columns(2)

    with left:

        fig = px.pie(
            status_data,
            names="Subscription Status",
            values="Subscriptions",
            title="Subscription Status Distribution",
            hole=0.55
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    with right:

        fig = px.bar(
            status_data,
            x="Subscription Status",
            y="Subscriptions",
            title="Subscriptions by Status",
            color_discrete_sequence=["#E50914"],
            text="Subscriptions"
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    st.metric(
        "Retention Rate",
        format_percentage(retention_rate)
    )

else:

    st.warning(
        "No recognized subscription status column was found. "
        "Churn and retention rates cannot be calculated from the current schema."
    )


st.markdown("---")


# --------------------------------------------------
# SUBSCRIPTION ANALYSIS
# --------------------------------------------------

st.subheader("Subscription Analysis")

left, right = st.columns(2)

with left:

    if "plan_id" in subscriptions.columns:

        plan_data = (
            subscriptions["plan_id"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Plan")
            .reset_index(name="Subscriptions")
        )

        fig = px.bar(
            plan_data,
            x="Plan",
            y="Subscriptions",
            title="Subscriptions by Plan",
            color_discrete_sequence=["#4F8EF7"],
            text="Subscriptions"
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:

        st.info("plan_id is not available in the subscriptions table.")


with right:

    date_column = next(
        (
            column for column in [
                "subscription_start_date",
                "start_date",
                "created_at"
            ]
            if column in subscriptions.columns
        ),
        None
    )

    if date_column:

        date_data = subscriptions.copy()

        date_data[date_column] = pd.to_datetime(
            date_data[date_column],
            errors="coerce"
        )

        date_data = date_data.dropna(
            subset=[date_column]
        )

        if not date_data.empty:

            date_data["Month"] = (
                date_data[date_column]
                .dt.to_period("M")
                .astype(str)
            )

            monthly_data = (
                date_data.groupby("Month")
                .size()
                .reset_index(name="Subscriptions")
            )

            fig = px.line(
                monthly_data,
                x="Month",
                y="Subscriptions",
                title="Subscription Starts Over Time",
                markers=True
            )

            st.plotly_chart(
                style_chart(fig),
                use_container_width=True
            )

        else:

            st.info("No valid subscription dates are available.")

    else:

        st.info("No recognized subscription date column was found.")


st.markdown("---")


# --------------------------------------------------
# CUSTOMER VIEWING ENGAGEMENT
# --------------------------------------------------

st.subheader("Customer Viewing Engagement")

if (
    "customer_id" in viewing.columns
    and "watch_duration_minutes" in viewing.columns
):

    viewing["watch_duration_minutes"] = pd.to_numeric(
        viewing["watch_duration_minutes"],
        errors="coerce"
    )

    engagement = (
        viewing.groupby("customer_id")
        .agg(
            Total_Watch_Minutes=(
                "watch_duration_minutes",
                "sum"
            ),
            Viewing_Sessions=(
                "customer_id",
                "size"
            )
        )
        .reset_index()
    )

    engagement["Watch_Hours"] = (
        engagement["Total_Watch_Minutes"] / 60
    )

    col1, col2 = st.columns(2)

    with col1:

        fig = px.histogram(
            engagement,
            x="Watch_Hours",
            nbins=30,
            title="Distribution of Customer Watch Hours",
            color_discrete_sequence=["#E50914"]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    with col2:

        top_customers = (
            engagement.nlargest(10, "Watch_Hours")
            .sort_values("Watch_Hours")
        )

        fig = px.bar(
            top_customers,
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

    st.metric(
        "Total Watch Hours",
        f"{engagement['Total_Watch_Minutes'].sum() / 60:,.0f}"
    )

else:

    st.info(
        "Viewing engagement requires customer_id and "
        "watch_duration_minutes in viewing_activity."
    )


st.markdown("---")


# --------------------------------------------------
# CHURN CUSTOMER RECORDS
# --------------------------------------------------

st.subheader("Customer Subscription Records")

if status_column:

    churn_records = subscriptions[
        subscriptions["_churned"]
    ].copy()

    if not churn_records.empty:

        customer_details = customers.drop_duplicates(
            subset=["customer_id"]
        )

        churn_records = churn_records.merge(
            customer_details,
            on="customer_id",
            how="left",
            suffixes=("", "_customer")
        )

        st.write(
            f"Found {churn_records['customer_id'].nunique():,} "
            "customers with a churn-related subscription status."
        )

        search_id = st.text_input(
            "Search Customer ID",
            placeholder="Enter a customer ID"
        )

        if search_id.strip():

            churn_records = churn_records[
                churn_records["customer_id"]
                .astype(str)
                .str.contains(
                    search_id.strip(),
                    case=False,
                    na=False
                )
            ]

        preferred_columns = [
            "customer_id",
            status_column,
            "plan_id",
            "country",
            "age",
            "gender",
            "acquisition_channel"
        ]

        display_columns = [
            column for column in preferred_columns
            if column in churn_records.columns
        ]

        if display_columns:

            st.dataframe(
                churn_records[display_columns],
                use_container_width=True,
                hide_index=True
            )

    else:

        st.success(
            "No churn-related subscription statuses were found "
            "in the current database records."
        )

else:

    st.info(
        "Customer churn records will appear here when a recognized "
        "subscription status column is available."
    )


st.markdown("---")


# --------------------------------------------------
# MODEL PREDICTION SECTION
# --------------------------------------------------

st.subheader("Machine Learning Churn Prediction")

st.info(
    "The project notebook contains the trained "
    "gradient_boosting_final_model. Its saved model artifact and "
    "matching preprocessing pipeline have not yet been connected here."
)

st.write(
    "The model prediction section will use the original churn model "
    "and its 70-feature input structure. CLV model artifacts will "
    "not be used for churn prediction."
)

customer_id_input = st.text_input(
    "Enter Customer ID for Model Prediction",
    key="churn_customer_search",
    placeholder="Enter customer ID"
)

if st.button(
    "Run Churn Prediction",
    type="primary"
):

    if not customer_id_input.strip():

        st.warning("Please enter a customer ID.")

    else:

        matching_customer = customers[
            customers["customer_id"]
            .astype(str)
            .eq(customer_id_input.strip())
        ]

        if matching_customer.empty:

            st.error("Customer ID was not found in the customers table.")

        else:

            st.warning(
                "Customer found. Model prediction is not enabled until "
                "the trained churn model and its preprocessing pipeline "
                "are loaded."
            )


st.markdown("---")


# --------------------------------------------------
# MODEL EVALUATION
# --------------------------------------------------

st.subheader("Churn Model Evaluation")

metric_cols = st.columns(5)

metric_names = [
    "Accuracy",
    "Precision",
    "Recall",
    "F1 Score",
    "ROC-AUC"
]

for column, metric_name in zip(metric_cols, metric_names):

    column.metric(
        metric_name,
        "—"
    )

st.caption(
    "Evaluation metrics will be loaded from the actual churn model "
    "test results after the model artifacts are connected."
)


st.markdown("---")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.caption(
    "Netflix Customer Intelligence | Customer Churn Analytics"
)
